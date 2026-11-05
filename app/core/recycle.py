"""Recycle only the selected indexed video files, preserving library records."""
import json
from pathlib import Path
from app.core.recycle_bin import send2trash
from app import db
from app.config import VIDEO_EXTENSIONS


def recycle_selected(franchise_id, seasons, mark_watched=True, signatures=None):
    recycled, failures = [], []
    for selected in seasons:
        season = db.get_season(selected["id"])
        if not season or season["franchise_id"] != franchise_id or season.get("storage_state") != "ON_DISK":
            continue
        if not selected.get("season_folder_path") or season.get("season_folder_path") != selected.get("season_folder_path"):
            failures.append("The selected folder changed; refresh the preview.")
            continue
        folder = Path(season["season_folder_path"]).resolve()
        selected_names = set(json.loads(selected.get("video_files_json") or "[]"))
        remaining = []
        for name in json.loads(season.get("video_files_json") or "[]"):
            if name not in selected_names:
                remaining.append(name)
                continue
            try:
                candidate = folder / name
                if candidate.is_symlink():
                    raise ValueError("Symbolic links must be reviewed separately")
                path = candidate.resolve()
                path.relative_to(folder)
                if path.suffix.lower() not in VIDEO_EXTENSIONS:
                    raise ValueError("Not an indexed video")
                if path.is_file():
                    if signatures is not None:
                        stat = path.stat()
                        if signatures.get(str(path)) != (stat.st_size, stat.st_mtime_ns):
                            raise ValueError("File changed since preview")
                    from app.core.file_operations import recycle_file
                    recycle_file(path, signatures.get(str(path)) if signatures is not None else None, recycle=send2trash)
                    if path.exists():
                        raise OSError("File was not moved")
                    recycled.append(str(path))
            except (ValueError, OSError) as error:
                remaining.append(name)
                failures.append(f"{name}: {error}")
        if remaining:
            size = 0
            for name in remaining:
                try:
                    path = (folder / name).resolve()
                    path.relative_to(folder)
                    size += path.stat().st_size if path.is_file() else 0
                except (ValueError, OSError):
                    pass
            db.update_season_field(season["id"], "video_files_json", json.dumps(remaining))
            db.update_season_field(season["id"], "size_bytes", size)
        else:
            db.mark_season_removed(season["id"])
    if mark_watched and recycled:
        db.update_franchise_field(franchise_id, "watch_status", "WATCHED")
    db.recalculate_franchise_size(franchise_id)
    db.recalculate_franchise_storage_state(franchise_id)
    return {"recycled": recycled, "failures": failures}
