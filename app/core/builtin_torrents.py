"""Libtorrent adapter. Call from download IO workers under downloads._lock.

No native handles cross into Qt. Magnets fetch metadata in upload-only mode
until paths have been validated and the reviewed file selection is applied.
"""
import os
import time
from pathlib import Path, PureWindowsPath
from app import db


def library():
    try:
        import libtorrent as lt
        return lt
    except ImportError as error:
        raise ValueError('Anime Vault downloader is unavailable. Install the project requirements, then restart the app.') from error


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    with temporary.open('wb') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def identity(hashes):
    return str(hashes.v1) if hashes.has_v1() else str(hashes.v2)


def listen_port():
    import socket
    # libtorrent interprets port 0 as disabled, so reserve an OS-chosen port
    # briefly rather than competing with qBittorrent's usual fixed port.
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0))
        return probe.getsockname()[1]


def safe_files(info):
    """Reject escapes, symlinks and Windows aliases before enabling payload IO."""
    lt = library()
    files = info.files()
    result, seen = [], set()
    if files.num_files() > 50000:
        raise ValueError('This torrent contains too many files to index safely. Choose a smaller torrent.')
    for i in range(files.num_files()):
        name = files.file_path(i).replace('\\', '/')
        parts = name.split('/')
        windows = PureWindowsPath(name)
        if (windows.is_absolute() or windows.drive or name.startswith('/') or
                any(p in ('', '.', '..') or p.endswith((' ', '.')) or
                    any(c in p for c in ':<>"|?*\x00') or
                    p.split('.')[0].upper() in {'CON','PRN','AUX','NUL',
                        *('COM'+str(n) for n in range(1,10)), *('LPT'+str(n) for n in range(1,10))}
                    for p in parts)):
            raise ValueError('Unsafe torrent filename. No files were selected for download.')
        if files.file_flags(i) & lt.file_storage.flag_symlink:
            raise ValueError('Torrent symlinks are not supported.')
        if name.casefold() in seen:
            raise ValueError('Torrent filenames collide on Windows.')
        seen.add(name.casefold())
        result.append({'index':i,'name':name,'size':files.file_size(i)})
    return result


def source_parameters(source):
    lt = library()
    if source.lower().startswith('magnet:?'):
        from app.core.magnet_capture import validate
        validate(source)
        return lt.parse_magnet_uri('magnet:'+source.split(':',1)[1])
    path = Path(source)
    if path.suffix.lower() != '.torrent' or not path.is_file() or path.stat().st_size > 16*1024*1024:
        raise ValueError('Choose a local .torrent file smaller than 16 MB.')
    params = lt.add_torrent_params()
    params.ti = lt.torrent_info(str(path))
    safe_files(params.ti)
    return params


