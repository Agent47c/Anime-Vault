"""Anime Vault native downloads and verified, completed-only local indexing."""
import json
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlencode, parse_qsl, urlunsplit
from app import db

_lock = threading.RLock()
_closing = False
DEFAULTS = {
            'source':'https://nyaa.si/?q={query}&f=0&c=0_0','group':'ASW','quality':'1080p',
            'destination':str(Path.home()/'Downloads'/'AnimeVault'),'enabled':False,'start_paused':False,
            'engine':'builtin','download_limit_kib':0,'upload_limit_kib':0,'seed_completed':False}


def settings():
    config={**DEFAULTS, **json.loads(db.get_state('downloads.settings','{}'))}
    if config['destination']==DEFAULTS['destination']:
        root=library_root()
        if root:config['destination']=str(Path(root)/'.animevault-downloads')
    # Old connection settings cannot select an external engine after upgrading.
    config['engine']='builtin'
    config['start_paused']=False  # Confirmed submissions start without a second file-selection gate.
    for key in ('url','username','secret'):
        config.pop(key,None)
    return config


def library_root():
    preferred=db.get_state('merge_destination')
    if preferred and Path(preferred).is_absolute():return preferred
    roots=db.get_watched_directories()
    return roots[0]['folder_path'] if len(roots)==1 else None


def validate_url(value, local=False):
    parsed=urlsplit(value)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Use an http/https URL without credentials in the address.')
    if local and parsed.hostname not in ('localhost','127.0.0.1','::1'):
        raise ValueError('Use localhost or 127.0.0.1 for a local URL.')
    if local and (parsed.query or parsed.fragment):
        raise ValueError('Use a base URL without a query or fragment.')
    return value.rstrip('/')


def save_settings(config,new_password=None):
    with _lock:
        config={**settings(),**config}
        config['start_paused']=False
        if config['engine'] not in ('qbittorrent','builtin'):
            raise ValueError('Anime Vault uses its built-in downloader.')
        config['engine']='builtin'
        for key in ('url','username','secret'):
            config.pop(key,None)
        for key in ('download_limit_kib','upload_limit_kib'):
            value=int(config[key])
            if value<0 or value>1000000:
                raise ValueError('Speed limits must be between 0 and 1,000,000 KiB/s.')
            config[key]=value
        search_url(config['source'],'test')
        if not Path(config['destination']).is_absolute():
            raise ValueError('Choose an absolute download destination.')
        db.set_state('downloads.settings',json.dumps(config))
        existing=jobs()
        if any(item.get('retry_after') for item in existing):
            for item in existing:item.pop('retry_after',None)
            _save_jobs(existing)
        if not config['enabled']:
            shutdown_builtin()


def search_url(template,query):
    validate_url(template)
    if template.count('{query}') != 1:
        raise ValueError('Search URL must contain {query} once, in a query parameter.')
    parsed=urlsplit(template)
    if '{query}' in parsed.netloc or '{query}' in parsed.path or '{query}' in parsed.fragment:
        raise ValueError('Place {query} in the search query parameter.')
    values=[(key,value.replace('{query}',query)) for key,value in parse_qsl(parsed.query,keep_blank_values=True)]
    return urlunsplit((parsed.scheme,parsed.netloc,parsed.path,urlencode(values),parsed.fragment))


def make_query(title,episode='',group='',quality=''):
    group=group.strip().strip('[]')
    return ' '.join(value for value in (f'[{group}]' if group else '',title.strip(),str(episode).strip(),quality.strip()) if value)


def test_connection(config,new_password=None):
    config={**settings(),**config,'engine':'builtin'}
    from app.core.builtin_torrents import EngineClient
    probe=EngineClient(config,network=False)
    try: version=probe.call('version')
    finally: probe.close()
    return 'Anime Vault downloader ready · libtorrent '+version


def jobs():
    return json.loads(db.get_state('downloads.jobs','[]'))


def _save_jobs(items):
    db.set_state('downloads.jobs',json.dumps(items))


def add_download(fid,source,season=0,origin=None,context=None):
    """Only explicitly submitted torrents are tracked; no unrelated client jobs."""
    with _lock:
        if _closing:
            raise ValueError('Anime Vault is closing. Reopen it to add downloads.')
        config=settings()
        items=jobs()
        source_identity=None
        if source.lower().startswith('magnet:?'):
            from app.core.magnet_capture import validate
            source_identity=validate(source)['identity']
        for previous in items:
            if origin and previous.get('origin')==origin:
                if previous.get('engine')!='builtin':
                    raise ValueError('This link belongs to an older external-client entry. Open Downloads and use Retry to add it to Anime Vault.')
                if previous.get('season') is not None and previous['season']!=season:
                    raise ValueError('This link was already assigned to another season. Review its existing download.')
                if context and previous.get('episode_keys') and set(previous['episode_keys'])!=set(context.get('episode_keys') or []):
                    raise ValueError('This link was already assigned to different episodes. Review the existing download.')
                continue
            if previous.get('desired')=='cancelled': continue
            if source_identity and previous.get('source_identity')==source_identity:
                raise ValueError('This torrent is already tracked. Open its existing download.')
            from app.core.download_queue import status as queue_status
            if context and previous['fid']==fid and queue_status(previous) in ('Queued','Downloading','Paused'):
                if set(context.get('episode_keys') or [])&set(previous.get('episode_keys') or []):
                    raise ValueError('Some selected episodes are already queued.')
        destination=_add_builtin(fid,source,season,origin,config,context,source_identity)
        current=jobs()
        item=next(j for j in current if j['destination']==destination)
        item.update(source_identity=source_identity,source_ref=source,season=season)
        _apply_download_context(item,context)
        _save_jobs(current)
        return destination


