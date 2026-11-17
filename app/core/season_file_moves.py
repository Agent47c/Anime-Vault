"""Explicit, reviewed episode moves and database season assignments."""
import json
import uuid
import os
import re
from pathlib import Path
from contextlib import closing
from app import db
from app.core import identity,downloads,download_assignment


def files(fid):
    series=db.get_series(fid)
    if not series:raise ValueError('This anime is no longer in the library.')
    owners=series.get('series_member_ids',[fid])
    # Reconcile externally moved files only with the existing strong signature
    # proof; a matching filename alone never authorizes a relink.
    root=Path(series.get('root_folder_path') or '')
    main=downloads.library_root()
    if series.get('root_folder_path') and root.parent!=root and root.is_dir() and (not main or not Path(main).resolve().is_relative_to(root.resolve())):
        from app.core.download_library import _safe
        _safe(root)
        with closing(db.get_connection()) as conn:
            missing=conn.execute("SELECT f.*,l.path FROM physical_files f JOIN file_locations l ON l.file_id=f.id JOIN seasons s ON s.id=f.season_id WHERE s.franchise_id IN (%s)" % ','.join('?' for _ in owners),owners).fetchall()
        missing=[r for r in missing if r['availability'] not in ('RECYCLED','REPLACED') and not Path(r['path']).exists() and r['mtime_ns'] is not None]
        if missing:
            from app.core.download_inventory import Snapshot
            inventory=Snapshot()
            actual={}
            for directory,dirs,names in os.walk(root,followlinks=False):
                dirs[:]=[d for d in dirs if not Path(directory,d).is_symlink() and not (hasattr(Path(directory,d),'is_junction') and Path(directory,d).is_junction())]
                for name in names:actual.setdefault(name.casefold(),[]).append(Path(directory,name))
            for row in missing:
                if not inventory.can_index(row['path']):continue
                matches=[p for p in actual.get(Path(row['path']).name.casefold(),[]) if not p.is_symlink() and identity.signature(p)==tuple(row[k] for k in ('size_bytes','mtime_ns','device','inode'))]
                if len(matches)==1:
                    identity.candidate_for(row['id'],matches[0])
                    with closing(db.get_connection()) as conn:record=conn.execute('SELECT id FROM repair_candidates WHERE file_id=? AND target=?',(row['id'],str(matches[0]))).fetchone()
                    if record:identity.approve_repair(record[0])
        # A copied/replaced file may have a new inode. Index it as new physical
        # content rather than pretending it is the missing old file. The user
        # still explicitly chooses its destination season and episode numbers.
        from app.config import VIDEO_EXTENSIONS
        from app.core.download_inventory import Snapshot
        inventory=Snapshot()
        blocked={Path(r['path']).name.casefold() for r in missing if not inventory.can_index(r['path'])}
        with closing(db.get_connection()) as conn:
            known={r[0] for r in conn.execute('SELECT path_key FROM file_locations')}
            local=conn.execute('SELECT * FROM seasons WHERE local_scan_key=?',('season-editor:'+str(fid),)).fetchone()
        fresh=[]
        for directory,dirs,names in os.walk(root,followlinks=False):
            dirs[:]=[d for d in dirs if not Path(directory,d).is_symlink() and not (hasattr(Path(directory,d),'is_junction') and Path(directory,d).is_junction())]
            for name in names:
                p=Path(directory,name)
                if p.name.casefold() not in blocked and p.suffix.lower() in VIDEO_EXTENSIONS and not p.is_symlink() and identity.path_key(p) not in known and inventory.can_index(p):fresh.append(p)
        if fresh:
            names=json.loads(local['video_files_json'] or '[]') if local else []
            names.extend(str(p.relative_to(root)) for p in fresh)
            if local:
                with closing(db.get_connection()) as conn,conn:
                    conn.execute('UPDATE seasons SET video_files_json=? WHERE id=?',(json.dumps(names),local['id']))
                    identity.sync_season(conn,{**dict(local),'video_files_json':json.dumps(names)})
            else:db.upsert_season(dict(franchise_id=fid,relation_type='SEASON',title_display='Files awaiting season assignment',season_folder_path=str(root),video_files_json=json.dumps(names),storage_state='ON_DISK',local_scan_key='season-editor:'+str(fid)))
        with closing(db.get_connection()) as conn,conn:
            for row in conn.execute("SELECT f.id,l.path FROM physical_files f JOIN file_locations l ON l.file_id=f.id JOIN seasons s ON s.id=f.season_id WHERE s.franchise_id IN (%s) AND f.availability='AVAILABLE'" % ','.join('?' for _ in owners),owners).fetchall():
                if not Path(row['path']).is_file():conn.execute("UPDATE physical_files SET availability='MISSING' WHERE id=?",(row['id'],))
    with closing(db.get_connection()) as conn:
        rows=conn.execute("SELECT f.id,l.path,s.season_number,GROUP_CONCAT(CASE WHEN e.mapping_verified=1 THEN e.release_number ELSE e.original_number END) AS numbers FROM physical_files f JOIN file_locations l ON l.file_id=f.id JOIN seasons s ON s.id=f.season_id LEFT JOIN file_episodes fe ON fe.file_id=f.id LEFT JOIN episodes e ON e.id=fe.episode_id WHERE s.franchise_id IN (%s) AND s.relation_type='SEASON' AND f.availability='AVAILABLE' GROUP BY f.id ORDER BY s.season_number,l.path" % ','.join('?' for _ in owners),owners).fetchall()
    result=[{**dict(r),'available':Path(r['path']).is_file()} for r in rows]
    return sorted(result,key=lambda r:[int(part) if part.isdigit() else part.casefold() for part in re.split(r'(\d+)',Path(r['path']).name)])


