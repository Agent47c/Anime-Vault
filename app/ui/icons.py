"""Small SVG line icons for the application shell."""
from functools import lru_cache

from PyQt5.QtCore import QByteArray, Qt
from PyQt5.QtGui import QIcon, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer


_PATHS = {
    "more": "M12 4h.01 M12 12h.01 M12 20h.01",
    "chevron-down": "M6 9l6 6 6-6",
    "arrow-left": "M19 12H5 M11 6l-6 6 6 6",
    "plus": "M12 4v16 M4 12h16",
    "import": "M6 3h9l4 4v14H6z M14 3v5h5 M9 12h7 M9 16h5",
    "edit": "M4 16l12-12 4 4L8 20H4z M14 6l4 4",
    "refresh": "M20 7V3l-4 4 M20 7a8 8 0 1 0 0 10 M4 17v4l4-4",
    "info": "M12 8h.01 M12 11v6 M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18",
    "select-multiple": "M2 12l4 4L16 6 M10 16l4 4L24 10",
    "pause": "M8 4v16 M16 4v16",
    "play": "M8 4l12 8-12 8z",
    "check": "M4 12l5 5L20 6",
    "calendar": "M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2 M3 9h18 M7 2v4 M17 2v4 M7 13h1 M12 13h1 M17 13h1 M7 17h1 M12 17h1",
    "flower": "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6 M12 9C4 2 9 0 12 5c3-5 8-3 0 4 M15 12c7-8 10-3 5 0 5 3 3 8-5 0 M12 15c8 7 3 10 0 5-3 5-8 3 0-5 M9 12C2 20-1 15 4 12-1 9 1 4 9 12",
    "library": "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
    "updates": "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9 M10 21h4",
    "organizer": "M3 6a2 2 0 0 1 2-2h4l3 3h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
    "storage": "M5 5h14l3 10v4H2v-4z M2 15h20 M17 17h1",
    "settings": "M4 6h16 M4 12h16 M4 18h16 M8 4v4 M16 10v4 M10 16v4",
    "downloads": "M12 3v12 M7 10l5 5 5-5 M4 17v4h16v-4",
    "list": "M4 6h16 M4 12h16 M4 18h16",
    "tray": "M4 13v7h16v-7 M12 3v12 M8 11l4 4 4-4",
    "power": "M12 3v9 M7 5a8 8 0 1 0 10 0",
    "trash": "M3 6h18 M9 6V3h6v3 M5 6l1 15h12l1-15 M10 10v7 M14 10v7",
    "search": "M15 15l5 5 M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0",
}


@lru_cache(maxsize=48)
def icon(name, color):
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        f'<path d="{_PATHS[name]}" fill="none" stroke="{color}" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )
    pixmap = QPixmap(44, 44)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    QSvgRenderer(QByteArray(svg.encode("utf-8"))).render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)
