"""A taller caption area that retains the native Windows resize frame."""
from PyQt5.QtCore import Qt, QEvent, QPointF, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QKeySequence
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QApplication, QShortcut
from app.ui.theme import COLORS


class CaptionButton(QPushButton):
    def __init__(self, role, window, callback, parent=None):
        super().__init__(parent)
        self.role, self.host = role, window
        self.setObjectName("caption_" + role)
        self.setFixedSize(48, 44)
        self.setAccessibleName({"minimize": "Minimize window", "maximize": "Maximize or restore window", "close": "Close window"}[role])
        self.setToolTip(self.accessibleName())
        self.clicked.connect(callback)

    def paintEvent(self, event):
        colors = COLORS.get(QApplication.instance().property("animevaultTheme"), COLORS["dark"])
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        hover = self.underMouse() or self.hasFocus()
        if hover:
            painter.fillRect(self.rect(), QColor(colors["accent"] if self.role == "close" else colors["bg_hover"]))
        painter.setPen(QPen(QColor(colors["on_red"] if hover and self.role == "close" else colors["text_primary"]), 1.2))
        x, y = self.width()/2, self.height()/2
        if self.role == "minimize":
            painter.drawLine(QPointF(x-5, y+3), QPointF(x+5, y+3))
        elif self.role == "close":
            painter.drawLine(QPointF(x-4, y-4), QPointF(x+4, y+4))
            painter.drawLine(QPointF(x+4, y-4), QPointF(x-4, y+4))
        elif self.host.isMaximized():
            painter.drawPolyline(*[QPointF(x-2,y-5), QPointF(x+5,y-5), QPointF(x+5,y+2)])
            painter.drawRect(QRectF(x-5,y-2,7,7))
        else:
            painter.drawRect(QRectF(x-5,y-5,10,10))


class AppTitleBar(QFrame):
    def __init__(self, window):
        super().__init__(window)
        self.host = window
        self.setObjectName("app_title_bar")
        self.setFixedHeight(44)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 0, 0)
        layout.setSpacing(10)
        self.logo = QLabel()
        self.logo.setFixedSize(20, 20)
        self.logo.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self.logo)
        title = QLabel("Anime Vault")
        title.setObjectName("app_caption_title")
        title.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(title)
        layout.addStretch()
        self.minimize_button = CaptionButton("minimize", window, window.showMinimized, self)
        self.maximize_button = CaptionButton("maximize", window, self.toggle_maximized, self)
        self.close_button = CaptionButton("close", window, window.close, self)
        for button in (self.minimize_button, self.maximize_button, self.close_button):
            layout.addWidget(button)
        self.fullscreen_shortcut = QShortcut(QKeySequence("F11"), window)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        self._fullscreen_was_maximized = False
        self._update_maximize_hint()
        window.installEventFilter(self)
        self.setAccessibleName("Anime Vault window title bar")

    def eventFilter(self, obj, event):
        if obj is self.host and event.type() in (QEvent.WindowStateChange, QEvent.WindowIconChange, QEvent.Show):
            self.logo.setPixmap(self.host.windowIcon().pixmap(20, 20))
            self.maximize_button.update()
            self._update_maximize_hint()
            from app.ui.window_chrome import apply_title_bar
            apply_title_bar(self.host, QApplication.instance())
        return False

    def _update_maximize_hint(self):
        label = "Exit fullscreen and show taskbar" if self.host.isFullScreen() else "Restore window" if self.host.isMaximized() else "Maximize (keep taskbar visible)"
        self.maximize_button.setToolTip(label + "\nExclusive fullscreen: F11")
        self.maximize_button.setAccessibleName(label)

    def toggle_fullscreen(self):
        if self.host.isFullScreen():
            self.host.showMaximized() if self._fullscreen_was_maximized else self.host.showNormal()
        else:
            self._fullscreen_was_maximized = self.host.isMaximized()
            self.host.showFullScreen()
        self._update_maximize_hint()

    def toggle_maximized(self):
        if self.host.isFullScreen():
            self.host.showMaximized()
        else:
            self.host.showNormal() if self.host.isMaximized() else self.host.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.host.windowHandle():
            self.host.windowHandle().startSystemMove()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_maximized()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        from app.ui.window_chrome import show_system_menu
        show_system_menu(self.host, event.globalPos())
