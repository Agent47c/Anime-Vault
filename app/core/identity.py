"""Stable content identities; legacy season inventories are compatibility views.

Never infer that equal filenames identify the same physical file. Missing files
retain episode associations and history until an explicit repair is approved.
"""
import json
import os
from pathlib import Path
from contextlib import closing
import sqlite3
import time
import re

from app import db
from app.core.parser import extract_episode_numbers

SCHEMA = """
CREATE TABLE IF NOT EXISTS library_series (
 id INTEGER PRIMARY KEY, franchise_id INTEGER UNIQUE REFERENCES franchises(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS releases (
 id INTEGER PRIMARY KEY, series_id INTEGER NOT NULL REFERENCES library_series(id),
 release_key TEXT NOT NULL, provider_id INTEGER, kind TEXT NOT NULL,
 UNIQUE(series_id, release_key)
);
CREATE TABLE IF NOT EXISTS season_releases (
 season_id INTEGER PRIMARY KEY REFERENCES seasons(id) ON DELETE CASCADE,
 release_id INTEGER NOT NULL REFERENCES releases(id)
);
CREATE TABLE IF NOT EXISTS episodes (
 id INTEGER PRIMARY KEY, release_id INTEGER NOT NULL REFERENCES releases(id),
 identity_key TEXT NOT NULL, original_number INTEGER, numbering_scheme TEXT NOT NULL,
 release_number INTEGER, mapping_verified INTEGER NOT NULL DEFAULT 0,
 mapping_source TEXT NOT NULL DEFAULT 'LOCAL',
 release_state TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK(release_state IN ('AIRED','UPCOMING','UNKNOWN')),
 aired_at INTEGER, notes TEXT NOT NULL DEFAULT '', UNIQUE(release_id, identity_key)
);
CREATE TABLE IF NOT EXISTS physical_files (
 id INTEGER PRIMARY KEY, season_id INTEGER REFERENCES seasons(id) ON DELETE SET NULL,
 original_name TEXT NOT NULL, size_bytes INTEGER, mtime_ns INTEGER,
 device TEXT, inode TEXT, sha256 TEXT, availability TEXT NOT NULL DEFAULT 'UNKNOWN'
);
CREATE TABLE IF NOT EXISTS file_locations (
 file_id INTEGER PRIMARY KEY REFERENCES physical_files(id), path TEXT NOT NULL,
 path_key TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS file_episodes (
 file_id INTEGER REFERENCES physical_files(id), episode_id INTEGER REFERENCES episodes(id),
 PRIMARY KEY(file_id, episode_id)
);
CREATE TABLE IF NOT EXISTS episode_history (
 id INTEGER PRIMARY KEY, episode_id INTEGER NOT NULL REFERENCES episodes(id),
 played_at INTEGER NOT NULL, position_seconds REAL, event TEXT NOT NULL DEFAULT 'PLAYED'
);
CREATE TABLE IF NOT EXISTS repair_candidates (
 id INTEGER PRIMARY KEY, file_id INTEGER NOT NULL REFERENCES physical_files(id),
 target TEXT NOT NULL, evidence TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'REVIEW',
 UNIQUE(file_id, target)
);
CREATE TABLE IF NOT EXISTS file_operations (
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, source TEXT NOT NULL, target TEXT,
 signature TEXT NOT NULL, status TEXT NOT NULL, error TEXT,
 created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_episode_history ON episode_history(episode_id, played_at);
CREATE INDEX IF NOT EXISTS idx_file_season ON physical_files(season_id);
"""


def path_key(path):
    # Windows may return both 8.3 and long spellings of the same folder.
    return os.path.normcase(str(Path(path).resolve(strict=False)))


def signature(path):
    stat = Path(path).stat()
    return (stat.st_size, stat.st_mtime_ns, str(stat.st_dev), str(stat.st_ino))


