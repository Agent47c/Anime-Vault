"""
Database layer — SQLite 3 (WAL Mode)
Handles schema creation, migrations, and all CRUD queries for the
Anime Library & Storage Manager.
"""

import sqlite3
import json
import os
from contextlib import closing
from contextlib import contextmanager
import threading

_refresh_view = threading.local()


class _SnapshotConnection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, parameters=()):
        if not sql.lstrip().upper().startswith("SELECT"):
            raise RuntimeError("Refresh snapshots are read-only")
        return self.connection.execute(sql, parameters)

    def close(self):
        pass


@contextmanager
def refresh_view(snapshot):
    previous = getattr(_refresh_view, "snapshot", None)
    _refresh_view.snapshot = snapshot
    try:
        yield
    finally:
        _refresh_view.snapshot = previous


def current_refresh_view():
    return getattr(_refresh_view, "snapshot", None)
from pathlib import Path
from typing import Optional, List, Dict, Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "library.db"
COVERS_DIR = DATA_DIR / "covers"
EXPORTS_DIR = DATA_DIR / "exports"


def _ensure_dirs():
    """Create data directories if they don't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
_SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS app_state (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS watched_directories (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_path            TEXT UNIQUE NOT NULL,
    auto_organize_seasons  BOOLEAN DEFAULT 1,
    last_scanned_at        DATETIME
);

CREATE TABLE IF NOT EXISTS franchises (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    anilist_id        INTEGER UNIQUE,
    mal_id            INTEGER,
    display_title     TEXT NOT NULL,
    title_en          TEXT,
    title_romaji      TEXT,
    title_native      TEXT,
    synopsis          TEXT DEFAULT '',
    genres            TEXT DEFAULT '[]',
    is_adult          BOOLEAN DEFAULT 0,
    cover_filename    TEXT,
    watch_status      TEXT DEFAULT 'WATCHED',
    storage_state     TEXT DEFAULT 'ON_DISK',
    total_size_bytes  INTEGER DEFAULT 0,
    user_rating       INTEGER CHECK(user_rating IS NULL OR (user_rating BETWEEN 1 AND 10)),
    user_notes        TEXT DEFAULT '',
    is_custom         BOOLEAN DEFAULT 0,
    needs_review      BOOLEAN DEFAULT 0,
    raw_import_name   TEXT,
    has_new_update    BOOLEAN DEFAULT 0,
    update_details    TEXT,
    root_folder_path  TEXT,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_checked_at   DATETIME
);

CREATE TABLE IF NOT EXISTS seasons (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    franchise_id      INTEGER NOT NULL,
    anilist_id        INTEGER UNIQUE,
    season_number     INTEGER DEFAULT 1,
    relation_type     TEXT DEFAULT 'SEASON',
    title_display     TEXT NOT NULL,
    title_romaji      TEXT,
    episodes_total    INTEGER,
    airing_status     TEXT DEFAULT 'FINISHED',
    next_airing_ep    INTEGER,
    next_airing_at    INTEGER,
    watch_status      TEXT DEFAULT 'WATCHED',
    season_folder_path TEXT,
    size_bytes        INTEGER DEFAULT 0,
    video_files_json  TEXT DEFAULT '[]',
    storage_state     TEXT DEFAULT 'ON_DISK',
    FOREIGN KEY (franchise_id) REFERENCES franchises(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_franchises_display_title
    ON franchises(display_title COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_franchises_rating
    ON franchises(user_rating DESC);
CREATE INDEX IF NOT EXISTS idx_franchises_size
    ON franchises(total_size_bytes DESC);
"""


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------
def get_connection() -> sqlite3.Connection:
    """Return a new connection with WAL mode and row factory enabled."""
    snapshot = current_refresh_view()
    if snapshot is not None:
        return _SnapshotConnection(snapshot["connection"])
    _ensure_dirs()
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Run the full schema DDL (safe to call multiple times)."""
    conn = get_connection()
    conn.executescript(_SCHEMA_SQL)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(franchises)")}
    for name in ("banner_filename", "metadata_json"):
        if name not in columns:
            conn.execute(f"ALTER TABLE franchises ADD COLUMN {name} TEXT")
    season_columns = {row["name"] for row in conn.execute("PRAGMA table_info(seasons)")}
    for name, kind in (("episode_start", "INTEGER"), ("episode_end", "INTEGER"), ("numbering_source", "TEXT"), ("local_scan_key", "TEXT"), ("scan_root", "TEXT")):
        if name not in season_columns:
            conn.execute(f"ALTER TABLE seasons ADD COLUMN {name} {kind}")
    conn.commit()
    from app.core.identity import migrate
    migrate(conn)
    from app.core.scan_state import migrate as migrate_scanning
    migrate_scanning(conn)
    conn.close()


# ---------------------------------------------------------------------------
# app_state helpers
# ---------------------------------------------------------------------------
def get_state(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = get_connection()
    row = conn.execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_state(key: str, value: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO app_state (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# watched_directories CRUD
# ---------------------------------------------------------------------------
def add_watched_directory(folder_path: str, auto_organize: bool = True) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT OR IGNORE INTO watched_directories (folder_path, auto_organize_seasons) VALUES (?, ?)",
        (folder_path, auto_organize),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_watched_directories() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT w.*, COALESCE(s.state,'UNSCANNED') AS availability,s.error AS scan_error FROM watched_directories w LEFT JOIN scan_roots s ON s.root_id=w.id ORDER BY w.folder_path").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def remove_watched_directory(dir_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM watched_directories WHERE id = ?", (dir_id,))
    conn.commit()
    conn.close()


def update_watched_directory_scan_time(dir_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE watched_directories SET last_scanned_at = CURRENT_TIMESTAMP WHERE id = ?",
        (dir_id,),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# franchises CRUD
# ---------------------------------------------------------------------------
def upsert_franchise(data: Dict[str, Any]) -> int:
    """Insert or update a franchise. Returns the franchise id."""
    conn = get_connection()
    anilist_id = data.get("anilist_id")

    # Check if exists by anilist_id
    existing = None
    if anilist_id:
        existing = conn.execute(
            "SELECT id FROM franchises WHERE anilist_id = ?", (anilist_id,)
        ).fetchone()

    if existing:
        fid = existing["id"]
        # Merge: update fields that are non-null in new data
        sets = []
        vals = []
        for key in [
            "mal_id", "display_title", "title_en", "title_romaji", "title_native",
            "synopsis", "genres", "is_adult", "cover_filename", "metadata_json", "watch_status",
            "storage_state", "total_size_bytes", "user_rating", "user_notes",
            "is_custom", "needs_review", "raw_import_name", "has_new_update",
            "update_details", "root_folder_path",
        ]:
            if key in data and data[key] is not None:
                sets.append(f"{key} = ?")
                vals.append(data[key])
        if sets:
            vals.append(fid)
            conn.execute(
                f"UPDATE franchises SET {', '.join(sets)} WHERE id = ?", vals
            )
            conn.commit()
        conn.close()
        return fid
    else:
        cols = [
            "anilist_id", "mal_id", "display_title", "title_en", "title_romaji",
            "title_native", "synopsis", "genres", "is_adult", "cover_filename", "metadata_json",
            "watch_status", "storage_state", "total_size_bytes", "user_rating",
            "user_notes", "is_custom", "needs_review", "raw_import_name",
            "has_new_update", "update_details", "root_folder_path",
        ]
        present = {k: data.get(k) for k in cols if k in data}
        if "display_title" not in present:
            present["display_title"] = data.get("title_en") or data.get("title_romaji") or "Unknown"
        placeholders = ", ".join(["?"] * len(present))
        col_names = ", ".join(present.keys())
        cur = conn.execute(
            f"INSERT INTO franchises ({col_names}) VALUES ({placeholders})",
            list(present.values()),
        )
        conn.commit()
        fid = cur.lastrowid
        conn.close()
        return fid


def get_franchise(fid: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM franchises WHERE id = ?", (fid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_franchise_by_anilist_id(anilist_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM franchises WHERE anilist_id = ?", (anilist_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_franchises(
    sort_by: str = "display_title",
    sort_order: str = "ASC",
    search: str = "",
    watch_status: Optional[str] = None,
    storage_state: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve franchises with optional filtering and sorting."""
    conn = get_connection()
    query = "SELECT * FROM franchises WHERE 1=1"
    params = []

    if search:
        query += " AND (display_title LIKE ? OR title_romaji LIKE ? OR title_native LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])

    if watch_status:
        query += " AND watch_status = ?"
        params.append(watch_status)

    if storage_state == "RECLAIM":
        query += " AND watch_status = 'WATCHED' AND storage_state IN ('ON_DISK', 'PARTIALLY_ON_DISK') AND total_size_bytes > 0"
    elif storage_state:
        query += " AND storage_state = ?"
        params.append(storage_state)


    # Sort mapping
    sort_map = {
        "display_title": "display_title COLLATE NOCASE",
        "user_rating": "user_rating",
        "total_size_bytes": "total_size_bytes",
        "created_at": "created_at",
        "watch_status": "watch_status",
    }
    col = sort_map.get(sort_by, "display_title COLLATE NOCASE")
    query += f" ORDER BY {col} {sort_order}"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_franchise(fid: int):
    conn = get_connection()
    conn.execute("DELETE FROM franchises WHERE id = ?", (fid,))
    conn.commit()
    conn.close()


