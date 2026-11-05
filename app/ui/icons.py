"""Small SVG line icons for the application shell."""
from functools import lru_cache

from PyQt5.QtCore import QByteArray, Qt
from PyQt5.QtGui import QIcon, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer


_PATHS = {
    "library": "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
    "updates": "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9 M10 21h4",
    "organizer": "M3 6a2 2 0 0 1 2-2h4l3 3h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
    "storage": "M5 5h14l3 10v4H2v-4z M2 15h20 M17 17h1",
    "settings": "M4 6h16 M4 12h16 M4 18h16 M8 4v4 M16 10v4 M10 16v4",
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
