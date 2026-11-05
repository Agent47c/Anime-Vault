"""A theme-aware close icon without font-dependent glyphs."""
from PyQt5.QtWidgets import QPushButton, QApplication
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QPointF, QRectF
from app.ui.theme import COLORS


class CloseButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("close_icon_button")
        self.setFixedSize(36, 36)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName("Close anime details")
        self.setToolTip("Close")

    def paintEvent(self, event):
        palette = COLORS.get(QApplication.instance().property("animevaultTheme"), COLORS["dark"])
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(palette["bg_hover"] if self.underMouse() else palette["bg_card_alt"]))
        painter.setPen(QPen(QColor(palette["border_focus"]), 2) if self.hasFocus() else Qt.NoPen)
        painter.drawRoundedRect(QRectF(1, 1, self.width()-2, self.height()-2), 17, 17)
        pen = QPen(QColor(palette["text_primary"] if self.underMouse() else palette["text_secondary"]), 1.8)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        x, y = self.width() / 2, self.height() / 2
        painter.drawLine(QPointF(x - 4, y - 4), QPointF(x + 4, y + 4))
        painter.drawLine(QPointF(x + 4, y - 4), QPointF(x - 4, y + 4))
