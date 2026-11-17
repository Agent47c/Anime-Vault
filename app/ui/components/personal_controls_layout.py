"""Use the complete Details band width, retaining narrow-window wrapping."""
from PyQt5.QtCore import QRect
from app.ui.components.flow_layout import FlowLayout


class PersonalControlsLayout(FlowLayout):
    def arrange(self,rect,measure):
        from app.ui.manga_pages import active
        if not active() or len(self.items)!=3:return super().arrange(rect,measure)
        left,top,right,bottom=self.getContentsMargins()
        area=rect.adjusted(left,top,-right,-bottom);gap=self.spacing()
        watch,rating,notes=self.items
        fixed=watch.sizeHint().width()+rating.sizeHint().width()+2*gap
        if area.width()>=fixed+220:
            widths=(area.width()-fixed,watch.sizeHint().width(),rating.sizeHint().width())
            height=max(item.sizeHint().height() for item in self.items);x=area.x()
            for item,width in zip((notes,watch,rating),widths):
                if not measure:item.setGeometry(QRect(x,area.y(),width,height))
                x+=width+gap
            return top+height+bottom
        original=self.items
        try:
            self.items=[notes,watch,rating]
            return super().arrange(rect,measure)
        finally:self.items=original
