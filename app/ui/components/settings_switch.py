"""Keyboard-operable, antialiased settings switch."""
from PyQt5.QtWidgets import QCheckBox, QApplication
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen
from app.ui.theme import COLORS


class SettingsSwitch(QCheckBox):
    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setChecked(checked)
        self.setFixedSize(44, 36)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.toggled.connect(self.update)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.update()

    def paintEvent(self, event):
        colors = COLORS.get(QApplication.instance().property("animevaultTheme"), COLORS["dark"])
        if self.property('animevaultTwilightSwitch'):
            from app.ui.home_style import colors as theme_colors
            c=theme_colors();colors=dict(accent_secondary=c['coral'],bg_card_alt=c['raised'],text_muted=c['muted'],bg_primary=c['bg'],border_focus=c['coral'])
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        track = QRectF(0, 0, 34, 18)
        track.moveCenter(QRectF(self.rect()).center())
        painter.setBrush(QColor(colors["accent_secondary"] if self.isChecked() else colors["bg_card_alt"]))
        painter.setPen(QPen(QColor(colors["text_muted"]), 1) if not self.isChecked() else Qt.NoPen)
        painter.drawRoundedRect(track, 9, 9)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(colors["bg_primary"] if self.isChecked() else colors["text_muted"]))
        thumb_x = track.right() - 15 if self.isChecked() else track.left() + 3
        painter.drawEllipse(QRectF(thumb_x, track.top() + 3, 12, 12))
        if self.hasFocus():
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(colors["border_focus"]), 2))
            focus = track.adjusted(-3, -3, 3, 3)
            painter.drawRoundedRect(focus, 12, 12)
