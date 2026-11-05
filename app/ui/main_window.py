from app.ui.navigation import navigate
"""
Main Application Window for Anime Library & Storage Manager.
Faithfully recreates the Anime Manager UI Reference mockups:
- Top Header with brand sparkle and central Search bar with Ctrl+K shortcut badge
- Sidebar with main nav, unread update badge, COLLECTIONS section with counts, and live 3 TB drive card
- Bottom status bar with API indicator, scan stats, Online/Offline badge, and drive capacity
- Quit & Tray workflow matching production rules
"""

import os
import shutil
import webbrowser
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFrame, QSystemTrayIcon,
    QMenu, QAction, QDialog, QCheckBox, QLineEdit, QShortcut,
    QProgressBar, QApplication, QSizePolicy, QRadioButton, QButtonGroup,
)
from PyQt5.QtGui import QIcon, QFont, QPixmap, QPainter, QColor, QPen, QKeySequence
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal, QRectF

from app import db
from app.core.storage import disk_snapshot, format_bytes
from app.config import (
    get_theme, is_offline, check_online,
    get_quit_preference, set_quit_preference,
    get_window_geometry, set_window_geometry,
)
from app.ui.theme import COLORS, apply_theme
from app.ui.icons import icon
from app.ui.pages.library_page import LibraryPage
from app.ui.pages.organizer_page import OrganizerPage
from app.ui.pages.updates_page import UpdatesPage
from app.ui.pages.storage_page import StoragePage
from app.ui.pages.settings_page import SettingsPage
from app.ui.pages.detail_modal import DetailModal
from app.ui.dialogs.custom_entry import CustomEntryDialog
from app.ui.dialogs.watched_import_dialog import WatchedImportDialog
from app.core.updater import UpdaterThread
from app.api import server


class ClickableLabel(QLabel):
    """A QLabel that safely emits a clicked signal on mouse press."""
    clicked = pyqtSignal()

    def __init__(self, *args):
        super().__init__(*args)
        self.setFocusPolicy(Qt.StrongFocus)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            event.accept()
            self.clicked.emit()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)


class ClickableFrame(QFrame):
    """A QFrame that safely emits a clicked signal on mouse press without SIP issues."""
    clicked = pyqtSignal()

    def __init__(self, *args):
        super().__init__(*args)
        self.setFocusPolicy(Qt.StrongFocus)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            event.accept()
            self.clicked.emit()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)