def update_franchise_field(fid: int, field: str, value: Any):
    """Update a single field on a franchise."""
    conn = get_connection()
    conn.execute(f"UPDATE franchises SET {field} = ? WHERE id = ?", (value, fid))
    conn.commit()
    conn.close()


def recalculate_franchise_size(fid: int):
    """Sum all season sizes and update total_size_bytes."""
    conn = get_connection()
    row = conn.execute(
        "SELECT COALESCE(SUM(size_bytes), 0) as total FROM seasons WHERE franchise_id = ?",
        (fid,),
    ).fetchone()
    total = row["total"]
    conn.execute(
        "UPDATE franchises SET total_size_bytes = ? WHERE id = ?", (total, fid)
    )
    conn.commit()
    conn.close()


def recalculate_franchise_storage_state(fid: int):
    """Set storage_state based on child season states.
    If on-disk seasons with video files exist, franchise is ON_DISK unless
    some seasons were explicitly deleted by the user (WATCHED_REMOVED).
    Un-downloaded optional AniList relation entries (movies/OVAs) do NOT
    downgrade an active series to PARTIALLY_ON_DISK.
    """
    conn = get_connection()
    seasons_list = conn.execute(
        "SELECT storage_state, size_bytes, relation_type, season_number FROM seasons WHERE franchise_id = ?", (fid,)
    ).fetchall()
    if not seasons_list:
        f_row = conn.execute("SELECT total_size_bytes FROM franchises WHERE id = ?", (fid,)).fetchone()
        if f_row and (f_row["total_size_bytes"] or 0) > 0:
            new_state = "ON_DISK"
        else:
            new_state = "NOT_DOWNLOADED"
    else:
        on_disk = [s for s in seasons_list if s["storage_state"] == "ON_DISK" and (s["size_bytes"] or 0) > 0]
        removed = [s for s in seasons_list if s["storage_state"] == "WATCHED_REMOVED"]

        if on_disk:
            if removed:
                new_state = "PARTIALLY_ON_DISK"
            else:
                new_state = "ON_DISK"
        elif removed:
            new_state = "WATCHED_REMOVED"
        else:
            new_state = "NOT_DOWNLOADED"

    conn.execute(
        "UPDATE franchises SET storage_state = ? WHERE id = ?", (new_state, fid)
    )
    conn.commit()
    conn.close()


