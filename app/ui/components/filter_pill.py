"""Vector-painted Library pills with smooth edges at display scale."""
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QApplication, QPushButton

from app.ui.theme import COLORS


class FilterPill(QPushButton):
    def paintEvent(self, event):
        colors = COLORS.get(QApplication.instance().property("animevaultTheme"), COLORS["dark"])
        active = self.property("active") == "true"
        hovered = self.underMouse()
        background = QColor("#ffffff" if active else colors["bg_hover"] if hovered else colors["bg_card"])
        text = QColor("#111827" if active else colors["text_primary"] if hovered else colors["text_secondary"])
        border = QColor(colors["text_primary"])
        border.setAlpha(0 if active else 31 if QApplication.instance().property("animevaultTheme") != "light" else 36)
        if self.property('homePill'):
            from app.ui.home_style import colors as home_colors
            c=home_colors();background=QColor(c['coral'] if active else c['raised'] if hovered else c['panel'])
            text=QColor(c['on_coral'] if active else c['text']);border=QColor(c['line'])
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        rect = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        painter.setPen(QPen(border, 1))
        painter.setBrush(background)
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        if self.hasFocus():
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(colors["border_focus"]), 2))
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), (rect.height() - 4) / 2, (rect.height() - 4) / 2)
        painter.setFont(self.font())
        painter.setPen(text)
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()
