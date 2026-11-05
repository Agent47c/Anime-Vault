"""
Smart Auto-Folder & Season Organizer Engine.
Scans anime folders, classifies organized vs unorganized structures,
generates safe file movement previews, and organizes files into clean Season X/ folders.
"""

import os
import re
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable
from collections import defaultdict

from app.config import VIDEO_EXTENSIONS
from app.core.parser import (
    clean_title,
    extract_season_number,
    extract_episode_number,
    parse_filename,
)
from app import db
from app.core.consolidation import explicit_season

# Supported subtitle and font extensions
SUBTITLE_EXTENSIONS = {".srt", ".ass", ".vtt", ".sub", ".idx"}
FONT_EXTENSIONS = {".ttf", ".otf", ".woff"}

DEFAULT_RULES = {
    "treat_direct_as_season_1": True,
    "detect_season_names": True,
    "detect_episode_numbers": True,
    "keep_subtitles_fonts": True,
    "organize_without_confirmation": False,
}


# ---------------------------------------------------------------------------
# Inspection & Classification
# ---------------------------------------------------------------------------
def is_clean_season_name(name: str) -> bool:
    """Check if a directory name is already a standard clean season or movie folder."""
    name_lower = name.strip().lower()
    if name_lower in {"arcs", "re-edits", "unassigned episodes", "extras"}:
        return True
    # Reject release group or quality tags in folder names
    if any(tag in name_lower for tag in ["1080p", "720p", "dual audio", "bluray", "webrip", "[", "]"]):
        return False
    if name_lower.startswith("season") or name_lower.startswith("s0") or name_lower.startswith("s1") or name_lower.startswith("s2"):
        return True
    if "movie" in name_lower or "ova" in name_lower or "special" in name_lower or "film" in name_lower:
        return True
    return False


