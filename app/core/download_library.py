"""Reviewed completed-download moves with stable IDs and recoverable journals."""
import json
import os
import re
from pathlib import Path
from contextlib import closing
from app import db
from app.core import downloads,identity
from app.core.season_paths import season_folder_name


def _safe(path):
    path=Path(path).absolute()
    if any(p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) for p in (path,*path.parents)):
        raise ValueError('Linked paths require manual review: '+str(path))
    return path


def _finished(source,target):
    from app.core.file_operations import completed_move
    return completed_move(source,target)


def preview(root=None,folder_overrides=None):
    from app.core.file_operations import recover_operations
    from app.core.consolidation import explicit_season
    recover_operations()
    from app.core.download_queue import status
    root=root or downloads.library_root()
    if not root or not Path(root).is_absolute():raise ValueError('Choose your main library folder in Organizer > Merge all anime > Destination library. This is separate from the download staging folder and watched folders.')
    root=_safe(root);rows=[];notes=[];targets=set();jobs=downloads.jobs();destinations=[];folder_overrides=folder_overrides or {}
    canonical_root=root.resolve()
    staging=[Path(job['root']).resolve() for job in jobs if job.get('root')]
    configured=Path(downloads.settings()['destination']).resolve()
    if configured!=canonical_root:staging.append(configured)
    def in_staging(path):
        path=Path(path).resolve()
        return any(path==base or path.is_relative_to(base) for base in staging)
    def library_folder(path):
        path=Path(path).resolve()
        return path!=canonical_root and path.is_relative_to(canonical_root) and not in_staging(path)
    for job in jobs:
        if job.get('library_moved'):continue
        if not job.get('indexed') or (job.get('integrity_missing') and not job.get('library_move_intent')):
            notes.append(f"{job.get('title','Anime')}: not ready — {job.get('status','waiting for verified completion')}");continue
        from app.core.download_inventory import ready
        if not ready(job) and not job.get('library_move_intent'):
            notes.append(f"{job.get('title','Anime')}: wait for verified completion — {job.get('status','not ready')}");continue
        try:
            series=db.get_series(job['fid'])
            if not series:raise ValueError('Linked anime no longer exists.')
            if job.get('library_move_intent'):
                planned=job['library_move_intent']
                if any(not Path(r['target']).is_relative_to(root) for r in planned):raise ValueError('Finish the previous move destination before changing libraries.')
            else:
                title=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',series['display_title']).strip(' .')[:100] or 'Anime'
                series_root=root/title;existing=series.get('root_folder_path')
                if existing and library_folder(existing):series_root=Path(existing)
                number=job.get('season') or 0
                destinations.append(dict(id=job['id'],fid=job['fid'],title=series['display_title'],anime_root=str(series_root),season=number))
                override=folder_overrides.get(job['id'])
                folder=series_root/(season_folder_name(number) if number else 'Episodes' if db.uses_continuous_episodes(series) else 'Unassigned episodes')
                # Only the padded spelling is a default destination. Old
                # spellings remain sources for a reviewed season consolidation.
                if number and series_root.is_dir():
                    from app.core.consolidation import explicit_season
                    candidates=[child for child in series_root.iterdir() if child.is_dir() and explicit_season(child.name)==number]
                    if len(candidates)>1 and not override:raise ValueError(f'Multiple folders match season {number}. Choose the destination folder explicitly.')
                    if candidates:
                        preferred=next((p for p in candidates if p.name.casefold()==season_folder_name(number).casefold()),None)
                        if preferred:folder=_safe(preferred)
                for season in db.get_series_seasons(job['fid'],series=series):
                    current=season.get('season_folder_path')
                    if number and season.get('season_number')==number and current and Path(current).is_dir() and Path(current).resolve()!=series_root.resolve() and Path(current).name.casefold()==season_folder_name(number).casefold() and Path(current).resolve().is_relative_to(series_root.resolve()) and library_folder(current):folder=Path(current);break
                approved=job.get('approved_destination') if job.get('move_when_completed') else None
                if approved:
                    if identity.path_key(approved['root'])!=identity.path_key(root):raise ValueError('The library root changed after confirmation. Review this move again.')
                    folder=_safe(approved['folder']);series_root=_safe(approved['anime'])
                    if not folder.resolve().is_relative_to(series_root.resolve()) or not series_root.resolve().is_relative_to(canonical_root):raise ValueError('The confirmed season destination is outside the library.')
                if override:
                    folder=_safe(override)
                    from app.core.consolidation import explicit_season
                    if explicit_season(folder.name) not in (None,number):raise ValueError('Choose the folder for the confirmed season, or use the episode mover to change its season.')
                    if folder.resolve()==series_root.resolve() or not folder.resolve().is_relative_to(series_root.resolve()) or not library_folder(folder):raise ValueError('Choose a season folder inside this anime’s library folder.')
                    if number and explicit_season(folder.name)==number:folder=folder.with_name(season_folder_name(number))
                sources={entry['path']:entry['size'] for entry in job.get('verified_files') or [] if identity.path_key(entry['path']) not in job.get('manually_organized_files',[])}
                base=_safe(job['destination'])
                chosen=job.get('selected_files')
                for index,entry in enumerate(job.get('download_files') or []):
                    if identity.path_key(base/entry['name']) in job.get('organized_sources',[]):continue
                    if (chosen is None and entry.get('priority',1)>0) or (chosen is not None and index in chosen):sources.setdefault(str(base/entry['name']),entry['size'])
                # Verification resolves Windows path casing while native torrent
                # metadata may keep the original spelling. These are one source.
                unique_sources={}
                for name,size in sources.items():
                    key=identity.path_key(name)
                    if key in unique_sources and unique_sources[key][1]!=size:raise ValueError('The completed-file inventories disagree about size: '+name)
                    unique_sources.setdefault(key,(name,size))
                planned=[]
                for name,size in unique_sources.values():
                    source=_safe(name)
                    if not source.resolve().is_relative_to(base.resolve()) or not source.is_file() or source.stat().st_size!=size:raise ValueError('Completed file changed or is outside its download folder: '+str(source))
                    relative=source.resolve().relative_to(base.resolve())
                    target=_safe(folder/relative)
                    if target.exists() and job.get('duplicate_action') in ('replace','redownload'):
                        # Keep the source basename intact; stage a second encoding
                        # separately so no old copy is overwritten during a move.
                        target=_safe(folder/('Download '+job['id'])/relative)
                    planned.append(dict(job_id=job['id'],anime=series['display_title'],source=str(source),target=str(target),signature=identity.signature(source),library_folder=str(series_root)))
                    if job.get('assignment_version')==1:planned[-1]['season_folder']=str(folder)
                if not planned:raise ValueError('No verified completed-file inventory is available.')
            for row in planned:
                source,target=_safe(row['source']),_safe(row['target']);key=identity.path_key(target)
                if in_staging(target):raise ValueError('The proposed library destination is inside download staging. Review the main library destination before moving files.')
                if key in targets:raise ValueError('Two files have the same destination: '+str(target))
                if target.exists() and not (not source.exists() and _finished(source,target)):raise ValueError('Destination already exists; no overwrite: '+str(target))
                if source.exists() and tuple(row['signature'])!=identity.signature(source):raise ValueError('Source changed since preview: '+str(source))
                if not source.exists() and not (target.is_file() and _finished(source,target)):raise ValueError('Source is missing: '+str(source))
                targets.add(key)
            rows.extend(planned)
        except (OSError,ValueError) as error:notes.append(f"{job.get('title','Anime')}: {error}")
    with closing(db.get_connection()) as conn:
        candidates=conn.execute("SELECT DISTINCT s.franchise_id,l.path,f.display_title FROM physical_files p JOIN file_locations l ON l.file_id=p.id JOIN seasons s ON s.id=p.season_id JOIN franchises f ON f.id=s.franchise_id WHERE p.availability='AVAILABLE' AND l.path_key LIKE ?",(identity.path_key(configured)+'%',)).fetchall()
    indexed={r['franchise_id']:dict(fid=r['franchise_id'],title=r['display_title']) for r in candidates if Path(r['path']).resolve().is_relative_to(configured) and Path(r['path']).is_file()}
    return dict(root=str(root),rows=rows,notes=notes,destinations=destinations,indexed_staging=list(indexed.values()))


