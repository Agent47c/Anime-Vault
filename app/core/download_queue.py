"""Queue presentation and controls for Anime Vault downloads."""
import time
import json
from pathlib import Path
from app.core import downloads as service

STATUSES=('Queued','Downloading','Paused','Stopped','Completed','Failed','Incomplete or missing files')


def bulk_action(command,identifiers,cancelled=lambda:False):
    """Reuse durable per-job controls; never remove files in a bulk operation."""
    if command not in ('pause','clear_completed'):raise ValueError('Unknown queue-wide action.')
    done=0;errors=[]
    for identifier in dict.fromkeys(identifiers):
        if cancelled():errors.append('Stopped before the next entry; remaining entries kept.');break
        item=None
        try:
            with service._lock:
                item=next((i for i in service.jobs() if i['id']==identifier),None)
                if item is None:continue
                if command=='clear_completed':
                    if status(item)!='Completed':continue
                    action(identifier,'remove')
                else:
                    seeding=status(item)=='Completed' and (item.get('upload_rate') or 0)>0
                    if item.get('engine')!='builtin' or not (status(item) in ('Downloading','Queued') or seeding):continue
                    action(identifier,'pause')
                done+=1
        except Exception as error:errors.append(f"{item.get('title',identifier) if item else identifier} ({identifier}): {error}")
    return f'{done} queue entries '+('cleared; all files kept.' if command=='clear_completed' else 'paused.')+(' Needs attention: '+'; '.join(errors) if errors else '')


def status(item):
    if item.get('integrity_missing'): return 'Incomplete or missing files'
    if item.get('library_moved') and item.get('indexed'):return 'Completed'
    value=item.get('status','').lower()
    if item.get('desired') in ('cancelled','stopped'): return 'Stopped'
    if 'missingfiles' in value:return 'Incomplete or missing files' if item.get('completed_once') or item.get('indexed') else 'Failed'
    if item.get('indexed') or value in ('indexed','complete','seeding'): return 'Completed'
    if any(word in value for word in ('error','unconfirmed','needs review','not found','failed')):
        return 'Failed'
    if item.get('desired')=='paused' or any(word in value for word in ('paused','stopped','choose files')):
        return 'Paused'
    if any(word in value for word in ('submitting','waiting','metadata','checking','queued','stall')):
        return 'Queued'
    return 'Downloading'


def check_completed_files(item):
    if not (item.get('indexed') or item.get('status')=='Indexed') or not item.get('verified_files'): return
    if time.time()-item.get('integrity_checked',0)<30: return
    item['integrity_checked']=time.time()
    missing=[]
    for file in item['verified_files']:
        path=Path(file['path'])
        try:
            if not path.is_file() or path.stat().st_size!=file['size']: missing.append(str(path))
        except OSError: missing.append(str(path))
    item['integrity_missing']=bool(missing)
    item['integrity_error']='Completed files are missing, inaccessible, or changed. Reconnect the drive or retry the transfer.' if missing else ''


def snapshot():
    with service._lock:
        items=service.jobs()
        for item in items:check_completed_files(item)
        service._save_jobs(items)
        return items


def scan_exclusions():
    from app import db
    roots=json.loads(db.get_state('downloads.unverified_roots','[]'))
    roots+=json.loads(db.get_state('library.removed_roots','[]'))
    library=service.library_root()
    if library:roots.append(str(Path(library)/'.animevault-downloads'))
    for item in service.jobs():
        if not item.get('indexed') and item.get('status')!='Indexed':
            roots.extend(path for path in (item.get('root'),item.get('observed_destination')) if path)
    return [Path(path).resolve() for path in set(roots)]


def retry_external(item):
    """Migrate a legacy queue row in place; keep its old partial files untouched."""
    if item.get('indexed') or item.get('completed_once'):
        raise ValueError('This completed entry is kept as history. Add a new release explicitly if needed.')
    source=item.get('source_ref') or item.get('magnet')
    if not source:
        raise ValueError('The original torrent link was not saved. Add it again from Find Download Files or Paste magnet / torrent.')
    if not service.settings()['enabled']:
        raise ValueError('Enable downloads in Settings first.')
    # Retain the old record as a durable, stopped audit trail. The new job uses a
    # unique folder so another client can never write into our active download.
    items=service.jobs()
    item=next(row for row in items if row['id']==item['id'])
    for other in items:
        if other.get('replaces_external')==item['id']:
            raise ValueError('This entry was already retried with Anime Vault. Use the newer download.')
    context={'title':item.get('release_title'),'episode_keys':item.get('episode_keys') or [],
             'source':item.get('source_name'),'quality':item.get('quality'),'group':item.get('group'),'season':item.get('season')}
    # Ignore only the replaced record during duplicate checks. Other jobs remain
    # protected. Keep its old location excluded from ordinary partial-file scans.
    from app import db
    roots=json.loads(db.get_state('downloads.unverified_roots','[]'))
    if item.get('root'):db.set_state('downloads.unverified_roots',json.dumps(sorted(set(roots+[item['root']]))))
    original=dict(item)
    import re
    from contextlib import closing
    config=service.settings();title=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',item['title']).strip(' .')[:100] or 'Anime'
    root=Path(config['destination']).resolve()/(title+'-'+item['id'][:10])
    with closing(db.get_connection()) as conn,conn:
        conn.execute('INSERT OR IGNORE INTO library_series(franchise_id) VALUES (?)',(item['fid'],))
        series_id=conn.execute('SELECT id FROM library_series WHERE franchise_id=?',(item['fid'],)).fetchone()[0]
    item.update(engine='builtin',series_id=series_id,legacy_destination=original.get('destination'),root=str(root),destination=str(root/(f"Season {item['season']:02}" if item.get('season') else 'Episodes')),desired='running',selection_confirmed=True,selected_files=None,indexed=False,submission_confirmed=False,status='Fetching torrent metadata',source_ref=source)
    from app.core.builtin_torrents import engine
    try:
        adapter=engine(config);params=adapter.prepare(item,source)
        if any(other['id']!=item['id'] and other.get('torrent_identity')==item['torrent_identity'] and other.get('desired')!='cancelled' for other in items):raise ValueError('This torrent already has another native entry. Use that entry instead.')
    except Exception as error:
        item.clear();item.update(original,status='Needs review: Native retry failed: '+str(error));service._save_jobs(items);raise
    service._save_jobs(items)
    try:adapter.attach(item,params);item['submission_confirmed']=True
    except Exception as error:item['status']='Needs review: '+str(error);raise
    finally:service._save_jobs(items)
    return 'Existing entry converted to Anime Vault and started. Previous files were kept.'


