"""Bounded Windows IPC for an app-launched PotPlayer instance only.

Protocol constants: https://github.com/ld3l/PotPlayerControl/blob/main/raw.md
20482/20484 are milliseconds; 20486 is playback state. No global key injection.
"""
import re
from pathlib import Path


def window_for(process, path):
    import win32gui, win32process
    if process is None:
        raise TimeoutError('No process handle for PotPlayer.')
    matches = []
    def inspect(hwnd, _):
        if win32process.GetWindowThreadProcessId(hwnd)[1] != process.pid:
            return
        if win32gui.GetClassName(hwnd) not in ('PotPlayer64', 'PotPlayer'):
            return
        matches.append((hwnd, win32gui.GetWindowText(hwnd)))
    win32gui.EnumWindows(inspect, None)
    if not matches:
        raise TimeoutError('Waiting for the app-launched PotPlayer window.')
    name = Path(path).name.casefold()
    stem = Path(path).stem.casefold()
    for hwnd, title in matches:
        title_cf = title.casefold()
        if name in title_cf or (len(stem) >= 3 and re.search(r'(?<!\w)' + re.escape(stem) + r'(?!\w)', title_cf)):
            return hwnd
    # While PotPlayer is initializing the file, its window title is the generic player name.
    for hwnd, title in matches:
        cleaned = title.strip().casefold()
        if cleaned in ('', 'potplayer', 'potplayer64', 'daum potplayer', 'potplayer 64-bit'):
            return hwnd
    from app.core.playback import MediaChanged
    raise MediaChanged('PotPlayer changed media, or its title no longer identifies the selected file.')


def send(hwnd, message, query, value=0):
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.WinDLL('user32',use_last_error=True)
    # HWND, WPARAM, LPARAM and DWORD_PTR are pointer-sized on 64-bit Windows.
    # Default ctypes int conversion can truncate the handle or overwrite result.
    send_message=user32.SendMessageTimeoutW
    send_message.argtypes=[wintypes.HWND,wintypes.UINT,ctypes.c_size_t,ctypes.c_ssize_t,
                          wintypes.UINT,wintypes.UINT,ctypes.POINTER(ctypes.c_size_t)]
    send_message.restype=ctypes.c_ssize_t
    result = ctypes.c_size_t(0)
    # SMTO_ABORTIFHUNG = 0x0002
    ok = send_message(hwnd, message, query, value, 0x0002, 200, ctypes.byref(result))
    if not ok:
        raise TimeoutError('PotPlayer did not respond to its playback query.')
    return ctypes.c_ssize_t(result.value).value


def poll(process, path):
    hwnd = window_for(process, path)
    duration = send(hwnd, 1024, 20482) / 1000.0
    position = send(hwnd, 1024, 20484) / 1000.0
    status = send(hwnd, 1024, 20486)
    paused = (status != 2)
    return max(0.0, position), max(0.0, duration), paused


def toggle(process, path):
    send(window_for(process, path), 273, 10014)
