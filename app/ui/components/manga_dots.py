"""Small cached paper-dot layer, shared by the supplied light workflow panels."""
from PyQt5.QtCore import Qt,QEvent
from PyQt5.QtGui import QPainter,QPixmap,QColor
from PyQt5.QtWidgets import QWidget,QApplication


class PaperDots(QWidget):
    def __init__(self,parent):
        super().__init__(parent);self.setAttribute(Qt.WA_TransparentForMouseEvents);self.setFocusPolicy(Qt.NoFocus)
        self.tile=QPixmap(10,10);self.tile.fill(Qt.transparent)
        painter=QPainter(self.tile);painter.setRenderHint(QPainter.Antialiasing);painter.setPen(Qt.NoPen);painter.setBrush(QColor(120,130,150,35));painter.drawEllipse(4,4,2,2);painter.end()
        parent.installEventFilter(self);self.setGeometry(parent.rect());self.lower()
    def eventFilter(self,obj,event):
        if event.type()==QEvent.Resize:self.setGeometry(obj.rect())
        return False
    def paintEvent(self,event):
        app=QApplication.instance()
        if app.property('animevaultDecorations') is False or app.property('animevaultHighContrast'):return
        painter=QPainter(self);painter.drawTiledPixmap(self.rect(),self.tile);painter.end()


def update_dots(parent,active):
    if parent is None:return
    if active and not hasattr(parent,'_paper_dots'):parent._paper_dots=PaperDots(parent)
    if hasattr(parent,'_paper_dots'):parent._paper_dots.setVisible(active);parent._paper_dots.lower()