def _completed_files(item,info,entries):
    target=Path(item['destination']).resolve()
    if Path(info['save_path']).resolve()!=target:
        raise ValueError('The download location differs from the reviewed destination. Review this download.')
    if not entries:
        raise ValueError('The torrent has no file inventory yet.')
    from app.config import VIDEO_EXTENSIONS
    files=[]
    for entry in entries:
        if entry.get('priority',1)==0:
            continue
        path=(target/entry['name']).resolve()
        if path==target or target not in path.parents:
            raise ValueError('A torrent file is outside the download destination.')
        if entry.get('progress',0)<1:
            raise ValueError('Some selected files are still downloading.')
        if path.suffix.lower() in VIDEO_EXTENSIONS:
            stat=path.stat()
            if stat.st_size!=entry['size']:
                raise ValueError('A completed file is missing or has an unexpected size.')
            files.append(path)
    if not files:
        raise ValueError('No completed video files found. Archives require manual extraction and review.')
    return files


def poll(cancelled=lambda:False):
    """Worker-only polling; completed jobs are idempotent across restarts."""
    with _lock:
        if _closing:
            return jobs(),False
        config=settings();items=jobs();changed=False
        from app.core.download_queue import check_completed_files
        for item in items: check_completed_files(item)
        if not config['enabled']:
            return items,False
        builtin=[item for item in items if item.get('engine')=='builtin' and item.get('desired')!='cancelled' and item.get('retry_after',0)<=time.time()]
        if builtin:
            from app.core.builtin_torrents import engine
            try:adapter=engine(config)
            except Exception as error:
                for item in builtin:item.update(status='Failed: '+str(error),retry_after=time.time()+60)
                _save_jobs(items);raise
            for item in builtin:
                if cancelled(): break
                try:
                    snapshot=adapter.snapshot(item)
                    item['submission_confirmed']=True
                    if snapshot.get('files'):item['download_files']=[dict(name=e['name'],size=e['size'],priority=e.get('priority',1)) for e in snapshot['files']]
                    item.update({k:v for k,v in snapshot.items() if k not in ('files','complete')})
                    if snapshot.get('complete') and not item.get('indexed'):
                        item['download_files']=[dict(name=e['name'],size=e['size'],priority=e.get('priority',0)) for e in snapshot['files']]
                        files=_completed_files(item,{'save_path':item['destination']},snapshot['files'])
                        _index_completed(item,files)
                        item['indexed']=True;changed=True
                        adapter.snapshot(item)  # Apply the completed seeding policy.
                except Exception as error:
                    item.update(status='Needs review: '+str(error),retry_after=time.time()+30)
            adapter.save()
            _save_jobs(items)
        # External-client history stays visible but is never polled or submitted.
        for item in items:
            if item.get('engine')!='builtin' and not item.get('indexed'):
                item['status']='Needs review: external client removed. Retry with Anime Vault or remove entry; files are kept.'
                item.pop('retry_after',None)
        _save_jobs(items)
        return items,changed


def _index_completed(item,files):
    if not db.get_franchise(item['fid']):
        raise ValueError('The linked anime was removed. Keep the files and review them manually.')
    from contextlib import closing
    with closing(db.get_connection()) as conn:
        identity=conn.execute('SELECT franchise_id FROM library_series WHERE id=?',(item.get('series_id'),)).fetchone()
    if not identity or identity[0]!=item['fid']:
        raise ValueError('The original series identity changed. Review this download before linking it.')
    from app.core.scanner import _update_on_disk_info
    inventory={str(path):(s.st_size,s.st_mtime_ns,str(s.st_dev),str(s.st_ino)) for path in files for s in [path.stat()]}
    _update_on_disk_info(item['fid'],item['root'],inventory=inventory)
    db.set_state('organizer_preview_stale','1')
    item['verified_files']=[dict(path=str(path),size=path.stat().st_size) for path in files]
    item['integrity_missing']=False
    item['indexed']=True
    item['completed_once']=True