def inspect_anime_folder(
    folder_path: str,
    anime_name: Optional[str] = None,
    rules: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Inspect an anime directory and classify its organization state.
    
    Returns a dictionary containing:
        - folder_path: str
        - anime_name: str
        - is_organized: bool
        - status_badge: str (e.g. 'Season 1', 'Matched', 'Organized', 'Needs review')
        - status_reason: str
        - video_count: int
        - total_size_bytes: int
        - moves: List of proposed move operations
    """
    if rules is None:
        rules = DEFAULT_RULES

    root = Path(folder_path)
    if not root.is_dir():
        return {
            "folder_path": folder_path,
            "anime_name": anime_name or Path(folder_path).name,
            "is_organized": True,
            "status_badge": "Missing",
            "status_reason": "Folder not found on disk",
            "video_count": 0,
            "total_size_bytes": 0,
            "moves": [],
        }

    display_name = anime_name or clean_title(root.name)

    # 1. Inspect direct video files in root
    direct_videos = []
    direct_subs = []
    direct_fonts = []
    try:
        for entry in root.iterdir():
            if entry.is_file():
                ext = entry.suffix.lower()
                if ext in VIDEO_EXTENSIONS:
                    direct_videos.append(entry)
                elif ext in SUBTITLE_EXTENSIONS:
                    direct_subs.append(entry)
                elif ext in FONT_EXTENSIONS:
                    direct_fonts.append(entry)
    except PermissionError:
        pass

    # 2. Inspect subdirectories
    clean_seasons = []
    non_standard_dirs = []
    all_sub_videos = []

    try:
        for entry in root.iterdir():
            if entry.is_dir():
                sub_vids = [
                    f for f in entry.rglob("*")
                    if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS
                ]
                if not sub_vids:
                    continue
                all_sub_videos.extend(sub_vids)
                if is_clean_season_name(entry.name):
                    clean_seasons.append((entry, sub_vids))
                else:
                    non_standard_dirs.append((entry, sub_vids))
    except PermissionError:
        pass

    total_video_count = len(direct_videos) + len(all_sub_videos)
    total_size = sum(f.stat().st_size for f in direct_videos) + sum(f.stat().st_size for f in all_sub_videos)

    # 3. Determine if already organized
    # An anime is organized if there are NO direct video files in root AND NO non-standard subdirectories with videos
    is_organized = (len(direct_videos) == 0 and len(non_standard_dirs) == 0 and len(clean_seasons) > 0)

    # If completely empty of videos:
    if total_video_count == 0:
        return {
            "folder_path": str(root),
            "anime_name": display_name,
            "is_organized": True,
            "status_badge": "Empty",
            "status_reason": "No video files found",
            "video_count": 0,
            "total_size_bytes": 0,
            "moves": [],
        }

    # 4. Generate proposed file moves
    moves = []
    proposed_seasons = set()

    # Plan moves for direct root videos
    for vfile in direct_videos:
        if not rules.get("treat_direct_as_season_1", True) and explicit_season(vfile.stem) is None and explicit_season(root.name) is None:
            continue
        season_num = 1
        if rules.get("detect_season_names", True):
            detected = extract_season_number(vfile.name, default=1 if rules.get("treat_direct_as_season_1", True) else 1)
            if detected is not None and detected >= 0:
                season_num = explicit_season(vfile.stem) or explicit_season(root.name) or detected

        if season_num == 0:
            target_sub = "Movies & OVAs"
        else:
            target_sub = f"Season {season_num}"

        target_dir = root / target_sub
        target_path = target_dir / vfile.name

        moves.append({
            "source": str(vfile),
            "target": str(target_path),
            "target_dir": str(target_dir),
            "season_num": season_num,
            "filename": vfile.name,
            "size_bytes": vfile.stat().st_size,
            "is_video": True,
            "already_in_place": False,
        })
        proposed_seasons.add(season_num)

        # Accompanying subtitles
        if rules.get("keep_subtitles_fonts", True):
            stem = vfile.stem
            for sfile in direct_subs:
                if sfile.name.startswith(stem) or stem in sfile.name:
                    sub_target = target_dir / sfile.name
                    moves.append({
                        "source": str(sfile),
                        "target": str(sub_target),
                        "target_dir": str(target_dir),
                        "season_num": season_num,
                        "filename": sfile.name,
                        "size_bytes": sfile.stat().st_size,
                        "is_video": False,
                        "already_in_place": False,
                    })

    # Plan moves for non-standard subdirectories (e.g. [EMBER] Season 3... -> Season 3)
    for sub_dir, sub_vids in non_standard_dirs:
        detected_season = extract_season_number(sub_dir.name, default=1)
        if detected_season == 0:
            target_sub = "Movies & OVAs"
        else:
            target_sub = f"Season {detected_season}"

        target_dir = root / target_sub
        for vfile in sub_vids:
            if detected_season > 0:
                file_season = explicit_season(vfile.stem) or explicit_season(sub_dir.name) or explicit_season(root.name) or detected_season
                target_dir = root / f"Season {file_season}"
            target_path = target_dir / vfile.name
            is_in_place = (vfile.parent == target_dir)
            moves.append({
                "source": str(vfile),
                "target": str(target_path),
                "target_dir": str(target_dir),
                "season_num": detected_season,
                "filename": vfile.name,
                "size_bytes": vfile.stat().st_size,
                "is_video": True,
                "already_in_place": is_in_place,
            })
            proposed_seasons.add(detected_season)

    # Status badge and reason
    if is_organized:
        status_badge = "Organized"
        seasons_str = ", ".join(d.name for d, _ in clean_seasons)
        status_reason = f"Clean season structure ({seasons_str})"
    elif direct_videos and non_standard_dirs:
        status_badge = "Needs review"
        status_reason = f"Mixed structure: {len(direct_videos)} root files + non-standard folders"
    elif direct_videos and not proposed_seasons:
        status_badge = "Needs review"
        status_reason = "Root files are unchanged because flat folder detection is off"
    elif direct_videos:
        if 1 in proposed_seasons and len(proposed_seasons) == 1:
            status_badge = "Season 1"
        else:
            status_badge = f"Season {min(proposed_seasons)}" if proposed_seasons else "Season 1"
        status_reason = f"{root} · {len(direct_videos)} flat root files detected"
    elif non_standard_dirs:
        status_badge = "Matched"
        first_season = min(proposed_seasons) if proposed_seasons else 1
        status_reason = f"Non-standard folders will be unified into Season {first_season}"
    else:
        status_badge = "Organized"
        status_reason = "Structured"

    return {
        "folder_path": str(root),
        "anime_name": display_name,
        "is_organized": is_organized,
        "status_badge": status_badge,
        "status_reason": status_reason,
        "video_count": total_video_count,
        "total_size_bytes": total_size,
        "moves": moves,
        "clean_seasons": [d.name for d, _ in clean_seasons],
    }


# ---------------------------------------------------------------------------
# Full Library Inspection
# ---------------------------------------------------------------------------
def inspect_all_library(
    rules: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Inspect all anime in the library and watched directories.
    
    Returns:
        {
            "unorganized": List of items needing organization,
            "organized": List of items already organized,
            "all": Combined list,
        }
    """
    if rules is None:
        rules = DEFAULT_RULES

    # 1. Collect all root paths from watched directories and franchises
    watched_dirs = db.get_watched_directories()
    all_franchises = db.get_all_franchises()

    # Map root_folder_path -> franchise dict
    folder_to_franchise = {}
    for f in all_franchises:
        rfp = f.get("root_folder_path")
        if rfp and os.path.isdir(rfp):
            folder_to_franchise[os.path.normpath(rfp).lower()] = f

    # Anime folders to inspect: folder_path -> display_name
    targets: Dict[str, Tuple[str, Optional[int]]] = {}

    loose_items = []
    unclassified_loose = []
    # Scan watched root directories for subfolders
    for wdir in watched_dirs:
        wpath = Path(wdir["folder_path"])
        if wpath.is_dir():
            from app.core.loose import inspect_loose_episodes
            found, unknown = inspect_loose_episodes(wpath)
            from app.core.scanner import index_loose_group
            for loose_item in found:
                loose_item["franchise_id"] = index_loose_group(loose_item)
            loose_items.extend(found)
            unclassified_loose.extend(unknown)
            try:
                for child in wpath.iterdir():
                    if child.is_dir():
                        norm = os.path.normpath(str(child)).lower()
                        franchise = folder_to_franchise.get(norm)
                        disp_name = franchise["display_title"] if franchise else clean_title(child.name)
                        fid = franchise["id"] if franchise else None
                        targets[str(child)] = (disp_name, fid)
            except PermissionError:
                pass

    # Add any franchise paths that weren't inside the watched dirs
    for f in all_franchises:
        rfp = f.get("root_folder_path")
        if rfp and os.path.isdir(rfp):
            if rfp not in targets:
                targets[rfp] = (f["display_title"], f["id"])

    unorganized_list = list(loose_items)
    organized_list = []
    all_list = list(loose_items)

    total_targets = len(targets)
    for idx, (fpath, (disp_name, fid)) in enumerate(sorted(targets.items(), key=lambda x: x[1][0].lower())):
        if progress_callback:
            progress_callback(disp_name, idx + 1, total_targets)

        item = inspect_anime_folder(fpath, anime_name=disp_name, rules=rules)
        if item["video_count"] > 0:
            from app.core.scanner import index_local_folder
            fid = index_local_folder(fpath, disp_name)
        item["franchise_id"] = fid

        # Only include if there are video files
        if item["video_count"] > 0:
            all_list.append(item)
            if item["is_organized"]:
                organized_list.append(item)
            else:
                unorganized_list.append(item)

    return {
        "unclassified_loose": unclassified_loose,
        "unorganized": unorganized_list,
        "organized": organized_list,
        "all": all_list,
    }


def find_missing_library_files(should_stop=lambda: False):
    """Search watched roots once and relink unambiguous, exact filename matches."""
    import json
    from collections import defaultdict
    from contextlib import closing
    from app.core.parser import normalize_for_matching

    def path_key(path):
        return os.path.normcase(os.path.normpath(path))

    from app.core.consolidation import repair_from_move_journals

    repaired_roots, repaired_seasons = repair_from_move_journals()
    records = db.get_all_franchises()
    missing = defaultdict(list)
    claimed = defaultdict(set)
    for record in records:
        for season in db.get_seasons_for_franchise(record["id"]):
            folder = season.get("season_folder_path")
            if not folder or season["storage_state"] == "REMOVED":
                continue
            files = [Path(folder) / name for name in json.loads(season["video_files_json"] or "[]")]
            for file in files:
                if should_stop():
                    raise InterruptedError
                if file.is_file():
                    claimed[path_key(file)].add(record["id"])
                else:
                    missing[file.name.casefold()].append((record, season, file))

    candidates = defaultdict(dict)
    roots = {Path(row["folder_path"]).resolve() for row in db.get_watched_directories()}
    unavailable = set()
    for root in roots if missing else ():
        if not root.is_dir():
            unavailable.add(str(root))
            continue
        for directory, _, filenames in os.walk(root, onerror=lambda error: unavailable.add(str(error.filename))):
            if should_stop():
                raise InterruptedError
            for name in filenames:
                if name.casefold() not in missing:
                    continue
                target = Path(directory) / name
                folders = [
                    parent for parent in target.parents
                    if parent == root or root in parent.parents
                ]
                candidates[name.casefold()][path_key(target)] = (target, folders)

    updates = defaultdict(dict)
    proposed_targets = defaultdict(set)
    for name, references in missing.items():
        for record, season, old in references:
            old_root = record.get("root_folder_path")
            titles = {normalize_for_matching(record.get(field) or "") for field in
                      ("display_title", "title_en", "title_romaji")}
            if old_root:
                titles.add(normalize_for_matching(clean_title(Path(old_root).name)))
            titles.discard("")
            matches = []
            for key, (target, folders) in candidates[name].items():
                if claimed[key] - {record["id"]}:
                    continue
                series_folder = next(
                    (folder for folder in folders if normalize_for_matching(clean_title(folder.name)) in titles),
                    None,
                )
                if series_folder or normalize_for_matching(clean_title(target.stem)) in titles:
                    matches.append((target, series_folder))
            if len(matches) == 1:
                updates[season["id"]][old] = matches[0]
                proposed_targets[path_key(matches[0][0])].add((season["id"], old))

    if should_stop():
        raise InterruptedError
    recovered = 0
    affected = set()
    with closing(db.get_connection()) as conn, conn:
        for sid, replacements in updates.items():
            season = conn.execute("SELECT * FROM seasons WHERE id=?", (sid,)).fetchone()
            if not season or not season["season_folder_path"]:
                continue
            originals = [Path(season["season_folder_path"]) / name for name in json.loads(season["video_files_json"])]
            updated = [
                replacements[file][0] if file in replacements
                and len(proposed_targets[path_key(replacements[file][0])]) == 1 else file
                for file in originals
            ]
            if updated == originals or not all(file.is_file() for file in updated):
                continue
            try:
                common = Path(os.path.commonpath([str(file.parent) for file in updated]))
            except ValueError:
                continue
            roots_found = {root for _, root in replacements.values() if root and all(root in file.parents for file in updated)}
            new_root = next(iter(roots_found)) if len(roots_found) == 1 else None
            conn.execute(
                "UPDATE seasons SET season_folder_path=?, video_files_json=?, size_bytes=?, storage_state='ON_DISK', scan_root=? WHERE id=?",
                (str(common), json.dumps([file.relative_to(common).as_posix() for file in updated]),
                 sum(file.stat().st_size for file in updated), str(new_root) if new_root else season["scan_root"], sid),
            )
            if new_root:
                fid = season["franchise_id"]
                current = conn.execute("SELECT root_folder_path FROM franchises WHERE id=?", (fid,)).fetchone()[0]
                other = conn.execute("SELECT scan_root, season_folder_path FROM seasons WHERE franchise_id=? AND storage_state='ON_DISK' AND id<>?", (fid, sid))
                if not current or not any(
                    row["season_folder_path"] and Path(current) in [Path(row["season_folder_path"]), *Path(row["season_folder_path"]).parents]
                    for row in other
                ):
                    conn.execute("UPDATE franchises SET root_folder_path=? WHERE id=?", (str(new_root), fid))
            recovered += sum(a != b for a, b in zip(originals, updated))
            affected.add(season["franchise_id"])
    for fid in affected:
        db.recalculate_franchise_size(fid)
        db.recalculate_franchise_storage_state(fid)
    return {"recovered": recovered, "unresolved": sum(map(len, missing.values())) - recovered,
            "unavailable": len(unavailable), "paths_repaired": repaired_roots + repaired_seasons}


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
def execute_organize_anime(
    item: Dict[str, Any],
    rules: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute organization for a single anime item.
    
    Safely moves files into target season folders, cleans up empty directories,
    and updates the database records.
    """
    if rules is None:
        rules = DEFAULT_RULES

    moved = 0
    skipped = 0
    errors = []

    moves = item.get("moves", [])
    root_path = Path(item["folder_path"])
    franchise_id = item.get("franchise_id")

    created_dirs = set()
    skipped_details = []

    for m in moves:
        if m.get("already_in_place"):
            skipped += 1
            skipped_details.append({"file": m.get("source", ""), "reason": "Already in place"})
            continue

        source = Path(m["source"])
        target = Path(m["target"])

        try:
            source.stat()  # Permission failures must be reported rather than skipped.
            if source == target:
                skipped += 1
                skipped_details.append({"file": str(source), "reason": "Already in place"})
                continue
            source.resolve().relative_to(root_path.resolve())
            target.resolve().relative_to(root_path.resolve())
            if source.is_symlink():
                raise ValueError("Symbolic links require manual review")
            target.parent.mkdir(parents=True, exist_ok=True)
            created_dirs.add(target.parent)

            # Avoid collision by appending suffix if target already exists with different file
            final_target = target
            if final_target.exists():
                counter = 1
                while final_target.exists():
                    final_target = target.parent / f"{target.stem}_{counter}{target.suffix}"
                    counter += 1

            shutil.move(str(source), str(final_target))
            moved += 1
        except Exception as e:
            kind = "permission" if isinstance(e, PermissionError) or getattr(e, "winerror", None) == 5 else "missing" if isinstance(e, FileNotFoundError) else "error"
            errors.append({"file": str(source), "target": str(target), "kind": kind, "error": str(e)})

    # Clean up empty subdirectories left behind
    # Preserve directories as well as files; organization is move-only.

    # File moves and library indexing have separate outcomes.
    try:
        if item.get("is_loose_group") and moved:
            from app.core.scanner import index_local_folder, index_loose_group
            index_local_folder(item["destination_root"], item["anime_name"])
            index_loose_group(item)  # Remove moved source references; retain failures.
        elif franchise_id:
            _sync_db_after_organize(franchise_id, root_path)
    except Exception as error:
        errors.append({"file": str(root_path), "kind": "index", "error": "Files processed, but library indexing failed: " + str(error)})

    return {
        "folder_path": str(root_path),
        "moved": moved,
        "skipped": skipped,
        "errors": errors,
        "skipped_details": skipped_details,
    }


def execute_organize_batch(
    items: List[Dict[str, Any]],
    rules: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> Dict[str, Any]:
    """Execute organization on multiple anime items."""
    total_items = len(items)
    total_moved = 0
    total_skipped = 0
    all_errors = []
    organized_folders = []
    skipped_details = []

    for idx, item in enumerate(items):
        if progress_callback:
            progress_callback(item.get("anime_name", ""), idx + 1, total_items)

        res = execute_organize_anime(item, rules=rules)
        total_moved += res["moved"]
        total_skipped += res["skipped"]
        skipped_details.extend(res.get("skipped_details", []))
        if res["errors"]:
            all_errors.extend(res["errors"])
        if res["moved"] > 0:
            organized_folders.append(res["folder_path"])

    return {
        "moved": total_moved,
        "skipped": total_skipped,
        "errors": all_errors,
        "organized_folders": organized_folders,
        "skipped_details": skipped_details,
    }


def _cleanup_empty_dirs_under(root: Path, preserve_dirs: set):
    """Remove empty subdirectories left behind after moving files."""
    try:
        for p in sorted(root.glob("**/"), key=lambda x: len(x.parts), reverse=True):
            if p == root:
                continue
            # If directory is empty
            if p.is_dir() and not any(p.iterdir()):
                try:
                    p.rmdir()
                except OSError:
                    pass
    except Exception:
        pass


def _sync_db_after_organize(franchise_id: int, root_path: Path):
    """Use the same path-aware inventory after organization and ordinary scans."""
    from app.core.scanner import _update_on_disk_info
    _update_on_disk_info(franchise_id, str(root_path))


def organization_summary(result):
    moved = result.get("moved", 0)
    errors = result.get("errors", [])
    skipped = result.get("skipped", 0)
    message = f"Moved: {moved} files\nSkipped: {skipped} files\nFailed: {len(errors)} files"
    if not moved:
        message = "No files were moved.\n\n" + message
    if any(error.get("kind") == "permission" for error in errors):
        message += "\n\nWindows denied access. Close the app, launch 'Run as administrator.cmd', approve the Windows prompt, then scan again before retrying."
    for error in errors[:5]:
        message += f"\n\n{error['file']}\n{error['error']}"
    for item in result.get("skipped_details", [])[:5]:
        message += f"\n{item['file']}: {item['reason']}"
    return message
