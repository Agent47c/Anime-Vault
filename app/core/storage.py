"""Measure the actual volumes containing configured library roots."""
import os
import shutil
from pathlib import Path
from app import db


def format_bytes(value):
    for unit, divisor in (("TB", 1024 ** 4), ("GB", 1024 ** 3), ("MB", 1024 ** 2)):
        if value >= divisor:
            return f"{value / divisor:.2f} {unit}"
    return f"{value:,} B"


def disk_snapshot():
    snapshot = db.current_refresh_view()
    if snapshot is not None:
        return snapshot["disk"]
    roots = [r["folder_path"] for r in db.get_watched_directories()]
    franchises = db.get_all_franchises()
    if not roots:
        roots = [f["root_folder_path"] for f in franchises if f.get("root_folder_path")]
    volumes = {}
    unavailable = []
    for root in roots:
        path = Path(root)
        try:
            if not path.exists():
                raise OSError("Library root unavailable")
            key = path.resolve().anchor.casefold() if os.name == "nt" else str(path.stat().st_dev)
            if key not in volumes:
                usage = shutil.disk_usage(path)
                volumes[key] = {"total": usage.total, "used": usage.used, "free": usage.free, "label": path.anchor or str(path)}
        except OSError:
            unavailable.append(str(root))
    return {
        "total": sum(v["total"] for v in volumes.values()),
        "used": sum(v["used"] for v in volumes.values()),
        "free": sum(v["free"] for v in volumes.values()),
        "label": ", ".join(v["label"] for v in volumes.values()),
        "unavailable": unavailable,
        "configured": bool(roots),
    }