def migrate(conn):
    # Called after the legacy migration has committed. SQLite backup includes WAL.
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='episodes'").fetchone():
        if conn.execute("SELECT 1 FROM seasons LIMIT 1").fetchone():
            folder = db.EXPORTS_DIR / 'migration-backups'
            folder.mkdir(parents=True, exist_ok=True)
            backup = folder / f'pre-identity-{time.time_ns()}.db'
            with closing(sqlite3.connect(str(backup))) as target:
                conn.backup(target)
    conn.executescript(SCHEMA)
    if 'mapping_source' not in {r['name'] for r in conn.execute('PRAGMA table_info(episodes)')}:
        conn.execute("ALTER TABLE episodes ADD COLUMN mapping_source TEXT NOT NULL DEFAULT 'LOCAL'")
        conn.commit()
    if conn.execute("SELECT 1 FROM app_state WHERE key='identity_schema_version'").fetchone():
        return
    with conn:
        for season in conn.execute('SELECT * FROM seasons').fetchall():
            sync_season(conn, dict(season), stat_files=False)
        last = conn.execute("SELECT value FROM app_state WHERE key='last_episode_path'").fetchone()
        if last and last[0] and not conn.execute("SELECT 1 FROM app_state WHERE key='last_episode_id'").fetchone():
            record_play(conn, last[0], event='LEGACY_LAST_PLAYED')
        conn.execute("INSERT OR REPLACE INTO app_state VALUES ('identity_schema_version','1')")


def _release(conn, season):
    linked = conn.execute('SELECT release_id FROM season_releases WHERE season_id=?', (season['id'],)).fetchone()
    if linked:
        # Folder rescans must not reinterpret existing episode identities.
        return linked[0]
    fid = season['franchise_id']
    conn.execute('INSERT OR IGNORE INTO library_series(franchise_id) VALUES (?)', (fid,))
    series = conn.execute('SELECT id FROM library_series WHERE franchise_id=?', (fid,)).fetchone()[0]
    franchise = conn.execute('SELECT anilist_id FROM franchises WHERE id=?', (fid,)).fetchone()
    choice = conn.execute('SELECT value FROM app_state WHERE key=?', (f'continuous_episodes:{fid}',)).fetchone()
    continuous = choice[0] == '1' if choice else bool(franchise and franchise[0] == 21)
    kind = season.get('relation_type') or 'SEASON'
    # Separate releases for movies/special collections; no merge by episode number.
    key = ('continuous' if continuous and kind == 'SEASON' else
           f"provider:{season['anilist_id']}" if season.get('anilist_id') else
           f"local:{kind}:{season.get('season_number')}" if kind == 'SEASON' and season.get('season_number') else
           f"local-folder:{season['id']}")
    provider = season.get('anilist_id') or (franchise[0] if continuous and kind == 'SEASON' and franchise else None)
    conn.execute('INSERT OR IGNORE INTO releases(series_id,release_key,provider_id,kind) VALUES (?,?,?,?)',
                 (series, key, provider, kind))
    rid = conn.execute('SELECT id FROM releases WHERE series_id=? AND release_key=?', (series, key)).fetchone()[0]
    conn.execute('INSERT INTO season_releases VALUES (?,?)', (season['id'], rid))
    return rid