def move(plan,cancelled=lambda:False):
    """Explicitly reviewed jobs only. Persist each move before proceeding."""
    from app.core.file_operations import move_file,copy_move_file,recover_operations
    recover_operations();moved=0;reconciled=0;errors=[]
    with downloads._lock:
        items=downloads.jobs()
        for identifier in dict.fromkeys(row['job_id'] for row in plan['rows']):
            if cancelled():break
            job=next((j for j in items if j['id']==identifier),None)
            from app.core.download_inventory import ready
            if not job or not job.get('indexed') or not (ready(job) or job.get('library_move_intent')):errors.append(f'{identifier}: download is no longer ready');continue
            rows=[r for r in plan['rows'] if r['job_id']==identifier]
            job.pop('library_move_error',None)
            job['library_move_intent']=rows;downloads._save_jobs(items)
            try:
                for row in rows:
                    source,target=_safe(row['source']),_safe(row['target'])
                    if source.exists():
                        if target.exists() or identity.signature(source)!=tuple(row['signature']):raise ValueError('Move preview changed; review again: '+str(source))
                    elif not (target.is_file() and _finished(source,target)):raise ValueError('Source unavailable; review again: '+str(source))
                if job.get('engine')=='builtin' and job.get('desired')!='cancelled':
                    downloads.control_builtin(identifier,'cancel')
                    items=downloads.jobs();job=next(j for j in items if j['id']==identifier)
                for row in rows:
                    if cancelled():break
                    source,target=_safe(row['source']),_safe(row['target'])
                    if source.exists():
                        if target.exists():raise ValueError('Destination exists; no overwrite: '+str(target))
                        if identity.signature(source)!=tuple(row['signature']):raise ValueError('Source changed: '+str(source))
                        target.parent.mkdir(parents=True,exist_ok=True)
                        operation=move_file if source.stat().st_dev==target.parent.stat().st_dev else copy_move_file
                        operation(source,target,row['signature']);moved+=1
                    elif not (target.is_file() and _finished(source,target)):raise ValueError('Unverified missing source: '+str(source))
                    else:reconciled+=1
                    for file in job.get('verified_files') or []:
                        if identity.path_key(file['path'])==identity.path_key(source):file['path']=str(target)
                    downloads._save_jobs(items)
                if all(not Path(r['source']).exists() and _finished(Path(r['source']),Path(r['target'])) for r in rows):
                    if job.get('assignment_version')==1:
                        from app.core.download_assignment import settle_folder
                        settle_folder(job,rows[0].get('season_folder') or str(Path(rows[0]['target']).parent))
                    db.update_franchise_field(job['fid'],'root_folder_path',rows[0]['library_folder'])
                    series=db.get_series(job['fid'])
                    if series and series['id']!=job['fid']:db.update_franchise_field(series['id'],'root_folder_path',rows[0]['library_folder'])
                    db.add_watched_directory(plan['root']);db.set_state('organizer_preview_stale','1')
                    if job.get('duplicate_action')=='replace':
                        from app.core.file_operations import recycle_file
                        # New files are verified at their final paths before any
                        # explicitly approved original is sent to the Recycle Bin.
                        for old in job.get('replacement_files') or []:
                            if cancelled():raise InterruptedError('Stopped before recycling the old copy. Both files are kept for review.')
                            if any(identity.path_key(old['path'])==identity.path_key(r['target']) for r in rows):raise ValueError('A replacement cannot recycle its new file.')
                            if Path(old['path']).exists():recycle_file(old['path'],old['signature'])
                        job['replacement_completed']=True;downloads._save_jobs(items)
                    # Keep the durable intent until replacement cleanup succeeds,
                    # so a locked old file remains visible and retryable in Organizer.
                    job.update(library_moved=True,library_destination=rows[0]['library_folder'],desired='cancelled',status='Indexed',integrity_missing=False)
                    job.pop('library_move_intent',None);job.pop('library_move_error',None);downloads._save_jobs(items,completed_moves=rows)
                elif cancelled():
                    job['library_move_error']='Move stopped before the next file. Review the remaining files to continue.';downloads._save_jobs(items)
            except Exception as error:
                errors.append(f"{job['title']}: {error}");job['library_move_error']=str(error);downloads._save_jobs(items)
    return f'{moved} files moved.'+(f' {reconciled} previously moved files reconciled.' if reconciled else '')+(' Stopped before the next file.' if cancelled() else '')+(' Review and retry: '+'; '.join(errors) if errors else '')