def pending(fid):
    value=db.get_state(f'season_file_move:{fid}')
    return json.loads(value) if value else None


def preview(fid,identifiers,season,episode_numbers=None,remove_empty=False,destination_folder=None):
    if pending(fid):return pending(fid)
    if not identifiers:raise ValueError('Select at least one episode file.')
    if not 1<=season<=999:raise ValueError('Choose a valid season number.')
    target=download_assignment.destination(fid,season,destination_folder,canonical=True)
    known={r['id']:r for r in files(fid)}
    from app.core.download_inventory import Snapshot
    inventory=Snapshot();rows=[];targets=set()
    for identifier in dict.fromkeys(identifiers):
        if identifier not in known:raise ValueError('An episode changed. Reload the file list.')
        source=Path(known[identifier]['path'])
        from app.core.download_library import _safe
        _safe(source)
        if not source.is_file() or not inventory.can_index(source):raise ValueError('Wait for verified download completion before moving: '+str(source))
        destination=Path(target['folder'])/source.name;key=identity.path_key(destination)
        if key in targets:raise ValueError('Selected files share a filename. Move one version at a time; no files will be overwritten.')
        targets.add(key)
        if destination.exists() and key!=identity.path_key(source):raise ValueError('Destination already contains this filename. No overwrite: '+str(destination))
        with closing(db.get_connection()) as conn:
            episodes=[dict(r) for r in conn.execute('SELECT e.* FROM episodes e JOIN file_episodes fe ON fe.episode_id=e.id WHERE fe.file_id=?',(identifier,))]
        numbers=[e['release_number'] if e['mapping_verified'] else e['original_number'] for e in episodes]
        source_numbers={str(e['id']):n for e,n in zip(episodes,numbers)}
        if episode_numbers and identifier in episode_numbers:
            assigned=episode_numbers[identifier]
            if len(assigned)!=len(episodes):raise ValueError('Enter one episode number for each episode in this file.')
            for e,n in zip(episodes,assigned):e.update(release_number=n,mapping_verified=1)
            numbers=assigned
        if not numbers or any(not isinstance(n,int) or not 1<=n<=9999 for n in numbers):raise ValueError('Confirm episode numbering for this file first: '+source.name)
        rows.append(dict(file_id=identifier,source_episode_numbers=source_numbers,source_season=known[identifier]['season_number'],source=str(source),target=str(destination),signature=list(identity.signature(source)),episodes=episodes))
    return dict(id=uuid.uuid4().hex,fid=fid,season=season,destination=target,rows=rows,remove_empty=remove_empty)