def sync_season(conn, season, stat_files=True, changed_paths=None):
    if not season.get('season_folder_path'):
        return
    rid = _release(conn, season)
    continuous = conn.execute('SELECT release_key FROM releases WHERE id=?', (rid,)).fetchone()[0] == 'continuous'
    for name in json.loads(season.get('video_files_json') or '[]'):
        path = Path(season['season_folder_path']) / name
        row = conn.execute('SELECT file_id FROM file_locations WHERE path_key=?', (path_key(path),)).fetchone()
        if row and changed_paths is not None:
            from app.core.scan_state import key
            owner = conn.execute('SELECT season_id FROM physical_files WHERE id=?',(row[0],)).fetchone()
            if key(path) not in changed_paths and owner and owner[0] == season['id']:
                continue
        if row and stat_files and path.is_file():
            existing = conn.execute('SELECT * FROM physical_files WHERE id=?', (row[0],)).fetchone()
            stored = tuple(existing[k] for k in ('size_bytes','mtime_ns','device','inode'))
            if existing['mtime_ns'] is not None and stored != signature(path):
                # A replaced/modified encoding is a different physical file. Its
                # logical episode may still share history with the previous copy.
                conn.execute("UPDATE physical_files SET availability='REPLACED' WHERE id=?", (row[0],))
                conn.execute('DELETE FROM file_locations WHERE file_id=?', (row[0],))
                row = None
        if row:
            file_id = row[0]
            # A scanner may discover an old location of an unresolved move.
            # Existing content mappings are immutable here, including its release.
            conn.execute('UPDATE physical_files SET season_id=? WHERE id=?', (season['id'], file_id))
        else:
            # Same-volume external moves are review candidates, not new links.
            if stat_files and path.is_file():
                values = signature(path)
                possible = conn.execute('SELECT f.id,l.path FROM physical_files f JOIN file_locations l ON l.file_id=f.id WHERE f.size_bytes=? AND f.mtime_ns=? AND f.device=? AND f.inode=? AND f.availability<>\'RECYCLED\'', values).fetchall()
                pending = [candidate for candidate in possible if not Path(candidate['path']).exists() and values[-1] != '0']
                if pending:
                    for candidate in pending:
                        conn.execute("INSERT OR IGNORE INTO repair_candidates(file_id,target,evidence) VALUES (?,?,'SAME_FILE_SIGNATURE')", (candidate['id'], str(path)))
                    continue
            file_id = conn.execute('INSERT INTO physical_files(season_id, original_name) VALUES (?,?)', (season['id'], path.name)).lastrowid
            conn.execute('INSERT INTO file_locations VALUES (?,?,?)', (file_id, str(path.absolute()), path_key(path)))
            numbers = extract_episode_numbers(path.name)
            season_token = re.search(r'\bS(\d{1,2})[ ._-]*E\d+', path.stem, re.I)
            scheme = 'SEASON' if season_token else 'ABSOLUTE' if continuous else 'SEASON' if season.get('season_number') else 'UNVERIFIED'
            explicit = bool(season_token)
            provider = conn.execute('SELECT provider_id FROM releases WHERE id=?', (rid,)).fetchone()[0]
            verified = bool(provider and ((continuous and not season_token) or season.get('numbering_source') == 'metadata' or (explicit and not continuous)))
            # Movies in a collection without individual release metadata remain distinct.
            prefix = f'season:{int(season_token[1])}:' if continuous and season_token else ''
            keys = [(f'{prefix}number:{number}', number) for number in numbers] if numbers and season.get('relation_type') == 'SEASON' else [(f'file:{file_id}', numbers[0] if numbers else None)]
            for key, number in keys:
                conn.execute('INSERT OR IGNORE INTO episodes(release_id,identity_key,original_number,numbering_scheme,release_number,mapping_verified) VALUES (?,?,?,?,?,?)',
                             (rid, key, number, scheme, number if verified else None, int(verified)))
                eid = conn.execute('SELECT id FROM episodes WHERE release_id=? AND identity_key=?', (rid, key)).fetchone()[0]
                conn.execute('INSERT OR IGNORE INTO file_episodes VALUES (?,?)', (file_id, eid))
        _release_states(conn, file_id, season)
        if stat_files:
            try:
                values = signature(path)
                conn.execute("UPDATE physical_files SET size_bytes=?,mtime_ns=?,device=?,inode=?,availability='AVAILABLE' WHERE id=?", (*values, file_id))
            except OSError:
                conn.execute("UPDATE physical_files SET availability='UNAVAILABLE' WHERE id=?", (file_id,))


