"""Readable boxed choices in a reusable, keyboard-accessible filter popover."""
from PyQt5.QtCore import Qt,QPoint,pyqtSignal
from PyQt5.QtWidgets import QPushButton,QFrame,QVBoxLayout,QHBoxLayout,QLabel,QWidget,QScrollArea
from app.ui.components.flow_layout import FlowLayout
from app.ui.home_style import colors,px


class _TagPopup(QFrame):
    def refresh_home_style(self):self.parentWidget()._style_popup(self)
    def keyPressEvent(self,event):
        if event.key()==Qt.Key_Escape:self.parentWidget().hidePopup();event.accept()
        else:super().keyPressEvent(event)


class TagPicker(QPushButton):
    currentIndexChanged=pyqtSignal(int)
    def __init__(self,title,multiple=True,parent=None):
        super().__init__(parent);self.title=title;self.multiple=multiple;self.items=[];self.selected=set();self.popup=None
        self.setCursor(Qt.PointingHandCursor);self.setMinimumHeight(44);self.setAccessibleName(title)
        self.clicked.connect(self.showPopup);self._refresh_label()
    def addItem(self,label,value=None):
        self.items.append((label,value))
        if not self.multiple and len(self.items)==1:self.selected={0}
        self._refresh_label()
    def addItems(self,labels):
        for label in labels:self.addItem(label,label)
    def count(self):return len(self.items)
    def currentIndex(self):return min(self.selected) if self.selected else 0
    def currentData(self):
        values=[self.items[i][1] for i in sorted(self.selected)]
        return None if not values else values[0] if len(values)==1 else tuple(values)
    def currentText(self):return self.items[self.currentIndex()][0] if self.items else ''
    def setCurrentText(self,value):
        index=next((i for i,item in enumerate(self.items) if item[0]==value),-1)
        if index>=0:self.setCurrentIndex(index)
    def setCurrentIndex(self,index):
        if not 0<=index<len(self.items):return
        values={index} if not self.multiple or self.items[index][1] is not None else set()
        self._set_selected(values)
    def _set_selected(self,values):
        if self.selected==values:return
        self.selected=values;self._refresh_label();self._refresh_checks();self.currentIndexChanged.emit(self.currentIndex())
    def toggle(self,index):
        if not self.multiple:self.setCurrentIndex(index);self.hidePopup();return
        if self.items[index][1] is None:self._set_selected(set());return
        values=set(self.selected)
        if index in values:values.remove(index)
        else:values.add(index)
        self._set_selected(values)
    def _refresh_label(self):
        labels=[self.items[i][0] for i in sorted(self.selected)]
        value=(self.items[0][0] if self.items else self.title) if not labels else labels[0] if len(labels)==1 else f'{self.title} · {len(labels)} selected'
        if self.multiple and len(labels)==1:value+=' · 1 selected'
        self.setText(value+'  ▾');self.setToolTip('\n'.join(labels) or value)
        self.setAccessibleDescription(f'{len(labels)} selected. '+', '.join(labels))
    def _refresh_checks(self):
        if self.popup is None:return
        for i,button in enumerate(self.tag_buttons):
            button.setChecked(i in self.selected or (not self.selected and self.items[i][1] is None))
        self.count_label.setText(f'{len(self.selected)} selected' if self.multiple else 'Choose one')
    def _style_popup(self,popup):
        c=colors();popup.setProperty('animevaultOwnScaledStyle',True)
        popup.setStyleSheet(f'''QFrame#tag_picker_popup {{background:{c['panel']};border:1px solid {c['line']};border-radius:12px;}}
            QLabel {{color:{c['text']};background:transparent;border:none;font-size:{px(14)}px;}}
            QWidget#tag_choices, QScrollArea, QScrollArea>QWidget {{background:transparent;border:none;}}
            QPushButton {{background:{c['raised']};color:{c['text']};border:1px solid {c['line']};border-radius:9px;padding:6px 12px;min-height:{px(32)}px;font-size:{px(14)}px;}}
            QPushButton:hover, QPushButton:focus {{border:1px solid {c['coral']};}}
            QPushButton:checked {{background:{c['coral']};color:{c['on_coral']};border-color:{c['coral']};}}''')
    def showPopup(self):
        if self.popup is not None:
            self._style_popup(self.popup);self._position_popup();return
        popup=_TagPopup(self,Qt.Popup|Qt.FramelessWindowHint);self.popup=popup;popup.setObjectName('tag_picker_popup');popup.setAccessibleName(self.title+' options')
        self._style_popup(popup)
        box=QVBoxLayout(popup);box.setContentsMargins(16,16,16,16);box.setSpacing(12)
        header=QHBoxLayout();header.addWidget(QLabel(self.title),1);self.count_label=QLabel();header.addWidget(self.count_label);box.addLayout(header)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content=QWidget();content.setObjectName('tag_choices');flow=FlowLayout(content);self.tag_buttons=[]
        for index,(label,_) in enumerate(self.items):
            tag=QPushButton(label);tag.setCheckable(True);tag.setCursor(Qt.PointingHandCursor);tag.setAccessibleName(label);tag.setMinimumWidth(px(110) if self.multiple else px(260))
            tag.clicked.connect(lambda checked=False,i=index:self.toggle(i));flow.addWidget(tag);self.tag_buttons.append(tag)
        scroll.setWidget(content);box.addWidget(scroll)
        done=QPushButton('Done' if self.multiple else 'Close');done.setCursor(Qt.PointingHandCursor);done.clicked.connect(self.hidePopup);box.addWidget(done,0,Qt.AlignRight)
        self._content=content;self._flow=flow;self._scroll=scroll
        self._position_popup()
    def _position_popup(self):
        popup=self.popup;screen=self.screen().availableGeometry();width=min(px(520 if self.multiple else 360),screen.width()-24)
        popup.setFixedWidth(width)
        for tag in self.tag_buttons:tag.ensurePolished()
        height=self._flow.heightForWidth(width-36);self._content.setMinimumHeight(height)
        self._scroll.setFixedHeight(min(height+8,max(120,screen.height()-190)))
        popup.adjustSize();self._refresh_checks()
        point=self.mapToGlobal(QPoint(0,self.height()+6));x=max(screen.left()+8,min(point.x(),screen.right()-popup.width()-8));y=point.y()
        if y+popup.height()>screen.bottom():y=self.mapToGlobal(QPoint()).y()-popup.height()-6
        popup.move(x,max(screen.top()+8,y));popup.show();self.tag_buttons[self.currentIndex()].setFocus()
    def hidePopup(self):
        if self.popup:self.popup.hide()
        self.setFocus(Qt.OtherFocusReason)
    def hideEvent(self,event):
        if self.popup:self.popup.hide()
        super().hideEvent(event)
