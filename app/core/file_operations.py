"""Durable move intents and idempotent reconciliation after interrupted IO.

Filesystem operations and SQLite cannot share a transaction. Commit intent with
FULL durability, move without overwrite, then commit references and completion
together. Reconciliation never guesses from a filename or retries a move itself.
"""
import json
import os
from pathlib import Path
import time
import uuid
import threading
from functools import wraps
from contextlib import closing
from app import db
from app.core import identity
from app.core.recycle_bin import send2trash

_operation_lock = threading.RLock()


def serialized(function):
    @wraps(function)
    def run(*args, **kwargs):
        with _operation_lock:
            return function(*args, **kwargs)
    return run


def _connection():
    conn = db.get_connection()
    conn.execute('PRAGMA synchronous=FULL')
    return conn


def _rename_noreplace(source, target):
    if os.name == 'nt':
        os.rename(source, target)  # Windows refuses an existing destination.
    else:
        os.link(source, target)  # No copy/delete fallback across volumes.
        os.unlink(source)


def _status(operation_id, status, error=None):
    with closing(_connection()) as conn, conn:
        conn.execute('UPDATE file_operations SET status=?,error=?,updated_at=? WHERE id=?', (status, error, int(time.time()), operation_id))


def prepare_move(source, target, expected=None):
    source, target = Path(source).absolute(), Path(target).absolute()
    if source.is_symlink() or target.is_symlink() or target.exists() or identity.path_key(source) == identity.path_key(target):
        raise ValueError('Unsafe or occupied move destination')
    before = identity.signature(source)
    if expected and tuple(before[:2]) != tuple(expected[:2]):
        raise ValueError('Source changed since preview')
    operation_id = uuid.uuid4().hex
    with closing(_connection()) as conn, conn:
        conn.execute('INSERT INTO file_operations VALUES (?,?,?,?,?,?,?,?,?)',
                     (operation_id, 'MOVE', str(source), str(target), json.dumps(before), 'PLANNED', None, int(time.time()), int(time.time())))
    return operation_id, before


def _complete(operation_id, source, target):
    with closing(_connection()) as conn, conn:
        conn.execute("UPDATE repair_candidates SET status='RESOLVED_BY_MOVE' WHERE file_id=(SELECT file_id FROM file_locations WHERE path_key=?) AND status='REVIEW'", (identity.path_key(source),))
        identity.relocate(conn, source, target)
        conn.execute("UPDATE file_operations SET status='COMPLETED',error=NULL,updated_at=? WHERE id=?", (int(time.time()), operation_id))


@serialized
def move_file(source, target, expected=None, rename=None):
    operation_id, before = prepare_move(source, target, expected)
    source, target = Path(source).absolute(), Path(target).absolute()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if identity.signature(source) != before or source.is_symlink() or target.exists():
            raise ValueError('Source or target changed before move')
        if str(target.parent.stat().st_dev) != before[2]:
            raise ValueError('Cross-volume moves require a separate verified-copy workflow; originals retained')
        (rename or _rename_noreplace)(source, target)
        if identity.signature(target) != before:
            raise ValueError('Moved file needs review: signature changed')
        _complete(operation_id, source, target)
        return operation_id
    except Exception as error:
        _status(operation_id, 'REVIEW' if not source.exists() else 'FAILED', str(error))
        raise


@serialized
def recover_operations():
    """Only reconcile proven moves. Leave absent, replaced or conflicting files for review."""
    recovered, errors = 0, []
    with closing(db.get_connection()) as conn:
        rows = conn.execute("SELECT * FROM file_operations WHERE status<>'COMPLETED'").fetchall()
    for row in rows:
        if row['kind'] != 'MOVE':
            _status(row['id'], 'REVIEW', row['error'] or 'Interrupted Recycle Bin operation; review required')
            errors.append(f"{row['source']}: interrupted Recycle Bin operation; review required")
            continue
        source, target = Path(row['source']), Path(row['target'])
        expected = tuple(json.loads(row['signature']))
        try:
            if not source.exists() and not target.is_symlink() and target.is_file() and expected[-1] != '0' and identity.signature(target) == expected:
                _complete(row['id'], source, target)
                recovered += 1
                continue
            message = (row['error'] or 'Move did not finish; preview and retry') if source.exists() and not target.exists() else 'Move needs review: source/destination unavailable or conflicting'
            _status(row['id'], 'FAILED' if source.exists() and not target.exists() else 'REVIEW', message)
            errors.append(f"{row['source']}: {message}")
        except (OSError, ValueError) as error:
            _status(row['id'], 'REVIEW', str(error))
            errors.append(f"{row['source']}: {error}")
    return {'recovered': recovered, 'errors': errors}


@serialized
def recycle_file(path, expected=None, recycle=None):
    path = Path(path).absolute()
    if path.is_symlink():
        raise ValueError('Symbolic links require manual review')
    before = identity.signature(path)
    if expected and tuple(before[:len(expected)]) != tuple(expected):
        raise ValueError('File changed since review')
    operation_id = uuid.uuid4().hex
    with closing(_connection()) as conn, conn:
        conn.execute('INSERT INTO file_operations VALUES (?,?,?,?,?,?,?,?,?)',
                     (operation_id, 'RECYCLE', str(path), None, json.dumps(before), 'PLANNED', None, int(time.time()), int(time.time())))
    try:
        if identity.signature(path) != before:
            raise ValueError('File changed before recycling')
        (recycle or send2trash)(str(path))
        if path.exists():
            raise OSError('Recycle Bin did not accept this file; original retained')
        with closing(_connection()) as conn, conn:
            conn.execute("UPDATE physical_files SET availability='RECYCLED' WHERE id=(SELECT file_id FROM file_locations WHERE path_key=?)", (identity.path_key(path),))
            touched = set()
            for season in conn.execute('SELECT * FROM seasons WHERE season_folder_path IS NOT NULL').fetchall():
                names = json.loads(season['video_files_json'] or '[]')
                remaining = [n for n in names if identity.path_key(Path(season['season_folder_path']) / n) != identity.path_key(path)]
                if remaining != names:
                    conn.execute('UPDATE seasons SET video_files_json=?,size_bytes=MAX(0,size_bytes-?),storage_state=? WHERE id=?', (json.dumps(remaining), before[0], season['storage_state'] if remaining else 'WATCHED_REMOVED', season['id']))
                    touched.add(season['franchise_id'])
            for fid in touched:
                conn.execute("UPDATE franchises SET total_size_bytes=(SELECT COALESCE(SUM(size_bytes),0) FROM seasons WHERE franchise_id=?) WHERE id=?", (fid, fid))
                states = {r[0] for r in conn.execute('SELECT storage_state FROM seasons WHERE franchise_id=?', (fid,))}
                state = 'PARTIALLY_ON_DISK' if {'ON_DISK','WATCHED_REMOVED'} <= states else 'ON_DISK' if 'ON_DISK' in states else 'WATCHED_REMOVED' if 'WATCHED_REMOVED' in states else 'NOT_DOWNLOADED'
                conn.execute('UPDATE franchises SET storage_state=? WHERE id=?', (state, fid))
            conn.execute("UPDATE file_operations SET status='COMPLETED',updated_at=? WHERE id=?", (int(time.time()), operation_id))
    except Exception as error:
        _status(operation_id, 'FAILED' if path.exists() else 'REVIEW', str(error))
        raise
