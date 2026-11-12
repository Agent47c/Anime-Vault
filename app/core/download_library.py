"""Reviewed completed-download moves with stable IDs and recoverable journals."""
import json
import os
import re
from pathlib import Path
from contextlib import closing
from app import db
from app.core import downloads,identity


def _safe(path):
    path=Path(path).absolute()
    if any(p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) for p in (path,*path.parents)):
        raise ValueError('Linked paths require manual review: '+str(path))
    return path


def _finished(source,target):
    with closing(db.get_connection()) as conn:
        record=conn.execute("SELECT kind,signature FROM file_operations WHERE source=? AND target=? AND status='COMPLETED'",(str(source),str(target))).fetchone()
    if not record:return False
    try:
        proof=json.loads(record['signature']);signature=identity.signature(target)
        return signature[:2]==tuple(proof['original'][:2]) if record['kind']=='COPY_MOVE' else signature==tuple(proof)
    except (OSError,ValueError,TypeError):return False


def preview(root=None):
    from app.core.file_operations import recover_operations
    recover_operations()
    from app.core.download_queue import status
    root=root or downloads.library_root()
    if not root or not Path(root).is_absolute():raise ValueError('Choose one main library root first.')
    root=_safe(root);rows=[];notes=[];targets=set()
    for job in downloads.jobs():
        if job.get('library_moved') or not job.get('indexed') or (job.get('integrity_missing') and not job.get('library_move_intent')):continue
        try:
            series=db.get_series(job['fid'])
            if not series:raise ValueError('Linked anime no longer exists.')
            if job.get('library_move_intent'):
                planned=job['library_move_intent']
                if any(not Path(r['target']).is_relative_to(root) for r in planned):raise ValueError('Finish the previous move destination before changing libraries.')
            else:
                title=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',series['display_title']).strip(' .')[:100] or 'Anime'
                series_root=root/title;existing=series.get('root_folder_path')
                if existing and Path(existing)!=root and Path(existing).is_relative_to(root) and not Path(existing).is_relative_to(Path(job['root'])) and '.animevault-downloads' not in Path(existing).parts:series_root=Path(existing)
                number=job.get('season') or 0
                folder=series_root/(f'Season {number:02}' if number else 'Episodes' if db.uses_continuous_episodes(series) else 'Unassigned episodes')
                for season in db.get_series_seasons(job['fid'],series=series):
                    current=season.get('season_folder_path')
                    if number and season.get('season_number')==number and current and Path(current).is_relative_to(series_root) and not Path(current).is_relative_to(Path(job['root'])) and '.animevault-downloads' not in Path(current).parts:folder=Path(current);break
                sources={entry['path']:entry['size'] for entry in job.get('verified_files') or []}
                base=_safe(job['destination'])
                chosen=job.get('selected_files')
                for index,entry in enumerate(job.get('download_files') or []):
                    if (chosen is None and entry.get('priority',1)>0) or (chosen is not None and index in chosen):sources.setdefault(str(base/entry['name']),entry['size'])
                planned=[]
                for name,size in sources.items():
                    source=_safe(name)
                    if not source.is_relative_to(base) or not source.is_file() or source.stat().st_size!=size:raise ValueError('Completed file changed or is outside its download folder: '+str(source))
                    planned.append(dict(job_id=job['id'],anime=series['display_title'],source=str(source),target=str(_safe(folder/source.relative_to(base))),signature=identity.signature(source),library_folder=str(series_root)))
                if not planned:raise ValueError('No verified completed-file inventory is available.')
            for row in planned:
                source,target=_safe(row['source']),_safe(row['target']);key=identity.path_key(target)
                if key in targets:raise ValueError('Two files have the same destination: '+str(target))
                if target.exists() and not (not source.exists() and _finished(source,target)):raise ValueError('Destination already exists; no overwrite: '+str(target))
                if source.exists() and tuple(row['signature'])!=identity.signature(source):raise ValueError('Source changed since preview: '+str(source))
                if not source.exists() and not (target.is_file() and _finished(source,target)):raise ValueError('Source is missing: '+str(source))
                targets.add(key)
            rows.extend(planned)
        except (OSError,ValueError) as error:notes.append(f"{job.get('title','Anime')}: {error}")
    return dict(root=str(root),rows=rows,notes=notes)


def move(plan,cancelled=lambda:False):
    """Explicitly reviewed jobs only. Persist each move before proceeding."""
    from app.core.file_operations import move_file,copy_move_file,recover_operations
    recover_operations();moved=0;reconciled=0;errors=[]
    with downloads._lock:
        items=downloads.jobs()
        for identifier in dict.fromkeys(row['job_id'] for row in plan['rows']):
            if cancelled():break
            job=next((j for j in items if j['id']==identifier),None)
            if not job or not job.get('indexed'):errors.append(f'{identifier}: download is no longer ready');continue
            rows=[r for r in plan['rows'] if r['job_id']==identifier]
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
                    job.update(library_moved=True,library_destination=rows[0]['library_folder'],desired='cancelled',status='Indexed',integrity_missing=False)
                    job.pop('library_move_intent',None);downloads._save_jobs(items)
                    job.pop('library_move_error',None);downloads._save_jobs(items)
                    db.update_franchise_field(job['fid'],'root_folder_path',rows[0]['library_folder'])
                    series=db.get_series(job['fid'])
                    if series and series['id']!=job['fid']:db.update_franchise_field(series['id'],'root_folder_path',rows[0]['library_folder'])
                    db.add_watched_directory(plan['root']);db.set_state('organizer_preview_stale','1')
            except (OSError,ValueError) as error:
                errors.append(f"{job['title']}: {error}");job['library_move_error']=str(error);downloads._save_jobs(items)
    return f'{moved} files moved.'+(f' {reconciled} previously moved files reconciled.' if reconciled else '')+(' Stopped before the next file.' if cancelled() else '')+(' Review and retry: '+'; '.join(errors) if errors else '')