def _assign(plan,row):
    """Rebind selected physical files only; retain all original episode history."""
    with closing(db.get_connection()) as conn,conn:
        current=conn.execute('SELECT f.season_id,l.path FROM physical_files f JOIN file_locations l ON l.file_id=f.id WHERE f.id=?',(row['file_id'],)).fetchone()
        if not current or identity.path_key(current['path'])!=identity.path_key(row['target']):raise ValueError('The moved file has a different library identity. Review before continuing.')
        fid=plan['fid'];number=plan['season'];folder=plan['destination']['folder']
        series=conn.execute('SELECT id FROM library_series WHERE franchise_id=?',(fid,)).fetchone()
        if not series:
            conn.execute('INSERT INTO library_series(franchise_id) VALUES (?)',(fid,));series=conn.execute('SELECT id FROM library_series WHERE franchise_id=?',(fid,)).fetchone()
        seasons=[dict(r) for r in conn.execute("SELECT * FROM seasons WHERE franchise_id=? AND season_number=? AND relation_type='SEASON' ORDER BY anilist_id IS NULL,id",(fid,number))]
        dest=next((s for s in seasons if s.get('season_folder_path') and identity.path_key(s['season_folder_path'])==identity.path_key(folder)),None) or next((s for s in seasons if not s.get('season_folder_path')),None)
        if not dest:
            sid=conn.execute("INSERT INTO seasons(franchise_id,season_number,relation_type,title_display,season_folder_path,video_files_json,storage_state,numbering_source) VALUES (?,?,'SEASON',?,?,'[]','ON_DISK','manual')",(fid,number,f'Season {number:02}',folder)).lastrowid
            dest=dict(conn.execute('SELECT * FROM seasons WHERE id=?',(sid,)).fetchone())
        linked=conn.execute('SELECT r.id,r.release_key FROM releases r JOIN season_releases sr ON sr.release_id=r.id WHERE sr.season_id=?',(dest['id'],)).fetchone()
        if linked and linked['release_key']!='continuous':rid=linked['id']
        else:
            key=f'local:SEASON:{number}'
            conn.execute("INSERT OR IGNORE INTO releases(series_id,release_key,kind) VALUES (?,?,'SEASON')",(series[0],key))
            rid=conn.execute('SELECT id FROM releases WHERE series_id=? AND release_key=?',(series[0],key)).fetchone()[0]
            if not linked:conn.execute('INSERT INTO season_releases VALUES (?,?)',(dest['id'],rid))
        for episode in row['episodes']:
            n=episode['release_number'] if episode['mapping_verified'] else episode['original_number']
            key=f'confirmed:number:{n}'
            conn.execute("INSERT OR IGNORE INTO episodes(release_id,identity_key,original_number,numbering_scheme,release_number,mapping_verified,mapping_source,notes) VALUES (?,?,?,'SEASON',?,1,'MANUAL',?)",(rid,key,episode['original_number'],n,episode['notes']))
            eid=conn.execute('SELECT id FROM episodes WHERE release_id=? AND identity_key=?',(rid,key)).fetchone()[0]
            conn.execute('INSERT INTO episode_history(episode_id,played_at,position_seconds,event) SELECT ?,h.played_at,h.position_seconds,h.event FROM episode_history h WHERE h.episode_id=? AND NOT EXISTS (SELECT 1 FROM episode_history old WHERE old.episode_id=? AND old.played_at=h.played_at AND old.position_seconds IS h.position_seconds AND old.event=h.event)',(eid,episode['id'],eid))
            conn.execute('INSERT OR IGNORE INTO file_episodes VALUES (?,?)',(row['file_id'],eid))
        keep={r[0] for r in conn.execute('SELECT id FROM episodes WHERE release_id=? AND identity_key IN (%s)' % ','.join('?' for _ in row['episodes']),[rid,*[f'confirmed:number:{e["release_number"] if e["mapping_verified"] else e["original_number"]}' for e in row['episodes']]])}
        for old in conn.execute('SELECT episode_id FROM file_episodes WHERE file_id=?',(row['file_id'],)).fetchall():
            if old[0] not in keep:conn.execute('DELETE FROM file_episodes WHERE file_id=? AND episode_id=?',(row['file_id'],old[0]))
        conn.execute('UPDATE physical_files SET season_id=? WHERE id=?',(dest['id'],row['file_id']))
        # Remove this selected path from its old compatibility inventory only.
        source=conn.execute('SELECT * FROM seasons WHERE id=?',(current['season_id'],)).fetchone()
        if source and source['id']!=dest['id']:
            base=Path(source['season_folder_path'] or '')
            paths={identity.path_key(r[0]):Path(r[0]) for r in conn.execute("SELECT l.path FROM file_locations l JOIN physical_files f ON f.id=l.file_id WHERE f.season_id=? AND f.availability NOT IN ('RECYCLED','REPLACED')",(source['id'],))}
            for name in json.loads(source['video_files_json'] or '[]'):
                p=base/name
                if p.is_file() and identity.path_key(p)!=identity.path_key(row['target']):paths.setdefault(identity.path_key(p),p)
            names=[]
            for p in paths.values():
                try:names.append(os.path.relpath(p.resolve(),base.resolve()))
                except ValueError:names.append(str(p))
            conn.execute('UPDATE seasons SET video_files_json=?,season_folder_path=?,storage_state=? WHERE id=?',(json.dumps(names),str(base) if names else None,'ON_DISK' if names else 'WATCHED_REMOVED',source['id']))
            if not names and not source['anilist_id']:conn.execute('INSERT OR REPLACE INTO app_state VALUES (?,?)',(f'season.hidden_folder:{source["id"]}','1'))
        names=json.loads(dest['video_files_json'] or '[]')
        if identity.path_key(row['target']) not in {identity.path_key(Path(dest['season_folder_path'] or folder)/n) for n in names}:
            names.append(os.path.relpath(Path(row['target']).resolve(),Path(folder).resolve()))
        conn.execute("UPDATE seasons SET season_folder_path=?,video_files_json=?,storage_state='ON_DISK' WHERE id=?",(folder,json.dumps(names),dest['id']))
        conn.execute('DELETE FROM app_state WHERE key=?',(f'season.hidden_folder:{dest["id"]}',))
        conn.execute('INSERT OR REPLACE INTO app_state VALUES (?,?)',(f'season_number_override:{dest["id"]}',str(number)))
        for sid in {current['season_id'],dest['id']}:
            conn.execute("UPDATE seasons SET size_bytes=(SELECT COALESCE(SUM(size_bytes),0) FROM physical_files WHERE season_id=? AND availability='AVAILABLE') WHERE id=?",(sid,sid))
            conn.execute('INSERT OR REPLACE INTO app_state VALUES (?,?)',(f'download.scoped_inventory:{sid}','1'))
        for owner in {fid,source['franchise_id'] if source else fid}:
            conn.execute("UPDATE franchises SET total_size_bytes=(SELECT COALESCE(SUM(size_bytes),0) FROM seasons WHERE franchise_id=?),storage_state=CASE WHEN EXISTS(SELECT 1 FROM seasons WHERE franchise_id=? AND storage_state='ON_DISK') THEN 'ON_DISK' ELSE 'WATCHED_REMOVED' END WHERE id=?",(owner,owner,owner))
        conn.execute('INSERT OR REPLACE INTO app_state VALUES (?,?)',('organizer_preview_stale','1'))
        conn.execute("INSERT INTO app_state VALUES ('files.move_revision','1') ON CONFLICT(key) DO UPDATE SET value=CAST(value AS INTEGER)+1")


