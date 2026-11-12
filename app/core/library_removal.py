"""Remove a series from visible library lists without erasing stable history."""
import json
from contextlib import closing
from pathlib import Path
from app import db

def removal_context(fid):
    series=db.get_series(fid)
    if not series:raise ValueError('This anime is no longer available.')
    members=series.get('series_member_ids',[fid])
    from app.core import downloads
    from app.core.download_queue import status
    if any(j.get('fid') in members and status(j) in ('Queued','Downloading','Paused','Seeding') for j in downloads.jobs()):raise ValueError('Stop this anime’s active downloads before removing it.')
    return series,members,db.get_series_seasons(fid,series=series)

def remove_entry(fid,require_no_files=False):
    series,members,seasons=removal_context(fid)
    if require_no_files:
        for season in seasons:
            if season.get('storage_state')=='ON_DISK':raise ValueError('Some local files could not be removed. The anime remains in your library.')
    hidden=set(json.loads(db.get_state('library.removed_ids','[]')));hidden.update(members)
    roots=set(json.loads(db.get_state('library.removed_roots','[]')))
    watched={Path(r['folder_path']).resolve() for r in db.get_watched_directories()}
    for path in [*(db.get_franchise(i).get('root_folder_path') for i in members),*(s.get('season_folder_path') for s in seasons)]:
        if path and Path(path).resolve() not in watched:roots.add(str(Path(path).resolve()))
    with closing(db.get_connection()) as conn, conn:
        for key,value in [('library.removed_roots',json.dumps(sorted(roots))),('library.removed_ids',json.dumps(sorted(hidden))),('organizer_preview_stale','1')]:
            conn.execute('INSERT INTO app_state(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,value))
    return 'Anime removed from the library. Local files were kept.' if not require_no_files else 'Files recycled and anime removed from the library.'
