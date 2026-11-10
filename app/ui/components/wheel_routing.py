"""Let page wheels pass closed editors; retain native popup/list scrolling."""
from PyQt5.QtCore import QObject,QEvent,QPointF
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QApplication,QWidget,QComboBox,QAbstractSpinBox,QAbstractScrollArea,QAbstractItemView


class WheelRouting(QObject):
    def eventFilter(self,obj,event):
        if event.type()==QEvent.Polish and isinstance(obj,QAbstractItemView):
            obj.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        if event.type()!=QEvent.Wheel or not isinstance(obj,QWidget):return False
        popup=QApplication.activePopupWidget()
        if popup and (popup is obj or popup.isAncestorOf(obj)):return False
        delta=event.pixelDelta().y() or event.angleDelta().y()
        if not delta:return False
        # A closed selector must not swallow the page wheel or change a match.
        editor=obj
        while editor and not isinstance(editor,(QComboBox,QAbstractSpinBox,QAbstractScrollArea)):
            editor=editor.parentWidget()
        if isinstance(editor,QComboBox) and editor.view().isVisible():return False
        if not isinstance(editor,(QComboBox,QAbstractSpinBox)):
            # Nested viewports may consume wheels even at their scroll boundary.
            if not isinstance(editor,QAbstractScrollArea) or obj is not editor.viewport():return False
            bar=editor.verticalScrollBar()
            if (delta>0 and bar.value()>bar.minimum()) or (delta<0 and bar.value()<bar.maximum()):return False
        ancestor=editor.parentWidget()
        while ancestor:
            if isinstance(ancestor,QAbstractScrollArea):
                bar=ancestor.verticalScrollBar()
                if (delta>0 and bar.value()>bar.minimum()) or (delta<0 and bar.value()<bar.maximum()):
                    viewport=ancestor.viewport()
                    forwarded=QWheelEvent(QPointF(viewport.mapFromGlobal(event.globalPos())),QPointF(event.globalPos()),
                        event.pixelDelta(),event.angleDelta(),event.buttons(),event.modifiers(),event.phase(),event.inverted(),event.source())
                    QApplication.sendEvent(viewport,forwarded)
                    event.accept()
                    return True
            ancestor=ancestor.parentWidget()
        if isinstance(editor,(QComboBox,QAbstractSpinBox)):
            # Keep controls editable via keyboard/menu, even at the page edge.
            event.accept()
            return True
        return False


def install_wheel_routing(app):
    if not hasattr(app,'_wheel_routing'):
        app._wheel_routing=WheelRouting(app)
        app.installEventFilter(app._wheel_routing)
        for widget in app.allWidgets():
            if isinstance(widget,QAbstractItemView):widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
