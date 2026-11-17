"""Responsive six/seven-title Library pagination without hidden poster widgets."""
from math import ceil
from PyQt5.QtCore import pyqtSignal,Qt
from PyQt5.QtWidgets import QFrame,QHBoxLayout,QLabel,QPushButton


class LibraryPagination(QFrame):
    changed=pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent);self.setObjectName('pagination');self.page=1;self.size=6;self.signature=None;self.pages=1
        box=QHBoxLayout(self);box.setContentsMargins(18,14,18,14);box.setSpacing(8)
        self.summary=QLabel();box.addWidget(self.summary,1)
        self.previous=QPushButton('Previous');self.previous.clicked.connect(lambda:self.go(self.page-1));box.addWidget(self.previous)
        self.numbers=[]
        for _ in range(5):
            button=QPushButton();button.setCheckable(True);button.clicked.connect(lambda checked=False,b=button:self.go(b.property('page')));box.addWidget(button);self.numbers.append(button)
        self.next=QPushButton('Next');self.next.clicked.connect(lambda:self.go(self.page+1));box.addWidget(self.next)
        for button in (self.previous,self.next,*self.numbers):button.setCursor(Qt.PointingHandCursor)
    def go(self,page):
        target=max(1,min(self.pages,int(page)))
        if target!=self.page:self.page=target;self.changed.emit()
    def paintEvent(self,event):
        from app.ui.manga_pages import active
        if not active():super().paintEvent(event);return
        from app.ui.components.neumorphic import paint_depth
        from PyQt5.QtGui import QPainter,QColor
        from PyQt5.QtCore import QRectF
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing);face=QRectF(self.rect()).adjusted(8,8,-8,-8);paint_depth(painter,face);painter.setPen(Qt.NoPen);painter.setBrush(QColor('white'));painter.drawRoundedRect(face,18,18);painter.end()
    def fit_width(self,width,scale=1):
        """Seven readable cards on wide viewports, six on narrower ones."""
        size=7 if width>=7*200*scale+6*20 else 6
        if size==self.size:return False
        first=(self.page-1)*self.size
        self.size=size;self.page=first//size+1
        return True
    def present(self,records):
        signature=tuple(r['id'] for r in records)
        if signature!=self.signature:self.page=1;self.signature=signature
        self.pages=max(1,ceil(len(records)/self.size));self.page=min(self.page,self.pages)
        start=(self.page-1)*self.size;end=min(len(records),start+self.size)
        self.summary.setText(f'SHOWING {start+1 if records else 0}–{end} OF {len(records)} TITLES   |   PAGE {self.page} / {self.pages}')
        self.previous.setEnabled(self.page>1);self.next.setEnabled(self.page<self.pages)
        candidates=sorted({1,self.pages,*range(max(1,self.page-1),min(self.pages,self.page+1)+1)})
        for button,value in zip(self.numbers,candidates):
            button.setText(str(value));button.setProperty('page',value);button.setChecked(value==self.page);button.setAccessibleName(f'Library page {value}');button.show()
        for button in self.numbers[len(candidates):]:button.hide()
        return records[start:end]
