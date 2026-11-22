"""Anime Vault native downloads and verified, completed-only local indexing."""
import json
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlencode, parse_qsl, urlunsplit
from app import db
from app.core.season_paths import season_folder_name

_lock = threading.RLock()
_closing = False
DEFAULTS = {
            'source':'https://nyaa.si/?q={query}&f=0&c=0_0','group':'ASW','quality':'1080p',
            'destination':str(Path.home()/'Downloads'/'AnimeVault'),'enabled':False,'start_paused':False,
            'engine':'builtin','download_limit_kib':0,'upload_limit_kib':0,'seed_completed':False}


def settings():
    saved=json.loads(db.get_state('downloads.settings','{}'))
    config={**DEFAULTS, **saved}
    if 'destination' not in saved:
        root=library_root()
        if root:config['destination']=str(Path(root)/'.animevault-downloads')
    # Old connection settings cannot select an external engine after upgrading.
    config['engine']='builtin'
    config['start_paused']=False  # Confirmed submissions start without a second file-selection gate.
    for key in ('url','username','secret'):
        config.pop(key,None)
    return config


def library_root():
    preferred=db.get_state('library.main_root') or db.get_state('merge_destination')
    if preferred and Path(preferred).is_absolute():return preferred
    import os
    roots=[];seen=set()
    for row in db.get_watched_directories():
        if not Path(row['folder_path']).is_absolute():continue
        path=os.path.abspath(row['folder_path']);key=os.path.normcase(path)
        if key not in seen:roots.append(path);seen.add(key)
    # Nested watched folders and staging directories are not additional main
    # libraries. Preserve ambiguity between genuinely separate library roots.
    roots=[root for root in roots if Path(root).name.lstrip('.').casefold()!='animevault-downloads']
    outer=[root for root in roots if not any(root!=other and Path(root).is_relative_to(Path(other)) for other in roots)]
    return outer[0] if len(outer)==1 else None


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
        else:
            from app.core.builtin_torrents import configure_active
            configure_active(config)
        return dict(config)


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


def _save_jobs(items,completed_moves=()):
    from contextlib import closing
    from app.core.download_inventory import signature
    from app.core.file_operations import _operation_lock
    with _operation_lock,closing(db.get_connection()) as conn,conn:
        previous=conn.execute("SELECT value FROM app_state WHERE key='downloads.jobs'").fetchone()
        if signature(json.loads(previous[0]) if previous else [])!=signature(items):
            conn.execute("INSERT INTO app_state VALUES ('downloads.inventory_revision','1') ON CONFLICT(key) DO UPDATE SET value=CAST(value AS INTEGER)+1")
            conn.execute("INSERT OR REPLACE INTO app_state VALUES ('organizer_preview_stale','1')")
        conn.execute("INSERT OR REPLACE INTO app_state VALUES ('downloads.jobs',?)",(json.dumps(items),))
        # Queue acknowledgement and temporary-proof cleanup commit together.
        # Unfinished moves keep their records, including after process interruption.
        if completed_moves:
            active={(r.get('source'),r.get('target')) for job in items for r in (job.get('library_move_intent') or [])}
            settled={job['id'] for job in items if job.get('library_moved') and not job.get('library_move_intent')}
            for row in completed_moves:
                if row.get('job_id') in settled and (row['source'],row['target']) not in active:
                    conn.execute("DELETE FROM file_operations WHERE source=? AND target=? AND kind IN ('MOVE','COPY_MOVE') AND status='COMPLETED'",(row['source'],row['target']))


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
                from app.core.download_queue import status as queue_status
                if not (context and context.get('duplicate_action') in ('replace','redownload') and previous.get('indexed') and queue_status(previous) in ('Completed','Seeding')):
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
        automatic=[j for j in items if j.get('assignment_version')==1 and j.get('move_when_completed') and j.get('indexed') and not j.get('library_moved') and not j.get('library_move_error')]
        if automatic and not cancelled():
            from app.core import download_library
            try:
                plan=download_library.preview()
                identifiers={j['id'] for j in automatic}
                plan['rows']=[r for r in plan['rows'] if r['job_id'] in identifiers]
                for job in automatic:
                    if not any(r['job_id']==job['id'] for r in plan['rows']):job['library_move_error']='Automatic move needs review. '+('; '.join(plan['notes']) or 'No ready files found.')
                _save_jobs(items)
                if plan['rows']:download_library.move(plan,cancelled);changed=True
            except Exception as error:
                for job in automatic:job['library_move_error']=str(error)
                _save_jobs(items)
            items=jobs()
        return items,changed


