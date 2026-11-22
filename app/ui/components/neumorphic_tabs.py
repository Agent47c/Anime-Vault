"""Master raised/inset materials for tab controls, without child effects."""
from PyQt5.QtCore import Qt,QRectF,QSize
from PyQt5.QtGui import QPainter,QColor,QPen
from PyQt5.QtWidgets import QTabBar


class NeumorphicTabBar(QTabBar):
    def tabSizeHint(self,index):
        from app.ui.manga_pages import active
        if not active():return super().tabSizeHint(index)
        from app.ui.home_style import px
        return QSize(self.fontMetrics().horizontalAdvance(self.tabText(index))+px(48),px(58))
    def paintEvent(self,event):
        from app.ui.manga_pages import active
        if not active():return super().paintEvent(event)
        from app.ui.components.neumorphic import paint_depth
        from app.ui.manga_style import manga_colors
        from app.ui.theme_catalog import is_manga_dark
        colors=manga_colors()
        dark=is_manga_dark()
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing)
        for index in range(self.count()):
            rect=QRectF(self.tabRect(index)).adjusted(8,8,-8,-8);selected=index==self.currentIndex()
            if not selected:paint_depth(painter,rect)
            face=colors['raised'] if selected and not dark else colors['panel']
            edge=colors['line'] if selected or dark else colors['panel']
            painter.setBrush(QColor(face));painter.setPen(QPen(QColor(edge),1));painter.drawRoundedRect(rect,8,8)
            if selected:paint_depth(painter,rect,True)
            painter.setPen(QColor(colors['text'] if self.isTabEnabled(index) else colors['muted']))
            painter.drawText(rect,Qt.AlignCenter,self.tabText(index))
