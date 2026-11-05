from collections import defaultdict
from contextlib import closing
from app.core.library_health import episode_inventory, season_health
from app.ui.components.design import MotifHeader
from app.ui.refresh import refresh_pixmap, refresh_image_exists, artwork_version
"""
Updates Page — New season & airing sequel alerts.
Shows anime that have new sequels, movies, or currently airing seasons.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QDialog, QComboBox, QButtonGroup, QMessageBox,
)
from PyQt5.QtGui import QFont, QPixmap, QColor
from PyQt5.QtCore import Qt, pyqtSignal, QThread

from app import db
from app.ui.navigation import navigate
from app.config import COVERS_DIR, cached_online


class UpdateActionWorker(QThread):
    """Keep HDD commits and checkpoints outside the GUI event loop."""
    def __init__(self, fid, action, parent=None):
        super().__init__(parent)
        self.fid, self.action, self.error = fid, action, None

    @staticmethod
    def perform(fid, action):
        if action == "watched":
            db.mark_watched_and_ignore_updates(fid)
        elif action == "dismiss":
            db.dismiss_updates(fid)
        else:
            db.set_update_disposition(fid, action)

    def run(self):
        try:
            self.perform(self.fid, self.action)
        except Exception as error:
            self.error = str(error)


class UpdateCard(QFrame):
    """A card showing an anime with an available update."""

    clicked = pyqtSignal(int)  # franchise_id
    dismissed = pyqtSignal()
    action_requested = pyqtSignal(int, str)

    def __init__(self, franchise: dict, parent=None, async_actions=False):
        super().__init__(parent)
        self.async_actions = async_actions
        self.franchise_id = franchise["id"]
        self.disposition = franchise.get("_update_disposition", "new")
        self.setObjectName("update_card")
        self.setProperty("singleLineActions", True)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame#update_card {
                background-color: #15161d;
                border: 1px solid #303139;
                border-radius: 12px;
                padding: 4px;
            }
            QFrame#update_card:hover {
                border-color: #b0b3c2;
                background-color: #1d1f29;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(12)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        outer.addLayout(layout)

        # Mini poster
        poster = QLabel()
        poster.setFixedSize(50, 70)
        poster.setAlignment(Qt.AlignCenter)
        poster.setStyleSheet("border-radius: 6px; background-color: #0d1117;")
        cover = franchise.get("cover_filename")
        if cover:
            cover_path = COVERS_DIR / cover
            if refresh_image_exists(cover_path):
                pixmap = refresh_pixmap(cover_path).scaled(
                    50, 70, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
                poster.setPixmap(pixmap)
        layout.addWidget(poster)

        # Info
        info = QVBoxLayout()
        info.setSpacing(4)

        title = QLabel(franchise.get("display_title", "Unknown"))
        title.setStyleSheet("font-weight: 600; font-size: 14px;")
        title.setWordWrap(True)
        info.addWidget(title)

        self.changes = [p.strip() for p in (franchise.get("update_details") or "").split(" | ") if p.strip()]
        count = len(self.changes)
        summary = QLabel(f"{count} change{'s' if count != 1 else ''} · New releases, announcements or airing episodes")
        summary.setStyleSheet("color: #b0b3c2; font-size: 12px; border: none; padding: 0;")
        summary.setWordWrap(True)
        info.addWidget(summary)
        if self.disposition != "new":
            saved = QLabel({"later": "Saved for later", "not_interested": "Not interested", "muted": "Updates muted"}[self.disposition])
            saved.setObjectName("subheading")
            info.addWidget(saved)
        preview = QLabel(self.changes[0] if self.changes else "Update available")
        preview.setWordWrap(True)
        preview.setTextFormat(Qt.PlainText)
        preview.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        preview.setStyleSheet("color: #dddfea; font-size: 12px; border: none; padding: 0;")
        info.addWidget(preview)

        layout.addLayout(info, 1)

        first = QHBoxLayout()
        first.setSpacing(10)
        first.addStretch()
        view_btn = QPushButton("View changes")
        view_btn.setProperty("accent", True)
        view_btn.setCursor(Qt.PointingHandCursor)
        view_btn.clicked.connect(self._show_changes)
        first.addWidget(view_btn)
        if self.disposition != "new":
            restore = QPushButton("Restore updates")
            restore.setCursor(Qt.PointingHandCursor)
            restore.setToolTip("Return this anime's updates to the active list")
            restore.clicked.connect(self._restore)
            first.addWidget(restore)
        else:
            later = QPushButton("Later")
            later.setToolTip("Save this anime's updates for later until you restore them")
            later.clicked.connect(lambda: self._defer("later"))
            first.addWidget(later)
            not_interested = QPushButton("Not interested")
            not_interested.setToolTip("Keep this anime out of active updates until restored")
            not_interested.clicked.connect(lambda: self._defer("not_interested"))
            first.addWidget(not_interested)
            mute = QPushButton("Mute anime")
            mute.setToolTip("Hide all future updates for this anime until restored")
            mute.clicked.connect(self._mute)
            first.addWidget(mute)
            watched = QPushButton("Watched and ignore")
            watched.setToolTip("Mark all seasons in this series as watched and ignore current updates. New changes can still appear later.")
            watched.clicked.connect(self._watched_and_ignore)
            first.addWidget(watched)
            dismiss_btn = QPushButton("Dismiss")
            dismiss_btn.clicked.connect(self._dismiss)
            first.addWidget(dismiss_btn)
        outer.addLayout(first)
        for control in self.findChildren(QPushButton):
            control.setCursor(Qt.PointingHandCursor)
            control.setMinimumHeight(36)
            control.setAccessibleName(control.text() + " for " + franchise.get("display_title", "anime"))

    def _perform_action(self, action):
        if self.async_actions:
            self.action_requested.emit(self.franchise_id, action)
            return
        UpdateActionWorker.perform(self.franchise_id, action)
        self.hide()
        self.dismissed.emit()

    def _watched_and_ignore(self):
        self._perform_action("watched")

    def _defer(self, disposition):
        self._perform_action(disposition)

    def _restore(self):
        self._perform_action("new")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Opening details can run a nested event loop that refreshes the
            # updates list and deletes this card. Do not touch self afterward.
            event.accept()
            self.clicked.emit(self.franchise_id)
            return
        super().mousePressEvent(event)

    def _mute(self):
        self._perform_action("muted")

    def _dismiss(self):
        self._perform_action("dismiss")

    def _show_changes(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("All changes")
        dialog.resize(720, 580)
        outer = QVBoxLayout(dialog)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        for change in self.changes:
            title, separator, status = change.partition(" — ")
            box = QFrame()
            box.setObjectName("change_row")
            box.setStyleSheet("#change_row { background: #1d1f29; border-radius: 8px; }")
            row = QVBoxLayout(box)
            name = QLabel(title)
            name.setTextFormat(Qt.PlainText)
            name.setWordWrap(True)
            name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            row.addWidget(name)
            if separator:
                label = QLabel(status)
                label.setStyleSheet("color: #b0b3c2; border: none;")
                label.setWordWrap(True)
                row.addWidget(label)
            layout.addWidget(box)
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        close = QPushButton("Close")
        close.clicked.connect(dialog.accept)
        outer.addWidget(close)
        navigate(dialog)


class UpdatesPage(QWidget):
    """Page showing all anime with detected updates."""

    card_clicked = pyqtSignal(int)  # franchise_id
    data_changed = pyqtSignal()
    refresh_requested = pyqtSignal()
    action_finished = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._apply_worker = None
        self._update_card_pool = {}
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 12)
        layout.setSpacing(16)

        masthead = MotifHeader("\u66f4\u65b0")
        header_layout = QHBoxLayout(masthead)
        header_layout.setContentsMargins(0, 0, 0, 0)
        headings = QVBoxLayout()
        headings.setAlignment(Qt.AlignVCenter)
        title = QLabel("Library updates")
        title.setObjectName("heading")
        headings.addWidget(title)
        desc = QLabel("Metadata, new episodes, seasons and local health warnings")
        desc.setObjectName("subheading")
        desc.setWordWrap(True)
        headings.addWidget(desc)
        header_layout.addLayout(headings, 1)
        refresh_button = QPushButton("Refresh metadata")
        refresh_button.setProperty("accent", True)
        refresh_button.clicked.connect(self.refresh_requested.emit)
        header_layout.addWidget(refresh_button)
        layout.addWidget(masthead)

        connection = QFrame()
        connection.setObjectName("final_panel")
        connection_row = QHBoxLayout(connection)
        connection_row.setContentsMargins(16, 12, 16, 12)
        connection_row.addWidget(QLabel("AniList metadata"))
        connection_row.addStretch()
        self.status_pill = QLabel()
        connection_row.addWidget(self.status_pill)
        layout.addWidget(connection)

        filters = QHBoxLayout()
        self._filter = "All"
        self._filter_buttons = QButtonGroup(self)
        for category in ("All", "Episodes", "Seasons", "Health", "New", "Later", "Not interested", "Muted"):
            button = QPushButton(category)
            button.setCheckable(True)
            button.setProperty("chip", True)
            button.setChecked(category == "All")
            self._filter_buttons.addButton(button)
            button.clicked.connect(lambda checked=False, value=category: self._select_filter(value))
            filters.addWidget(button)
        filters.addStretch()
        layout.addLayout(filters)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setSpacing(8)
        self.list_layout.setAlignment(Qt.AlignTop)

        scroll.setWidget(self.list_widget)
        layout.addWidget(scroll, 1)

    def refresh(self, check_artwork=True):
        """Reload updates and per-anime saved choices from persistent storage."""
        # Update status pill
        online = cached_online()
        if online is None:
            self.status_pill.setText("Online status unchecked")
            self.status_pill.setObjectName("status_offline")
        elif not online:
            self.status_pill.setText("Offline Mode")
            self.status_pill.setObjectName("status_offline")
        else:
            self.status_pill.setText("Online")
            self.status_pill.setObjectName("status_online")
        self.status_pill.setStyleSheet(self.status_pill.styleSheet())  # Force refresh

        franchises = db.get_all_franchises()
        choices = db.update_dispositions()
        for record in franchises:
            cached = self._update_card_pool.get(record["id"])
            record["_cover_version"] = artwork_version(record.get("cover_filename")) if check_artwork or cached is None else cached[0][-1]
            record["_update_disposition"] = choices.get(record["id"], "new")
        self._updates = [record for record in franchises if record.get("has_new_update") and record["_update_disposition"] == "new"]
        self._saved_updates = [record for record in franchises if record["_update_disposition"] != "new"]
        self._health_records = franchises
        self._health = None
        self._render_cards()

    def _select_filter(self, value):
        self._filter = value
        for button in self._filter_buttons.buttons():
            button.setChecked(button.text() == value)
        self._render_cards()

    def _read_health(self, franchises):
        by_franchise = defaultdict(list)
        with closing(db.get_connection()) as conn:
            for row in conn.execute(
                "SELECT * FROM seasons WHERE storage_state='ON_DISK' AND relation_type='SEASON'"
            ):
                by_franchise[row["franchise_id"]].append(dict(row))
        alerts = []
        for record in franchises:
            seasons = by_franchise[record["id"]]
            if not seasons:
                continue
            if db.uses_continuous_episodes(record):
                inventory = episode_inventory(seasons, continuous=True)
                gap_count = len(inventory["missing_episodes"])
                duplicate_count = len({episode for result in inventory["seasons"].values()
                                       for episode in result["duplicate_episodes"]})
            else:
                results = [season_health(season) for season in seasons]
                gap_count = sum(len(result["missing_episodes"]) for result in results)
                duplicate_count = sum(len(result["duplicate_episodes"]) for result in results)
            if gap_count or duplicate_count:
                alerts.append((record, gap_count, duplicate_count))
        return alerts

    def _start_update_action(self, fid, action):
        if self._apply_worker and self._apply_worker.isRunning():
            return
        self.setEnabled(False)
        cached = self._update_card_pool.get(fid)
        if cached:
            for button in cached[1].findChildren(QPushButton):
                button.setToolTip("Saving your choice...")
        self.status_pill.setText("Saving your choice...")
        self._apply_worker = UpdateActionWorker(fid, action, self)
        self._apply_worker.finished.connect(self._update_action_finished)
        self._apply_worker.start()

    def _update_action_finished(self):
        worker = self._apply_worker
        self._apply_worker = None
        self.setEnabled(True)
        if worker.error:
            QMessageBox.warning(self, "Could not save update choice", worker.error)
        self.refresh(check_artwork=False)
        self.data_changed.emit()
        self.action_finished.emit(worker.fid)
        worker.deleteLater()

    def _remove_update(self, fid):
        self.refresh()
        self.data_changed.emit()

    def _render_cards(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                if not isinstance(item.widget(), UpdateCard):
                    item.widget().deleteLater()

        known = {record["id"] for record in self._updates + self._saved_updates}
        for fid in list(self._update_card_pool):
            if fid not in known:
                self._update_card_pool.pop(fid)[1].deleteLater()
        shown = 0
        if self._filter != "Health":
            saved_filter = {"Later": "later", "Not interested": "not_interested", "Muted": "muted"}.get(self._filter)
            records = [record for record in self._saved_updates if record["_update_disposition"] == saved_filter] if saved_filter else self._updates
            for record in records:
                changes = (record.get("update_details") or "").split(" | ")
                is_episode = lambda change: change.strip().lower().startswith("episode ") and "airing" in change.lower()
                if self._filter == "Episodes" and not any(map(is_episode, changes)):
                    continue
                if self._filter == "Seasons" and not any(change.strip() and not is_episode(change) for change in changes):
                    continue
                fingerprint = tuple(record.get(key) for key in ("display_title", "cover_filename", "update_details", "_update_disposition", "_cover_version"))
                cached = self._update_card_pool.get(record["id"])
                if cached is None or cached[0] != fingerprint:
                    if cached is not None:
                        cached[1].deleteLater()
                    card = UpdateCard(record, self.list_widget, async_actions=True)
                    card.action_requested.connect(self._start_update_action)
                    card.clicked.connect(self.card_clicked.emit)
                    card.dismissed.connect(lambda fid=record["id"]: self._remove_update(fid))
                    self._update_card_pool[record["id"]] = (fingerprint, card)
                else:
                    card = cached[1]
                self.list_layout.addWidget(card)
                card.show()
                shown += 1
        if self._filter == "Health":
            if self._health is None:
                self._health = self._read_health(self._health_records)
            for record, gaps, duplicates in self._health:
                card = QFrame()
                card.setObjectName("final_panel")
                row = QHBoxLayout(card)
                row.setContentsMargins(16, 12, 16, 12)
                poster = QLabel((record.get("display_title") or "?")[0].upper())
                poster.setAlignment(Qt.AlignCenter)
                poster.setFixedSize(44, 64)
                poster.setStyleSheet("background: #1e2230; border-radius: 8px; font-size: 22px; font-weight: 700;")
                cover = record.get("cover_filename")
                if cover and refresh_image_exists(COVERS_DIR / cover):
                    poster.setPixmap(refresh_pixmap(COVERS_DIR / cover).scaled(
                        44, 64, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                row.addWidget(poster)
                details = QVBoxLayout()
                heading = QLabel(record["display_title"])
                heading.setTextFormat(Qt.PlainText)
                heading.setWordWrap(True)
                details.addWidget(heading)
                summary = QLabel(f"Episode gaps: {gaps}  /  Repeated episode numbers: {duplicates}")
                summary.setObjectName("subheading")
                details.addWidget(summary)
                if duplicates:
                    note = QLabel("May be revised episodes or different encodes. Use Organizer to check exact duplicates.")
                    note.setWordWrap(True)
                    note.setObjectName("subheading")
                    details.addWidget(note)
                row.addLayout(details, 1)
                review = QPushButton("Review files")
                review.setProperty("accent", True)
                review.clicked.connect(lambda checked=False, fid=record["id"]: self.card_clicked.emit(fid))
                row.addWidget(review)
                self.list_layout.addWidget(card)
                shown += 1
        if not shown:
            empty = QLabel("No updates in this category.")
            empty.setObjectName("subheading")
            empty.setAlignment(Qt.AlignCenter)
            empty.setMinimumHeight(120)
            self.list_layout.addWidget(empty)
        self.list_layout.addStretch()
