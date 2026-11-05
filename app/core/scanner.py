"""
Fast internal drive scanner & duplicate merger.
Scans watched directories, matches folder names against AniList,
and merges txt-imported entries with on-disk entries.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from collections import defaultdict

from app import db
from app.config import VIDEO_EXTENSIONS, is_offline
from app.core.parser import (
    clean_title,
    extract_base_anime_name,
    extract_season_number,
    normalize_for_matching,
)
from app.core import anilist_client


# ---------------------------------------------------------------------------
# Scanner signals (for PyQt thread communication)
# ---------------------------------------------------------------------------
class ScanProgress:
    """Simple progress container for scanner callbacks."""
    def __init__(self):
        self.current = 0
        self.total = 0
        self.current_item = ""
        self.cancelled = False


# ---------------------------------------------------------------------------
# Full library scan
# ---------------------------------------------------------------------------
def scan_watched_directories(
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
    scan_progress: Optional[ScanProgress] = None,
    *, new_only: bool = False, allow_network: bool = True,
) -> Dict[str, Any]:
    """Scan all watched directories, match folders against AniList,
    and merge with existing library entries.

    Args:
        progress_callback: Optional fn(message, current, total)
        scan_progress: Optional ScanProgress for cancellation support

    Returns:
        Summary dict with counts.
    """
    dirs = db.get_watched_directories()
    if not dirs:
        return {"scanned": 0, "new": 0, "updated": 0, "errors": []}

    def path_key(path):
        return os.path.normcase(os.path.abspath(path))

    known_folders, known_loose = set(), set()
    if new_only:
        from contextlib import closing
        with closing(db.get_connection()) as conn:
            known_folders.update(path_key(row[0]) for row in conn.execute(
                "SELECT root_folder_path FROM franchises WHERE root_folder_path IS NOT NULL AND root_folder_path <> ''"
            ))
            for row in conn.execute("SELECT scan_root, local_scan_key FROM seasons WHERE scan_root IS NOT NULL"):
                key = row["local_scan_key"] or ""
                if key.startswith("loose-root:"):
                    known_loose.add((path_key(row["scan_root"]), key))
                elif row["scan_root"]:
                    known_folders.add(path_key(row["scan_root"]))

    # Collect all anime folders across all watched directories
    anime_folders = []
    for wd in dirs:
        folder = Path(wd["folder_path"]).resolve()
        if not folder.is_dir():
            continue
        try:
            for entry in folder.iterdir():
                if path_key(entry) not in known_folders and entry.is_dir():
                    anime_folders.append({
                        "path": str(entry),
                        "name": entry.name,
                        "watched_dir_id": wd["id"],
                    })
        except PermissionError:
            continue

    from app.core.loose import inspect_loose_episodes
    for wd in dirs:
        if Path(wd["folder_path"]).is_dir():
            loose, unknown = inspect_loose_episodes(wd["folder_path"])
            for item in loose:
                if (path_key(item["folder_path"]), "loose-root:" + item["loose_key"]) in known_loose:
                    continue
                item.update({"path": wd["folder_path"], "name": item["anime_name"], "watched_dir_id": wd["id"]})
                anime_folders.append(item)

    total = len(anime_folders)
    new_count = 0
    updated_count = 0
    errors = []
    indexed_ids = set()

    for idx, af in enumerate(anime_folders):
        if scan_progress and scan_progress.cancelled:
            break

        folder_name = af["name"]
        clean_name = clean_title(folder_name)

        if progress_callback:
            progress_callback(f"Scanning: {clean_name}", idx + 1, total)
        if scan_progress:
            scan_progress.current = idx + 1
            scan_progress.total = total
            scan_progress.current_item = clean_name

        # Check if already in library by folder path first, then by title match
        if af.get("is_loose_group"):
            indexed_ids.add(index_loose_group(af))
            updated_count += 1
            continue
        existing = db.find_franchise_by_folder_path(af["path"])
        if not existing:
            existing = db.find_franchise_by_title(clean_name)
        if not existing:
            # Also try the raw folder name
            existing = db.find_franchise_by_title(folder_name)


        try:
            if existing:
                _update_on_disk_info(existing["id"], af["path"])
                indexed_ids.add(existing["id"])
                updated_count += 1
            else:
                fid = _create_from_folder(af, clean_name)
                if fid:
                    indexed_ids.add(fid)
                    new_count += 1
        except OSError as error:
            errors.append(f"{folder_name}: {error}")

        # Update scan time
        db.update_watched_directory_scan_time(af["watched_dir_id"])

    def cancelled():
        return bool(scan_progress and scan_progress.cancelled)

    if allow_network and not cancelled() and (indexed_ids or not new_only) and not is_offline():
        from app.core.matching import auto_match_indexed_folders
        errors.extend(auto_match_indexed_folders(cancelled, progress_callback, indexed_ids if new_only else None))

    return {
        "scanned": total,
        "new": new_count,
        "updated": updated_count,
        "errors": errors,
    }


def _create_from_folder(af: Dict, clean_name: str) -> Optional[int]:
    """Index the local folder before attempting metadata matching."""
    groups = collect_video_groups(af["path"])
    if not groups:
        return None
    franchise_data = {
        "display_title": clean_name,
        "title_romaji": af["name"],
        "root_folder_path": af["path"],
        "storage_state": "ON_DISK",
        "is_custom": 1,
        "needs_review": 1,
    }
    fid = db.upsert_franchise(franchise_data)
    _update_on_disk_info(fid, af["path"], groups=groups)
    return fid


def collect_video_groups(folder_path: str):
    """Recursively inventory exact paths; local arcs and alternate editions stay distinct."""
    from app.core.parser import extract_episode_range, extract_episode_numbers, classification_filename
    import re
    root = Path(folder_path).resolve()
    groups = {}
    loose = []

    def add(key, sn, kind, label, file, declared=None):
        group = groups.setdefault(key, {"key": key, "season_number": sn, "relation_type": kind, "title": label, "files": [], "ranges": set()})
        group["files"].append(file)
        if declared:
            group["ranges"].add(declared)

    def fail(error):
        raise error  # Never persist a partial inventory after an unreadable subtree.

    for current, dirs, files in os.walk(root, onerror=fail, followlinks=False):
        dirs[:] = [name for name in dirs if extract_season_number(name, None) != -1 and not (Path(current) / name).is_symlink()]
        parent = Path(current)
        for name in files:
            file = parent / name
            if file.suffix.lower() not in VIDEO_EXTENSIONS or file.is_symlink() or extract_season_number(name, None) == -1:
                continue
            if re.search(r'Re-edit|One Piece Log', name, re.I):
                add('collection:reedits', 0, 'COLLECTION', 'Re-edits', file)
                continue
            ancestors = [parent] + list(parent.parents)
            ancestors = [path for path in ancestors if path == root or root in path.parents]
            season_folder = next((path for path in ancestors if (extract_season_number(path.name, None) or 0) > 0), None)
            is_special = bool(re.search(r"\b(?:specials?|ovas?|extras?|bonus|NCOP|NCED|SP\d+)\b|\d+SP\b|Fan[ ._-]+Letter", classification_filename(name), re.I))
            is_movie = bool(re.search(r"\b(?:movies?|films?)\b", name.replace("_", " "), re.I))
            media_folder = next((path for path in ancestors if extract_season_number(path.name, None) == 0), None)
            if is_special:
                add("specials", 0, "SPECIAL", "Specials & extras", file)
            elif is_movie or (media_folder and re.search(r"\b(?:movies?|films?)\b", media_folder.name, re.I)):
                add("movies", 0, "MOVIE", "Movies", file)
            elif media_folder:
                add("specials", 0, "SPECIAL", "Specials & extras", file)
            elif (extract_season_number(name, None) or 0) > 0:
                sn = extract_season_number(name)
                declared = extract_episode_range(season_folder.name) if season_folder and extract_season_number(season_folder.name) == sn else None
                add(f"season:{sn}", sn, "SEASON", f"Season {sn}", file, declared)
            elif season_folder:
                sn = extract_season_number(season_folder.name)
                add(f"season:{sn}", sn, "SEASON", season_folder.name, file, extract_episode_range(season_folder.name))
            elif parent.name.casefold() == 'unassigned episodes':
                add('loose', 0, 'SEASON', 'Unassigned episodes · arc unverified', file)
            elif parent != root:
                top = root / file.relative_to(root).parts[0]
                label = clean_title(top.name)
                add("collection:" + normalize_for_matching(label), 0, "COLLECTION", label, file, extract_episode_range(top.name))
            else:
                loose.append(file)

    # Loose episodes can join an arc only when their IDs fall inside its known
    # interval. Unassigned tails are not guessed into an invented season.
    has_episode_groups = any(g["relation_type"] in ("SEASON", "COLLECTION") for g in groups.values())
    for file in loose:
        if not has_episode_groups:
            sn = extract_season_number(file.name, None) or extract_season_number(root.name, None) or 1
            add(f"season:{sn}", sn, "SEASON", root.name, file, extract_episode_range(root.name))
            continue
        numbers = extract_episode_numbers(file.name)
        normalized = normalize_for_matching(clean_title(file.stem))
        collection = next((group for group in groups.values() if group["key"].startswith("collection:") and normalize_for_matching(group["title"]) in normalized), None)
        if collection:
            collection["files"].append(file)
            continue
        candidates = []
        for group in groups.values():
            if group["relation_type"] != "SEASON":
                continue
            observed = [ep for item in group["files"] for ep in extract_episode_numbers(item.name)]
            if len(group["ranges"]) == 1:
                start, end = next(iter(group["ranges"]))
                if observed and (min(observed) < start or max(observed) > end):
                    start, end = min(observed), max(observed)
            elif observed:
                start, end = min(observed), max(observed)
            else:
                continue
            if numbers and all(start <= ep <= end for ep in numbers):
                candidates.append(group)
        if len(candidates) == 1:
            candidates[0]["files"].append(file)
        else:
            add("loose", 0, "SEASON", "Loose episodes · arc unverified", file)

    return list(groups.values())


def _update_on_disk_info(fid: int, folder_path: str, groups=None):
    """Replace the local inventory from a complete scan, without moving any files."""
    root = Path(folder_path).resolve()
    if not root.is_dir():
        return
    if groups is None:
        groups = collect_video_groups(folder_path)
    all_existing = db.get_seasons_for_franchise(fid)
    def belongs_to_root(season):
        if season.get("scan_root"):
            return Path(season["scan_root"]).resolve() == root
        folder = season.get("season_folder_path")
        if not folder:
            return True  # Unassigned provider metadata may be matched once.
        try:
            Path(folder).resolve().relative_to(root)
            return True
        except ValueError:
            return False
    existing = [season for season in all_existing if belongs_to_root(season)]
    used_ids = set()
    from contextlib import closing
    with closing(db.get_connection()) as conn, conn:
        for group in groups:
            matches = [s for s in existing if s.get("local_scan_key") == group["key"]]
            if not matches:
                if group["key"].startswith("season:"):
                    matches = [s for s in existing if s["season_number"] == group["season_number"] and s.get("relation_type") == "SEASON" and not s.get("local_scan_key")]
                elif group["key"] == "movies":
                    matches = [s for s in existing if s["season_number"] == 0 and s.get("season_folder_path") and not s.get("local_scan_key")]
                elif group["key"] == "loose":
                    matches = [s for s in existing if s.get("season_folder_path") == str(root) and not s.get("local_scan_key") and not s.get("anilist_id")]
            match = next((s for s in matches if s["id"] not in used_ids), None)
            files = sorted(set(group["files"]))
            common = Path(os.path.commonpath([str(file.parent) for file in files]))
            ranges = group["ranges"]
            declared = next(iter(ranges)) if len(ranges) == 1 else None
            data = {
                "franchise_id": fid, "season_number": group["season_number"],
                "relation_type": group["relation_type"], "title_display": group["title"],
                "season_folder_path": str(common),
                "video_files_json": json.dumps([file.relative_to(common).as_posix() for file in files]),
                "size_bytes": sum(file.stat().st_size for file in files), "storage_state": "ON_DISK",
                "episode_start": declared[0] if declared else None,
                "episode_end": declared[1] if declared else None,
                "numbering_source": "folder" if declared else "observed",
                "local_scan_key": group["key"],
                "scan_root": str(root),
            }
            if not match:
                # A consolidation may change the scanner key while keeping the release.
                group_files = set(files)
                relocated = [
                    s for s in existing if s["id"] not in used_ids
                    and s.get("season_folder_path")
                    and any(Path(s["season_folder_path"]) / name in group_files
                            for name in json.loads(s.get("video_files_json") or "[]"))
                ]
                if len(relocated) == 1:
                    match = relocated[0]
            if match:
                values = {key: value for key, value in data.items() if key != "franchise_id"}
                if match.get("anilist_id"):
                    values.pop("title_display")
                assignments = ", ".join(f"{key}=?" for key in values)
                conn.execute(f"UPDATE seasons SET {assignments} WHERE id=?", [*values.values(), match["id"]])
                used_ids.add(match["id"])
            else:
                columns = ", ".join(data)
                placeholders = ", ".join("?" for _ in data)
                cursor = conn.execute(f"INSERT INTO seasons ({columns}) VALUES ({placeholders})", list(data.values()))
                used_ids.add(cursor.lastrowid)
        # Obsolete scanner rows must not retain vanished files or inflate totals.
        for season in existing:
            if season["id"] in used_ids or not season.get("season_folder_path"):
                continue
            try:
                Path(season["season_folder_path"]).resolve().relative_to(root.resolve())
            except ValueError:
                continue
            conn.execute("UPDATE seasons SET video_files_json='[]', size_bytes=0, storage_state='NOT_DOWNLOADED' WHERE id=?", (season["id"],))
        conn.execute("UPDATE franchises SET root_folder_path=COALESCE(root_folder_path, ?) WHERE id=?", (str(root), fid))
    db.recalculate_franchise_size(fid)
    db.recalculate_franchise_storage_state(fid)
    from app.core.identity import sync_inventory
    for sid in used_ids:
        sync_inventory(sid)


# ---------------------------------------------------------------------------
# .txt file importer
# ---------------------------------------------------------------------------
def import_txt_file(filepath: str) -> Dict[str, Any]:
    """Import anime titles from a .txt file (one per line).
    Merges with existing entries if the title already exists.

    Returns summary with counts.
    """
    from app.core.parser import parse_txt_line

    path = Path(filepath)
    if not path.is_file():
        return {"imported": 0, "merged": 0, "skipped": 0, "errors": []}

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    imported = 0
    merged = 0
    skipped = 0
    errors = []

    for line in lines:
        parsed = parse_txt_line(line)
        if not parsed:
            skipped += 1
            continue

        title = parsed["title"]
        notes = parsed["notes"]

        # Check for existing entry
        existing = db.find_franchise_by_title(title)
        if existing:
            # Merge: update watch status and notes
            fid = existing["id"]
            if notes:
                old_notes = existing.get("user_notes", "") or ""
                if notes not in old_notes:
                    db.update_franchise_field(
                        fid, "user_notes",
                        f"{old_notes}\n{notes}".strip()
                    )
            db.update_franchise_field(fid, "watch_status", "WATCHED")
            merged += 1
        else:
            # New entry — try AniList if online
            franchise_data = {
                "display_title": title,
                "title_romaji": title,
                "watch_status": "WATCHED",
                "storage_state": "NOT_DOWNLOADED",
                "raw_import_name": line.strip(),
                "user_notes": notes,
            }

            if not is_offline():
                results = anilist_client.search_anime(title, per_page=3)
                if results:
                    media = results[0]
                    anilist_data = anilist_client.extract_franchise_data(media)
                    franchise_data.update(anilist_data)

            fid = db.upsert_franchise(franchise_data)

            # Download cover if we got AniList data
            if not is_offline() and "anilist_id" in franchise_data:
                results = anilist_client.search_anime(title, per_page=1)
                if results:
                    cover = anilist_client.download_cover(results[0], fid)
                    if cover:
                        db.update_franchise_field(fid, "cover_filename", cover)

            imported += 1

    return {
        "imported": imported,
        "merged": merged,
        "skipped": skipped,
        "errors": errors,
    }


def index_local_folder(folder_path, title):
    existing = db.find_franchise_by_folder_path(str(Path(folder_path).resolve())) or db.find_franchise_by_title(title)
    fid = existing["id"] if existing else db.upsert_franchise({"display_title": title, "is_custom": 1, "needs_review": 1, "storage_state": "ON_DISK", "root_folder_path": str(Path(folder_path).resolve())})
    _update_on_disk_info(fid, folder_path)
    return fid


def index_loose_group(item):
    """Index only this anime's loose files, never its unrelated siblings."""
    root = Path(item["folder_path"]).resolve()
    key = "loose-root:" + item["loose_key"]
    conn = db.get_connection()
    row = conn.execute("SELECT f.* FROM franchises f JOIN seasons s ON s.franchise_id=f.id WHERE s.scan_root=? AND s.local_scan_key=? LIMIT 1", (str(root), key)).fetchone()
    conn.close()
    existing = dict(row) if row else db.find_franchise_by_title(item["anime_name"])
    fid = existing["id"] if existing else db.upsert_franchise({"display_title": item["anime_name"], "is_custom": 1, "needs_review": 1, "storage_state": "ON_DISK"})
    files = [Path(name) for name in item["source_files"] if Path(name).is_file()]
    seasons = db.get_seasons_for_franchise(fid)
    season = next((s for s in seasons if s.get("scan_root") == str(root) and s.get("local_scan_key") == key), None)
    if not season and not files:
        return fid
    data = {"franchise_id": fid, "season_number": item["season_number"], "relation_type": "SEASON", "title_display": item["anime_name"] + f" · Season {item['season_number']}", "scan_root": str(root), "local_scan_key": key, "season_folder_path": str(root), "video_files_json": json.dumps([p.name for p in files]), "size_bytes": sum(p.stat().st_size for p in files), "storage_state": "ON_DISK" if files else "NOT_DOWNLOADED", "numbering_source": "observed"}
    if season:
        for field, value in data.items():
            if field != "franchise_id":
                db.update_season_field(season["id"], field, value)
    else:
        db.upsert_season(data)
    db.recalculate_franchise_size(fid)
    db.recalculate_franchise_storage_state(fid)
    return fid
