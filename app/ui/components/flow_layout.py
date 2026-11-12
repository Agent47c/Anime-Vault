"""Small wrapping layout for Home filters at large text/window sizes."""
from PyQt5.QtCore import Qt,QRect,QSize
from PyQt5.QtWidgets import QLayout

class FlowLayout(QLayout):
    def __init__(self,parent=None):
        super().__init__(parent);self.items=[];self.setContentsMargins(0,0,0,0);self.setSpacing(8)
    def addItem(self,item):self.items.append(item)
    def count(self):return len(self.items)
    def itemAt(self,index):return self.items[index] if 0<=index<len(self.items) else None
    def takeAt(self,index):return self.items.pop(index) if 0<=index<len(self.items) else None
    def expandingDirections(self):return Qt.Orientations(Qt.Horizontal)
    def hasHeightForWidth(self):return True
    def heightForWidth(self,width):return self.arrange(QRect(0,0,width,0),True)
    def minimumSize(self):
        result=QSize()
        for item in self.items:result=result.expandedTo(item.minimumSize())
        left,top,right,bottom=self.getContentsMargins()
        return result+QSize(left+right,top+bottom)
    def sizeHint(self):return self.minimumSize()
    def setGeometry(self,rect):super().setGeometry(rect);self.arrange(rect,False)
    def arrange(self,rect,measure):
        left,top,right,bottom=self.getContentsMargins();outer_y=rect.y()
        rect=rect.adjusted(left,top,-right,-bottom)
        x,y=rect.x(),rect.y();height=0;gap=self.spacing()
        for item in self.items:
            size=item.sizeHint();width=min(size.width(),rect.width())
            if x+width>rect.right()+1 and height:
                x=rect.x();y+=height+gap;height=0
            if item.widget() and item.widget().property('homeAlignRight'):x=max(x,rect.right()+1-width)
            if not measure:item.setGeometry(QRect(x,y,width,size.height()))
            x+=width+gap;height=max(height,size.height())
        return y+height-outer_y+bottom
