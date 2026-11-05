"""Keep windowed Python startup failures visible and diagnosable."""
import sys
import traceback
from pathlib import Path


def prepare_windowed_logging():
    if sys.stdout is not None and sys.stderr is not None:
        return
    path = Path(__file__).resolve().parent.parent / "data" / "startup.log"
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
