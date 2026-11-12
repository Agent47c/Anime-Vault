from app.preferences import motion_duration
"""Embed workflow dialogs in the main content stack without nested event loops."""
from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve
from PyQt5 import sip
from PyQt5.QtGui import QColor, QPainter, QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedLayout, QPushButton, QSizePolicy, QShortcut, QApplication, QLabel
from app.ui.dialogs.drawer import DrawerDialog


_TAB_NAMES = {0:'Library', 1:'Organizer', 2:'Updates', 3:'Storage', 4:'Settings', 5:'Downloads'}


def navigation_path(page, owner=None, seen=None):
    """Build the active workflow ancestry without reading data or rebuilding pages."""
    root = [_TAB_NAMES.get(owner, 'Anime Vault')]
    if page is None or sip.isdeleted(page):
        return root
    seen = set() if seen is None else seen
    if id(page) in seen:
        return root
    seen.add(id(page))
    dialog = getattr(page, 'workflow', None)
    if dialog is None:
        return root
    owner = page._nav_owner_index
    previous = page._nav_previous
    if previous is not None and not sip.isdeleted(previous) and not getattr(previous, '_nav_completed', False):
        parts = navigation_path(previous, owner, seen)
    else:
        parts = list(page._nav_parent_path)
    page._nav_parent_path = tuple(parts)
    if not page._nav_completed and not sip.isdeleted(dialog):
        title = dialog.property('navigationTitle') or dialog.windowTitle()
        if title:
            parts.append(title)
    return parts


def _refresh_navigation_titles(dialog):
    page = getattr(dialog, '_navigation_page', None)
    if page is None or sip.isdeleted(page):
        return
    stack = page.parentWidget()
    # Only inspect the small retained workflow chain, never the poster grid.
    for index in range(stack.count()):
        candidate = stack.widget(index)
        ancestor = candidate
        while ancestor is not None and not sip.isdeleted(ancestor):
            if ancestor is page:
                header = getattr(candidate, '_nav_header', None)
                if header is not None and not sip.isdeleted(header):
                    header.refresh_title()
                break
            ancestor = getattr(ancestor, '_nav_previous', None)


class _Backdrop(QWidget):
    def __init__(self, image):
        super().__init__()
        self.image = image

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.image)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 158))


class _NavigationHeader(QWidget):
    """One consistent Back/breadcrumb row for full-page workflows."""
    def __init__(self, owner, dialog, parent):
        super().__init__(parent)
        self.setObjectName('navigation_header')
        self.setProperty('animevaultThemeScope', True)
        self.setProperty('animevaultOwnScaledStyle', True)
        self.owner, self.dialog, self.page = owner, dialog, parent
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)
        self.back = QPushButton('Back')
        self.back.setMinimumWidth(88)
        self.back.setCursor(Qt.PointingHandCursor)
        self.back.setAccessibleName('Go back')
        row.addWidget(self.back)
        self.breadcrumb = QLabel()
        self.breadcrumb.setObjectName('navigation_breadcrumb')
        self.breadcrumb.setTextFormat(Qt.PlainText)
        self.breadcrumb.setWordWrap(True)
        self.breadcrumb.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        row.addWidget(self.breadcrumb, 1)
        self.refresh_title()
        self.refresh_home_style()

    def refresh_title(self):
        parts = navigation_path(self.page, self.owner)
        self.page._nav_breadcrumb_parts = tuple(parts)
        text = ' / '.join(parts)
        self.breadcrumb.setText(text)
        self.breadcrumb.setToolTip(text)

    def refresh_home_style(self):
        from app.ui.home_style import colors, px
        from app.ui.icons import icon
        c = colors()
        self.back.setIcon(icon('arrow-left', c['text']))
        self.setStyleSheet(f"QWidget#navigation_header {{background:{c['bg']};border:none;}} "
                           f"QLabel#navigation_breadcrumb {{background:transparent;border:none;color:{c['muted']};font-size:{px(12)}px;}}")


def set_navigation_title(dialog, title):
    """Update an async workflow's breadcrumb without rebuilding its header."""
    dialog.setProperty('navigationTitle', title)
    _refresh_navigation_titles(dialog)


def navigation_owner(host, page):
    """The root tab that owns a workflow, independent of its stack position."""
    if page is None or sip.isdeleted(page):
        return None
    owner = getattr(page, '_nav_owner_index', None)
    return owner if owner is not None else host.stacked_widget.indexOf(page)


def _available_page(host, page, fallback):
    while page is not None:
        if sip.isdeleted(page):
            break
        if not getattr(page, '_nav_completed', False) and host.stacked_widget.indexOf(page) >= 0:
            return page
        page = getattr(page, '_nav_previous', None)
    return fallback


def switch_tab(host, index, restore=True):
    """Retain live per-tab navigation; explicit searches may request the root."""
    memory = host._tab_navigation = getattr(host, '_tab_navigation', {})
    current = host.stacked_widget.currentWidget()
    owner = navigation_owner(host, current)
    if owner is not None:
        memory[owner] = current
    root = host.stacked_widget.widget(index)
    target = _available_page(host, memory.get(index), root) if restore else root
    memory[index] = target
    header = getattr(target, '_nav_header', None)
    if header is not None and not sip.isdeleted(header):
        header.refresh_title()
    host.stacked_widget.setCurrentWidget(target)


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
    page._nav_owner_index = navigation_owner(host, previous)
    page._nav_parent_path = tuple(navigation_path(previous, page._nav_owner_index))
    page._nav_completed = False
    dialog._navigation_page = page
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

        panel.setMaximumWidth(getattr(dialog,'workflow_width',580 if centered else 560))
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
    header = _NavigationHeader(page._nav_owner_index, dialog, page)
    dialog._navigation_header = page._nav_header = header
    back = header.back
    layout.addWidget(header)
    dialog.windowTitleChanged.connect(lambda _: _refresh_navigation_titles(dialog))
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
        target = _available_page(host, previous, host.stacked_widget.widget(page._nav_owner_index))
        host._tab_navigation = getattr(host, '_tab_navigation', {})
        host._tab_navigation[page._nav_owner_index] = target
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
        memory = getattr(host, '_tab_navigation', {})
        if memory.get(page._nav_owner_index) is page:
            memory[page._nav_owner_index] = _available_page(host, previous, host.stacked_widget.widget(page._nav_owner_index))
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
        if navigation_owner(host, target) != page._nav_owner_index:
            return  # Switching tabs suspends this workflow rather than closing it.
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
        back.clicked.connect(dialog.reject if drawer else go_back)
    dialog.finished.connect(finished)
    host._tab_navigation = getattr(host, '_tab_navigation', {})
    host._tab_navigation[page._nav_owner_index] = page
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
