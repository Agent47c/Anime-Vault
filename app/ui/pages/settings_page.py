from app.ui.components.design import MotifHeader
from app.ui.navigation import navigate
"""
Settings Page — Folder paths, .txt importer, JSON/CSV export, media player, backups, and preferences.
"""

import os
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGroupBox, QGridLayout, QFormLayout, QComboBox,
    QCheckBox, QFileDialog, QListWidget, QListWidgetItem,
    QMessageBox, QProgressBar, QApplication, QLineEdit, QButtonGroup,
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal, QThread

from app import db
from app import preferences as prefs
from app.ui.components.settings_switch import SettingsSwitch
from app.config import (
    get_theme, set_theme, get_quit_preference, set_quit_preference,
    get_media_player_type, set_media_player_type,
    get_custom_player_path, set_custom_player_path,
    detect_installed_players,
)
from app.core.scanner import scan_watched_directories, import_txt_file
from app.core.exporter import export_json, export_csv
from app.ui.dialogs.watched_import_dialog import WatchedImportDialog


class ScanWorker(QThread):
    """Background scanner thread."""
    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def run(self):
        try:
            def on_progress(msg, current, total):
                self.progress.emit(msg, current, total)
            from app.core.scanner import ScanProgress
            result = scan_watched_directories(progress_callback=on_progress, scan_progress=ScanProgress(self.isInterruptionRequested))
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class SettingsPage(QWidget):
    """Settings and configuration page."""

    theme_changed = pyqtSignal(str)
    scan_completed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scan_worker = None
        self._setup_ui()

    preferences_changed = pyqtSignal()

    def _panel(self, title):
        panel = QFrame()
        panel.setObjectName("settings_panel")
        box = QVBoxLayout(panel)
        box.setContentsMargins(20, 20, 20, 20)
        box.setSpacing(0)
        heading = QLabel(title)
        heading.setObjectName("settings_panel_title")
        box.addWidget(heading)
        box.addSpacing(6)
        return panel, box

    def _row(self, box, title, hint="", control=None):
        widget = QWidget()
        widget.setObjectName("settings_row")
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 10, 0, 10)
        row.setSpacing(16)
        labels = QVBoxLayout()
        labels.setSpacing(2)
        label = QLabel(title)
        label.setObjectName("settings_label")
        label.setWordWrap(True)
        labels.addWidget(label)
        if hint:
            detail = QLabel(hint)
            detail.setObjectName("settings_hint")
            detail.setWordWrap(True)
            labels.addWidget(detail)
        row.addLayout(labels, 1)
        if control:
            row.addWidget(control, 0, Qt.AlignVCenter)
            control.setAccessibleName(title)
            control.setAccessibleDescription(hint)
        box.addWidget(widget)
        line = QFrame()
        line.setObjectName("settings_divider")
        line.setFixedHeight(1)
        box.addWidget(line)
        return widget

    def _toggle(self, box, title, hint, key):
        switch = SettingsSwitch(prefs.enabled(key))
        switch.toggled.connect(lambda value: self._save_preference(key, value))
        self._row(box, title, hint, switch)
        return switch

    def _save_preference(self, key, value):
        prefs.save(key, value)
        if key in ("reduce_motion", "high_contrast", "decorations"):
            self.theme_changed.emit(self.theme_combo.currentData())
        self.preferences_changed.emit()

    @staticmethod
    def _button(text, callback, primary=False):
        button = QPushButton(text)
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumHeight(36)
        button.setProperty("accent", primary)
        button.clicked.connect(callback)
        return button

    def _setup_ui(self):
        self.setObjectName("settings_page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content.setObjectName("settings_content")
        page = QVBoxLayout(content)
        page.setContentsMargins(32, 12, 32, 32)
        page.setSpacing(20)
        header = MotifHeader("\u8a2d\u5b9a")
        heading = QVBoxLayout(header)
        heading.setContentsMargins(0, 0, 0, 0)
        heading.setSpacing(4)
        title = QLabel("Settings")
        title.setObjectName("settings_heading")
        heading.addWidget(title)
        subtitle = QLabel("Appearance, metadata, media player, scanning and backups")
        subtitle.setObjectName("settings_subtitle")
        subtitle.setWordWrap(True)
        heading.addWidget(subtitle)
        page.addWidget(header)
        grid = QGridLayout()
        grid.setSpacing(20)
        left, right = QVBoxLayout(), QVBoxLayout()
        for column in (left, right):
            column.setSpacing(20)
        grid.addLayout(left, 0, 0)
        grid.addLayout(right, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        page.addLayout(grid)
        page.addStretch()

        panel, box = self._panel("Appearance and accessibility")
        self.theme_combo = QComboBox()
        for label, value in (("Match Windows", "system"), ("Dark", "dark"), ("Light", "light")):
            self.theme_combo.addItem(label, value)
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(get_theme())))
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self._row(box, "Theme", "Follow Windows or choose a fixed appearance", self.theme_combo)
        self._toggle(box, "Compact library", "Show the compact list instead of the poster grid", "compact_library")
        self._toggle(box, "Reduce motion", "Turn off hover and transition animations", "reduce_motion")
        size_row = QWidget()
        size_layout = QHBoxLayout(size_row)
        size_layout.setContentsMargins(4, 4, 4, 4)
        size_layout.setSpacing(4)
        size_row.setObjectName("settings_segments")
        self.size_buttons = QButtonGroup(self)
        for text, value in (("Default", "1.0"), ("Large", "1.15"), ("Extra large", "1.3")):
            button = QPushButton(text)
            button.setCheckable(True)
            button.setChecked(str(prefs.text_scale()) == value)
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(36)
            button.clicked.connect(lambda checked, val=value: self._set_text_size(val))
            size_layout.addWidget(button)
            self.size_buttons.addButton(button)
        self._row(box, "Text size", "Scale labels, buttons and tables", None)
        box.addWidget(size_row, 0, Qt.AlignLeft)
        self._toggle(box, "High contrast", "Stronger borders and text; also follows Windows", "high_contrast")
        self._toggle(box, "Decorative kanji and patterns", "Turn off for a calmer, plainer look", "decorations")
        left.addWidget(panel)

        panel, box = self._panel("Media player")
        self.player_combo = QComboBox()
        for label, value in (("Windows default", "default"), ("VLC", "vlc"), ("MPV", "mpv"), ("MPC-HC", "mpc-hc"), ("Custom executable", "custom")):
            self.player_combo.addItem(label, value)
        self.player_combo.setCurrentIndex(max(0, self.player_combo.findData(get_media_player_type())))
        self._row(box, "Default player", "Used by Resume and Play episode", self.player_combo)
        self.custom_path_edit = QLineEdit(get_custom_player_path() or "")
        self.custom_path_edit.setPlaceholderText("Player executable path")
        self.custom_path_edit.textChanged.connect(set_custom_player_path)
        path_control = QWidget()
        path_layout = QHBoxLayout(path_control)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.addWidget(self.custom_path_edit, 1)
        path_layout.addWidget(self._button("Browse...", self._browse_custom_player))
        self.custom_path_box = self._row(box, "Executable", "", path_control)
        self.custom_path_box.setVisible(get_media_player_type() == "custom")
        self.player_combo.currentIndexChanged.connect(self._on_player_changed)
        self._row(box, "Installed players", "Find VLC, MPV and MPC-HC", self._button("Detect players", self._auto_detect_players))
        self.player_status = QLabel("")
        self.player_status.setObjectName("settings_hint")
        self.player_status.setWordWrap(True)
        box.addWidget(self.player_status)
        left.addWidget(panel)

        panel, box = self._panel("Metadata and AniList")
        self._toggle(box, "Automatic metadata updates", "Check for new seasons and episodes", "metadata_auto")
        self._toggle(box, "Prefer official English titles", "Fall back to Romaji and Japanese; applies to new matches", "prefer_english")
        self._toggle(box, "Allow mature (18+) titles", "Include adult titles in search results", "allow_mature")
        self._toggle(box, "Rematch low-confidence titles", "Allow automatic exact-title checks for entries needing review", "rematch_low_confidence")
        left.addWidget(panel)

        panel, box = self._panel("Application behavior")
        self.quit_combo = QComboBox()
        for label, value in (("Always ask", ""), ("Minimize to tray", "tray"), ("Exit completely", "exit")):
            self.quit_combo.addItem(label, value)
        self.quit_combo.setCurrentIndex(max(0, self.quit_combo.findData(get_quit_preference() or "")))
        self.quit_combo.currentIndexChanged.connect(self._on_quit_pref_changed)
        self._row(box, "Close button", "Choose what happens when the window closes", self.quit_combo)
        from app.config import get_always_admin, set_always_admin
        self.always_admin_cb = SettingsSwitch(get_always_admin())
        self.always_admin_cb.toggled.connect(set_always_admin)
        self._row(box, "Always run as administrator", "Applies on next launch. Windows approval is still required.", self.always_admin_cb)
        left.addWidget(panel)
        panel, box = self._panel("About")
        self._row(box, "Anime Vault", "Anime Library & Storage Manager v1.0.0")
        left.addWidget(panel)
        left.addStretch()

        panel, box = self._panel("Scanning and organization")
        self._toggle(box, "Flat folder detection", "Treat direct root video files as Season 1", "flat_detection")
        self._toggle(box, "Preview file movements", "Require confirmation before organizing", "preview_moves")
        self.schedule_combo = QComboBox()
        for label, value in (("Manual only", "manual"), ("On startup", "startup"), ("Every hour", "hourly"), ("Every day", "daily")):
            self.schedule_combo.addItem(label, value)
        self.schedule_combo.setCurrentIndex(max(0, self.schedule_combo.findData(db.get_state("scan_schedule", "startup"))))
        self.schedule_combo.currentIndexChanged.connect(self._set_schedule)
        self._row(box, "Scheduled scan", "Check folders for newly added anime", self.schedule_combo)
        right.addWidget(panel)

        panel, box = self._panel("Watched list import")
        self._toggle(box, "Auto-select high-confidence matches", "Select matches at 90% or higher; Apply still confirms the import", "import_auto")
        self._toggle(box, "Review ambiguous matches", "Leave uncertain matches unchecked for your review", "import_review")
        self._toggle(box, "Ignore duplicate entries", "Skip repeated titles and entries already in the library", "import_ignore_duplicates")
        self._row(box, "Import watched list", "Review anime titles from a text file", self._button("Open importer (Ctrl+I)", self._open_watched_importer))
        right.addWidget(panel)

        panel, box = self._panel("Database and backup")
        self._row(box, "Database", "library.db - SQLite (WAL)")
        self._row(box, "Backup", "Save a copy of the library before making changes", self._button("Create backup", self._backup_db))
        self._row(box, "Restore", "Restore a saved library; a safety copy is kept", self._button("Restore backup", self._restore_db))
        exports = QWidget()
        buttons = QHBoxLayout(exports)
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.addWidget(self._button("JSON", self._export_json))
        buttons.addWidget(self._button("CSV", self._export_csv))
        self._row(box, "Export", "Full library for safe keeping", exports)
        self.backup_status = QLabel("")
        self.backup_status.setObjectName("settings_hint")
        self.backup_status.setWordWrap(True)
        box.addWidget(self.backup_status)
        right.addWidget(panel)

        panel, box = self._panel("Downloads")
        self._row(box, "qBittorrent and search source", "Configure the local client, search URL and completed-download indexing.")
        from app.ui.downloads import open_downloads
        box.addWidget(self._button("Configure downloads",lambda:open_downloads(self)))
        right.addWidget(panel)

        panel, box = self._panel("Library roots and scanning")
        detail = QLabel("Folders used to discover and index your anime.")
        detail.setObjectName("settings_hint")
        box.addWidget(detail)
        box.addSpacing(12)
        self.dirs_list = QListWidget()
        self.dirs_list.setMinimumHeight(110)
        self.dirs_list.setMaximumHeight(160)
        box.addWidget(self.dirs_list)
        box.addSpacing(12)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self._button("+ Add folder", self._add_directory))
        buttons.addWidget(self._button("Remove selected", self._remove_directory))
        buttons.addStretch()
        box.addLayout(buttons)
        box.addSpacing(12)
        box.addWidget(self._button("Scan all directories", self._scan_directories, True), 0, Qt.AlignLeft)
        self.scan_progress = QProgressBar()
        self.scan_progress.hide()
        box.addWidget(self.scan_progress)
        self.scan_status = QLabel("")
        self.scan_status.setObjectName("settings_hint")
        self.scan_status.setWordWrap(True)
        box.addWidget(self.scan_status)
        right.addWidget(panel)
        right.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self._refresh_dirs_list()

    def _set_text_size(self, value):
        db.set_state("text_scale", value)
        self.theme_changed.emit(self.theme_combo.currentData())

    def _set_schedule(self):
        db.set_state("scan_schedule", self.schedule_combo.currentData())
        self.preferences_changed.emit()

    def _refresh_dirs_list(self):
        self.dirs_list.clear()
        dirs = db.get_watched_directories()
        for d in dirs:
            state = d.get('availability','UNSCANNED')
            suffix = ' · ' + state.title() if state in ('OFFLINE','INACCESSIBLE') else ''
            item = QListWidgetItem(d["folder_path"] + suffix)
            item.setToolTip(d.get('scan_error') or d['folder_path'])
            item.setData(Qt.UserRole, d["id"])
            self.dirs_list.addItem(item)

    def _add_directory(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Anime Root Folder")
        if folder:
            db.add_watched_directory(folder)
            self._refresh_dirs_list()

    def _remove_directory(self):
        item = self.dirs_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select", "Please select a directory to remove.")
            return
        dir_id = item.data(Qt.UserRole)
        db.remove_watched_directory(dir_id)
        self._refresh_dirs_list()

    def _scan_directories(self):
        self.scan_progress.setVisible(True)
        self.scan_progress.setRange(0, 0)
        self.scan_status.setText("Scanning directories...")

        self._scan_worker = ScanWorker()
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.start()

    def _on_scan_progress(self, msg: str, current: int, total: int):
        if total > 0:
            self.scan_progress.setRange(0, total)
            self.scan_progress.setValue(current)
        self.scan_status.setText(msg)

    def _on_scan_finished(self, result: dict):
        self.scan_progress.setVisible(False)
        self.scan_status.setText(
            f"✅ Scan complete! "
            f"Scanned: {result.get('scanned', 0)} • "
            f"New: {result.get('new', 0)} • "
            f"Updated: {result.get('updated', 0)}"
        )
        errors = result.get("errors", [])
        if errors:
            self.scan_status.setText(
                self.scan_status.text() + f" • ⚠️ {len(errors)} errors"
            )
        self.scan_completed.emit()

    def _on_scan_error(self, error: str):
        self.scan_progress.setVisible(False)
        self.scan_status.setText(f"❌ Error: {error}")

    def _on_player_changed(self):
        val = self.player_combo.currentData()
        set_media_player_type(val)
        self.custom_path_box.setVisible(val == "custom")

    def _browse_custom_player(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Media Player Executable", "", "Executables (*.exe);;All Files (*.*)"
        )
        if path:
            self.custom_path_edit.setText(path)
            set_custom_player_path(path)

    def _auto_detect_players(self):
        found = detect_installed_players()
        if found:
            details = ", ".join(f"{k.upper()}: {v}" for k, v in found.items())
            self.player_status.setText(f"✅ Detected: {list(found.keys())}")
            QMessageBox.information(self, "Players Detected", f"Found media players:\n\n{details}")
        else:
            self.player_status.setText("No external players found in standard paths.")
            QMessageBox.information(
                self, "Not Found",
                "No VLC, MPV, or MPC-HC installations were found in standard directories. "
                "You can specify a custom executable path."
            )

    def _open_watched_importer(self):
        dlg = WatchedImportDialog(parent=self)
        dlg.import_completed.connect(self.scan_completed.emit)
        navigate(dlg)

    def _backup_db(self):
        try:
            backup_path = db.backup_database()
            self.backup_status.setText(f"✅ Backup created: {Path(backup_path).name}")
            QMessageBox.information(
                self, "Backup Successful",
                f"SQLite database backup successfully saved to:\n\n{backup_path}"
            )
        except Exception as e:
            self.backup_status.setText(f"❌ Backup failed: {str(e)}")

    def _restore_db(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Database Backup to Restore", "", "SQLite Databases (*.db);;All Files (*.*)"
        )
        if not path:
            return

        confirm = QMessageBox.question(
            self, "Confirm Restore",
            "Restoring a database will replace your current library.\n"
            "An automatic safety copy of your current database will be preserved.\n\n"
            "Do you wish to proceed?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            try:
                db.restore_database(path)
                self.backup_status.setText(f"✅ Database restored from: {Path(path).name}")
                QMessageBox.information(self, "Restore Complete", "Database restored successfully.")
                self.scan_completed.emit()
            except Exception as e:
                self.backup_status.setText(f"❌ Restore failed: {str(e)}")
                QMessageBox.warning(self, "Restore Failed", f"Failed to restore database:\n{str(e)}")

    def _export_json(self):
        try:
            filepath = export_json()
            self.backup_status.setText(f"✅ Exported to: {filepath}")
        except Exception as e:
            self.backup_status.setText(f"❌ Error: {str(e)}")

    def _export_csv(self):
        try:
            filepath = export_csv()
            self.backup_status.setText(f"✅ Exported to: {filepath}")
        except Exception as e:
            self.backup_status.setText(f"❌ Error: {str(e)}")

    def _on_theme_changed(self):
        theme = self.theme_combo.currentData()
        set_theme(theme)
        self.theme_changed.emit(theme)

    def _on_quit_pref_changed(self):
        pref = self.quit_combo.currentData()
        set_quit_preference(pref)