def action(identifier,command):
    if command not in ('pause','resume','stop','retry','remove'):
        raise ValueError('Unknown queue action.')
    with service._lock:
        items=service.jobs();item=next((i for i in items if i['id']==identifier),None)
        if item is None: raise ValueError('Download entry no longer exists.')
        if item.get('library_moved') and command not in ('remove','stop'):raise ValueError('These files are in the library. Open their anime details to play or repair them.')
        if item.get('engine')!='builtin':
            if command=='retry': return retry_external(item)
            if command not in ('remove','stop'):
                raise ValueError('This entry belongs to the removed external client. Use Retry to create an Anime Vault download.')
        if command in ('resume','retry'):
            item.pop('retry_after',None);item['selection_confirmed']=True;service._save_jobs(items)
        builtin=item.get('engine')=='builtin'
        if builtin:
            if command in ('retry','resume'):
                from app.core.builtin_torrents import restart_failed
                restart_failed()
            if command=='remove':
                if service.settings()['enabled'] and item.get('desired')!='cancelled':
                    service.control_builtin(identifier,'cancel')
            else:
                if command=='retry' or (command=='resume' and item.get('desired')=='cancelled'):
                    item.update(indexed=False,integrity_missing=False,desired='paused')
                    service._save_jobs(items)
                    from app.core.builtin_torrents import engine
                    engine(service.settings()).recheck(item)
                    item['submission_confirmed']=True;service._save_jobs(items)
                service.control_builtin(identifier,'pause' if command=='stop' else 'resume' if command=='retry' else command)
        # Legacy entries are local history only; no external API requests.
        items=service.jobs();item=next(i for i in items if i['id']==identifier)
        if command=='remove':
            if not item.get('indexed') and item.get('status')!='Indexed' and item.get('root'):
                from app import db
                roots=json.loads(db.get_state('downloads.unverified_roots','[]'))
                db.set_state('downloads.unverified_roots',json.dumps(sorted(set(roots+[item['root']]))))
            items=[i for i in items if i['id']!=identifier]
        else:
            if command in ('retry','resume'): item['desired']='running'
            if command=='stop': item['desired']='stopped';item['status']='Stopped'
            if command=='pause': item['desired']='paused';item['status']='Paused'
            if command=='retry': item.update(status='Queued',indexed=False,integrity_missing=False)
        service._save_jobs(items)
        return 'Entry removed. Downloaded files were kept.' if command=='remove' else command.capitalize()+' requested.'


def recycle_files(identifier):
    """Explicit file deletion is separate from removing a queue entry."""
    with service._lock:
        item=next(i for i in service.jobs() if i['id']==identifier)
        if item.get('library_moved'):raise ValueError('These files are in the library. Use Delete files in anime details to review them.')
        root=Path(item['root'])
        destination=Path(item['destination'])
        if root.is_symlink() or root.is_junction() or destination.is_symlink() or destination.is_junction() or root.resolve()!=destination.resolve().parent:
            raise ValueError('Download location changed. Review the folder manually.')
        if not root.name.endswith('-'+item['id'][:10]):
            raise ValueError('This is not an isolated download folder. Use library file review.')
        inventory=item.get('download_files') or []
        if not inventory and item.get('verified_files'):
            inventory=[dict(name=str(Path(f['path']).relative_to(destination)),size=f['size']) for f in item['verified_files']]
        if not inventory:raise ValueError('No known download-file inventory yet. Wait for metadata or choose Files first; unknown files were kept.')
        owned=[]
        for entry in inventory:
            path=destination/entry['name']
            if path.is_symlink() or path.is_junction() or not path.resolve().is_relative_to(destination.resolve()):
                raise ValueError('Download file location changed. Review it manually.')
            for parent in path.parents:
                if parent==destination.parent:break
                if parent.is_symlink() or parent.is_junction():raise ValueError('Download folder contains a changed link or junction.')
            if path.is_file() and path.stat().st_size>entry.get('size',path.stat().st_size):
                raise ValueError('Download file size changed. Review the file manually.')
            if path.is_file():owned.append(path)
        if item.get('desired')!='cancelled': action(identifier,'stop')
        if item.get('engine')=='builtin':
            current=next(i for i in service.jobs() if i['id']==identifier)
            if current.get('desired')!='cancelled': service.control_builtin(identifier,'cancel')

        if root.exists():
            from app.core.file_operations import recycle_file
            from app.core.recycle_bin import send2trash
            for path in owned:
                recycle_file(path,recycle=send2trash)
        items=service.jobs();item=next(i for i in items if i['id']==identifier)
        item.update(desired='stopped',status='Stopped',integrity_missing=True,
                    integrity_error='Download files were moved to the Recycle Bin.')
        service._save_jobs(items)
        from app import db
        db.set_state('organizer_preview_stale','1')
        return 'Files moved to Recycle Bin. Library history and the queue record were kept.'
