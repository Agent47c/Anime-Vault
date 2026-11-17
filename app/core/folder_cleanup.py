"""User-confirmed removal of stale folder associations, never video deletion."""
import json
from contextlib import closing
from pathlib import Path
from app import db
from app.core.identity import path_key as identity_path
from app.config import VIDEO_EXTENSIONS
from app.core.file_operations import serialized


def hidden_folder_ids():
    with closing(db.get_connection()) as conn:
        return {int(row[0].rsplit(':',1)[1]) for row in conn.execute("SELECT key FROM app_state WHERE key LIKE 'season.hidden_folder:%' AND value='1'")}


@serialized
def remove_stale_folder(season_id,delete_empty_directory=False):
    with closing(db.get_connection()) as conn:
        row=conn.execute('SELECT * FROM seasons WHERE id=?',(season_id,)).fetchone()
        owned=conn.execute('SELECT f.id,f.availability,l.path FROM physical_files f JOIN file_locations l ON l.file_id=f.id WHERE f.season_id=?',(season_id,)).fetchall()
    if row is None:raise ValueError('This folder entry is no longer available.')
    season=dict(row);value=season.get('season_folder_path')
    if not value:
        if any(Path(r['path']).is_file() for r in owned if r['availability'] not in ('RECYCLED','REPLACED')):raise ValueError('This entry still owns files at another location. Review them first.')
        db.set_state(f'season.hidden_folder:{season_id}','1')
        return 'Empty entry removed. Metadata and watch history were kept.'
    folder=Path(value)
    from app.core.download_inventory import Snapshot
    readiness=Snapshot();readiness.assert_not_moving(folder)
    if readiness.in_staging(folder) and any(not job.get('library_moved') for root,job in readiness.owners if folder.resolve()==root or folder.resolve().is_relative_to(root)):
        raise ValueError('This folder belongs to a tracked download. Finish or review that download first.')
    if folder.is_symlink() or (hasattr(folder,'is_junction') and folder.is_junction()):raise ValueError('Linked folders must be reviewed manually.')
    names=json.loads(season.get('video_files_json') or '[]')
    with closing(db.get_connection()) as conn:
        neighbours=conn.execute('SELECT s.id,s.season_folder_path FROM seasons s WHERE s.id<>? AND s.season_folder_path IS NOT NULL',(season_id,)).fetchall()
    shared=any(identity_path(row['season_folder_path'])==identity_path(folder) for row in neighbours)
    if any(Path(item['path']).is_file() for item in owned if item['availability'] not in ('RECYCLED','REPLACED')):
        raise ValueError('This entry still owns a video at another recorded location. Scan or locate it before removing the folder association.')
    if any((folder/name).is_file() for name in names):raise ValueError('This folder still has indexed videos. Use the existing file review instead.')
    if folder.exists() and not (shared and not owned and not names):
        import os
        def failed(error):raise error
        for directory,folders,files in os.walk(folder,followlinks=False,onerror=failed):
            if any((Path(directory)/name).is_symlink() or (hasattr(Path(directory)/name,'is_junction') and (Path(directory)/name).is_junction()) for name in folders):raise ValueError('Linked folders must be reviewed manually.')
            if any(Path(name).suffix.lower() in VIDEO_EXTENSIONS for name in files):raise ValueError('This folder still contains videos. Scan or locate them before removing its entry.')
    if delete_empty_directory and folder.exists():
        if shared:raise ValueError('Another entry uses this folder. Remove the empty entry without deleting the directory.')
        protected=[Path(r['folder_path']).resolve() for r in db.get_watched_directories()]
        from app.core.downloads import library_root
        main=library_root()
        if main:protected.append(Path(main).resolve())
        if not folder.is_absolute() or folder.parent==folder or folder.resolve() in protected:raise ValueError('A library root cannot be deleted through a season-folder action.')
        if any(folder.iterdir()):raise ValueError('The directory is not empty. Its files have been kept.')
        folder.rmdir()  # Non-recursive: concurrent new files make this fail safely.
    with closing(db.get_connection()) as conn,conn:
        conn.execute("UPDATE seasons SET season_folder_path=NULL,scan_root=NULL,video_files_json='[]',size_bytes=0,storage_state='NOT_DOWNLOADED' WHERE id=?",(season_id,))
        conn.execute("UPDATE physical_files SET availability='MISSING' WHERE season_id=? AND availability NOT IN ('RECYCLED','REPLACED')",(season_id,))
        conn.execute('INSERT OR REPLACE INTO app_state VALUES (?,?)',(f'season.hidden_folder:{season_id}','1'))
        conn.execute("INSERT OR REPLACE INTO app_state VALUES ('organizer_preview_stale','1')")
        conn.execute("INSERT INTO app_state VALUES ('inventory_revision','1') ON CONFLICT(key) DO UPDATE SET value=CAST(value AS INTEGER)+1")
        conn.execute("INSERT INTO app_state VALUES ('files.move_revision','1') ON CONFLICT(key) DO UPDATE SET value=CAST(value AS INTEGER)+1")
    db.recalculate_franchise_size(season['franchise_id']);db.recalculate_franchise_storage_state(season['franchise_id'])
    return 'Folder entry removed. Anime metadata and watch history were kept.'