def _release_states(conn, file_id, season):
    calendar = dict(season)
    if not calendar.get('next_airing_ep'):
        franchise = conn.execute('SELECT anilist_id,metadata_json FROM franchises WHERE id=?', (season['franchise_id'],)).fetchone()
        release = conn.execute('SELECT r.provider_id FROM releases r JOIN season_releases sr ON r.id=sr.release_id WHERE sr.season_id=?', (season['id'],)).fetchone()
        if franchise and release and franchise[0] == release[0]:
            upcoming = (json.loads(franchise[1] or '{}') or {}).get('nextAiringEpisode') or {}
            calendar.update(next_airing_ep=upcoming.get('episode'), next_airing_at=upcoming.get('airingAt'))
    for row in conn.execute('SELECT e.* FROM episodes e JOIN file_episodes fe ON e.id=fe.episode_id WHERE fe.file_id=?', (file_id,)).fetchall():
        if row['mapping_source'] == 'MANUAL':
            continue
        if season.get('airing_status') == 'NOT_YET_RELEASED':
            conn.execute("UPDATE episodes SET release_state='UPCOMING' WHERE id=? AND aired_at IS NULL", (row['id'],))
        elif row['mapping_verified'] and season.get('airing_status') == 'FINISHED' and season.get('episodes_total') and row['release_number'] is not None and row['release_number'] <= season['episodes_total']:
            conn.execute("UPDATE episodes SET release_state='AIRED' WHERE id=? AND aired_at IS NULL", (row['id'],))
        elif row['mapping_verified'] and row['release_number'] is not None and calendar.get('next_airing_ep') and calendar.get('next_airing_at'):
            if calendar['next_airing_ep'] == row['release_number']:
                conn.execute('UPDATE episodes SET aired_at=? WHERE id=?', (calendar['next_airing_at'], row['id']))
            elif row['release_number'] < calendar['next_airing_ep']:
                conn.execute("UPDATE episodes SET release_state='AIRED' WHERE id=?", (row['id'],))


def bind_release(sid, media):
    """An explicit release match updates metadata, never replaces episode IDs."""
    with closing(db.get_connection()) as conn, conn:
        season = conn.execute('SELECT * FROM seasons WHERE id=?', (sid,)).fetchone()
        if not season:
            raise ValueError('Local release no longer exists')
        rid = _release(conn, dict(season))
        conn.execute('UPDATE releases SET provider_id=? WHERE id=?', (media['id'], rid))
        sync_season(conn, dict(season))
        for file in conn.execute('SELECT f.id,f.original_name FROM physical_files f WHERE f.season_id=?', (sid,)).fetchall():
            if re.search(r'\bS\d{1,2}E\d+', file['original_name'], re.I) or season['numbering_source'] == 'metadata':
                conn.execute('UPDATE episodes SET mapping_verified=1,release_number=original_number WHERE id IN (SELECT episode_id FROM file_episodes WHERE file_id=?) AND numbering_scheme<>\'ABSOLUTE\'', (file['id'],))
            _release_states(conn, file['id'], dict(season))


def save_episode_notes(episode_id, notes):
    with closing(db.get_connection()) as conn, conn:
        if conn.execute('UPDATE episodes SET notes=? WHERE id=?', (notes, episode_id)).rowcount != 1:
            raise ValueError('Episode no longer exists')


def sync_inventory(sid=None, changed_paths=None):
    with closing(db.get_connection()) as conn, conn:
        rows = conn.execute('SELECT * FROM seasons' + (' WHERE id=?' if sid else ''), (sid,) if sid else ()).fetchall()
        for row in rows:
            sync_season(conn, dict(row), changed_paths=changed_paths)


def track_play(path):
    # New files can be discovered directly by the lazy episode chooser.
    with closing(db.get_connection()) as conn, conn:
        seasons = conn.execute('SELECT * FROM seasons WHERE season_folder_path IS NOT NULL').fetchall()
        for row in seasons:
            season = dict(row)
            # Compare the relative name rather than stat'ing every episode on an HDD.
            try:
                name = Path(path).resolve().relative_to(Path(season['season_folder_path']).resolve()).as_posix()
            except ValueError:
                continue
            known_names = {n.replace('\\', '/') for n in json.loads(season.get('video_files_json') or '[]')}
            if name in known_names:
                sync_season(conn, {**season, 'video_files_json': json.dumps([name])})
        pending = any(path_key(row[0]) == path_key(path) for row in conn.execute("SELECT target FROM repair_candidates WHERE status='REVIEW'"))
        if pending:
            raise ValueError('This file has a pending path repair. Use Organizer > Find missing files to review it first.')
        known = conn.execute('SELECT 1 FROM file_locations WHERE path_key=?', (path_key(path),)).fetchone()
        if not known:
            # Lazy discovery can find a new file before the next local refresh.
            candidates = [dict(row) for row in seasons if Path(row['season_folder_path']).resolve() in Path(path).resolve().parents]
            longest = max((len(Path(row['season_folder_path']).parts) for row in candidates), default=0)
            candidates = [row for row in candidates if len(Path(row['season_folder_path']).parts) == longest]
            if len(candidates) != 1:
                raise ValueError('Refresh the library and review this file\'s release before playing it. No episode history has been reassigned.')
            season = candidates[0]
            name = os.path.relpath(path, season['season_folder_path'])
            names = json.loads(season['video_files_json'] or '[]')
            if name not in names:
                names.append(name)
            season['video_files_json'] = json.dumps(names)
            sync_season(conn, {**season, 'video_files_json': json.dumps([name])})
            size = conn.execute("SELECT COALESCE(SUM(f.size_bytes),0) FROM physical_files f JOIN file_locations l ON l.file_id=f.id WHERE f.season_id=? AND f.availability='AVAILABLE'", (season['id'],)).fetchone()[0]
            conn.execute('UPDATE seasons SET video_files_json=?,size_bytes=? WHERE id=?', (season['video_files_json'], size, season['id']))
        if not record_play(conn, path):
            raise ValueError('This file needs a verified path repair before playing.')
        conn.execute("INSERT OR REPLACE INTO app_state VALUES ('last_episode_path',?)", (str(path),))


