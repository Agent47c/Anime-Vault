from app.preferences import motion_duration
"""Embed workflow dialogs in the main content stack without nested event loops."""
from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve
from PyQt5 import sip
from PyQt5.QtGui import QColor, QPainter, QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedLayout, QPushButton, QSizePolicy, QShortcut, QApplication
from app.ui.dialogs.drawer import DrawerDialog


class _Backdrop(QWidget):
    def __init__(self, image):
        super().__init__()
        self.image = image

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.image)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 158))


def navigate(dialog, callback=None):
    parent = dialog.parentWidget()
    while parent and not hasattr(parent, "stacked_widget"):
        parent = parent.parentWidget()
    if parent is None:
        return dialog.exec_()
    host = parent
    previous = host.stacked_widget.currentWidget()
    opener = QApplication.focusWidget()
    page = QWidget(host.stacked_widget)
    page.workflow = dialog
    page._nav_previous = previous
    page._nav_completed = False
    drawer = isinstance(dialog, DrawerDialog) and not getattr(dialog,'full_page',False)
    centered = getattr(dialog, "centered_workflow", False)
    backdrop = None
    if drawer or centered:
        layers = QStackedLayout(page)
        layers.setStackingMode(QStackedLayout.StackAll)
        backdrop = _Backdrop(previous.grab())
        layers.addWidget(backdrop)
        foreground = QWidget()
        foreground.setObjectName("workflow_foreground")
        foreground.setStyleSheet("QWidget#workflow_foreground { background: transparent; }")
        layers.addWidget(foreground)
        layers.setCurrentWidget(foreground)
        row = QHBoxLayout(foreground)
        row.setContentsMargins(16, 10, 16 if centered else 0, 10 if centered else 0)
        row.addStretch()
        panel = QWidget()
        panel.setObjectName("workflow_panel")

        panel.setMaximumWidth(580 if centered else 560)
        row.addWidget(panel, 4)
        if getattr(dialog, "compact_workflow", False):
            row.setAlignment(panel, Qt.AlignVCenter)
            panel.setMaximumHeight(260)
        if centered:
            row.addStretch()
        layout = QVBoxLayout(panel)
    else:
        layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0) if drawer else layout.setContentsMargins(16, 10, 16, 10)
    back = QPushButton("Back")
    back.setMinimumWidth(88)
    if drawer:
        back.hide()
        back.setParent(page)
    else:
        layout.addWidget(back, 0, Qt.AlignLeft)
    dialog.setProperty("animevaultThemeScope", True)
    dialog._embedded = True
    if not dialog.objectName():
        dialog.setObjectName("workflow_dialog")
    dialog.setAccessibleName(dialog.windowTitle())
    dialog.setParent(panel if drawer or centered else page)
    dialog.setWindowFlags(Qt.Widget)
    dialog.setModal(False)
    dialog.setMinimumSize(0, 0)
    dialog.setMaximumSize(16777215, 16777215)
    dialog.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    layout.addWidget(dialog, 1)
    host.stacked_widget.addWidget(page)
    host._navigation_pages = getattr(host, "_navigation_pages", []) + [page]
    def go_back():
        target = previous
        while getattr(target, "_nav_completed", False):
            target = target._nav_previous
        host.stacked_widget.setCurrentWidget(target)
        if opener is not None and not sip.isdeleted(opener) and opener.isVisible():
            opener.setFocus()
    def cleanup_page():
        if sip.isdeleted(page):
            return
        host._navigation_pages = [item for item in host._navigation_pages if item is not page]
        host.stacked_widget.removeWidget(page)
        page.deleteLater()

    def finished(result):
        if page._nav_completed:
            return
        page._nav_completed = True
        if backdrop is not None:
            backdrop.image = QPixmap()
        if callback:
            callback(result)
        if host.stacked_widget.currentWidget() is page:
            go_back()
        if getattr(dialog, "dispose_on_leave", False):
            host.stacked_widget.currentChanged.disconnect(leave_page)
            worker = getattr(dialog, "_worker", None)
            if worker is not None and worker.isRunning():
                worker.finished.connect(cleanup_page)
            else:
                cleanup_page()

    def leave_page(index):
        target=host.stacked_widget.currentWidget()
        ancestor=target
        while ancestor is not None:
            if ancestor is page:return  # A child drawer can return to this page.
            ancestor=getattr(ancestor,'_nav_previous',None)
        if target is not page and not page._nav_completed:
            dialog.reject()

    if getattr(dialog, "dispose_on_leave", False):
        back.clicked.connect(dialog.reject)
        host.stacked_widget.currentChanged.connect(leave_page)
        escape = QShortcut(Qt.Key_Escape, page)
        escape.setContext(Qt.WidgetWithChildrenShortcut)
        escape.activated.connect(dialog.reject)
    else:
        back.clicked.connect(go_back)
    dialog.finished.connect(finished)
    host.stacked_widget.setCurrentWidget(page)
    dialog.show()
    if drawer:
        escape = QShortcut(Qt.Key_Escape, page)
        escape.setContext(Qt.WidgetWithChildrenShortcut)
        escape.activated.connect(dialog.reject)
        row.activate()
        target = panel.pos()
        slide = QPropertyAnimation(panel, b"pos", page)
        slide.setStartValue(QPoint(foreground.width(), target.y()))
        slide.setEndValue(target)
        slide.setDuration(motion_duration(220))
        slide.setEasingCurve(QEasingCurve.OutCubic)
        slide.start()
    return None
