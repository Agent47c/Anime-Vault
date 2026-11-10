"""Prepare detail data, coverage and artwork outside the event loop."""
import json
import os
import sqlite3
from pathlib import Path
from app import db
from app.config import COVERS_DIR,get_last_episode_path
from app.core.library_health import episode_inventory
from app.core.image_profiles import load_cached_image


def prepare_details(fid):
    memory=sqlite3.connect(':memory:',check_same_thread=False);memory.row_factory=sqlite3.Row
    try:
        source=db.get_connection()
        try:source.backup(memory)
        finally:source.close()
        snapshot={'connection':memory}
        with db.refresh_view(snapshot):
            series=db.get_series(fid)
            if not series:memory.close();return None
            seasons=db.get_series_seasons(series['id'],series=series)
            continuous=db.uses_continuous_episodes(series)
            coverage=episode_inventory(seasons,continuous=continuous)
            poster=load_cached_image(COVERS_DIR/series['cover_filename']) if series.get('cover_filename') else None
            resume=(None,None);saved=get_last_episode_path()
            if saved and Path(saved).is_file():
                key=os.path.normcase(os.path.abspath(saved))
                for season in seasons:
                    folder=season.get('season_folder_path')
                    if folder and season.get('storage_state')=='ON_DISK' and any(os.path.normcase(os.path.abspath(Path(folder)/name))==key for name in json.loads(season.get('video_files_json') or '[]')):
                        resume=(Path(saved),season);break
            return dict(franchise=series,seasons=seasons,continuous=continuous,coverage=coverage,poster=poster,resume=resume,snapshot=snapshot)
    except Exception:
        memory.close();raise