def record_play(conn, path, event='PLAYED'):
    episodes = conn.execute('SELECT fe.episode_id FROM file_locations l JOIN file_episodes fe ON fe.file_id=l.file_id WHERE l.path_key=? ORDER BY fe.episode_id', (path_key(path),)).fetchall()
    for row in episodes:
        conn.execute('INSERT INTO episode_history(episode_id,played_at,event) VALUES (?,?,?)', (row[0], int(time.time()), event))
    if episodes:
        conn.execute("INSERT OR REPLACE INTO app_state VALUES ('last_episode_id',?)", (str(episodes[0][0]),))
        conn.execute("INSERT OR REPLACE INTO app_state VALUES ('last_file_id',(SELECT CAST(file_id AS TEXT) FROM file_locations WHERE path_key=?))", (path_key(path),))
    return [row[0] for row in episodes]


def last_path():
    with closing(db.get_connection()) as conn:
        row = conn.execute("SELECT l.path,f.availability FROM file_locations l JOIN physical_files f ON f.id=l.file_id JOIN app_state a ON a.key='last_file_id' AND l.file_id=CAST(a.value AS INTEGER)").fetchone()
        if row and row['availability'] not in ('RECYCLED','REPLACED'):
            return row[0]
        alternative = conn.execute("SELECT l.path FROM app_state a JOIN file_episodes fe ON fe.episode_id=CAST(a.value AS INTEGER) JOIN physical_files f ON f.id=fe.file_id JOIN file_locations l ON l.file_id=f.id WHERE a.key='last_episode_id' AND f.availability='AVAILABLE' ORDER BY f.id LIMIT 1").fetchone()
        if alternative:
            return alternative[0]
        if row:
            return row[0]
        row = conn.execute("SELECT value FROM app_state WHERE key='last_episode_path'").fetchone()
        return row[0] if row else None


def resolve_path(path):
    """Resolve stale UI references only through completed, recorded moves."""
    current, seen = str(path), set()
    with closing(db.get_connection()) as conn:
        while path_key(current) not in seen:
            seen.add(path_key(current))
            if Path(current).is_file():
                return current
            candidates = [row['target'] for row in conn.execute("SELECT source,target FROM file_operations WHERE kind='MOVE' AND status='COMPLETED' ORDER BY updated_at DESC") if path_key(row['source']) == path_key(current)]
            if not candidates:
                break
            current = candidates[0]
    return current


