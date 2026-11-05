"""
Application configuration, state management, and offline detection.
"""

import os
import json
import socket
from pathlib import Path
from typing import Optional

from app import db

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
COVERS_DIR = DATA_DIR / "covers"
EXPORTS_DIR = DATA_DIR / "exports"

# ---------------------------------------------------------------------------
# Load .env if present
# ---------------------------------------------------------------------------
def _load_env():
    env_file = BASE_DIR / ".env"
    if env_file.is_file():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

_load_env()

# ---------------------------------------------------------------------------
# Supported video extensions
# ---------------------------------------------------------------------------
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".webm", ".ts"}

# ---------------------------------------------------------------------------
# API endpoints & network settings
# ---------------------------------------------------------------------------
ANILIST_GRAPHQL_URL = os.getenv("ANILIST_GRAPHQL_URL", "https://graphql.anilist.co")
JIKAN_BASE_URL = os.getenv("JIKAN_BASE_URL", "https://api.jikan.moe/v4")
LOCAL_API_PORT = int(os.getenv("LOCAL_API_PORT", "8765"))
LOCAL_API_HOST = os.getenv("LOCAL_API_HOST", "127.0.0.1")
API_ACCESS_TOKEN = os.getenv("API_ACCESS_TOKEN", "")
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "false").lower() in ("true", "1", "yes")

# ---------------------------------------------------------------------------
# Offline detection
# ---------------------------------------------------------------------------
_is_offline: Optional[bool] = None


def check_online(timeout: float = 2.0) -> bool:
    """Non-blocking connectivity check to AniList GraphQL endpoint.
    Returns True if online, False otherwise."""
    global _is_offline
    try:
        sock = socket.create_connection(("graphql.anilist.co", 443), timeout=timeout)
        sock.close()
        _is_offline = False
        return True
    except (socket.timeout, OSError):
        _is_offline = True
        return False


def cached_online() -> Optional[bool]:
    """Read connectivity status without opening a network connection."""
    return None if _is_offline is None else not _is_offline


def is_offline() -> bool:
    """Return cached offline status. Runs check_online() on first call."""
    global _is_offline
    if _is_offline is None:
        check_online()
    return _is_offline


# ---------------------------------------------------------------------------
# App state convenience wrappers
# ---------------------------------------------------------------------------
def get_last_streaming_url() -> Optional[str]:
    return db.get_state("last_streaming_url")


def set_last_streaming_url(url: str):
    db.set_state("last_streaming_url", url)


def get_last_franchise_id() -> Optional[int]:
    val = db.get_state("last_active_franchise_id")
    return int(val) if val else None


def set_last_franchise_id(fid: int):
    db.set_state("last_active_franchise_id", str(fid))


def get_last_episode_path() -> Optional[str]:
    from app.core.identity import last_path
    return last_path()


def set_last_episode_path(path: str):
    from app.core.identity import track_play
    track_play(path)


def get_window_geometry() -> Optional[str]:
    return db.get_state("window_geometry")


def set_window_geometry(geometry: str):
    db.set_state("window_geometry", geometry)


def get_default_sort() -> str:
    return db.get_state("default_sort", "display_title")


def set_default_sort(sort_key: str):
    db.set_state("default_sort", sort_key)


def get_quit_preference() -> Optional[str]:
    """Returns 'tray', 'exit', or None (ask every time)."""
    return db.get_state("quit_preference")


def set_quit_preference(pref: str):
    db.set_state("quit_preference", pref)


def get_theme() -> str:
    """Returns 'dark' or 'light'."""
    return db.get_state("theme", "system")


def set_theme(theme: str):
    db.set_state("theme", theme)


# ---------------------------------------------------------------------------
# Media player configuration & secure launch
# ---------------------------------------------------------------------------
def get_media_player_type() -> str:
    """Returns 'default', 'vlc', 'mpv', 'mpc-hc', or 'custom'."""
    return db.get_state("media_player_type", "default")


def set_media_player_type(player_type: str):
    db.set_state("media_player_type", player_type)


def get_custom_player_path() -> Optional[str]:
    return db.get_state("custom_player_path")


def set_custom_player_path(path: str):
    db.set_state("custom_player_path", path)


def detect_installed_players() -> dict:
    """Scan well-known install locations on Windows for external media players."""
    candidates = {
        "vlc": [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        ],
        "mpv": [
            r"C:\Program Files\mpv\mpv.exe",
            r"C:\mpv\mpv.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\mpv\mpv.exe"),
        ],
        "mpc-hc": [
            r"C:\Program Files\MPC-HC\mpc-hc64.exe",
            r"C:\Program Files (x86)\MPC-HC\mpc-hc.exe",
            r"C:\Program Files\K-Lite Codec Pack\MPC-HC64\mpc-hc64.exe",
        ],
    }
    found = {}
    for name, paths in candidates.items():
        for p in paths:
            if os.path.isfile(p):
                found[name] = p
                break
    return found


def launch_video_file(video_path: str) -> bool:
    """Safely launch a video file in the configured player with security validation.
    
    Validates:
    - File exists
    - Suffix is in approved VIDEO_EXTENSIONS
    - Sets last opened episode in persistent state
    """
    import subprocess
    from app.core.identity import resolve_path
    path = Path(resolve_path(video_path)).resolve()

    if not path.is_file():
        raise FileNotFoundError(f"Video file does not exist: {video_path}")

    if path.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError(f"Unsupported video file format: {path.suffix}")

    # Record last played file
    set_last_episode_path(str(path))

    player_type = get_media_player_type()
    installed = detect_installed_players()

    player_exe = None
    if player_type == "custom":
        custom = get_custom_player_path()
        if custom and os.path.isfile(custom):
            player_exe = custom
    elif player_type in installed:
        player_exe = installed[player_type]

    if player_exe:
        subprocess.Popen([player_exe, str(path)])
        return True
    else:
        # Fallback to Windows default registered handler
        os.startfile(str(path))
        return True



def get_always_admin():
    return db.get_state("always_run_as_administrator", "0") == "1"


def set_always_admin(enabled):
    db.set_state("always_run_as_administrator", "1" if enabled else "0")
