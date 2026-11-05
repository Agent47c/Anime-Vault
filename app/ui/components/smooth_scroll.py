from app.preferences import motion_duration
"""A single wheel animation; touchpad pixel scrolling stays native."""
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QAbstractAnimation
from PyQt5.QtWidgets import QScrollArea


class SmoothScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._animation = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
        self._animation.setDuration(160)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self.verticalScrollBar().sliderPressed.connect(self._animation.stop)

    def wheelEvent(self, event):
        if not event.pixelDelta().isNull() or event.modifiers() & Qt.ControlModifier or not event.angleDelta().y():
            self._animation.stop()
            super().wheelEvent(event)
            return
        self._animation.setDuration(motion_duration(160))
        bar = self.verticalScrollBar()
        start = bar.value()
        target = self._animation.endValue() if self._animation.state() == QAbstractAnimation.Running else start
        target = max(bar.minimum(), min(bar.maximum(), int(target - event.angleDelta().y())))
        self._animation.stop()
        self._animation.setStartValue(start)
        self._animation.setEndValue(target)
        self._animation.start()
        event.accept()
