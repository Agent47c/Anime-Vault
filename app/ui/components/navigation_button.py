"""Crisp capsule navigation with lightweight, reduced-motion-aware hover."""
from PyQt5.QtCore import Qt,QRectF,QSize,QPropertyAnimation,QEasingCurve,pyqtProperty,pyqtSignal
from PyQt5.QtGui import QColor,QPainter,QFont,QFontMetricsF,QPen
from PyQt5.QtWidgets import QPushButton,QApplication
from app.ui.home_style import colors,px


def blend(first,second,amount):
    a,b=QColor(first),QColor(second)
    return QColor.fromRgbF(*(a.getRgbF()[i]*(1-amount)+b.getRgbF()[i]*amount for i in range(4)))


class NavigationButton(QPushButton):
    size_changed=pyqtSignal()
    def __init__(self,title,parent=None):
        self.caption=title;self.count=None;self._hover=0.0
        super().__init__(title,parent)
        self.setObjectName('home_tab');self.setFixedHeight(44);self.setCursor(Qt.PointingHandCursor)
        self.setProperty('animevaultOwnScaledStyle',True)
        self.hover_animation=QPropertyAnimation(self,b'hoverAmount',self)
        self.hover_animation.setEasingCurve(QEasingCurve.OutCubic)
    def setText(self,text):
        if text==self.text():return
        suffix=text[len(self.caption):].strip() if text.startswith(self.caption) else ''
        self.count=int(suffix) if self.caption in ('Updates','Downloads') and suffix.isdigit() and int(suffix)>0 else None
        super().setText(text);self.setAccessibleName(text);self.updateGeometry();self.update();self.size_changed.emit()
    def _font(self):
        font=QFont('Plus Jakarta Sans');font.setPixelSize(px(14));font.setWeight(QFont.Medium);return font
    def _badge_width(self):
        return max(24,round(QFontMetricsF(self._font()).horizontalAdvance(str(self.count)))+12) if self.count else 0
    def sizeHint(self):
        text=self.caption if self.count else self.text()
        width=QFontMetricsF(self._font()).horizontalAdvance(text)+44
        if self.count:width+=8+self._badge_width()
        return QSize(round(width),44)
    def minimumSizeHint(self):return self.sizeHint()
    @pyqtProperty(float)
    def hoverAmount(self):return self._hover
    @hoverAmount.setter
    def hoverAmount(self,value):self._hover=value;self.update()
    def _animate(self,target):
        self.hover_animation.stop();duration=0 if QApplication.instance().property('animevaultReducedMotion') else 180
        if not duration:self.hoverAmount=target;return
        self.hover_animation.setDuration(duration);self.hover_animation.setStartValue(self._hover);self.hover_animation.setEndValue(target);self.hover_animation.start()
    def enterEvent(self,event):self._animate(1.0);super().enterEvent(event)
    def leaveEvent(self,event):self._animate(0.0);super().leaveEvent(event)
    def hideEvent(self,event):self.hover_animation.stop();self.hoverAmount=0.0;super().hideEvent(event)
    def paintEvent(self,event):
        c=colors();active=bool(self.property('active'));p=QPainter(self)
        p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.TextAntialiasing)
        if not self.isEnabled():p.setOpacity(.4)
        lift=2*self._hover;rect=QRectF(1,3-lift,self.width()-2,self.height()-5)
        p.setPen(Qt.NoPen)
        p.setBrush(blend(c['coral'],c['text'],self._hover*.09) if active else blend(c['panel'],c['raised'],self._hover))
        p.drawRoundedRect(rect,rect.height()/2,rect.height()/2)
        if self.hasFocus():
            p.setBrush(Qt.NoBrush);p.setPen(QPen(QColor(c['text'] if active else c['coral']),2));p.drawRoundedRect(rect.adjusted(1,1,-1,-1),18,18)
        p.setFont(self._font());p.setPen(QColor(c['on_coral']) if active else blend(c['muted'],c['text'],self._hover))
        label=self.caption if self.count else self.text();text_rect=rect.adjusted(15,0,-15,0)
        if self.count:
            badge=QRectF(rect.right()-15-self._badge_width(),rect.center().y()-11,self._badge_width(),22)
            text_rect.setRight(badge.left()-8)
            p.setPen(Qt.NoPen);p.setBrush(blend(c['coral'],c['on_coral'],.12) if active else QColor(c['coral']));p.drawRoundedRect(badge,7,7)
            p.setPen(QColor(c['on_coral']));p.drawText(badge,Qt.AlignCenter,str(self.count))
            p.setPen(QColor(c['on_coral']) if active else blend(c['muted'],c['text'],self._hover))
        p.drawText(text_rect,Qt.AlignCenter,label)