def relocate(conn, source, target):
    """Update location and all compatibility references in the SAME transaction."""
    row = conn.execute('SELECT file_id FROM file_locations WHERE path_key=?', (path_key(source),)).fetchone()
    if row:
        conn.execute('UPDATE file_locations SET path=?,path_key=? WHERE file_id=?', (str(target), path_key(target), row[0]))
        conn.execute("UPDATE physical_files SET availability='AVAILABLE' WHERE id=?", (row[0],))
    old = conn.execute("SELECT value FROM app_state WHERE key='last_episode_path'").fetchone()
    if old and old[0] and path_key(old[0]) == path_key(source):
        conn.execute("UPDATE app_state SET value=? WHERE key='last_episode_path'", (str(target),))
    for season in conn.execute('SELECT * FROM seasons WHERE season_folder_path IS NOT NULL').fetchall():
        paths = [(Path(season['season_folder_path']) / name).resolve() for name in json.loads(season['video_files_json'] or '[]')]
        updated = [Path(target).resolve() if path_key(path) == path_key(source) else path for path in paths]
        if updated == paths:
            continue
        common = Path(os.path.commonpath([str(path.parent) for path in updated]))
        conn.execute('UPDATE seasons SET season_folder_path=?,video_files_json=?,scan_root=NULL WHERE id=?',
                     (str(common), json.dumps([os.path.relpath(path, common).replace('\\', '/') for path in updated]), season['id']))
        franchise = conn.execute('SELECT root_folder_path FROM franchises WHERE id=?', (season['franchise_id'],)).fetchone()
        old_root = franchise[0] if franchise else None
        # Keep the existing series root while any owned files remain under it.
        all_paths = []
        for sibling in conn.execute('SELECT season_folder_path,video_files_json FROM seasons WHERE franchise_id=?', (season['franchise_id'],)):
            if sibling[0]:
                all_paths.extend((Path(sibling[0]) / n).resolve() for n in json.loads(sibling[1] or '[]'))
        if old_root and not any(Path(old_root).resolve() in p.parents for p in all_paths):
            new_root = Path(os.path.commonpath([str(p.parent) for p in all_paths]))
            if re.match(r'(?i)^(?:season[ _-]*\d+|movies?|specials?|unassigned episodes|re-edits)', new_root.name):
                new_root = new_root.parent
            conn.execute('UPDATE franchises SET root_folder_path=? WHERE id=?', (str(new_root), season['franchise_id']))


def candidate_for(file_id, target):
    """Fingerprint evidence is a candidate, never permission to relink."""
    target = Path(target)
    with closing(db.get_connection()) as conn, conn:
        file = conn.execute('SELECT * FROM physical_files WHERE id=?', (file_id,)).fetchone()
        if not file or target.is_symlink():
            raise ValueError('Invalid repair candidate')
        values = signature(target)
        strong = tuple(file[k] for k in ('size_bytes', 'mtime_ns', 'device', 'inode')) == values and values[-1] != '0'
        evidence = 'SAME_FILE_SIGNATURE' if strong else 'NAME_ONLY_UNVERIFIED'
        conn.execute('INSERT OR REPLACE INTO repair_candidates(file_id,target,evidence) VALUES (?,?,?)', (file_id, str(target), evidence))
        return evidence


def approve_repair(candidate_id):
    with closing(db.get_connection()) as conn, conn:
        candidate = conn.execute('SELECT c.*,l.path FROM repair_candidates c JOIN file_locations l USING(file_id) WHERE c.id=?', (candidate_id,)).fetchone()
        if not candidate or candidate['status'] != 'REVIEW' or Path(candidate['path']).exists():
            raise ValueError('Repair is no longer applicable')
        file = conn.execute('SELECT * FROM physical_files WHERE id=?', (candidate['file_id'],)).fetchone()
        if Path(candidate['target']).is_symlink() or signature(candidate['target']) != tuple(file[k] for k in ('size_bytes','mtime_ns','device','inode')) or file['inode'] in (None, '0'):
            raise ValueError('Repair needs a verified file signature; filename alone is insufficient')
        occupied = conn.execute('SELECT file_id FROM file_locations WHERE path_key=?', (path_key(candidate['target']),)).fetchone()
        if occupied and occupied[0] != file['id']:
            raise ValueError('Candidate already belongs to another indexed file')
        relocate(conn, candidate['path'], candidate['target'])
        conn.execute("UPDATE repair_candidates SET status=CASE WHEN id=? THEN 'APPROVED' ELSE 'SUPERSEDED' END WHERE file_id=?", (candidate_id, candidate['file_id']))


