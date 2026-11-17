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
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing)
        for index in range(self.count()):
            rect=QRectF(self.tabRect(index)).adjusted(8,8,-8,-8);selected=index==self.currentIndex()
            if not selected:paint_depth(painter,rect)
            painter.setBrush(QColor('#e2e5ed' if selected else 'white'));painter.setPen(QPen(QColor('#c4c9d4' if selected else 'white'),1));painter.drawRoundedRect(rect,8,8)
            if selected:paint_depth(painter,rect,True)
            painter.setPen(QColor('#111217' if self.isTabEnabled(index) else '#8a91a2'))
            painter.drawText(rect,Qt.AlignCenter,self.tabText(index))
