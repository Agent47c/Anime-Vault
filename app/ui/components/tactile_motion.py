"""Small-control animation state; transforms painting, never layout geometry."""
from PyQt5.QtCore import QObject,QEvent,QVariantAnimation,QEasingCurve,QPointF,Qt
from PyQt5.QtWidgets import QApplication,QAbstractButton,QToolTip


class TactileMotion(QObject):
    def __init__(self,widget,update,kind='secondary'):
        super().__init__(widget);self.widget=widget;self.update=update;self.kind=kind
        self.hover=0.;self.pressed=False;self.pointer_inside=False
        self.animation=QVariantAnimation(self);self.animation.setDuration(230)
        curve=QEasingCurve(QEasingCurve.BezierSpline)
        curve.addCubicBezierSegment(QPointF(.34,1.56),QPointF(.64,1),QPointF(1,1))
        self.animation.setEasingCurve(curve);self.animation.valueChanged.connect(self._value)
        widget.installEventFilter(self)

    def allowed(self):
        app=QApplication.instance()
        return not(app.property('animevaultReducedMotion') or app.property('animevaultHighContrast'))

    def _value(self,value):self.hover=float(value);self.update()

    def target(self,value):
        self.animation.stop()
        if not self.allowed():self._value(0.);return
        self.animation.setStartValue(float(self.hover));self.animation.setEndValue(float(value));self.animation.start()

    def transform(self,painter):
        if not self.allowed() or not self.widget.isEnabled():return
        h=self.hover;primary=self.kind=='primary';rail=self.kind=='rail'
        down=self.pressed or (isinstance(self.widget,QAbstractButton) and self.widget.isDown())
        scale=(.95 if rail else .97 if primary or self.kind=='chip' else .98) if down else 1
        lift=1 if down else 0
        center=self.widget.rect().center();painter.translate(0,lift)
        painter.translate(center);painter.scale(scale,scale);painter.translate(-center)

    def eventFilter(self,obj,event):
        kind=event.type()
        if kind==QEvent.Enter:self.pointer_inside=True
        elif kind in (QEvent.Leave,QEvent.Hide,QEvent.WindowDeactivate):self.pointer_inside=False
        keyboard_focus=kind==QEvent.FocusIn and event.reason() in (Qt.TabFocusReason,Qt.BacktabFocusReason,Qt.ShortcutFocusReason)
        if kind==QEvent.Enter or keyboard_focus:
            self.target(1.)
            if self.kind=='rail' and kind==QEvent.Enter and obj.toolTip():
                QToolTip.showText(obj.mapToGlobal(obj.rect().topRight()),obj.toolTip(),obj)
        elif kind==QEvent.FocusIn and not self.pointer_inside:
            self.pressed=False;self.target(0.)
        elif kind in (QEvent.Leave,QEvent.FocusOut,QEvent.Hide,QEvent.EnabledChange,QEvent.UngrabMouse,QEvent.WindowDeactivate):
            self.pressed=False;self.target(0.)
        elif kind==QEvent.MouseButtonPress and event.button()==Qt.LeftButton:self.pressed=True;self.update()
        elif kind==QEvent.MouseButtonRelease and event.button()==Qt.LeftButton:self.pressed=False;self.update()
        elif kind==QEvent.KeyPress and event.key() in (Qt.Key_Space,Qt.Key_Return):self.pressed=True;self.update()
        elif kind==QEvent.KeyRelease and event.key() in (Qt.Key_Space,Qt.Key_Return):self.pressed=False;self.update()
        return False
