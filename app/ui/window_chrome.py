"""Use Windows' native title bar with colors from the active app theme."""
import ctypes
import sys
from PyQt5 import sip
from PyQt5.QtCore import QObject, QEvent, QTimer, Qt


def _colorref(color):
    value = color.lstrip("#")
    return int(value[0:2], 16) | int(value[2:4], 16) << 8 | int(value[4:6], 16) << 16


def _native_handle(widget):
    """Read an existing native handle without recreating a closing window."""
    try:
        if sip.isdeleted(widget) or not widget.isVisible() or not widget.isWindow():
            return None
        handle = widget.effectiveWinId()
        return int(handle) if handle else None
    except (TypeError, ValueError, RuntimeError):
        return None


def apply_title_bar(widget, app):
    if app is None or sip.isdeleted(app) or sys.platform != "win32" or app.platformName() != "windows" or sip.isdeleted(widget):
        return
    if not widget.isWindow() or widget.windowFlags() & Qt.FramelessWindowHint:
        return
    hwnd = _native_handle(widget)
    if hwnd is None:
        return
    from app.ui.theme import COLORS
    theme = app.property("animevaultTheme") or "dark"
    contrast = bool(app.property("animevaultHighContrast"))
    colors = COLORS.get(theme, COLORS["dark"])
    try:
        api = ctypes.windll.dwmapi.DwmSetWindowAttribute
        api.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
        api.restype = ctypes.c_long
        def set_attribute(attribute, value):
            data = ctypes.c_uint(value)
            return api(hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data))
        if widget.property("animevaultCustomTitleBar"):
            user = ctypes.windll.user32
            get_style = user.GetWindowLongPtrW
            get_style.argtypes = [ctypes.c_void_p, ctypes.c_int]
            get_style.restype = ctypes.c_ssize_t
            set_style = user.SetWindowLongPtrW
            set_style.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
            set_style.restype = ctypes.c_ssize_t
            style = get_style(hwnd, -16)
            # Remove only the short native caption; keep thick-frame resizing,
            # minimize/maximize flags and the native system menu/snap behavior.
            if style & 0x00C00000:
                set_style(hwnd, -16, style & ~0x00C00000)
                position = user.SetWindowPos
                position.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
                position(hwnd, None, 0, 0, 0, 0, 0x0027)
        # Windows 10 uses immersive dark mode; Windows 11 also supports exact colors.
        dark = int(theme == "dark" and not contrast)
        if set_attribute(20, dark) != 0:
            set_attribute(19, dark)
        for attribute, key in ((35, "bg_primary"), (36, "text_primary"), (34, "bg_card")):
            set_attribute(attribute, 0xFFFFFFFF if contrast else _colorref(colors[key]))
    except (AttributeError, OSError, ValueError, TypeError, RuntimeError):
        # Older Windows and other platforms retain the standard native frame.
        return


class TitleBarStyler(QObject):
    def eventFilter(self, widget, event):
        if event.type() in (QEvent.Show, QEvent.WinIdChange) and hasattr(widget, "isWindow") and widget.isWindow() and widget.isVisible():
            app = self.parent()
            QTimer.singleShot(0, lambda: apply_title_bar(widget, app) if not sip.isdeleted(widget) else None)
        return False


def install_title_bar_style(app):
    if not hasattr(app, "_title_bar_styler"):
        app._title_bar_styler = TitleBarStyler(app)
        app.installEventFilter(app._title_bar_styler)
    for widget in app.topLevelWidgets():
        if widget.isVisible():
            apply_title_bar(widget, app)


def show_system_menu(widget, point):
    if sys.platform != "win32":
        return
    user = ctypes.windll.user32
    hwnd = _native_handle(widget)
    if hwnd is None:
        return
    user.GetSystemMenu.argtypes = [ctypes.c_void_p, ctypes.c_bool]
    user.GetSystemMenu.restype = ctypes.c_void_p
    menu = user.GetSystemMenu(hwnd, False)
    user.TrackPopupMenu.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
    # Get the native position directly for mixed-DPI monitor configurations.
    from ctypes import wintypes
    cursor = wintypes.POINT()
    user.GetCursorPos(ctypes.byref(cursor))
    command = user.TrackPopupMenu(menu, 0x0102, cursor.x, cursor.y, 0, hwnd, None)
    if command:
        user.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
        user.PostMessageW(hwnd, 0x0112, command, 0)


def maximize_bounds(monitor, work, frame=(0,0,0,0)):
    """Fill the work area with the client, placing resize borders outside it."""
    left,top,right,bottom=frame
    return (work[0]-monitor[0]-left,work[1]-monitor[1]-top,
            work[2]-work[0]+left+right,work[3]-work[1]+top+bottom)


def handle_maximize_message(widget, message):
    """Keep a custom-caption window inside the monitor's taskbar work area."""
    if sys.platform != "win32" or not message or widget.isFullScreen():
        return False
    from ctypes import wintypes
    class MINMAXINFO(ctypes.Structure):
        _fields_ = [("reserved", wintypes.POINT), ("max_size", wintypes.POINT), ("max_position", wintypes.POINT), ("min_track", wintypes.POINT), ("max_track", wintypes.POINT)]
    class MONITORINFO(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT), ("work", wintypes.RECT), ("flags", wintypes.DWORD)]
    try:
        event = wintypes.MSG.from_address(int(message))
        if event.message != 0x0024 or not event.lParam:  # WM_GETMINMAXINFO
            return False
        user = ctypes.windll.user32
        user.MonitorFromWindow.argtypes = [ctypes.c_void_p, wintypes.DWORD]
        user.MonitorFromWindow.restype = ctypes.c_void_p
        monitor = user.MonitorFromWindow(event.hWnd, 2)
        info = MONITORINFO()
        info.size = ctypes.sizeof(info)
        user.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]
        if not user.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return False
        m, w = info.monitor, info.work
        # The thick resize frame remains after removing the native caption.
        # Windows needs its outer rectangle expanded by that frame; otherwise
        # the visible client is inset on every edge instead of fully maximizing.
        try:
            user.GetDpiForWindow.argtypes=[ctypes.c_void_p]
            user.GetDpiForWindow.restype=ctypes.c_uint
            dpi=user.GetDpiForWindow(event.hWnd) or 96
            user.GetSystemMetricsForDpi.argtypes=[ctypes.c_int,ctypes.c_uint]
            user.GetSystemMetricsForDpi.restype=ctypes.c_int
            metric=lambda index:user.GetSystemMetricsForDpi(index,dpi)
        except AttributeError:
            metric=user.GetSystemMetrics
        # Qt's custom-caption client includes the one-pixel visible border.
        border_x=max(0,metric(32)+metric(92)-metric(5))
        border_y=max(0,metric(33)+metric(92)-metric(6))
        x, y, width, height = maximize_bounds((m.left,m.top,m.right,m.bottom), (w.left,w.top,w.right,w.bottom),
                                             (border_x,border_y,border_x,border_y))
        limits = MINMAXINFO.from_address(event.lParam)
        limits.max_position.x, limits.max_position.y = x, y
        limits.max_size.x, limits.max_size.y = width, height
        scale = widget.devicePixelRatioF()
        limits.min_track.x = max(limits.min_track.x, round(widget.minimumWidth() * scale))
        limits.min_track.y = max(limits.min_track.y, round(widget.minimumHeight() * scale))
        return True
    except (AttributeError, OSError, TypeError, ValueError):
        return False
