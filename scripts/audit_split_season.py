"""Demonstrate one release split across download/library locations; temp files only."""
import sys, json, tempfile
from pathlib import Path
from contextlib import ExitStack, closing
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import db
from app.core.scanner import _update_on_disk_info
with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
    root=Path(directory)
    for key,value in [('DATA_DIR',root),('DB_PATH',root/'library.db'),('COVERS_DIR',root/'covers'),('EXPORTS_DIR',root/'exports')]:
        stack.enter_context(patch.object(db,key,value))
    db.init_db()
    fid=db.upsert_franchise({'display_title':'Split Season Audit'})
    for location,episode in [('Library',1),('Downloads',2)]:
        folder=root/location/'Split Season Audit'
        file=folder/'Season 01'/f'Split Season Audit S01E{episode:02}.mkv'
        file.parent.mkdir(parents=True);file.write_bytes(b'synthetic audit fixture')
        _update_on_disk_info(fid,str(folder))
    seasons=db.get_seasons_for_franchise(fid)
    with closing(db.get_connection()) as conn:
        releases=conn.execute('SELECT COUNT(DISTINCT release_id) FROM season_releases').fetchone()[0]
    print(json.dumps({'season_numbers':[s['season_number'] for s in seasons],
                      'detail_badge_season_count':len([s for s in seasons if s['relation_type']=='SEASON']),
                      'distinct_release_identities':releases},indent=2))