def find_repair_candidates(cancelled=lambda: False):
    sync_inventory()
    # Missing records are retained, including episode notes and play events.
    with closing(db.get_connection()) as conn:
        files = [dict(row) for row in conn.execute('SELECT f.*,l.path FROM physical_files f JOIN file_locations l ON l.file_id=f.id WHERE f.availability<>\'RECYCLED\'')]
    missing = [row for row in files if not Path(row['path']).is_file()]
    by_name = {}
    by_signature = {}
    for row in missing:
        by_name.setdefault(Path(row['path']).name.casefold(), []).append(row)
        fingerprint = tuple(row[k] for k in ('size_bytes','mtime_ns','device','inode'))
        if row['inode'] not in (None, '0'):
            by_signature.setdefault(fingerprint, []).append(row)
    candidates, unavailable, seen = [], set(), set()
    for watched in db.get_watched_directories():
        root = Path(watched['folder_path'])
        if not root.is_dir():
            unavailable.add(str(root))
            continue
        for directory, folders, names in os.walk(root, followlinks=False, onerror=lambda error: unavailable.add(str(error.filename))):
            if cancelled():
                raise InterruptedError('Repair scan cancelled')
            folders[:] = [name for name in folders if not (Path(directory) / name).is_symlink()]
            for name in names:
                if cancelled():
                    raise InterruptedError('Repair scan cancelled')
                target = Path(directory) / name
                if target.is_symlink():
                    continue
                from app.config import VIDEO_EXTENSIONS
                if target.suffix.lower() not in VIDEO_EXTENSIONS:
                    continue
                try:
                    matches = {file['id']: file for file in by_name.get(name.casefold(), [])}
                    if by_signature:
                        matches.update({file['id']: file for file in by_signature.get(signature(target), [])})
                except OSError:
                    unavailable.add(str(target))
                    continue
                for file in matches.values():
                    key = (file['id'], path_key(target))
                    if key in seen or target.is_symlink():
                        continue
                    seen.add(key)
                    try:
                        evidence = candidate_for(file['id'], target)
                    except OSError:
                        unavailable.add(str(target))
                        continue
                    with closing(db.get_connection()) as conn:
                        row = conn.execute('SELECT id FROM repair_candidates WHERE file_id=? AND target=?', (file['id'], str(target))).fetchone()
                    candidates.append({'id': row[0], 'file_id': file['id'], 'source': file['path'], 'target': str(target), 'evidence': evidence})
    return {'recovered': 0, 'unresolved': len(missing), 'unavailable': len(unavailable), 'candidates': candidates}


def set_episode_release(episode_id, release_number, aired_at=None, state='UNKNOWN'):
    """Explicit verified mapping, independent of a physical filename."""
    if state not in {'AIRED','UPCOMING','UNKNOWN'} or not isinstance(release_number, int) or release_number < 0:
        raise ValueError('Invalid verified episode mapping')
    with closing(db.get_connection()) as conn, conn:
        conn.execute("UPDATE episodes SET release_number=?,mapping_verified=1,mapping_source='MANUAL',release_state=?,aired_at=? WHERE id=?", (release_number, state, aired_at, episode_id))


def episode_state(episode, now=None):
    now = time.time() if now is None else now
    if episode.get('aired_at') is not None:
        return 'AIRED' if episode['aired_at'] <= now else 'UPCOMING'
    return episode.get('release_state') or 'UNKNOWN'


def mapped_inventory_files(season):
    """Use verified release numbers for health checks, without rewriting names."""
    names = json.loads(season.get('video_files_json') or '[]')
    if not season.get('id') or not season.get('season_folder_path'):
        return names
    with closing(db.get_connection()) as conn:
        rows = conn.execute('SELECT l.path,e.release_number,e.mapping_verified FROM physical_files f JOIN file_locations l ON l.file_id=f.id JOIN file_episodes fe ON fe.file_id=f.id JOIN episodes e ON e.id=fe.episode_id WHERE f.season_id=? AND f.availability=\'AVAILABLE\'', (season['id'],)).fetchall()
    # Keep ambiguous basenames untouched. No filename-only identity assignment.
    mapped = {}
    for row in rows:
        mapped.setdefault(os.path.normcase(Path(row['path']).name), []).append(row)
    result = []
    for name in names:
        matches = mapped.get(os.path.normcase(Path(name).name), [])
        paths = {row['path'] for row in matches}
        if len(paths) == 1 and matches and all(row['mapping_verified'] and row['release_number'] is not None for row in matches):
            result.extend(f"Episode {row['release_number']}.mkv" for row in matches)
        else:
            result.append(name)
    return result