class QuitConfirmDialog(QDialog):
    """Clean custom dialog prompting user whether to minimize to tray or quit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Close Anime Vault?")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.choice = None
        self._shade = None
        self._setup_ui()
        self.resize(580, 580)
        self.finished.connect(self._clear_shade)

    def _setup_ui(self):
        from app.ui.components.workflow import chrome, card, text
        body, self.confirm_button = chrome(self, "Close Anime Vault?", "Choose what happens to the app and its background tasks.", "\u7d42\u4e86", "Minimize to tray", self._confirm_choice)
        status, labels = card()
        endpoint = server.api_base_url()
        row = QHBoxLayout()
        pill = text("Running" if endpoint else "Stopped", "workflow_match")
        pill.setWordWrap(False)
        pill.setProperty("tone", "success" if endpoint else "warning")
        row.addWidget(pill, 0, Qt.AlignVCenter)
        row.addWidget(text("Streaming API", "workflow_row_title"))
        row.addWidget(text(endpoint or "Not running"), 1)
        labels.addLayout(row)
        parent = self.parentWidget()
        running = parent._running_threads() if parent and hasattr(parent, "_running_threads") else []
        if running:
            warning = text("Background work is in progress. Exiting will stop it safely.")
            warning.setObjectName("quit_warning")
            labels.addWidget(warning)
        body.addWidget(status)
        self.choice_group = QButtonGroup(self)
        self.tray_radio, self.exit_radio = QRadioButton(), QRadioButton()
        for radio, heading, hint, glyph, recommended in (
            (self.tray_radio, "Minimize to tray", "Keeps streaming and background tasks running", "tray", True),
            (self.exit_radio, "Exit completely", "Stops the app and the streaming server", "power", False),
        ):
            option = ClickableFrame()
            option.setObjectName("quit_choice")
            option.setMinimumHeight(80)
            option.setAccessibleName(heading)
            option.setCursor(Qt.PointingHandCursor)
            line = QHBoxLayout(option)
            line.setContentsMargins(16, 12, 16, 12)
            line.setSpacing(14)
            self.choice_group.addButton(radio)
            radio.setAccessibleName(heading)
            line.addWidget(radio)
            image = QLabel()
            image.setObjectName("quit_icon")
            image.setFixedSize(44, 44)
            image.setAlignment(Qt.AlignCenter)
            color = COLORS.get(QApplication.instance().property("animevaultTheme"), COLORS["dark"])["red_text"]
            image.setPixmap(icon(glyph, color).pixmap(22, 22))
            image.setAttribute(Qt.WA_TransparentForMouseEvents)
            line.addWidget(image)
            description = QVBoxLayout()
            description.setSpacing(3)
            heading_label = text(heading, "workflow_row_title")
            hint_label = text(hint)
            for label in (heading_label, hint_label):
                label.setAttribute(Qt.WA_TransparentForMouseEvents)
            description.addWidget(heading_label)
            description.addWidget(hint_label)
            line.addLayout(description, 1)
            if recommended:
                recommended_label = text("Recommended", "workflow_match")
                recommended_label.setWordWrap(False)
                line.addWidget(recommended_label, 0, Qt.AlignVCenter)
            option.clicked.connect(lambda radio=radio: radio.setChecked(True))
            def select(checked, frame=option):
                frame.setProperty("selected", checked)
                frame.style().unpolish(frame)
                frame.style().polish(frame)
                self.confirm_button.setText("Minimize to tray" if self.tray_radio.isChecked() else "Exit completely")
            radio.toggled.connect(select)
            body.addWidget(option)
        self.tray_radio.setChecked(True)
        remember = QHBoxLayout()
        remember.setSpacing(16)
        self.remember_cb = QCheckBox("Remember my choice")
        self.remember_cb.setCursor(Qt.PointingHandCursor)
        remember.addWidget(self.remember_cb)
        hint = text("Change it in Settings > Application behavior")
        remember.addWidget(hint, 1)
        body.addLayout(remember)
        body.addStretch()
        self.cancel_button.setFocus()

    def _confirm_choice(self):
        self._choose_tray() if self.tray_radio.isChecked() else self._choose_exit()

    def showEvent(self, event):
        parent = self.parentWidget()
        if parent:
            host = parent.window()
            self._shade = QFrame(host)
            self._shade.setObjectName("quit_scrim")
            self._shade.setGeometry(host.rect())
            self._shade.show()
            self._shade.raise_()
            origin = host.mapToGlobal(host.rect().topLeft())
            self.move(origin.x() + (host.width()-self.width())//2, origin.y() + (host.height()-self.height())//2)
        super().showEvent(event)

    def _clear_shade(self, *_):
        if self._shade:
            self._shade.deleteLater()
            self._shade = None

    def _choose_tray(self):
        self.choice = "tray"
        if self.remember_cb.isChecked():
            set_quit_preference("tray")
        self.accept()

    def _choose_exit(self):
        self.choice = "exit"
        if self.remember_cb.isChecked():
            set_quit_preference("exit")
        self.accept()


class MainWindow(QMainWindow):
    """Main window with top header, sidebar navigation, collections, and tray support."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Anime Vault")
        self.setProperty("animevaultCustomTitleBar", True)
        self.setProperty("animevaultScopedWindow", True)
        self.setMinimumSize(1100, 720)

        self._updater_thread = None
        self._unread_updates = 0

        self._setup_ui()
        self._setup_tray()
        self._restore_geometry()
        self._connect_signals()
        self._refresh_metrics()
        self._dirty_pages = set()
        self.stacked_widget.currentChanged.connect(self._refresh_dirty_page)

        # Check connectivity on startup
        self._scan_schedule_timer = QTimer(self)
        self._scan_schedule_timer.timeout.connect(self._check_new_anime)
        self._apply_settings_preferences()
        QTimer.singleShot(0, self._recover_file_operations)
        if db.get_state("scan_schedule", "startup") != "manual":
            QTimer.singleShot(0, self._check_new_anime)

    # -----------------------------------------------------------------------
    # UI Setup
    # -----------------------------------------------------------------------
    def nativeEvent(self, event_type, message):
        from app.ui.window_chrome import handle_maximize_message
        if handle_maximize_message(self, message):
            return True, 0
        return super().nativeEvent(event_type, message)

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        from app.ui.components.title_bar import AppTitleBar
        self.title_bar = AppTitleBar(self)
        root_layout.addWidget(self.title_bar)

        # 1. Top Header Bar (Brand Sparkle + Center Search Bar + Window Controls)
        top_header = self._create_top_header()
        root_layout.addWidget(top_header)
        

        # 2. Main Body (Sidebar + Content Area)
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        sidebar = self._create_sidebar()
        body_layout.addWidget(sidebar)

        # Stacked Pages Content Area
        self.stacked_widget = QStackedWidget()
        self.library_page = LibraryPage()
        self.organizer_page = OrganizerPage()
        self.updates_page = UpdatesPage()
        self.storage_page = StoragePage()
        self.settings_page = SettingsPage()

        self.stacked_widget.addWidget(self.library_page)    # 0
        self.stacked_widget.addWidget(self.organizer_page)  # 1
        self.stacked_widget.addWidget(self.updates_page)    # 2
        self.stacked_widget.addWidget(self.storage_page)    # 3
        self.stacked_widget.addWidget(self.settings_page)   # 4

        content_column = QVBoxLayout()
        content_column.setContentsMargins(0, 0, 0, 0)
        content_column.setSpacing(0)
        content_column.addWidget(self.stacked_widget, 1)
        body_layout.addLayout(content_column, 1)
        root_layout.addLayout(body_layout, 1)

        # 3. Bottom Status Bar
        self.bottom_bar = self._create_bottom_bar()
        self.task_status_button = QPushButton()
        self.task_status_button.setObjectName("task_banner")
        self.task_status_button.setAccessibleName("View background task")
        self.task_status_button.clicked.connect(self._view_active_task)
        self.task_status_button.hide()
        root_layout.addWidget(self.task_status_button)
        root_layout.addWidget(self.bottom_bar)
        for scope in (self.title_bar, top_header, sidebar, self.bottom_bar, self.task_status_button, self.library_page, self.organizer_page, self.updates_page, self.storage_page, self.settings_page):
            scope.setProperty("animevaultThemeScope", True)
        self._task_timer = QTimer(self)
        self._task_timer.setInterval(500)
        self._task_timer.timeout.connect(self._update_task_status)
        self._task_timer.start()

    def _create_top_header(self) -> QWidget:
        header = QFrame()
        header.setFixedHeight(76)
        header.setObjectName("top_bar")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(28, 0, 28, 0)
        layout.setSpacing(16)

        # Center: Universal Search Input with Ctrl+K shortcut
        search_container = QFrame()
        search_container.setMinimumWidth(280)
        search_container.setMaximumWidth(640)
        search_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        search_container.setFixedHeight(44)
        search_container.setObjectName("shell_search")
        s_layout = QHBoxLayout(search_container)
        s_layout.setContentsMargins(10, 0, 10, 0)
        s_layout.setSpacing(8)

        s_icon = QLabel()
        self.search_icon = s_icon
        s_icon.setStyleSheet("color: #898d9f; font-size: 12px; background: transparent; border: none;")
        s_layout.addWidget(s_icon)

        self.top_search_input = QLineEdit()
        self.top_search_input.setPlaceholderText("Search by English title")
        self.top_search_input.setStyleSheet("background: transparent; border: none; color: #f3f4f6; font-size: 12px; padding: 0;")
        self.top_search_input.textChanged.connect(self._on_search_text_changed)
        s_layout.addWidget(self.top_search_input, 1)

        self.clear_search_button = QPushButton("\u00d7")
        self.clear_search_button.setObjectName("clear_search")
        self.clear_search_button.setFixedSize(32, 32)
        self.clear_search_button.setCursor(Qt.PointingHandCursor)
        self.clear_search_button.setAccessibleName("Clear search")
        self.clear_search_button.setToolTip("Clear search")
        self.clear_search_button.clicked.connect(self.top_search_input.clear)
        self.clear_search_button.setVisible(bool(self.top_search_input.text()))
        self.top_search_input.textChanged.connect(
            lambda text: self.clear_search_button.setVisible(bool(text))
        )
        s_layout.addWidget(self.clear_search_button)
        # Equal side regions keep the search centered even with actions on the right.
        left_space = QWidget()
        left_space.setMinimumWidth(238)
        left_brand_layout = QHBoxLayout(left_space)
        left_brand_layout.setContentsMargins(0, 0, 0, 0)
        # Brand Badge: Japanese "ア" in squircle + AnimeVault
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        brand_row.setContentsMargins(0, 0, 0, 0)

        badge = QLabel("\u30a2")
        badge.setFixedSize(36, 36)
        badge.setAlignment(Qt.AlignCenter)
        badge.setObjectName("brand_mark")
        brand_row.addWidget(badge)

        brand_title = QLabel("Anime Vault")
        brand_title.setObjectName("brand_title")
        brand_row.addWidget(brand_title)
        brand_row.addStretch()
        left_brand_layout.addLayout(brand_row)

        layout.addWidget(left_space, 1)
        layout.addWidget(search_container, 3)

        # Global Ctrl+K Shortcut
        shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        shortcut.activated.connect(self.top_search_input.setFocus)

        # Right Actions: Refresh + Add Anime
        right_actions = QHBoxLayout()
        right_actions.setSpacing(10)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName('toolbar_refresh')
        self.refresh_button = refresh_btn
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setFixedHeight(44)
        refresh_btn.setMinimumWidth(148)
        refresh_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        refresh_menu = QMenu(refresh_btn)
        local = refresh_menu.addAction("Refresh and sync local files")
        local.setToolTip("Scan your library folders without contacting metadata APIs")
        local.triggered.connect(lambda: self._request_refresh(internet=False))
        online = refresh_menu.addAction("Refresh and sync with internet")
        online.setToolTip("Scan folders, match titles and fetch AniList updates")
        online.triggered.connect(lambda: self._request_refresh(internet=True))
        refresh_menu.setToolTipsVisible(True)
        refresh_btn.setMenu(refresh_menu)
        refresh_btn.setToolTip("Choose local-only refresh or internet sync. F5 uses local-only refresh.")
        right_actions.addWidget(refresh_btn)

        add_btn = QPushButton("Add anime")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setFixedSize(120, 44)
        add_btn.setProperty("accent", True)
        add_btn.clicked.connect(self._open_custom_entry_dialog)
        right_actions.addWidget(add_btn)

        right_space = QWidget()
        right_space.setMinimumWidth(238)
        right_layout = QHBoxLayout(right_space)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addStretch()
        right_layout.addLayout(right_actions)
        layout.addWidget(right_space, 1)
        return header

    def _create_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(248)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(6)

        # Navigation Buttons (Library, Updates, Organizer, Storage, Settings)
        self.nav_buttons = []
        nav_items = [("Library", 0), ("Updates", 2), ("Organizer", 1), ("Storage", 3), ("Settings", 4)]
        for text, index in nav_items:
            btn_frame = ClickableFrame()
            btn_frame.setCursor(Qt.PointingHandCursor)
            btn_frame.setFixedHeight(44)
            btn_frame.setObjectName("shell_nav")
            btn_frame.setAccessibleName(text)
            f_layout = QHBoxLayout(btn_frame)
            f_layout.setContentsMargins(12, 0, 12, 0)
            f_layout.setSpacing(12)
            nav_icon = QLabel()
            nav_icon.setFixedSize(22, 22)
            f_layout.addWidget(nav_icon)

            lbl = QLabel(text)
            lbl.setObjectName("nav_text")
            f_layout.addWidget(lbl, 1)

            if index == 2:
                badge_lbl = QLabel("0")
                badge_lbl.setObjectName(f"nav_badge_{index}")
                badge_lbl.setFixedHeight(24)
                badge_lbl.setMinimumWidth(28)
                badge_lbl.setAlignment(Qt.AlignCenter)
                f_layout.addWidget(badge_lbl, 0, Qt.AlignVCenter)

            btn_frame.clicked.connect(lambda idx=index: self._on_nav_clicked(idx))
            layout.addWidget(btn_frame)
            self.nav_buttons.append((btn_frame, nav_icon, text.lower(), index))

        self._update_nav_selection(0)

        layout.addSpacing(18)

        # COLLECTIONS Section Header
        col_header = QLabel("COLLECTIONS")
        col_header.setObjectName("shell_caption")
        layout.addWidget(col_header)

        # Collections list matching mockup: Watching, Plan to watch, Dropped, Watched, removed
        self.coll_counts = {}
        collections = [
            ("Watching", "WATCHING"),
            ("Plan to watch", "PLAN_TO_WATCH"),
            ("Dropped", "DROPPED"),
            ("Watched, removed", "WATCHED_REMOVED"),
        ]

        for name, key in collections:
            row = ClickableFrame()
            row.setCursor(Qt.PointingHandCursor)
            row.setFixedHeight(44)
            row.setObjectName("collection_row")
            row.setAccessibleName(name)
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(12, 0, 12, 0)
            r_layout.setSpacing(8)

            t_lbl = QLabel(name)
            t_lbl.setObjectName("shell_muted")
            r_layout.addWidget(t_lbl, 1)

            c_lbl = QLabel("0")
            c_lbl.setObjectName("shell_muted")
            self.coll_counts[key] = c_lbl
            r_layout.addWidget(c_lbl)

            row.clicked.connect(lambda status=key: self._on_collection_clicked(status))
            layout.addWidget(row)

        layout.addStretch()

        # Bottom Pinned Storage Info Card in Sidebar (Matching Library.png Mockup)
        drive_card = QFrame()
        drive_card.setObjectName("sidebar_drive_card")
        d_layout = QVBoxLayout(drive_card)
        d_layout.setSpacing(6)
        d_layout.setContentsMargins(16, 16, 16, 16)

        # Large Free Space Header
        self.sidebar_free_title = QLabel("Checking storage…")
        self.sidebar_free_title.setObjectName("drive_free")
        d_layout.addWidget(self.sidebar_free_title)

        # Progress bar
        self.sidebar_drive_bar = QProgressBar()
        self.sidebar_drive_bar.setFixedHeight(8)
        self.sidebar_drive_bar.setTextVisible(False)
        self.sidebar_drive_bar.setObjectName("sidebar_drive_bar")
        d_layout.addWidget(self.sidebar_drive_bar)

        # Subtitle metrics
        self.sidebar_drive_lbl = QLabel("Checking library drive…")
        self.sidebar_drive_lbl.setObjectName("shell_muted")
        self.sidebar_drive_lbl.setWordWrap(True)
        d_layout.addWidget(self.sidebar_drive_lbl)

        # "Review storage" clickable link
        review_storage_lbl = ClickableLabel("Review storage")
        review_storage_lbl.setCursor(Qt.PointingHandCursor)
        review_storage_lbl.setObjectName("storage_link")
        review_storage_lbl.clicked.connect(lambda: self._on_nav_clicked(3))
        d_layout.addWidget(review_storage_lbl)

        layout.addWidget(drive_card)
        return sidebar

    def _create_bottom_bar(self) -> QWidget:
        bar = QFrame()
        bar.setFixedHeight(34)
        bar.setObjectName("status_bar")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(16)

        # Left: Streaming API running · 127.0.0.1:8765
        endpoint = server.api_base_url()
        self.api_status_label = ClickableLabel(f"Streaming API running \u00b7 {endpoint}" if endpoint else "Streaming API unavailable")
        dot = QLabel()
        dot.setObjectName("api_dot")
        dot.setProperty("available", bool(endpoint))
        dot.setFixedSize(8, 8)
        layout.addWidget(dot)
        self.api_status_label.setObjectName("shell_muted")
        self.api_status_label.setCursor(Qt.PointingHandCursor)
        self.api_status_label.setToolTip("Click to open local API in web browser")
        self.api_status_label.clicked.connect(self._open_api_url)
        layout.addWidget(self.api_status_label)

        # Center: Last scan info
        self.scan_stats_label = QLabel("Last scan just now · 0 anime indexed")
        self.scan_stats_label.setObjectName("shell_muted")
        layout.addWidget(self.scan_stats_label, 1)

        # Right: Online/Offline Badge
        self.status_pill = ClickableLabel("Online · AniList & Jikan")
        self.status_pill.setStyleSheet("""
            background-color: rgba(34, 197, 94, 0.15);
            color: #22c55e;
            border-radius: 10px;
            padding: 2px 10px;
            font-size: 11px;
            font-weight: 600;
        """)
        self.status_pill.setCursor(Qt.PointingHandCursor)
        self.status_pill.setToolTip("Click to recheck internet connection")
        self.status_pill.clicked.connect(self._initial_online_check)
        layout.addWidget(self.status_pill)

        # Total free drive text
        self.bottom_free_label = QLabel("Checking storage…")
        self.bottom_free_label.setObjectName("shell_muted")
        layout.addWidget(self.bottom_free_label)

        return bar

    # -----------------------------------------------------------------------
    # System Tray
    # -----------------------------------------------------------------------
    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon = self._generate_app_icon()
        self.setWindowIcon(icon)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Anime Vault")

        tray_menu = QMenu()
        restore_action = QAction("Open Anime Vault", self)
        restore_action.triggered.connect(self._restore_from_tray)
        tray_menu.addAction(restore_action)

        open_library_action = QAction("View Library", self)
        open_library_action.triggered.connect(lambda: (self._restore_from_tray(), self._on_nav_clicked(0)))
        tray_menu.addAction(open_library_action)

        open_storage_action = QAction("Storage Manager", self)
        open_storage_action.triggered.connect(lambda: (self._restore_from_tray(), self._on_nav_clicked(3)))
        tray_menu.addAction(open_storage_action)

        tray_menu.addSeparator()

        open_api_action = QAction("Open Local API in Browser", self)
        open_api_action.triggered.connect(self._open_api_url)
        tray_menu.addAction(open_api_action)

        tray_menu.addSeparator()

        exit_action = QAction("Exit Completely", self)
        exit_action.triggered.connect(self._force_exit)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _generate_app_icon(self) -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setBrush(QColor("#15161d"))
        painter.setPen(QPen(QColor("#df2545"), 3))
        painter.drawRoundedRect(4, 4, 56, 56, 14, 14)

        painter.setPen(QColor("#df2545"))
        font = QFont("Segoe UI", 28, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(0, 0, 64, 64), Qt.AlignCenter, "✦")
        painter.end()
        return QIcon(pixmap)

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.isVisible():
                self.hide()
            else:
                self._restore_from_tray()

    def _restore_from_tray(self):
        self.showNormal()
        self.activateWindow()

    # -----------------------------------------------------------------------
    # Navigation & Signals
    # -----------------------------------------------------------------------
    def _on_nav_clicked(self, index: int):
        self._update_nav_selection(index)
        self.stacked_widget.setCurrentIndex(index)

        # Pages retain their rendered data. Refresh through data-change signals
        # or the explicit Refresh action, never by doing HDD I/O on a tab click.

    def _update_nav_selection(self, active_index: int):
        self._active_nav_index = active_index
        palette = COLORS.get(QApplication.instance().property("animevaultTheme"), COLORS["dark"])
        self.search_icon.setPixmap(icon("search", palette["text_muted"]).pixmap(22, 22))
        for frame, label, name, index in self.nav_buttons:
            active = index == active_index
            frame.setProperty("active", active)
            for widget in (frame, *frame.findChildren(QLabel)):
                widget.style().unpolish(widget)
                widget.style().polish(widget)
            label.setPixmap(icon(name, palette["red_text"] if active else palette["text_secondary"]).pixmap(22, 22))

    def _on_collection_clicked(self, watch_status: str):
        self._on_nav_clicked(0)  # Go to library
        # Filter library page
        self.library_page._current_filter = watch_status
        self.library_page.activate_filter(watch_status)

    def _on_search_text_changed(self, text: str):
        # Forward search to library page
        if self.stacked_widget.currentIndex() != 0:
            self._on_nav_clicked(0)
        self.library_page.set_search_query(text)

    def _connect_signals(self):
        self.library_page.card_clicked.connect(self._open_detail_modal)
        self.library_page.airing_clicked.connect(self._open_airing_detail)
        self.library_page.add_custom_clicked.connect(self._open_custom_entry_dialog)
        self.library_page.data_changed.connect(self._on_data_updated)
        self.organizer_page.data_changed.connect(self._on_data_updated)
        self.updates_page.refresh_requested.connect(lambda: self._start_refresh(allow_network=True, sync_internet=True))
        self.updates_page.card_clicked.connect(self._open_detail_modal)
        self.updates_page.data_changed.connect(self._on_data_updated)
        self.settings_page.theme_changed.connect(self._on_theme_changed)
        self.settings_page.scan_completed.connect(self._on_data_updated)
        self.settings_page.preferences_changed.connect(self._apply_settings_preferences)
        self.storage_page.data_changed.connect(self._on_data_updated)
        self.storage_page.filter_requested.connect(self._on_storage_filter_requested)
        self.storage_page.anime_clicked.connect(self._open_detail_modal)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self.top_search_input.setFocus)
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self._request_refresh)
        QShortcut(QKeySequence("F5"), self).activated.connect(self._request_refresh)
        QShortcut(QKeySequence("Ctrl+I"), self).activated.connect(self._open_watched_import_dialog)
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(lambda: self._on_nav_clicked(1))

    def _on_storage_filter_requested(self, filter_name: str):
        self._on_nav_clicked(0)
        self.library_page.activate_filter(filter_name)

    def _open_watched_import_dialog(self):
        dlg = WatchedImportDialog(parent=self)
        dlg.import_completed.connect(self._on_data_updated)
        navigate(dlg)


    def _open_airing_detail(self, release):
        modal = DetailModal(release["fid"], parent=self)
        modal.data_changed.connect(self._on_data_updated)
        navigate(modal)
        modal.check_release_episode(release)

    def _open_detail_modal(self, franchise_id: int):
        modal = DetailModal(franchise_id, parent=self)
        modal.data_changed.connect(self._on_data_updated)
        navigate(modal)

    def _open_custom_entry_dialog(self):
        dialog = CustomEntryDialog(parent=self)
        dialog.entry_saved.connect(lambda fid: self._on_data_updated())
        navigate(dialog)

    def _on_theme_changed(self, theme: str):
        apply_theme(QApplication.instance(), theme)
        self._update_nav_selection(self._active_nav_index)

    def _apply_settings_preferences(self):
        from app import preferences as prefs
        if hasattr(self, "_scan_schedule_timer"):
            self._scan_schedule_timer.stop()
            interval = {"hourly": 3600000, "daily": 86400000}.get(db.get_state("scan_schedule", "startup"))
            if interval:
                self._scan_schedule_timer.start(interval)
        compact = prefs.enabled("compact_library")
        if (self.library_page.view_mode == "compact") != compact:
            self.library_page._set_view_mode("compact" if compact else "grid")
        auto_metadata = prefs.enabled("metadata_auto")
        previous = getattr(self, "_auto_metadata_enabled", auto_metadata)
        self._auto_metadata_enabled = auto_metadata
        if not auto_metadata and self._updater_thread and self._updater_thread.isRunning():
            self._updater_thread.cancel()
        elif auto_metadata and not previous:
            self._start_background_updater()
        self.organizer_page.apply_settings_preferences()

    def _check_new_anime(self):
        self._start_refresh(scan_library=True, new_only=True)

    def _recover_file_operations(self):
        from contextlib import closing
        with closing(db.get_connection()) as conn:
            pending = conn.execute("SELECT 1 FROM file_operations WHERE status<>'COMPLETED' LIMIT 1").fetchone()
        if pending:
            self._start_refresh(allow_network=False)

    def _request_refresh(self, internet=False):
        if not getattr(self, "_refresh_busy", False):
            self._start_refresh(scan_library=True, allow_network=internet, sync_internet=internet)

    def _refresh_dirty_page(self, index):
        page = self.stacked_widget.widget(index)
        if page in getattr(self, "_dirty_pages", set()):
            self._start_refresh(allow_network=False)

    def _on_data_updated(self):
        self._dirty_pages.update((self.library_page, self.storage_page, self.updates_page))
        self._start_refresh()

    def _start_refresh(self, scan_library=False, new_only=False, allow_network=True, sync_internet=False):
        if getattr(self, "_shutdown_pending", False):
            return
        if getattr(self, "_refresh_busy", False):
            self._refresh_pending = True
            return
        from app.ui.refresh import RefreshWorker
        self._refresh_busy = True
        self._refresh_invalidates_others = bool(scan_library or sync_internet)
        self._refresh_pending = False
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Checking…" if new_only else "Refreshing…")
        self._refresh_worker = RefreshWorker(self, scan_library=scan_library, new_only=new_only, allow_network=allow_network, sync_internet=sync_internet)
        self._refresh_worker.progress.connect(self._show_scan_progress)
        self._refresh_worker.ready.connect(self._apply_refresh_snapshot)
        self._refresh_worker.failed.connect(self._refresh_failed)
        self._refresh_worker.unchanged.connect(self._finish_refresh)
        self._refresh_worker.start()

    def _show_scan_progress(self, message, current, total):
        if not getattr(self, "_shutdown_pending", False):
            self.scan_stats_label.setText(f"{message} ({current}/{total})")

    def _apply_refresh_snapshot(self, snapshot):
        if getattr(self, "_shutdown_pending", False):
            snapshot["connection"].close()
            return
        self._refresh_snapshot = snapshot
        if snapshot.get("scan_errors"):
            self.refresh_button.setToolTip("\n".join(snapshot["scan_errors"][:10]))
            self.scan_stats_label.setText(f"Review needed: {len(snapshot['scan_errors'])} scan/file-operation issues — open Organizer")
        else:
            self.refresh_button.setToolTip("")
        pages = [self.library_page, self.storage_page, self.updates_page]
        current = self.stacked_widget.currentWidget()
        if self._refresh_invalidates_others:
            self._dirty_pages.update(page for page in pages if page is not current)
        if current in pages:
            self._dirty_pages.discard(current)
        self._refresh_steps = ([current.refresh] if current in pages else []) + [self._refresh_metrics]
        self._apply_refresh_step()

    def _apply_refresh_step(self):
        if getattr(self, "_shutdown_pending", False):
            self._finish_refresh()
            return
        try:
            if not self._refresh_steps:
                self._finish_refresh()
                return
            step = self._refresh_steps.pop(0)
            with db.refresh_view(self._refresh_snapshot):
                step()
            QTimer.singleShot(0, self._apply_refresh_step)
        except Exception as error:
            self._refresh_failed(str(error))

    def _finish_refresh(self):
        snapshot = getattr(self, "_refresh_snapshot", None)
        if snapshot is not None:
            snapshot["connection"].close()
            self._refresh_snapshot = None
        self._refresh_busy = False
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh")
        if getattr(self, "_refresh_pending", False) and not getattr(self, "_shutdown_pending", False):
            QTimer.singleShot(0, self._on_data_updated)

    def _refresh_failed(self, message):
        self._refresh_pending = False
        self._finish_refresh()
        self.refresh_button.setToolTip("Refresh failed: " + message)
        self.scan_stats_label.setText("Refresh failed — " + message)

    def _refresh_metrics(self):
        stats = db.get_library_stats()
        total_anime = len(db.get_series_library())
        total_bytes = stats.get("total_bytes", 0)

        # Update collections counts
        all_franchises = db.get_all_franchises()
        watching_cnt = sum(1 for f in all_franchises if f.get("watch_status") == "WATCHING")
        watched_cnt = sum(1 for f in all_franchises if f.get("watch_status") == "WATCHED")
        plan_cnt = sum(1 for f in all_franchises if f.get("watch_status") == "PLAN_TO_WATCH")
        dropped_cnt = sum(1 for f in all_franchises if f.get("watch_status") == "DROPPED")

        if "WATCHING" in self.coll_counts:
            self.coll_counts["WATCHING"].setText(str(watching_cnt))
        if "WATCHED" in self.coll_counts:
            self.coll_counts["WATCHED"].setText(str(watched_cnt))
        if "PLAN_TO_WATCH" in self.coll_counts:
            self.coll_counts["PLAN_TO_WATCH"].setText(str(plan_cnt))
        if "DROPPED" in self.coll_counts:
            self.coll_counts["DROPPED"].setText(str(dropped_cnt))

        if "WATCHED_REMOVED" in self.coll_counts:
            self.coll_counts["WATCHED_REMOVED"].setText(str(stats.get("watched_removed", 0)))
        self._unread_updates = sum(bool(f.get("has_new_update")) for f in all_franchises)
        badge = self.findChild(QLabel, "nav_badge_2")
        if badge:
            badge.setText(str(self._unread_updates))
            badge.setVisible(self._unread_updates > 0)

        disk = disk_snapshot()
        if disk["total"]:
            self.sidebar_free_title.setText(f"{format_bytes(disk['free'])} free")
            self.sidebar_drive_lbl.setText(f"{format_bytes(disk['used'])} of {format_bytes(disk['total'])} used")
            self.sidebar_drive_bar.setValue(round(100 * disk["used"] / disk["total"]))
            self.bottom_free_label.setText(f"{format_bytes(disk['free'])} free · {disk['label']}")
        else:
            self.sidebar_free_title.setText("Storage unavailable")
            self.sidebar_drive_lbl.setText("Library drive is offline" if disk["configured"] else "Add a library folder in Settings")
            self.sidebar_drive_bar.setValue(0)
            self.bottom_free_label.setText("Drive capacity unavailable")
        self.sidebar_drive_lbl.setToolTip("Unavailable roots: " + ", ".join(disk["unavailable"]) if disk["unavailable"] else disk["label"])
        self.scan_stats_label.setText(f"Last scan just now · {total_anime} anime indexed")

    def _open_api_url(self):
        endpoint = server.api_base_url()
        if endpoint:
            webbrowser.open(f"{endpoint}/api/library")

    # -----------------------------------------------------------------------
    # Connectivity & Startup Checker
    # -----------------------------------------------------------------------
    def _initial_online_check(self):
        if getattr(self, "_shutdown_pending", False):
            return
        online = check_online()
        if online:
            self.status_pill.setText("Online · AniList & Jikan")
            self.status_pill.setStyleSheet("""
                background-color: rgba(34, 197, 94, 0.15);
                color: #22c55e;
                border-radius: 10px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 600;
            """)
            from app import preferences as prefs
            if prefs.enabled("metadata_auto"):
                self._start_background_updater()
        else:
            self.status_pill.setText("Offline Mode · using cached data")
            self.status_pill.setStyleSheet("""
                background-color: rgba(245, 158, 11, 0.15);
                color: #f59e0b;
                border-radius: 10px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 600;
            """)

        self._refresh_metrics()

    def _start_background_updater(self):
        if self._updater_thread and self._updater_thread.isRunning():
            return
        self._updater_thread = UpdaterThread(parent=self)
        self._updater_thread.update_found.connect(self._on_update_found)
        self._updater_thread.finished_signal.connect(self._on_updater_finished)
        self._updater_thread.start()

    def _on_update_found(self, franchise_id: int, details: str):
        # Counts come from persisted pending updates, rather than accumulating per scan.
        pass

    def _on_updater_finished(self, total_found: int):
        self._on_data_updated()

    # -----------------------------------------------------------------------
    # Window Geometry & Close Event
    # -----------------------------------------------------------------------
    def _restore_geometry(self):
        saved = get_window_geometry()
        if saved:
            try:
                parts = [int(p) for p in saved.split(",")]
                if len(parts) == 4:
                    self.setGeometry(parts[0], parts[1], parts[2], parts[3])
            except Exception:
                pass

    def _save_geometry(self):
        rect = self.geometry()
        geo_str = f"{rect.x()},{rect.y()},{rect.width()},{rect.height()}"
        set_window_geometry(geo_str)

    def _running_threads(self):
        from app.ui.io_task import running
        threads = running()
        workflows = [self, self.organizer_page, self.organizer_page.merge_page, self.updates_page] + [p.workflow for p in getattr(self, "_navigation_pages", [])]
        for workflow in workflows:
            for name in ("_batch_worker", "_organize_worker", "_apply_worker", "_search_worker", "_worker", "_refresh_worker", "_merge_worker", "_merge_plan_worker"):
                worker = getattr(workflow, name, None)
                if worker and worker.isRunning():
                    threads.append(worker)
        if self._updater_thread and self._updater_thread.isRunning():
            threads.append(self._updater_thread)
        return threads

    def _finish_pending_exit(self):
        from app.ui.artwork import artwork_loader
        if self._running_threads() or artwork_loader().pool.activeThreadCount():
            return
        self._shutdown_timer.stop()
        self._exit_ready = True
        server.stop_server()
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        QApplication.quit()

    def _active_task_page(self, protect_only=False):
        pages = [self.organizer_page] + ([self.updates_page] if hasattr(self, "updates_page") else []) + ([self.organizer_page.merge_page] if hasattr(self.organizer_page, "merge_page") else []) + list(getattr(self, "_navigation_pages", []))
        for page in pages:
            workflow = getattr(page, "workflow", page)
            names = ("_batch_worker", "_organize_worker", "_apply_worker", "_merge_worker") if protect_only else ("_batch_worker", "_organize_worker", "_apply_worker", "_search_worker", "_worker", "_merge_worker", "_merge_plan_worker")
            for name in names:
                worker = getattr(workflow, name, None)
                if worker and worker.isRunning():
                    return page
        return None

    def _update_task_status(self):
        active = self._active_task_page()
        self.task_status_button.setVisible(active is not None)
        if active is not None:
            self.task_status_button.setText("Task in progress — you can navigate. Keep the app open until it finishes. Click to view.")

    def _view_active_task(self):
        page = self._active_task_page()
        if page is not None:
            if page is self.organizer_page.merge_page:
                self.organizer_page.organizer_tabs.setCurrentWidget(page)
                self.stacked_widget.setCurrentWidget(self.organizer_page)
            else:
                self.stacked_widget.setCurrentWidget(page)

    def closeEvent(self, event):
        if getattr(self, "_shutdown_pending", False):
            event.ignore()
            return
        if self._active_task_page(protect_only=True) is not None:
            event.ignore()
            self._update_task_status()
            self.task_status_button.setText("Cannot close while a task is running. Navigate freely; wait for it to finish before exiting.")
            return
        pref = get_quit_preference()

        if pref == "tray":
            event.ignore()
            self.hide()
            return

        if pref == "exit":
            self._save_geometry()
            if self._cleanup_and_exit():
                event.accept()
            else:
                event.ignore()
            return

        dialog = QuitConfirmDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            if dialog.choice == "tray":
                event.ignore()
                self.hide()
            elif dialog.choice == "exit":
                self._save_geometry()
                if self._cleanup_and_exit():
                    event.accept()
                else:
                    event.ignore()
            else:
                event.ignore()
        else:
            event.ignore()

    def _force_exit(self):
        if getattr(self, "_shutdown_pending", False):
            return
        if self._active_task_page(protect_only=True) is not None:
            self.show()
            self._update_task_status()
            return
        self._save_geometry()
        if self._cleanup_and_exit():
            QApplication.quit()

    def _cleanup_and_exit(self):
        from app.ui.artwork import artwork_loader
        loader = artwork_loader()
        loader.pool.clear()
        threads = self._running_threads()
        if threads or loader.pool.activeThreadCount():
            self._shutdown_pending = True
            self._task_timer.stop()
            for worker in threads:
                worker.requestInterruption()
                if hasattr(worker, "cancel"):
                    worker.cancel()
            self.show()
            self.task_status_button.show()
            self.task_status_button.setText("Closing — stopping background tasks safely. Waiting for active requests to finish…")
            self._shutdown_timer = QTimer(self)
            self._shutdown_timer.setInterval(100)
            self._shutdown_timer.timeout.connect(self._finish_pending_exit)
            self._shutdown_timer.start()
            return False
        if hasattr(self, "tray_icon") and self.tray_icon:
            self.tray_icon.hide()
        server.stop_server()
        return True
