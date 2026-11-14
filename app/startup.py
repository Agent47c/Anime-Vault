"""Keep windowed Python startup failures visible and diagnosable."""
import sys
import traceback
from pathlib import Path


def prepare_windowed_logging():
    if sys.stdout is not None and sys.stderr is not None:
        return
    from app.paths import DATA_DIR
    path = DATA_DIR / "startup.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream
    def report(kind, error, tb):
        traceback.print_exception(kind, error, tb, file=stream)
        stream.flush()
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, f"{error}\n\nDetails: {path}", "AnimeVault startup error", 0x10)
    sys.excepthook = report


def hold_installer_mutex():
    """Let Setup request an orderly close instead of replacing an active app."""
    if sys.platform != 'win32' or not getattr(sys, 'frozen', False):
        return
    import atexit
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.windll.kernel32
    kernel.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.CreateMutexW(None, False, 'AnimeVault.Installed.Desktop')
    if not handle:
        raise ctypes.WinError()
    atexit.register(kernel.CloseHandle, handle)
    try:
        global_handle = kernel.CreateMutexW(None, False, 'Global\\AnimeVault.Installed.Desktop')
        if global_handle:
            atexit.register(kernel.CloseHandle, global_handle)
    except Exception:
        pass
