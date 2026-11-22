"""Paint card depth inside reserved margins; no nested graphics effects."""
from PyQt5.QtCore import QRectF,Qt,QPointF
from PyQt5.QtGui import QPainter,QColor,QPen
from PyQt5.QtWidgets import QFrame

class PaperCard(QFrame):
    def paintEvent(self,event):
        from app.ui.manga_pages import active
        if not active():return super().paintEvent(event)
        from app.ui.components.neumorphic import paint_depth
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing)
        rect=QRectF(self.rect()).adjusted(10,10,-10,-10);paint_depth(painter,rect)
        from app.ui.manga_style import manga_colors
        from app.ui.theme_catalog import is_manga_dark
        colors=manga_colors()
        painter.setPen(QPen(QColor(colors['line'] if is_manga_dark() else colors['panel']),1))
        painter.setBrush(QColor(colors['panel']));painter.drawRoundedRect(rect,14,14)
        if self.objectName()=='update_card':
            painter.setPen(QPen(QColor('#ff2e93'),4,Qt.SolidLine,Qt.RoundCap));painter.drawLine(rect.topLeft()+QPointF(2,14),rect.bottomLeft()+QPointF(2,-14))
