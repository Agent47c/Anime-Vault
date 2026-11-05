"""Explicit Windows administrator launcher; Windows displays the UAC prompt."""
import ctypes
import subprocess
import sys
from pathlib import Path


def launch(extra_args=None):
    if sys.platform != "win32":
        raise RuntimeError("Administrator launching is supported on Windows only.")
    root = Path(__file__).resolve().parent
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    executable = str(pythonw if pythonw.exists() else Path(sys.executable))
    extra_args=list(extra_args or [])
    if extra_args not in ([],['--from-browser']):
        raise ValueError('Unsupported administrator startup arguments.')
    arguments = subprocess.list2cmdline([str(root / "main.py"),*extra_args])
    if getattr(sys, "frozen", False):
        executable, arguments = sys.executable, subprocess.list2cmdline(extra_args)
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, arguments, str(root), 1)
    if result <= 32:
        raise RuntimeError("Administrator launch was cancelled or denied. No app was started.")


if __name__ == "__main__":
    try:
        launch()
    except Exception as error:
        print(error)
        sys.exit(1)
