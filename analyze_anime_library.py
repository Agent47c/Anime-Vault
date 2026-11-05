"""
Anime Library Structure & Organization Analyzer
Scans your anime library directory and compares disk folders against library.db.
Generates a comprehensive CSV report at: data/exports/anime_library_structure_analysis.csv
"""

import os
import sys
import csv
import json
import sqlite3
from pathlib import Path

# Ensure project root in path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.config import VIDEO_EXTENSIONS
from app.core.parser import clean_title, extract_season_number, normalize_for_matching


def analyze_library(target_dir: str = None) -> str:
    """Analyze folder structures and export CSV report."""
    db_path = BASE_DIR / "data" / "library.db"
    exports_dir = BASE_DIR / "data" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    csv_path = exports_dir / "anime_library_structure_analysis.csv"

    # Connect to DB to get current state
    db_franchises = {}
    db_seasons = {}
    if db_path.is_file():
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        for r in cur.execute("SELECT * FROM franchises").fetchall():
            db_franchises[r["id"]] = dict(r)
            if r["root_folder_path"]:
                norm_p = str(Path(r["root_folder_path"])).lower()
                db_franchises[norm_p] = dict(r)

        for s in cur.execute("SELECT * FROM seasons").fetchall():
            fid = s["franchise_id"]
            if fid not in db_seasons:
                db_seasons[fid] = []
            db_seasons[fid].append(dict(s))
            if s["season_folder_path"]:
                norm_sp = str(Path(s["season_folder_path"])).lower()
                if fid in db_franchises and norm_sp not in db_franchises:
                    db_franchises[norm_sp] = db_franchises[fid]
        conn.close()


    # Determine folders to analyze
    folders_to_scan = []
    if target_dir:
        folders_to_scan.append(Path(target_dir))
    else:
        # Check DB watched directories or fallback to E:\Seen Anime
        if db_path.is_file():
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT folder_path FROM watched_directories").fetchall()
            for r in rows:
                p = Path(r["folder_path"])
                if p.is_dir():
                    folders_to_scan.append(p)
            conn.close()

        if not folders_to_scan:
            fallback = Path(r"E:\Seen Anime")
            if fallback.is_dir():
                folders_to_scan.append(fallback)

    if not folders_to_scan:
        print("No valid anime directories found to scan.")
        return ""

    rows_out = []
    total_folders = 0
    flat_folders_count = 0
    multi_season_count = 0

    print("=" * 80)
    print("ANIME LIBRARY STRUCTURE ANALYSIS")
    print("=" * 80)

    for watched_dir in folders_to_scan:
        print(f"\nScanning watched root: {watched_dir}")
        for entry in sorted(watched_dir.iterdir(), key=lambda x: x.name.lower()):
            if not entry.is_dir():
                continue

            total_folders += 1
            folder_name = entry.name
            clean_name = clean_title(folder_name)
            folder_path = str(entry)
            norm_path = str(entry).lower()

            # Inspect files directly in root
            direct_video_files = []
            direct_other_files = []
            direct_video_size = 0
            try:
                for f in entry.iterdir():
                    if f.is_file():
                        sz = f.stat().st_size
                        if f.suffix.lower() in VIDEO_EXTENSIONS:
                            direct_video_files.append((f.name, sz))
                            direct_video_size += sz
                        else:
                            direct_other_files.append((f.name, sz))
            except PermissionError:
                pass

            # Inspect subdirectories
            subdirs_info = []
            total_sub_video_size = 0
            total_sub_video_count = 0

            try:
                for sub in sorted(entry.iterdir(), key=lambda x: x.name.lower()):
                    if sub.is_dir():
                        s_name = sub.name
                        s_num = extract_season_number(s_name)
                        sub_vfiles = []
                        sub_vsize = 0
                        try:
                            for sf in sub.iterdir():
                                if sf.is_file() and sf.suffix.lower() in VIDEO_EXTENSIONS:
                                    sub_vfiles.append(sf.name)
                                    sub_vsize += sf.stat().st_size
                        except PermissionError:
                            pass

                        subdirs_info.append({
                            "name": s_name,
                            "detected_season": s_num,
                            "video_count": len(sub_vfiles),
                            "size_bytes": sub_vsize,
                            "sample_file": sub_vfiles[0] if sub_vfiles else "",
                        })
                        total_sub_video_size += sub_vsize
                        total_sub_video_count += len(sub_vfiles)
            except PermissionError:
                pass

            # Total metrics
            total_video_files = len(direct_video_files) + total_sub_video_count
            total_video_bytes = direct_video_size + total_sub_video_size

            # Structural pattern
            if len(direct_video_files) > 0 and len(subdirs_info) == 0:
                pattern = "FLAT_ROOT_VIDEOS"
                flat_folders_count += 1
            elif len(direct_video_files) == 0 and len(subdirs_info) > 0:
                pattern = "SUBDIRECTORIES_ONLY"
                multi_season_count += 1
            elif len(direct_video_files) > 0 and len(subdirs_info) > 0:
                pattern = "MIXED_ROOT_AND_SUBDIRS"
            else:
                pattern = "EMPTY_OR_NO_VIDEOS"

            # Check matching in DB
            db_record = db_franchises.get(norm_path)
            if not db_record:
                from app import db as app_db
                rec = app_db.find_franchise_by_title(clean_name) or app_db.find_franchise_by_title(folder_name)
                if rec:
                    db_record = rec
            db_title = db_record.get("display_title", "NOT_IN_DB") if db_record else "NOT_IN_DB"
            db_state = db_record.get("storage_state", "NONE") if db_record else "NONE"
            db_size = db_record.get("total_size_bytes", 0) if db_record else 0
            db_fid = db_record.get("id") if db_record else ""


            # Check if seasons are mapped in DB
            db_season_count = len(db_seasons.get(db_fid, [])) if db_fid else 0

            # Diagnosis note
            diagnosis = []
            if pattern == "FLAT_ROOT_VIDEOS" and db_size == 0 and total_video_bytes > 0:
                diagnosis.append("BUG: Flat folder videos not indexed (DB size is 0 bytes)")
            if total_video_bytes > 0 and db_state in ("NOT_DOWNLOADED", "WATCHED_REMOVED"):
                diagnosis.append(f"BUG: Files exist on disk ({total_video_bytes / (1024**3):.1f} GB) but DB state is {db_state}")
            if pattern == "SUBDIRECTORIES_ONLY" and db_state == "PARTIALLY_ON_DISK" and total_sub_video_count > 50:
                diagnosis.append("BUG: Complete series wrongly marked PARTIALLY_ON_DISK due to AniList movie relations")
            if not db_record:
                diagnosis.append("WARNING: Folder not in database")

            diag_str = " | ".join(diagnosis) if diagnosis else "OK"

            # CSV row
            rows_out.append({
                "folder_name": folder_name,
                "clean_name": clean_name,
                "pattern": pattern,
                "direct_video_count": len(direct_video_files),
                "direct_video_gb": f"{direct_video_size / (1024**3):.2f}",
                "subdirs_count": len(subdirs_info),
                "subdirs_video_count": total_sub_video_count,
                "subdirs_video_gb": f"{total_sub_video_size / (1024**3):.2f}",
                "total_video_count": total_video_files,
                "total_disk_gb": f"{total_video_bytes / (1024**3):.2f}",
                "db_franchise_id": db_fid,
                "db_title": db_title,
                "db_storage_state": db_state,
                "db_size_gb": f"{db_size / (1024**3):.2f}",
                "db_seasons_indexed": db_season_count,
                "diagnosis": diag_str,
                "subdirs_details": "; ".join([f"{s['name']}(S{s['detected_season']}:{s['video_count']}eps)" for s in subdirs_info]),
            })

    # Write CSV
    fieldnames = [
        "folder_name", "clean_name", "pattern",
        "direct_video_count", "direct_video_gb",
        "subdirs_count", "subdirs_video_count", "subdirs_video_gb",
        "total_video_count", "total_disk_gb",
        "db_franchise_id", "db_title", "db_storage_state", "db_size_gb",
        "db_seasons_indexed", "diagnosis", "subdirs_details",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"\nAnalysis complete! Processed {total_folders} folders.")
    print(f" - Flat root video folders: {flat_folders_count}")
    print(f" - Subdirectory folders: {multi_season_count}")
    print(f" - CSV Report saved to: {csv_path}\n")

    # Print top problem folders
    issues = [r for r in rows_out if r["diagnosis"] != "OK"]
    print(f"Found {len(issues)} folders with discrepancies:")
    for r in issues[:20]:
        print(f" • [{r['pattern']}] {r['folder_name']}: {r['diagnosis']}")

    return str(csv_path)


if __name__ == "__main__":
    analyze_library()
