"""Saved user preferences shared by the UI and existing workflows."""
from app import db

DEFAULTS = {
    "reduce_motion": False, "high_contrast": False, "decorations": True,
    "compact_library": False, "metadata_auto": True, "prefer_english": True,
    "allow_mature": True, "rematch_low_confidence": True,
    "flat_detection": True, "preview_moves": True,
    "import_auto": True, "import_review": True, "import_ignore_duplicates": True,
    "import_rematch_existing": True,
    "folder_watchers": False, "list_watchers": False,
}


def enabled(key):
    return db.get_state("preference:" + key, "1" if DEFAULTS.get(key, False) else "0") == "1"


def save(key, value):
    db.set_state("preference:" + key, "1" if value else "0")


def text_scale():
    value = db.get_state("text_scale", "1.0")
    return float(value) if value in ("1.0", "1.15", "1.3") else 1.0


def windows_light_theme():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            return bool(winreg.QueryValueEx(key, "AppsUseLightTheme")[0])
    except (ImportError, OSError):
        return False


def system_high_contrast():
    try:
        import ctypes
        from ctypes import wintypes
        class HIGHCONTRAST(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwFlags", wintypes.DWORD), ("lpszDefaultScheme", wintypes.LPWSTR)]
        setting = HIGHCONTRAST()
        setting.cbSize = ctypes.sizeof(setting)
        return bool(ctypes.windll.user32.SystemParametersInfoW(0x0042, setting.cbSize, ctypes.byref(setting), 0) and setting.dwFlags & 1)
    except (AttributeError, OSError):
        return False


def reduced_motion():
    if enabled("reduce_motion"):
        return True
    try:
        import ctypes
        animate = ctypes.c_int(1)
        ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(animate), 0)
        return not animate.value
    except (AttributeError, OSError):
        return False


def motion_duration(milliseconds):
    return 0 if reduced_motion() else milliseconds