class Engine:
    def __init__(self, config, network=True):
        self.lt = library()
        self.folder = Path(db.DATA_DIR)/'builtin-downloads'
        self.handles = {}
        self.configured = {}
        self.waiting = set()
        self.last_save = 0
        port=listen_port()
        self.session = self.lt.session({
            'listen_interfaces':f'0.0.0.0:{port},[::]:{port}' if network else f'127.0.0.1:{port}',
            'enable_dht':network, 'enable_lsd':network,
            'enable_upnp':False, 'enable_natpmp':False,
            'ignore_limits_on_local_network':False,
            'connections_limit':100, 'active_downloads':3, 'active_seeds':2,
            'alert_mask':int(self.lt.alert.category_t.status_notification |
                             self.lt.alert.category_t.storage_notification |
                             self.lt.alert.category_t.error_notification),
        })
        self.configure(config)

    def configure(self, config):
        self.session.apply_settings({
            'download_rate_limit':int(config.get('download_limit_kib',0))*1024,
            'upload_rate_limit':int(config.get('upload_limit_kib',0))*1024,
        })
        self.seed = bool(config.get('seed_completed',False))

    def prepare(self, item, source):
        params = source_parameters(source)
        key = identity(params.ti.info_hashes() if params.ti else params.info_hashes)
        if any(identity(h.info_hashes()) == key for h in self.handles.values()):
            raise ValueError('This torrent is already in the built-in downloader. Use its existing download.')
        item['torrent_identity'] = key
        if params.ti:
            atomic_write(self.folder/(item['id']+'.torrent'), Path(source).read_bytes())
        else:
            item['magnet'] = source
        return params

    def attach(self, item, params=None):
        if item['id'] in self.handles:
            return self.handles[item['id']]
        lt = self.lt
        resume = self.folder/(item['id']+'.resume')
        if params is None:
            try:
                params = lt.read_resume_data(resume.read_bytes())
                key = identity(params.ti.info_hashes() if params.ti else params.info_hashes)
                if key != item['torrent_identity']:
                    raise ValueError('Saved torrent identity does not match.')
            except (OSError, RuntimeError, ValueError):
                params = source_parameters(item.get('magnet') or str(self.folder/(item['id']+'.torrent')))
        key = identity(params.ti.info_hashes() if params.ti else params.info_hashes)
        if key != item['torrent_identity']:
            raise ValueError('Torrent identity changed. Download remains stopped.')
        if params.ti:
            safe_files(params.ti)
        target = Path(item['destination'])
        target.mkdir(parents=True, exist_ok=True)
        params.save_path = str(target.resolve())
        # Ignore native resume priorities/paused state in favour of durable user choices.
        params.flags &= ~lt.torrent_flags.auto_managed
        params.flags |= lt.torrent_flags.duplicate_is_error
        params.flags |= lt.torrent_flags.upload_mode
        params.flags &= ~lt.torrent_flags.paused
        if params.ti:
            params.file_priorities = [0]*params.ti.num_files()
        handle = self.session.add_torrent(params)
        self.handles[item['id']] = handle
        return handle

    def configure_handle(self, item, handle):
        info = handle.torrent_file()
        if info is None:
            return []
        entries = safe_files(info)
        key = (item.get('selection_confirmed',False), tuple(item.get('selected_files') or []),
               item.get('desired','paused'), self.seed, item.get('indexed',False))
        if self.configured.get(item['id']) != key:
            handle.pause()
            priorities = [0]*len(entries)
            if item.get('selection_confirmed'):
                indices = item.get('selected_files')
                if indices is None:
                    indices = list(range(len(entries)))
                if any(type(i) is not int or i < 0 or i >= len(entries) for i in indices):
                    raise ValueError('Invalid torrent file selection.')
                for i in indices:
                    priorities[i] = 4
            handle.prioritize_files(priorities)
            handle.unset_flags(self.lt.torrent_flags.upload_mode)
            if item.get('selection_confirmed') and item.get('desired') == 'running' and (self.seed or not item.get('indexed')):
                handle.resume()
            self.configured[item['id']] = key
        return entries

    def drain(self):
        for alert in self.session.pop_alerts():
            if isinstance(alert, self.lt.save_resume_data_alert):
                identifier = next((key for key,h in self.handles.items() if h == alert.handle), None)
                if identifier:
                    atomic_write(self.folder/(identifier+'.resume'), bytes(self.lt.write_resume_data_buf(alert.params)))
                    self.waiting.discard(identifier)
            elif isinstance(alert, self.lt.save_resume_data_failed_alert):
                self.waiting.difference_update(key for key,h in self.handles.items() if h == alert.handle)

    def snapshot(self, item):
        if item.get('desired') == 'cancelled':
            self.remove(item['id'])
            return {'status':'Cancelled — files kept','progress':item.get('progress',0),'files':[],
                    'download_rate':0,'upload_rate':0,'eta':None}
        handle = self.attach(item)
        try:
            entries = self.configure_handle(item, handle)
        except Exception:
            handle.pause()
            raise
        status = handle.status()
        if not entries:
            return {'status':'Fetching torrent metadata','progress':0,'files':[]}
        if not (self.folder/(item['id']+'.torrent')).exists():
            atomic_write(self.folder/(item['id']+'.torrent'), bytes(self.lt.bencode(self.lt.create_torrent(handle.torrent_file()).generate())))
        progress = handle.file_progress()
        # Native priority changes are asynchronous. Completion decisions must
        # use the durable selection, never the previous native priority list.
        selected=item.get('selected_files')
        priorities=[4 if item.get('selection_confirmed') and (selected is None or i in selected) else 0 for i in range(len(entries))]
        for entry in entries:
            i=entry['index']
            entry.update(priority=priorities[i],progress=(progress[i]/entry['size'] if entry['size'] else 1))
        chosen = [entry for entry in entries if entry['priority'] > 0]
        total = sum(e['size'] for e in chosen)
        done = sum(min(e['size'], progress[e['index']]) for e in chosen)
        checking = status.state in (self.lt.torrent_status.checking_files,self.lt.torrent_status.checking_resume_data,self.lt.torrent_status.allocating)
        error = status.errc.message() if status.errc.value() else ''
        complete = bool(chosen) and all(e['progress'] >= 1 for e in chosen) and not checking and not error
        if complete and not self.seed:
            handle.pause()  # Seeding opt-out also applies when library indexing fails.
        if error: state='Error: '+error
        elif checking: state='Checking files'
        elif not item.get('selection_confirmed'): state='Choose files to start'
        elif complete: state='Seeding' if self.seed and item.get('desired')=='running' else 'Complete'
        elif item.get('desired')=='paused': state='Paused'
        else: state='Downloading'
        remaining=max(0,total-done)
        return {'status':state,'progress':done/total if total else 0,'files':entries,'downloaded':done,'total':total,
                'complete':complete,'download_rate':status.download_payload_rate,
                'upload_rate':status.upload_payload_rate,'eta':int(remaining/status.download_payload_rate) if status.download_payload_rate else None}

    def save(self):
        self.drain()
        if time.monotonic()-self.last_save < 30:
            return
        self.last_save = time.monotonic()
        for key,handle in self.handles.items():
            if key not in self.waiting:
                handle.save_resume_data(self.lt.save_resume_flags_t.save_info_dict)
                self.waiting.add(key)

    def remove(self, identifier):
        handle=self.handles.pop(identifier,None)
        if handle is not None:
            self.session.remove_torrent(handle)  # Deliberately no delete_files flag.
        self.configured.pop(identifier,None)
        self.waiting.discard(identifier)

    def recheck(self,item):
        handle=self.attach(item)
        handle.force_recheck();handle.resume()
        self.configured.pop(item['id'],None)

    def close(self):
        self.session.pause()
        for key,handle in self.handles.items():
            handle.save_resume_data(self.lt.save_resume_flags_t.save_info_dict | self.lt.save_resume_flags_t.flush_disk_cache)
            self.waiting.add(key)
        end=time.monotonic()+8
        try:
            while self.waiting and time.monotonic()<end:
                self.drain()
                time.sleep(.02)
        finally:
            self.handles.clear()
            self.session=None


