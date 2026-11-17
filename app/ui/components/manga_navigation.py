"""Bounded rail hover animations; distance falloff replaces the HTML's uniform blur."""
from PyQt5.QtCore import QEvent, QVariantAnimation, QEasingCurve, Qt, QPoint
from PyQt5.QtWidgets import QApplication, QGraphicsBlurEffect, QWidget


def blur_for_distance(distance):
    return min(2.4, max(0, distance) * .65)


def opacity_for_blur(radius):
    distance=max(0,radius)/.65
    return 1-.5*distance if distance<=1 else max(.3,.5-.07*(distance-1))


class NavigationDepth(QGraphicsBlurEffect):
    """One effect per small control: blur, gentle fade and the reference's 4% shrink."""
    def draw(self,painter):
        depth=min(1,self.blurRadius()/2.4)
        opacity=opacity_for_blur(self.blurRadius())
        if opacity<=0:return
        painter.save();painter.setOpacity(opacity)
        if hasattr(self,'motion'):self.motion.transform(painter)
        center=self.parent().rect().center();scale=1-.04*depth
        painter.translate(center);painter.scale(scale,scale);painter.translate(-center)
        from app.ui.components.neumorphic import paint_depth
        inset=self.parent().isDown() or self.parent().isChecked() or (hasattr(self,'motion') and self.motion.hover>.01)
        if not QApplication.instance().property('animevaultHighContrast') and not inset:paint_depth(painter,self.parent().rect(),radius=8)
        super().draw(painter)
        if not QApplication.instance().property('animevaultHighContrast') and inset:paint_depth(painter,self.parent().rect(),True,radius=8)
        painter.restore()
    def boundingRectFor(self,rect):return super().boundingRectFor(rect).adjusted(-12,-12,12,12)


class RailSlot(QWidget):
    """Reserve only the closed width; the sibling rail floats above page content."""
    def __init__(self,rail,parent):
        super().__init__(parent);self.rail=rail;self.setFixedWidth(94)
        rail.setParent(parent)
    def sync(self):
        if self.isVisible():
            self.rail.move(self.mapTo(self.rail.parentWidget(),QPoint(0,0)))
            self.rail.setFixedHeight(self.height());self.rail.show();self.rail.raise_()
    def resizeEvent(self,event):super().resizeEvent(event);self.sync()
    def moveEvent(self,event):super().moveEvent(event);self.sync()
    def showEvent(self,event):super().showEvent(event);self.sync()
    def hideEvent(self,event):
        self.rail._expanded=False;self.rail._hovered=None
        self.rail.width_motion.stop();self.rail._set_rail_width(94);self.rail._blur_group(None);self.rail.hide();super().hideEvent(event)


class RailMotion:
    def setup_motion(self, groups):
        self.motion_groups=groups;self._motions=[];self._blur_effects={};self._expanded=False;self._hovered=None
        for group in groups:
            for button in group:
                effect=NavigationDepth(button);effect.setBlurRadius(0);effect.setBlurHints(QGraphicsBlurEffect.AnimationHint)
                from app.ui.components.tactile_motion import TactileMotion
                effect.motion=TactileMotion(button,effect.update,'rail')
                effect.motion.setParent(effect)
                button.setGraphicsEffect(effect);self._blur_effects[button]=effect
                button.installEventFilter(self)
        self.width_motion=QVariantAnimation(self);self.width_motion.setEasingCurve(QEasingCurve.OutCubic)
        self.width_motion.valueChanged.connect(self._set_rail_width)

    def _set_rail_width(self,value):
        width=int(value);self.setFixedWidth(width)
        for group in self.motion_groups:
            for button in group:
                button.setFixedWidth(width-36)
                label=button.property('railLabel')
                count=button.property('collectionCount')
                button.setText((f'{label}  {count}' if count is not None else label) if width>155 else '')

    def _motion_allowed(self):
        app=QApplication.instance()
        return not (app.property('animevaultReducedMotion') or app.property('animevaultHighContrast'))

    def _blur_group(self,group,focused=None):
        for animation in self._motions:animation.stop();animation.deleteLater()
        self._motions=[]
        for items in self.motion_groups:
            anchor=focused if items is group else next((i for i,b in enumerate(items) if b.isChecked()),None) if self._expanded else None
            for index,button in enumerate(items):
                effect=self._blur_effects[button]
                target=blur_for_distance(abs(index-anchor)) if anchor is not None and self._motion_allowed() else 0
                if button is self._hovered:target=0
                if not self._motion_allowed():effect.setBlurRadius(0);continue
                animation=QVariantAnimation(self);animation.setDuration(180 if self._motion_allowed() else 0)
                # QVariantAnimation cannot interpolate float -> integer zero;
                # keep both ends floating-point so hover actually clears blur.
                animation.setStartValue(float(effect.blurRadius()));animation.setEndValue(float(target));animation.valueChanged.connect(effect.setBlurRadius)
                animation.start();self._motions.append(animation)

    def eventFilter(self,obj,event):
        if event.type() in (QEvent.Enter,QEvent.FocusIn):
            self._hovered=obj
            if self._expanded:self._blur_group(None)
        elif event.type() in (QEvent.Leave,QEvent.FocusOut):
            if self._hovered is obj:self._hovered=None
            if self._expanded:self._blur_group(None)
        return super().eventFilter(obj,event)

    def enterEvent(self,event):
        self._expanded=True;self._blur_group(None)
        if not self._motion_allowed():self.width_motion.stop();self._set_rail_width(240);super().enterEvent(event);return
        self.width_motion.stop();self.width_motion.setDuration(280 if self._motion_allowed() else 0)
        self.width_motion.setStartValue(self.width());self.width_motion.setEndValue(240);self.width_motion.start()
        super().enterEvent(event)

    def leaveEvent(self,event):
        self._expanded=False;self._hovered=None
        if not self._motion_allowed():self._blur_group(None);self.width_motion.stop();self._set_rail_width(94);super().leaveEvent(event);return
        self._blur_group(None);self.width_motion.stop();self.width_motion.setDuration(220 if self._motion_allowed() else 0)
        self.width_motion.setStartValue(self.width());self.width_motion.setEndValue(94);self.width_motion.start()
        super().leaveEvent(event)