def apply(plan,cancelled=lambda:False):
    from app.core.file_operations import _operation_lock,move_file,copy_move_file,recover_operations
    from app.core.download_library import _safe,_finished
    with downloads._lock,_operation_lock:
        recover_operations();saved=pending(plan['fid'])
        if saved and saved['id']!=plan['id']:raise ValueError('Finish the previous season move first.')
        anime=db.get_series(plan['fid'])
        if not anime:raise ValueError('This anime was removed. Files were kept.')
        owners=anime.get('series_member_ids',[plan['fid']])
        folder=Path(plan['destination']['folder']).resolve();root=Path(plan['destination']['root']).resolve()
        if not folder.is_relative_to(root):raise ValueError('The season folder must be inside the main library.')
        # Validate the whole plan before the first move or reassignment.
        from app.core.download_inventory import Snapshot
        inventory=Snapshot()
        for row in plan['rows']:
            source,target=_safe(row['source']),_safe(row['target'])
            if identity.path_key(target)!=identity.path_key(folder/source.name):raise ValueError('The reviewed destination changed.')
            with closing(db.get_connection()) as conn:
                location=conn.execute('SELECT l.path,s.franchise_id,f.availability FROM file_locations l JOIN physical_files f ON f.id=l.file_id JOIN seasons s ON s.id=f.season_id WHERE l.file_id=?',(row['file_id'],)).fetchone()
            if not location or location['franchise_id'] not in owners or location['availability']!='AVAILABLE' or identity.path_key(location['path']) not in (identity.path_key(source),identity.path_key(target)):raise ValueError('The file location or anime assignment changed. Review it again.')
            if source.exists():
                if not inventory.can_index(source):raise ValueError('This download is no longer verified. Wait for completion before moving it.')
                if list(identity.signature(source))!=row['signature']:raise ValueError('A selected file changed. Reload the preview.')
                if target.exists() and identity.path_key(source)!=identity.path_key(target):raise ValueError('Destination already exists; no overwrite.')
            elif not _finished(source,target):raise ValueError('A selected file is missing or changed.')
        db.set_state(f'season_file_move:{plan["fid"]}',json.dumps(plan))
        for row in plan['rows']:
            if cancelled():raise InterruptedError('Move stopped. Review the saved move to continue.')
            source,target=_safe(row['source']),_safe(row['target'])
            jobs=downloads.jobs()
            for job in jobs:
                if any(identity.path_key(f['path'])==identity.path_key(source) for f in job.get('verified_files',[])) and job.get('engine')=='builtin' and job.get('desired')!='cancelled':
                    from app.core.download_queue import action
                    action(job['id'],'stop')
            with closing(db.get_connection()) as conn,conn:
                owner=conn.execute('SELECT season_id FROM physical_files WHERE id=?',(row['file_id'],)).fetchone()
                if owner:conn.execute('INSERT OR REPLACE INTO app_state VALUES (?,?)',(f'download.scoped_inventory:{owner[0]}','1'))
            if identity.path_key(source)!=identity.path_key(target) and source.exists():
                target.parent.mkdir(parents=True,exist_ok=True)
                (move_file if source.stat().st_dev==target.parent.stat().st_dev else copy_move_file)(source,target,row['signature'])
            _assign(plan,row)
            jobs=downloads.jobs()
            for job in jobs:
                matched=False
                for file in job.get('verified_files',[]):
                    if identity.path_key(file['path'])==identity.path_key(source):file['path']=str(target);matched=True
                if matched:
                    job['organized_sources']=list(set(job.get('organized_sources',[]))|{identity.path_key(source)})
                    job['manually_organized_files']=list(set(job.get('manually_organized_files',[]))|{identity.path_key(target)})
                    if all(identity.path_key(f['path']) in job['manually_organized_files'] for f in job['verified_files']):job.update(library_moved=True,library_destination=plan['destination']['anime'])
                    from app.core.download_discovery import episode_key
                    mapping={}
                    with closing(db.get_connection()) as conn:
                        for episode in row['episodes']:
                            release=conn.execute('SELECT release_key FROM releases WHERE id=?',(episode['release_id'],)).fetchone()
                            n=episode['release_number'] if episode['mapping_verified'] else episode['original_number']
                            oldn=row.get('source_episode_numbers',{}).get(str(episode['id']),n)
                            old=episode_key(bool(release and release[0]=='continuous'),row['source_season'],oldn)
                            mapping[old]=episode_key(False,plan['season'],n)
                    job['episode_keys']=[mapping.get(k,k) for k in job.get('episode_keys',[])]
                    scopes={k.split(':')[1] for k in job['episode_keys']}
                    if len(scopes)==1:
                        scope=next(iter(scopes));job.update(season=int(scope[1:]) if scope.startswith('S') else 0,continuous=scope=='ABS')
                        with closing(db.get_connection()) as conn:
                            job['local_season_id']=conn.execute('SELECT season_id FROM physical_files WHERE id=?',(row['file_id'],)).fetchone()[0]
                    download_assignment.remember(job)
            downloads._save_jobs(jobs)
        db.update_franchise_field(plan['fid'],'root_folder_path',plan['destination']['anime'])
        if plan.get('remove_empty'):
            anime=Path(plan['destination']['anime']).resolve()
            for old in {Path(r['source']).parent for r in plan['rows']}:
                if old.resolve()!=anime and old.resolve()!=Path(plan['destination']['folder']).resolve() and old.resolve().is_relative_to(anime):
                    try:old.rmdir() # Empty directories only; never recursive deletion.
                    except OSError:pass
        db.set_state(f'season_file_move:{plan["fid"]}','')
    return f'{len(plan["rows"])} episode files assigned to Season {plan["season"]}. Original filenames were kept.'