class EngineClient:
    """Private pipe to a native-only helper; never load libtorrent into Qt."""
    def __init__(self,config,network=True):
        import subprocess,sys,queue,threading
        self.folder=Path(db.DATA_DIR)/'builtin-downloads'
        self.responses=queue.Queue()
        executable=Path(sys.executable)
        if executable.name.lower()=='pythonw.exe' and executable.with_name('python.exe').exists():
            executable=executable.with_name('python.exe')
        command=([str(executable),'--builtin-torrent-host'] if getattr(sys,'frozen',False) else
                 [str(executable),str(Path(__file__).resolve().parents[2]/'builtin_torrent_host.py')])
        self.process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                                      creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.reader=threading.Thread(target=self._read,daemon=True)
        self.reader.start()
        try:
            self.call('init',config=config,network=network,folder=str(db.DATA_DIR))
        except Exception:
            self.process.kill();self.process.wait(timeout=5)
            raise

    def _read(self):
        import json,struct
        try:
            while True:
                raw=self.process.stdout.read(4)
                if len(raw)!=4: break
                size=struct.unpack('<I',raw)[0]
                if size>32*1024*1024: break
                payload=self.process.stdout.read(size)
                if len(payload)!=size: break
                self.responses.put(json.loads(payload))
        finally:
            self.responses.put({'error':'Built-in engine stopped. Your files are kept; restart the app to recover downloads.'})

    def call(self,command,**values):
        import json,struct,queue
        try:
            payload=json.dumps(dict(command=command,**values)).encode('utf-8')
            self.process.stdin.write(struct.pack('<I',len(payload))+payload)
            self.process.stdin.flush()
            result=self.responses.get(timeout=20)
        except (OSError,ValueError,queue.Empty) as error:
            self.process.kill();self.process.wait(timeout=5)
            raise ValueError('Built-in engine is unavailable. Restart Anime Vault to recover downloads.') from error
        if 'error' in result: raise ValueError(result['error'])
        return result.get('value')

    def configure(self,config): self.call('configure',config=config)
    def prepare(self,item,source): item.update(self.call('prepare',item=item,source=source))
    def attach(self,item,params=None): self.call('attach',item=item)
    def snapshot(self,item): return self.call('snapshot',item=item)
    def save(self): self.call('save')
    def recheck(self,item): self.call('recheck',item=item)
    def close(self):
        if self.process.poll() is None:
            try: self.call('close')
            finally:
                try: self.process.wait(timeout=10)
                except Exception: self.process.kill();self.process.wait(timeout=5)
        self.reader.join(timeout=1)
        for stream in (self.process.stdin,self.process.stdout):
            try: stream.close()
            except OSError: pass  # A crashed Windows child can leave a broken pipe.


_engine=None


def engine(config):
    global _engine
    if _engine is None:
        _engine=EngineClient(config)
    else:
        _engine.configure(config)
    return _engine


def active():
    return _engine is not None


def restart_failed():
    global _engine
    if _engine is not None and _engine.process.poll() is not None:
        _engine.close();_engine=None


def shutdown():
    global _engine
    if _engine is not None:
        try:
            _engine.close()
        finally:
            _engine=None