def _add_builtin(fid,source,season,origin,config,context=None,source_identity=None):
    if not config['enabled']:
        raise ValueError('Save and enable downloads first.')
    items=jobs()
    if origin:
        previous=next((job for job in items if job.get('origin')==origin),None)
        if previous:
            if previous['fid']!=fid:
                raise ValueError('This link is already associated with another anime.')
            if previous.get('desired')=='cancelled':
                raise ValueError('This download was cancelled. Add it again from Downloads if needed.')
            if not previous.get('submission_confirmed'):
                raise ValueError('The previous submission needs review. Use Retry on its existing Downloads entry; do not add it twice.')
            return previous['destination']
    series=db.get_franchise(fid)
    if not series:
        raise ValueError('Choose an anime from the library first.')
    from contextlib import closing
    with closing(db.get_connection()) as conn,conn:
        conn.execute('INSERT OR IGNORE INTO library_series(franchise_id) VALUES (?)',(fid,))
        series_id=conn.execute('SELECT id FROM library_series WHERE franchise_id=?',(fid,)).fetchone()[0]
    import re
    identifier=uuid.uuid4().hex
    title=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',series['display_title']).strip(' .')[:100] or 'Anime'
    root=Path(config['destination']).resolve()/(title+'-'+identifier[:10])
    target=root/(f'Season {season:02}' if season else 'Episodes')
    item={'id':identifier,'engine':'builtin','origin':origin,'fid':fid,'series_id':series_id,'title':series['display_title'],
          'root':str(root),'destination':str(target),'status':'Fetching torrent metadata','progress':0,
          'created':time.time(),'season':season,'desired':'running',
          'selection_confirmed':True,'selected_files':None,'submission_confirmed':False,
          'source_ref':source,'source_identity':source_identity}
    _apply_download_context(item,context)
    from app.core.builtin_torrents import engine
    adapter=engine(config)
    params=adapter.prepare(item,source)
    if any(job.get('torrent_identity')==item['torrent_identity'] and job.get('desired')!='cancelled' for job in items):
        raise ValueError('This torrent already has a tracked download. Use its existing entry.')
    items.append(item)
    _save_jobs(items)  # Durable identity and destination before native submission.
    try:
        adapter.attach(item,params)
        item['submission_confirmed']=True
    except Exception as error:
        item['status']='Needs review: '+str(error)
        raise
    finally:
        _save_jobs(items)
    return item['destination']


def builtin_files(identifier):
    with _lock:
        if _closing: raise ValueError('Anime Vault is closing.')
        if not settings()['enabled']: raise ValueError('Enable and save downloads first.')
        items=jobs();item=next(j for j in items if j['id']==identifier and j.get('engine')=='builtin')
        if item.get('library_moved'):raise ValueError('These files have moved to the library. Use the anime details page.')
        from app.core.builtin_torrents import engine
        files=engine(settings()).snapshot(item)['files']
        if files:
            item['download_files']=[dict(name=e['name'],size=e['size'],priority=e.get('priority',1)) for e in files];_save_jobs(items)
        return files


def control_builtin(identifier,action,selected=None):
    with _lock:
        if _closing: raise ValueError('Anime Vault is closing.')
        if not settings()['enabled']: raise ValueError('Enable and save downloads first.')
        items=jobs()
        item=next(j for j in items if j['id']==identifier and j.get('engine')=='builtin')
        if action not in ('pause','resume','cancel','files'):
            raise ValueError('Unknown download action.')
        if item.get('desired')=='cancelled':
            raise ValueError('This download was cancelled. Its files have been kept.')
        from app.core.builtin_torrents import engine
        adapter=engine(settings())
        if action=='files':
            entries=adapter.snapshot(item)['files']
            if not entries:
                raise ValueError('Torrent metadata is still loading. Try again shortly.')
            if not selected or any(type(i) is not int or i<0 or i>=len(entries) for i in selected):
                raise ValueError('Select at least one valid file.')
            if item.get('indexed'):
                raise ValueError('These files were already indexed. Start a separate download to change the selection.')
            item.update(selected_files=sorted(set(selected)),selection_confirmed=True,desired='running')
            prefixes={key.rsplit(':',1)[0] for key in item.get('episode_keys') or []}
            if len(prefixes)==1:
                from app.core.parser import extract_episode_numbers
                prefix=next(iter(prefixes))
                mapped={prefix+':'+str(number) for i in selected for number in extract_episode_numbers(entries[i]['name'])}
                known=set(item['episode_keys'])&mapped
                if known:item['episode_keys']=sorted(known)
        elif action=='resume':
            item['selection_confirmed']=True
            item['desired']='running'
        else:
            item['desired']='cancelled' if action=='cancel' else 'paused'
        _save_jobs(items)  # User choice must survive a crash before the native call.
        snapshot=adapter.snapshot(item)
        item.update({k:v for k,v in snapshot.items() if k not in ('files','complete')})
        _save_jobs(items)
        return item['status']


def shutdown_builtin():
    with _lock:
        from app.core.builtin_torrents import shutdown
        shutdown()


def begin_shutdown():
    global _closing
    _closing=True


def _apply_download_context(item,context):
    if context:
        item.update(release_title=context.get('title'),episode_keys=context.get('episode_keys') or [],
                    source_name=context.get('source'),quality=context.get('quality'),group=context.get('group'),season=context.get('season'))