def find_franchise_by_folder_path(folder_path: str) -> Optional[Dict[str, Any]]:
    """Case-insensitive search by root_folder_path."""
    if not folder_path:
        return None
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM franchises WHERE root_folder_path = ? COLLATE NOCASE LIMIT 1",
        (folder_path,),
    ).fetchone()
    if not row:
        row = conn.execute(
            "SELECT f.* FROM franchises f JOIN seasons s ON s.franchise_id=f.id "
            "WHERE s.season_folder_path = ? COLLATE NOCASE OR s.scan_root = ? COLLATE NOCASE LIMIT 1",
            (folder_path, folder_path),
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def find_franchise_by_title(title: str) -> Optional[Dict[str, Any]]:
    """Case-insensitive search by display_title, title_en, or title_romaji."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM franchises WHERE "
        "display_title = ? COLLATE NOCASE OR "
        "title_en = ? COLLATE NOCASE OR "
        "title_romaji = ? COLLATE NOCASE "
        "LIMIT 2",
        (title, title, title),
    ).fetchall()
    conn.close()
    return dict(rows[0]) if len(rows) == 1 else None



# ---------------------------------------------------------------------------
# seasons CRUD
# ---------------------------------------------------------------------------
def upsert_season(data: Dict[str, Any]) -> int:
    """Insert or update a season. Returns the season id."""
    conn = get_connection()
    anilist_id = data.get("anilist_id")

    existing = None
    if anilist_id:
        existing = conn.execute(
            "SELECT id FROM seasons WHERE anilist_id = ?", (anilist_id,)
        ).fetchone()

    if existing:
        sid = existing["id"]
        override=conn.execute('SELECT value FROM app_state WHERE key=?',('season_number_override:'+str(sid),)).fetchone()
        if override:
            data=dict(data);data['season_number']=int(override[0])
        sets = []
        vals = []
        for key in [
            "franchise_id", "season_number", "relation_type", "title_display",
            "title_romaji", "episodes_total", "airing_status", "next_airing_ep",
            "next_airing_at", "watch_status", "season_folder_path", "size_bytes",
            "video_files_json", "storage_state", "episode_start", "episode_end", "numbering_source", "local_scan_key", "scan_root",
        ]:
            if key in data and data[key] is not None:
                sets.append(f"{key} = ?")
                vals.append(data[key])
        if sets:
            vals.append(sid)
            conn.execute(
                f"UPDATE seasons SET {', '.join(sets)} WHERE id = ?", vals
            )
            from app.core.identity import sync_season
            sync_season(conn, dict(conn.execute('SELECT * FROM seasons WHERE id=?', (sid,)).fetchone()))
            conn.commit()
        conn.close()
        return sid
    else:
        cols = [
            "franchise_id", "anilist_id", "season_number", "relation_type",
            "title_display", "title_romaji", "episodes_total", "airing_status",
            "next_airing_ep", "next_airing_at", "watch_status",
            "season_folder_path", "size_bytes", "video_files_json", "storage_state", "episode_start", "episode_end", "numbering_source", "local_scan_key", "scan_root",
        ]
        present = {k: data.get(k) for k in cols if k in data}
        if "franchise_id" not in present:
            conn.close()
            raise ValueError("franchise_id is required for new seasons")
        if "title_display" not in present:
            present["title_display"] = "Unknown Season"
        placeholders = ", ".join(["?"] * len(present))
        col_names = ", ".join(present.keys())
        cur = conn.execute(
            f"INSERT INTO seasons ({col_names}) VALUES ({placeholders})",
            list(present.values()),
        )
        from app.core.identity import sync_season
        sync_season(conn, dict(conn.execute('SELECT * FROM seasons WHERE id=?', (cur.lastrowid,)).fetchone()))
        conn.commit()
        sid = cur.lastrowid
        conn.close()
        return sid


def get_seasons_for_franchise(fid: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM seasons WHERE franchise_id = ? ORDER BY CASE WHEN relation_type='SEASON' AND (season_number=0 OR season_number IS NULL) THEN 10000 ELSE season_number END, relation_type",
        (fid,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_season(sid: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM seasons WHERE id = ?", (sid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_season_folder(sid: int, folder: str):
    """Index a manually selected season folder while preserving its metadata."""
    from contextlib import closing
    from app.core.scanner import collect_video_groups

    root = Path(folder).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Choose a season folder.")
    files = sorted({file for group in collect_video_groups(str(root)) for file in group["files"]})
    if not files:
        raise ValueError("The selected folder contains no supported videos.")
    names = json.dumps([file.relative_to(root).as_posix() for file in files])
    size = sum(file.stat().st_size for file in files)
    with closing(get_connection()) as conn, conn:
        season = conn.execute("SELECT * FROM seasons WHERE id=?", (sid,)).fetchone()
        if not season:
            raise ValueError("This season no longer exists.")
        fid = season["franchise_id"]
        current = conn.execute("SELECT root_folder_path FROM franchises WHERE id=?", (fid,)).fetchone()[0]
        scan_root = next(
            (str(path) for value in (season["scan_root"], current) if value
             for path in (Path(value).resolve(),) if path == root or path in root.parents),
            str(root),
        )
        conn.execute(
            "UPDATE seasons SET season_folder_path=?, scan_root=?, video_files_json=?, size_bytes=?, storage_state='ON_DISK' WHERE id=?",
            (str(root), scan_root, names, size, sid),
        )
        if not current or not Path(current).is_dir():
            conn.execute("UPDATE franchises SET root_folder_path=? WHERE id=?", (scan_root, fid))
    recalculate_franchise_size(fid)
    recalculate_franchise_storage_state(fid)


def delete_season(sid: int):
    conn = get_connection()
    row = conn.execute("SELECT franchise_id FROM seasons WHERE id = ?", (sid,)).fetchone()
    fid = row["franchise_id"] if row else None
    conn.execute("DELETE FROM seasons WHERE id = ?", (sid,))
    conn.commit()
    conn.close()
    if fid:
        recalculate_franchise_size(fid)
        recalculate_franchise_storage_state(fid)


def update_season_field(sid: int, field: str, value: Any):
    conn = get_connection()
    conn.execute(f"UPDATE seasons SET {field} = ? WHERE id = ?", (value, sid))
    conn.commit()
    conn.close()


def mark_season_removed(sid: int):
    """Mark a season as removed from disk."""
    conn = get_connection()
    conn.execute(
        "UPDATE seasons SET storage_state = 'WATCHED_REMOVED', size_bytes = 0, "
        "video_files_json = '[]' WHERE id = ?",
        (sid,),
    )
    row = conn.execute("SELECT franchise_id FROM seasons WHERE id = ?", (sid,)).fetchone()
    conn.commit()
    conn.close()
    if row:
        recalculate_franchise_size(row["franchise_id"])
        recalculate_franchise_storage_state(row["franchise_id"])


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------
def get_library_stats() -> Dict[str, Any]:
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as c FROM franchises").fetchone()["c"]
    on_disk = conn.execute(
        "SELECT COUNT(*) as c FROM franchises WHERE storage_state = 'ON_DISK'"
    ).fetchone()["c"]
    partial = conn.execute(
        "SELECT COUNT(*) as c FROM franchises WHERE storage_state = 'PARTIALLY_ON_DISK'"
    ).fetchone()["c"]
    removed = conn.execute(
        "SELECT COUNT(*) as c FROM franchises WHERE storage_state = 'WATCHED_REMOVED'"
    ).fetchone()["c"]
    watched = conn.execute(
        "SELECT COUNT(*) as c FROM franchises WHERE watch_status = 'WATCHED'"
    ).fetchone()["c"]
    total_size = conn.execute(
        "SELECT COALESCE(SUM(total_size_bytes), 0) as s FROM franchises"
    ).fetchone()["s"]
    reclaim_size = conn.execute(
        "SELECT COALESCE(SUM(total_size_bytes), 0) as s FROM franchises "
        "WHERE watch_status = 'WATCHED' AND storage_state IN ('ON_DISK', 'PARTIALLY_ON_DISK')"
    ).fetchone()["s"]

    # Count indexed files
    season_files_rows = conn.execute(
        "SELECT video_files_json FROM seasons WHERE storage_state != 'WATCHED_REMOVED'"
    ).fetchall()
    total_files = 0
    for r in season_files_rows:
        try:
            arr = json.loads(r["video_files_json"] or "[]")
            total_files += len(arr)
        except Exception:
            pass

    conn.close()
    return {
        "total_franchises": total,
        "on_disk": on_disk,
        "partially_on_disk": partial,
        "watched_removed": removed,
        "watched_count": watched,
        "total_size_bytes": total_size,
        "total_bytes": total_size,  # alias
        "potential_reclaim_bytes": reclaim_size,
        "total_files_indexed": total_files,
    }


def rematch_franchise(fid: int, anilist_data: Dict[str, Any], cover_filename: Optional[str] = None):
    """Update metadata link without touching local folders or files."""
    conn = get_connection()
    sets = [
        "anilist_id = ?",
        "mal_id = ?",
        "display_title = ?",
        "title_en = ?",
        "title_romaji = ?",
        "title_native = ?",
        "synopsis = ?",
        "genres = ?",
        "is_adult = ?",
        "needs_review = 0",
        "metadata_json = NULL",
        "banner_filename = NULL",
    ]
    vals = [
        anilist_data.get("anilist_id"),
        anilist_data.get("mal_id"),
        anilist_data.get("display_title") or anilist_data.get("title_en") or anilist_data.get("title_romaji"),
        anilist_data.get("title_en"),
        anilist_data.get("title_romaji"),
        anilist_data.get("title_native"),
        anilist_data.get("synopsis", ""),
        anilist_data.get("genres", "[]") if isinstance(anilist_data.get("genres"), str) else json.dumps(anilist_data.get("genres", [])),
        1 if anilist_data.get("is_adult") else 0,
    ]
    if cover_filename:
        sets.append("cover_filename = ?")
        vals.append(cover_filename)

    vals.append(fid)
    conn.execute(f"UPDATE franchises SET {', '.join(sets)} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def backup_database(directory=None) -> str:
    """Create a timestamped SQLite database backup. Returns the backup filepath."""
    from datetime import datetime
    import uuid
    _ensure_dirs()
    backups_dir = Path(directory or get_state('backup_directory',str(DATA_DIR/'backups')))
    if not backups_dir.is_absolute(): raise ValueError('Choose an absolute backup directory.')
    backups_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backups_dir / f"library_backup_{ts}_{uuid.uuid4().hex[:8]}.db"
    with closing(get_connection()) as source, closing(sqlite3.connect(str(backup_file))) as target:
        source.backup(target)
    return str(backup_file)


def restore_database(backup_path: str) -> bool:
    """Restore through SQLite so active WAL files cannot override the backup."""
    src=Path(backup_path)
    if not src.is_file(): raise FileNotFoundError(f"Backup file not found: {backup_path}")
    with closing(sqlite3.connect(src.resolve().as_uri()+'?mode=ro',uri=True)) as incoming:
        if incoming.execute('PRAGMA quick_check').fetchone()[0]!='ok':
            raise ValueError('Backup failed its database integrity check.')
        incoming.execute('SELECT COUNT(*) FROM franchises').fetchone()
        rollback=backup_database()
        try:
            with closing(get_connection()) as target: incoming.backup(target)
            init_db()
            return True
        except Exception:
            with closing(sqlite3.connect(rollback)) as safety, closing(get_connection()) as target:
                safety.backup(target)
            raise


def dismiss_updates(fid: int):
    """Remember each dismissed change, without hiding the library entry."""
    with closing(get_connection()) as conn, conn:
        row = conn.execute("SELECT update_details FROM franchises WHERE id = ?", (fid,)).fetchone()
        if not row:
            return
        key = f"dismissed_updates:{fid}"
        old = conn.execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
        dismissed = set(json.loads(old["value"])) if old else set()
        dismissed.update(part.strip() for part in (row["update_details"] or "").split(" | ") if part.strip())
        conn.execute("INSERT INTO app_state(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(sorted(dismissed))))
        conn.execute("UPDATE franchises SET has_new_update=0, update_details=NULL WHERE id=?", (fid,))


def mark_watched_and_ignore_updates(fid):
    """Mark all owned series records watched and dismiss only known changes."""
    series = get_series(fid)
    if not series:
        return
    members = series.get("series_member_ids", [fid])
    with closing(get_connection()) as conn, conn:
        for member_id in members:
            record = conn.execute("SELECT update_details FROM franchises WHERE id=?", (member_id,)).fetchone()
            if record is None:
                continue
            key = f"dismissed_updates:{member_id}"
            old = conn.execute("SELECT value FROM app_state WHERE key=?", (key,)).fetchone()
            dismissed = set(json.loads(old["value"])) if old else set()
            dismissed.update(part.strip() for part in (record["update_details"] or "").split(" | ") if part.strip())
            for state_key, value in ((key, json.dumps(sorted(dismissed))), (f"update_disposition:{member_id}", "new"), (f"muted_updates:{member_id}", "0")):
                conn.execute("INSERT INTO app_state(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (state_key, value))
            conn.execute("UPDATE franchises SET watch_status='WATCHED',has_new_update=0,update_details=NULL WHERE id=?", (member_id,))


def publish_updates(fid: int, details: Optional[str]) -> Optional[str]:
    """Publish only changes not already dismissed; a genuinely new change reappears."""
    with closing(get_connection()) as conn, conn:
        row = conn.execute("SELECT value FROM app_state WHERE key=?", (f"dismissed_updates:{fid}",)).fetchone()
        dismissed = set(json.loads(row["value"])) if row else set()
        muted = conn.execute("SELECT value FROM app_state WHERE key=?", (f"muted_updates:{fid}",)).fetchone()
        suppressed = bool(muted and muted["value"] == "1")
        pending = [part.strip() for part in (details or "").split(" | ") if part.strip() and part.strip() not in dismissed]
        result = " | ".join(dict.fromkeys(pending)) or None
        conn.execute("UPDATE franchises SET has_new_update=?, update_details=?, last_checked_at=CURRENT_TIMESTAMP WHERE id=?", (bool(result) and not suppressed, result, fid))
    return None if suppressed else result


def cache_media(fid: int, media: Dict[str, Any], cover=None, banner=None):
    """Save provider metadata and artwork without changing personal library fields."""
    from app.core.release_calendar import remember_metadata
    previous = get_franchise(fid)
    if previous:
        try:
            remember_metadata(json.loads(previous.get('metadata_json') or '{}'))
        except (TypeError, ValueError):
            pass
    remember_metadata(media)
    from app.core.anilist_client import extract_franchise_data
    data = extract_franchise_data(media)
    with closing(get_connection()) as conn, conn:
        conn.execute("UPDATE franchises SET synopsis=?, genres=?, metadata_json=?, cover_filename=COALESCE(?,cover_filename), banner_filename=COALESCE(?,banner_filename) WHERE id=?", (data["synopsis"], data["genres"], json.dumps(media, ensure_ascii=False), cover, banner, fid))


def update_dispositions():
    """Read all saved update choices with a single database connection."""
    with closing(get_connection()) as conn:
        rows = conn.execute("SELECT key,value FROM app_state WHERE key LIKE 'update_disposition:%' OR key LIKE 'muted_updates:%'").fetchall()
    choices, muted = {}, set()
    for row in rows:
        prefix, _, number = row["key"].partition(":")
        if not number.isdigit():
            continue
        fid = int(number)
        if prefix == "update_disposition" and row["value"] in ("new", "later", "not_interested", "muted"):
            choices[fid] = row["value"]
        elif prefix == "muted_updates" and row["value"] == "1":
            muted.add(fid)
    for fid in muted:
        choices.setdefault(fid, "muted")
    return choices


def update_disposition(fid):
    """Read a saved update choice, including older muted entries."""
    state = get_state(f"update_disposition:{fid}")
    if state in ("later", "not_interested", "muted"):
        return state
    return "muted" if get_state(f"muted_updates:{fid}", "0") == "1" else "new"


def set_update_disposition(fid, disposition):
    if disposition not in ("new", "later", "not_interested", "muted"):
        raise ValueError("Unknown update choice")
    with closing(get_connection()) as conn, conn:
        record = conn.execute("SELECT update_details FROM franchises WHERE id=?", (fid,)).fetchone()
        if record is None:
            return
        for key, value in ((f"update_disposition:{fid}", disposition), (f"muted_updates:{fid}", "0" if disposition == "new" else "1")):
            conn.execute("INSERT INTO app_state(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        dismissed_row = conn.execute("SELECT value FROM app_state WHERE key=?", (f"dismissed_updates:{fid}",)).fetchone()
        dismissed = set(json.loads(dismissed_row["value"])) if dismissed_row else set()
        pending = [part.strip() for part in (record["update_details"] or "").split(" | ") if part.strip() and part.strip() not in dismissed]
        details = " | ".join(dict.fromkeys(pending)) or None
        conn.execute("UPDATE franchises SET has_new_update=?, update_details=? WHERE id=?", (bool(details) and disposition == "new", details, fid))


def mute_updates(fid, muted=True):
    set_update_disposition(fid, "muted" if muted else "new")


def updates_muted(fid):
    return get_state(f"muted_updates:{fid}", "0") == "1"


def get_series_library(**filters):
    snapshot=current_refresh_view()
    if not filters and snapshot is not None and 'series_groups' in snapshot:
        return snapshot['series_groups']
    from app.core.series import build_groups
    all_entries = get_all_franchises(sort_by=filters.get("sort_by", "display_title"), sort_order=filters.get("sort_order", "ASC"))
    matching = {entry["id"] for entry in get_all_franchises(**filters)}
    related = list(json.loads(get_state("series_relation_cache", "{}" )).values())
    return [entry for entry in build_groups(all_entries, related, json.loads(get_state("series_overrides", "{}"))) if matching.intersection(entry["series_member_ids"])]


def get_series(fid):
    return next((entry for entry in get_series_library() if fid in entry["series_member_ids"]), get_franchise(fid))


def uses_continuous_episodes(series):
    if not series:
        return False
    value = get_state(f"continuous_episodes:{series['id']}")
    return value == "1" if value is not None else series.get("anilist_id") == 21


def set_continuous_episodes(fid, enabled):
    set_state(f"continuous_episodes:{fid}", "1" if enabled else "0")


def get_series_seasons(fid, series=None):
    series = get_series(fid) if series is None else series
    if not series:
        return []
    seasons = []
    for member_id in series.get("series_member_ids", [fid]):
        member = get_franchise(member_id)
        for season in get_seasons_for_franchise(member_id):
            season["release_title"] = member["display_title"]
            seasons.append(season)
    return sorted(seasons, key=lambda season: ((season.get('season_number') or 10000) if season.get('relation_type')=='SEASON' else (season.get('season_number') or 0), season['id']))


def group_with_series(member_id, target_id):
    if member_id == target_id or not get_franchise(member_id) or not get_franchise(target_id):
        raise ValueError("Choose two different existing library records")
    links = json.loads(get_state("series_overrides", "{}"))
    # Target the current group's representative and link all members together.
    source = get_series(member_id)
    target = get_series(target_id)
    for fid in source["series_member_ids"]:
        links[str(fid)] = target["id"]
    set_state("series_overrides", json.dumps(links))


def reset_manual_grouping(fid):
    members = set(get_series(fid)["series_member_ids"])
    links = json.loads(get_state("series_overrides", "{}"))
    links = {source: target for source, target in links.items() if int(source) not in members and target not in members}
    set_state("series_overrides", json.dumps(links))
