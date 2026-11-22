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
        from app.ui.theme_catalog import is_manga
        manga=is_manga()
        if manga:
            from app.ui.manga_style import manga_colors
            from app.ui.theme_catalog import is_manga_dark
            c=manga_colors();dark=is_manga_dark()
            background=QColor('#e5e2e1' if active and dark else 'white' if active else c['panel'] if dark else c['bg'])
            text=QColor('#111217' if active else c['text'])
            painter.setBrush(background)
            if hovered or self.hasFocus():
                painter.setPen(QPen(QColor(c['coral']),1))
        radius=8 if manga else rect.height()/2
        painter.drawRoundedRect(rect,radius,radius)
        if self.hasFocus() and not manga:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(colors["border_focus"]), 2))
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), (rect.height() - 4) / 2, (rect.height() - 4) / 2)
        painter.setFont(self.font())
        painter.setPen(text)
        if manga:
            import re
            match=re.match(r'^(.*?)\s+(\d+)$',self.text())
            if match:
                label,count=match.groups();metrics=painter.fontMetrics();count_width=metrics.horizontalAdvance(count)+14
                total=metrics.horizontalAdvance(label)+count_width+10;x=(self.width()-total)/2
                painter.setPen(text if active else QColor(c['muted']));painter.drawText(QRectF(x,0,metrics.horizontalAdvance(label)+2,self.height()),Qt.AlignVCenter,label)
                badge=QRectF(x+metrics.horizontalAdvance(label)+10,(self.height()-22)/2,count_width,22)
                if active:painter.setPen(Qt.NoPen);painter.setBrush(QColor('#111217'));painter.drawRoundedRect(badge,3,3)
                painter.setPen(QColor('white' if active else c['muted'] if dark else '#7c8599'));painter.drawText(badge,Qt.AlignCenter,count)
                return
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()
