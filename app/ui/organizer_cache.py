"""Persist Organizer previews without walking the user's media directories."""
import json
import os
import time
from contextlib import closing
from app import db


def configuration(rules):
    roots = sorted(os.path.normcase(os.path.abspath(row['folder_path'])) for row in db.get_watched_directories())
    with closing(db.get_connection()) as conn:
        operations = conn.execute("SELECT COUNT(*),COALESCE(MAX(updated_at),0) FROM file_operations WHERE status='COMPLETED'").fetchone()
    return {'season_naming': 'padded-targets-v2', 'roots': roots, 'rules': rules, 'operations': list(operations), 'inventory_revision': db.get_state('inventory_revision','0'), 'downloads_revision':db.get_state('downloads.inventory_revision','0'),'files_revision':db.get_state('files.move_revision','0')}


def same_scan_state(before,after):
    return all(before.get(key)==after.get(key) for key in ('season_naming','roots','rules','operations','downloads_revision','files_revision'))


def save_preview(results, config):
    if not same_scan_state(config,configuration(config['rules'])):return False
    payload = json.dumps({'version': 1, 'config': config, 'saved_at': int(time.time()), 'results': results})
    with closing(db.get_connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        if not same_scan_state(config,configuration(config['rules'])):return False
        conn.execute("INSERT OR REPLACE INTO app_state VALUES ('organizer_preview_cache',?)", (payload,))
        conn.execute("INSERT OR REPLACE INTO app_state VALUES ('organizer_preview_stale','0')")
    return True


def load_preview(rules):
    try:
        payload = json.loads(db.get_state('organizer_preview_cache', '{}'))
        results = payload.get('results')
        if payload.get('version') != 1 or not isinstance(results, dict) or not all(isinstance(results.get(key), list) for key in ('all','organized','unorganized')):
            return None
        if any(not isinstance(item, dict) for key in ('all','organized','unorganized') for item in results[key]):
            return None
        valid = payload.get('config') == configuration(rules) and db.get_state('organizer_preview_stale', '0') != '1'
        return results, valid
    except (ValueError, TypeError, AttributeError):
        return None


def invalidate_preview():
    db.set_state('organizer_preview_stale', '1')
