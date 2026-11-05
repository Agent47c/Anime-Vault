"""
Manual JSON / CSV backup generator.
Exports the full library to data/exports/.
"""

import csv
import json
import time
from pathlib import Path
from typing import Dict, Any

from app import db
from app.config import EXPORTS_DIR


def export_json() -> str:
    """Export entire library to a timestamped JSON file. Returns filepath."""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filepath = EXPORTS_DIR / f"library_export_{timestamp}.json"

    franchises = db.get_all_franchises()
    export_data = []

    for f in franchises:
        seasons = db.get_seasons_for_franchise(f["id"])
        f["seasons"] = seasons
        # Parse genres back to list
        try:
            f["genres"] = json.loads(f.get("genres", "[]"))
        except (json.JSONDecodeError, TypeError):
            f["genres"] = []
        export_data.append(f)

    filepath.write_text(
        json.dumps(export_data, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8",
    )
    return str(filepath)


def export_csv() -> str:
    """Export franchise list to a timestamped CSV file. Returns filepath."""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filepath = EXPORTS_DIR / f"library_export_{timestamp}.csv"

    franchises = db.get_all_franchises()

    headers = [
        "ID", "AniList ID", "Display Title", "English Title", "Romaji Title",
        "Japanese Title", "Genres", "Watch Status", "Storage State",
        "Size (GB)", "User Rating", "Notes", "Root Folder", "Created At",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for fr in franchises:
            size_gb = round((fr.get("total_size_bytes", 0) or 0) / (1024**3), 2)
            genres = fr.get("genres", "[]")
            if isinstance(genres, str):
                try:
                    genres = ", ".join(json.loads(genres))
                except (json.JSONDecodeError, TypeError):
                    pass
            writer.writerow([
                fr["id"],
                fr.get("anilist_id", ""),
                fr["display_title"],
                fr.get("title_en", ""),
                fr.get("title_romaji", ""),
                fr.get("title_native", ""),
                genres,
                fr.get("watch_status", ""),
                fr.get("storage_state", ""),
                size_gb,
                fr.get("user_rating", ""),
                fr.get("user_notes", ""),
                fr.get("root_folder_path", ""),
                fr.get("created_at", ""),
            ])

    return str(filepath)
