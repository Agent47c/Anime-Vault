"""Persistent scan checkpoints and match decisions, never media content hashes."""
import hashlib
import json
import os
import time
from pathlib import Path
from contextlib import closing
from app import db
from app.config import VIDEO_EXTENSIONS
from app.core.parser import extract_season_number

SCHEMA = """
CREATE TABLE IF NOT EXISTS scan_roots (
 root_id INTEGER PRIMARY KEY REFERENCES watched_directories(id) ON DELETE CASCADE,
 state TEXT NOT NULL, error TEXT, checked_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS scan_scopes (
 root_id INTEGER REFERENCES watched_directories(id) ON DELETE CASCADE,
 scope TEXT NOT NULL, fingerprint TEXT NOT NULL, franchise_id INTEGER,
 PRIMARY KEY(root_id,scope)
);
CREATE TABLE IF NOT EXISTS scan_files (
 root_id INTEGER,scope TEXT NOT NULL,path_key TEXT NOT NULL,signature TEXT NOT NULL,
 present INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(root_id,path_key)
);
CREATE INDEX IF NOT EXISTS scan_files_scope ON scan_files(root_id,scope);
CREATE TABLE IF NOT EXISTS matching_decisions (
 kind TEXT NOT NULL,local_id INTEGER NOT NULL,provider_id INTEGER,
 source TEXT NOT NULL, evidence_json TEXT NOT NULL DEFAULT '{}',
 PRIMARY KEY(kind,local_id)
);
CREATE TABLE IF NOT EXISTS matching_review (
 local_id INTEGER PRIMARY KEY,context_json TEXT NOT NULL,candidates_json TEXT NOT NULL,
 reason TEXT NOT NULL,updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS artwork_assets (
 provider_id TEXT NOT NULL,kind TEXT NOT NULL,version TEXT NOT NULL,
 filename TEXT,state TEXT NOT NULL,retry_at REAL NOT NULL DEFAULT 0,
 PRIMARY KEY(provider_id,kind,version)
);
"""


def migrate(conn):
    conn.executescript(SCHEMA)
    if 'local_availability' not in {r['name'] for r in conn.execute('PRAGMA table_info(franchises)')}:
        conn.execute("ALTER TABLE franchises ADD COLUMN local_availability TEXT DEFAULT 'UNKNOWN'")
    # Preserve pre-existing confirmed links; do not pretend to know who selected them.
    if not conn.execute("SELECT 1 FROM app_state WHERE key='scan_schema_version'").fetchone():
        for kind, table in (('series','franchises'),('season','seasons')):
            conn.execute(f"INSERT OR IGNORE INTO matching_decisions(kind,local_id,provider_id,source) SELECT ?,id,anilist_id,'LEGACY_CONFIRMED' FROM {table} WHERE anilist_id IS NOT NULL", (kind,))
        conn.execute("INSERT INTO app_state VALUES ('scan_schema_version','1')")
    conn.commit()


def key(path):
    from app.core.identity import path_key
    return path_key(path)


def inventory(folder, cancelled=lambda: False, recursive=True):
    """Metadata-only enumeration. Any unreadable subtree aborts this checkpoint."""
    files = {}
    def fail(error):
        raise error
    for directory, folders, names in os.walk(folder, onerror=fail, followlinks=False):
        if cancelled():
            raise InterruptedError('Scan cancelled')
        folders[:] = sorted(n for n in folders if extract_season_number(n,None) != -1 and not (Path(directory)/n).is_symlink()) if recursive else []
        for name in sorted(names):
            if cancelled():
                raise InterruptedError('Scan cancelled')
            path = Path(directory)/name
            if path.suffix.lower() not in VIDEO_EXTENSIONS or path.is_symlink():
                continue
            stat = path.stat()
            files[str(path)] = (stat.st_size,stat.st_mtime_ns,str(stat.st_dev),str(stat.st_ino))
    fingerprint = hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
    return fingerprint,files


