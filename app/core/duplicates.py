"""Conservative byte-identical duplicate review within one release."""
import hashlib
import json
import os
from collections import defaultdict
from contextlib import closing
from pathlib import Path

from app import db
from app.config import VIDEO_EXTENSIONS
from app.core.consolidation import explicit_season
from app.core.parser import extract_episode_numbers
from app.core.recycle_bin import send2trash


def signature(path):
    stat = path.stat()
    return (stat.st_size, stat.st_mtime_ns, stat.st_ino)


def digest(path, cancelled):
    before = signature(path)
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            if cancelled():
                raise InterruptedError("Cancelled")
            block = stream.read(1024 * 1024)
            if not block:
                break
            hasher.update(block)
    if signature(path) != before:
        raise ValueError(f"File changed while checking: {path}")
    return hasher.hexdigest(), before


def find_duplicates(cancelled=lambda: False, progress=lambda text: None):
    from app.core.identity import sync_inventory
    sync_inventory()
    buckets = defaultdict(list)
    seen = set()
    errors = []
    for record in db.get_all_franchises():
        if cancelled():
            raise InterruptedError("Cancelled")
        for season in db.get_seasons_for_franchise(record["id"]):
            folder = season.get("season_folder_path")
            if not folder or season.get("storage_state") != "ON_DISK":
                continue
            root = Path(folder).resolve()
            for name in json.loads(season.get("video_files_json") or "[]"):
                if cancelled():
                    raise InterruptedError("Cancelled")
                path = root / name
                try:
                    resolved = path.resolve()
                    if root not in resolved.parents or path.is_symlink() or path.suffix.lower() not in VIDEO_EXTENSIONS:
                        continue
                    identity = os.path.normcase(str(resolved))
                    if identity in seen or not path.is_file():
                        continue
                    seen.add(identity)
                    # Nested explicit seasons override a broad parent inventory.
                    number = next((explicit_season(parent.name) for parent in path.parents
                                   if (parent == root or root in parent.parents) and explicit_season(parent.name) is not None),
                                  season.get("season_number"))
                    episodes = tuple(extract_episode_numbers(path.name))
                    if not episodes:
                        continue
                    release = season.get("anilist_id") or number
                    scope = (record["id"], season.get("relation_type"), release, number, episodes)
                    stat = signature(path)
                    buckets[(scope, stat[0])].append((resolved, record["display_title"], episodes))
                except OSError as error:
                    errors.append(str(error))
    groups = []
    for candidates in buckets.values():
        if len(candidates) < 2:
            continue
        hashes = defaultdict(list)
        for path, title, episodes in candidates:
            progress(f"Checking {title} / {path.name}")
            try:
                checksum, stat = digest(path, cancelled)
                hashes[checksum].append({"path": str(path), "signature": stat, "title": title, "episodes": episodes})
            except (OSError, ValueError) as error:
                errors.append(str(error))
        for checksum, files in hashes.items():
            if len(files) > 1:
                files.sort(key=lambda file: file["path"].casefold())
                groups.append({"hash": checksum, "files": files})
    return groups, errors


def delete_duplicate(group, candidate, cancelled=lambda: False):
    """Recheck both files, retain the keeper, and remove only the reviewed copy."""
    keeper = group["files"][0]
    if candidate not in group["files"][1:] or candidate["path"] == keeper["path"]:
        raise ValueError("A verified retained copy is required.")
    for entry in (keeper, candidate):
        path = Path(entry["path"])
        checksum, stat = digest(path, cancelled)
        if checksum != group["hash"] or tuple(entry["signature"]) != stat:
            raise ValueError("Files changed since the scan. Scan again before deleting.")
    if cancelled():
        raise InterruptedError("Cancelled")
    path = Path(candidate["path"])
    if path.is_symlink() or signature(path) != tuple(candidate["signature"]):
        raise ValueError("The selected file changed.")
    # Record the intent before the filesystem action so a failed DB write can
    # be reconciled from this log without guessing which file was removed.
    journal = db.DATA_DIR / "exports" / "duplicate-deletions.jsonl"
    journal.parent.mkdir(parents=True, exist_ok=True)
    with journal.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"event": "planned", "path": str(path), "kept": keeper["path"], "sha256": group["hash"]}) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
        from app.core.file_operations import recycle_file
        current = path.stat()
        expected = (candidate['signature'][0], candidate['signature'][1], str(current.st_dev), str(candidate['signature'][2]))
        recycle_file(path, expected, recycle=send2trash)
        if path.exists():
            raise OSError('Recycle Bin operation did not remove the selected copy')
        stream.write(json.dumps({"event": "recycled", "path": str(path), "kept": keeper["path"], "sha256": group["hash"]}) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    touched = set()
    with closing(db.get_connection()) as connection, connection:
        from app.core.identity import path_key
        connection.execute("UPDATE physical_files SET availability='RECYCLED' WHERE id=(SELECT file_id FROM file_locations WHERE path_key=?)", (path_key(path),))
        for season in connection.execute("SELECT * FROM seasons WHERE season_folder_path IS NOT NULL").fetchall():
            root = Path(season["season_folder_path"])
            names = json.loads(season["video_files_json"] or "[]")
            remaining = [name for name in names if os.path.normcase(str((root / name).resolve())) != os.path.normcase(str(path))]
            if len(remaining) == len(names):
                continue
            size = sum((root / name).stat().st_size for name in remaining if (root / name).is_file())
            connection.execute("UPDATE seasons SET video_files_json=?, size_bytes=?, storage_state=? WHERE id=?",
                               (json.dumps(remaining), size, "ON_DISK" if remaining else "NOT_DOWNLOADED", season["id"]))
            touched.add(season["franchise_id"])
    for fid in touched:
        db.recalculate_franchise_size(fid)
        db.recalculate_franchise_storage_state(fid)