def _index_completed(item,files):
    if not db.get_franchise(item['fid']):
        raise ValueError('The linked anime was removed. Keep the files and review them manually.')
    from contextlib import closing
    with closing(db.get_connection()) as conn:
        identity=conn.execute('SELECT franchise_id FROM library_series WHERE id=?',(item.get('series_id'),)).fetchone()
    if not identity or identity[0]!=item['fid']:
        raise ValueError('The original series identity changed. Review this download before linking it.')
    if item.get('assignment_version') == 1:
        from app.core.download_assignment import register,remember
        if not item.get('source_episodes') and len(files)==1:
            from app.core.parser import extract_episode_numbers
            original=extract_episode_numbers(files[0].name)
            if len(original)==len(item.get('episode_keys') or []):
                item['source_episodes']=original
                item['release_title']=files[0].stem
        register(item,files)
        remember(item)
    else:
        from app.core.scanner import _update_on_disk_info
        inventory={str(path):(s.st_size,s.st_mtime_ns,str(s.st_dev),str(s.st_ino)) for path in files for s in [path.stat()]}
        _update_on_disk_info(item['fid'],item['root'],inventory=inventory,verified_download=True)
    db.set_state('organizer_preview_stale','1')
    item['verified_files']=[dict(path=str(path),size=path.stat().st_size) for path in files]
    item['integrity_missing']=False
    item['indexed']=True
    item['completed_once']=True
    if item.get('desired')=='stopped':item.update(desired='cancelled',status='Completed',transfer_stopped=True)


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
    target=root/(season_folder_name(season) if season else 'Episodes')
    item={'id':identifier,'engine':'builtin','origin':origin,'fid':fid,'series_id':series_id,'title':series['display_title'],
          'root':str(root),'destination':str(target),'status':'Fetching torrent metadata','progress':0,
          'created':time.time(),'season':season,'desired':'running',
          'selection_confirmed':True,'selected_files':None,'submission_confirmed':False,
          'source_ref':source,'source_identity':source_identity}
    _apply_download_context(item,context)
    from app.core.builtin_torrents import engine
    adapter=engine(config)
    params=adapter.prepare(item,source)
    duplicates=[job for job in items if job.get('torrent_identity')==item['torrent_identity'] and job.get('desired')!='cancelled']
    for previous in duplicates:
        from app.core.download_queue import status as queue_status
        if not (context and context.get('duplicate_action') in ('replace','redownload') and previous.get('indexed') and queue_status(previous) in ('Completed','Seeding')):
            raise ValueError('This torrent already has a tracked download. Use its existing entry.')
        control_builtin(previous['id'],'cancel')  # Detach only; retain old payload.
        items=jobs()
        old=next(j for j in items if j['id']==previous['id']);old['retired_for_redownload']=True
        _save_jobs(items)
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
            if item.get('assignment_version')==1:
                from app.config import VIDEO_EXTENSIONS
                from app.core.parser import extract_episode_numbers
                videos=[e for i,e in enumerate(entries) if i in selected and Path(e['name']).suffix.lower() in VIDEO_EXTENSIONS]
                keys=item.get('episode_keys') or [];source=item.get('source_episodes') or []
                mapping=dict(zip(source,keys)) if len(source)==len(keys) else {}
                bindings={}
                for entry in videos:
                    numbers=extract_episode_numbers(entry['name'])
                    assigned=[mapping[n] for n in numbers] if numbers and all(n in mapping for n in numbers) else keys if len(videos)==1 and len(keys)==1 else []
                    if not assigned:raise ValueError('These files need an explicit episode assignment. Confirm their anime and episodes before changing the selection.')
                    bindings[str(Path(entry['name']))]=assigned
                if not bindings:raise ValueError('Select at least one video file.')
                chosen_keys={k for value in bindings.values() for k in value}
                item['episode_keys']=[k for k in keys if k in chosen_keys]
                if mapping:item['source_episodes']=[n for n,k in zip(source,keys) if k in chosen_keys]
                item['file_bindings']=bindings
            prefixes={key.rsplit(':',1)[0] for key in item.get('episode_keys') or []}
            if len(prefixes)==1 and item.get('assignment_version')!=1:
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
                    source_name=context.get('source'),quality=context.get('quality'),group=context.get('group'),season=context.get('season'),continuous=context.get('continuous'))
        for key in ('assignment_version','source_episodes','local_season_id','file_bindings','move_when_completed','approved_destination','duplicate_action','replacement_files'):
            if key in context:item[key]=context[key]