def changes(root_id,scope,files):
    files = {key(path):sig for path,sig in files.items()}
    with closing(db.get_connection()) as conn:
        old = {r['path_key']:r for r in conn.execute('SELECT * FROM scan_files WHERE root_id=? AND scope=?',(root_id,scope))}
    changed = {path for path,sig in files.items() if path not in old or not old[path]['present'] or json.loads(old[path]['signature']) != list(sig)}
    removed = {path for path,row in old.items() if row['present'] and path not in files}
    return changed,removed


def checkpoint(root_id,scope,fingerprint,files,fid):
    with closing(db.get_connection()) as conn,conn:
        conn.execute("INSERT INTO app_state VALUES ('inventory_revision','1') ON CONFLICT(key) DO UPDATE SET value=CAST(value AS INTEGER)+1")
        conn.execute('INSERT OR REPLACE INTO scan_scopes VALUES (?,?,?,?)',(root_id,scope,fingerprint,fid))
        conn.execute('UPDATE scan_files SET present=0 WHERE root_id=? AND scope=?',(root_id,scope))
        for path,sig in files.items():
            conn.execute('INSERT OR REPLACE INTO scan_files VALUES (?,?,?,?,1)',(root_id,scope,key(path),json.dumps(sig)))
        conn.execute("""UPDATE physical_files SET availability=(
            SELECT CASE WHEN s.present=1 THEN 'AVAILABLE' ELSE 'MISSING' END
            FROM file_locations l JOIN scan_files s ON s.path_key=l.path_key
            WHERE l.file_id=physical_files.id AND s.root_id=? AND s.scope=?)
            WHERE availability NOT IN ('RECYCLED','REPLACED') AND id IN (
            SELECT l.file_id FROM file_locations l JOIN scan_files s ON s.path_key=l.path_key
            WHERE s.root_id=? AND s.scope=?)""",(root_id,scope,root_id,scope))


def restore_scope(root_id,scope):
    with closing(db.get_connection()) as conn,conn:
        conn.execute("UPDATE physical_files SET availability='AVAILABLE' WHERE availability IN ('OFFLINE','INACCESSIBLE') AND id IN (SELECT l.file_id FROM file_locations l JOIN scan_files s ON s.path_key=l.path_key WHERE s.root_id=? AND s.scope=? AND s.present=1)",(root_id,scope))


def root_status(watched,state,error=None):
    root = Path(watched['folder_path']).resolve()
    with closing(db.get_connection()) as conn,conn:
        conn.execute('INSERT OR REPLACE INTO scan_roots VALUES (?,?,?,?)',(watched['id'],state,error,int(time.time())))
        for row in conn.execute('SELECT id,root_folder_path FROM franchises WHERE root_folder_path IS NOT NULL').fetchall():
            path = Path(row['root_folder_path']).resolve()
            if path == root or root in path.parents:
                conn.execute('UPDATE franchises SET local_availability=? WHERE id=? AND local_availability<>?',(state,row['id'],state))
        if state != 'ONLINE':
            conn.execute("UPDATE physical_files SET availability=? WHERE id IN (SELECT l.file_id FROM file_locations l JOIN scan_files s ON s.path_key=l.path_key WHERE s.root_id=?) AND availability NOT IN ('RECYCLED','REPLACED','MISSING')",(state,watched['id']))


def decision(conn,kind,local_id,provider_id,source='MANUAL',evidence=None):
    old = conn.execute('SELECT source FROM matching_decisions WHERE kind=? AND local_id=?',(kind,local_id)).fetchone()
    if source == 'AUTO' and old and old[0] in ('MANUAL','LEGACY_CONFIRMED'):
        return False
    conn.execute('INSERT OR REPLACE INTO matching_decisions VALUES (?,?,?,?,?)',(kind,local_id,provider_id,source,json.dumps(evidence or {})))
    return True
