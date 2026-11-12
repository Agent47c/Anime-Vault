"""Storage overview using the existing inventory and conservative health checks."""
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QSizePolicy,
)
from PyQt5.QtGui import QColor, QPainter, QPainterPath
from PyQt5.QtCore import QSize, Qt, pyqtSignal, QRectF
from app import db
from app.config import COVERS_DIR
from app.core.storage import disk_snapshot, format_bytes
from app.core.library_health import episode_inventory
from app.ui.components.design import MotifHeader, ElidedLabel
from app.ui.refresh import refresh_pixmap, refresh_image_exists
from app.ui.dialogs.delete_confirm import DeleteConfirmDialog
from app.ui.theme import COLORS


class SegmentedCapacityBar(QWidget):
    """Custom bar widget rendering three distinct segments: Anime, Other, and Free."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(14)
        self.anime_pct = 0.0
        self.other_pct = 0.0
        self.free_pct = 0.0

    def set_values(self, anime_bytes: int, total_used_bytes: int, total_capacity_bytes: int):
        if total_capacity_bytes <= 0:
            self.anime_pct = self.other_pct = self.free_pct = 0.0
            self.update()
            return

        anime_bytes = min(max(0, anime_bytes), total_used_bytes)
        other_bytes = max(0, total_used_bytes - anime_bytes)
        free_bytes = max(0, total_capacity_bytes - total_used_bytes)

        self.anime_pct = min(1.0, max(0.0, anime_bytes / total_capacity_bytes))
        self.other_pct = min(1.0, max(0.0, other_bytes / total_capacity_bytes))
        self.free_pct = min(1.0, max(0.0, free_bytes / total_capacity_bytes))
        self.update()

    def paintEvent(self, event):
        colors = COLORS.get(QApplication.instance().property("animevaultTheme"), COLORS["dark"])
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), 9, 9)
        painter.setClipPath(path)

        # Free space background (track)
        painter.fillRect(0, 0, w, h, QColor(colors["bg_card_alt"]))

        # Anime library segment (magenta)
        anime_w = int(w * self.anime_pct)
        if anime_w > 0:
            painter.fillRect(0, 0, anime_w, h, QColor(colors["accent_secondary"]))

        # Other files segment (lavender)
        other_w = int(w * self.other_pct)
        if other_w > 0:
            painter.fillRect(anime_w, 0, other_w, h, QColor(colors["text_muted"]))

        painter.end()


class StorageTable(QTableWidget):
    """Keep the title readable and scroll horizontally when columns no longer fit."""

    def fit_title(self):
        remaining = self.viewport().width() - sum(self.columnWidth(i) for i in range(1, self.columnCount()))
        self.horizontalHeader().resizeSection(0, max(240, remaining))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_title()


class StoragePage(QWidget):
    data_changed = pyqtSignal()
    refresh_requested = pyqtSignal()
    filter_requested = pyqtSignal(str)
    anime_clicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("storage_page")
        self._setup_ui()
        self.refresh()

    @staticmethod
    def _label(text, name):
        label = QLabel(text)
        label.setObjectName(name)
        return label

    @staticmethod
    def _button(text):
        button = QPushButton(text)
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumHeight(44)
        return button

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content.setObjectName("storage_content")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 20, 40, 40)
        layout.setSpacing(24)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        header = MotifHeader("\u5bb9\u91cf")
        row = QHBoxLayout(header)
        row.setContentsMargins(0, 0, 0, 0)
        titles = QVBoxLayout()
        titles.setSpacing(4)
        titles.addWidget(self._label("Storage", "storage_heading"))
        subtitle = self._label("Disk usage, watch status and how much space each collection takes", "storage_secondary")
        subtitle.setWordWrap(True)
        titles.addWidget(subtitle)
        row.addLayout(titles, 1)
        self.rescan_btn = self._button("Refresh storage")
        self.rescan_btn.setProperty("accent", True)
        self.rescan_btn.clicked.connect(self.refresh_requested.emit)
        row.addWidget(self.rescan_btn, 0, Qt.AlignVCenter)
        layout.addWidget(header)

        hero = QFrame()
        hero.setObjectName("storage_panel")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        hero_layout.setSpacing(16)
        self.drive_label = self._label("Library drive", "storage_panel_title")
        hero_layout.addWidget(self.drive_label)
        hero_layout.addWidget(self._label("Anime library and local media storage", "storage_secondary"))
        cap = QHBoxLayout()
        cap.setSpacing(8)
        self.free_big_label = self._label("Checking...", "storage_free")
        cap.addWidget(self.free_big_label, 0, Qt.AlignBottom)
        self.capacity_sub_label = self._label("", "storage_secondary")
        cap.addWidget(self.capacity_sub_label, 0, Qt.AlignBottom)
        cap.addStretch()
        hero_layout.addLayout(cap)
        self.capacity_bar = SegmentedCapacityBar()
        self.capacity_bar.setAccessibleName("Library, other files and free disk space")
        hero_layout.addWidget(self.capacity_bar)
        legend = QHBoxLayout()
        legend.setSpacing(28)
        self.legend_anime = self._label("", "storage_secondary")
        self.legend_other = self._label("", "storage_secondary")
        self.legend_free = self._label("", "storage_secondary")
        for label in (self.legend_anime, self.legend_other, self.legend_free):
            label.setWordWrap(True)
            legend.addWidget(label)
        legend.addStretch()
        hero_layout.addLayout(legend)
        layout.addWidget(hero)

        cards = QHBoxLayout()
        cards.setSpacing(16)
        self.card_on_disk = self._create_stat_card("On disk, complete titles")
        self.card_partial = self._create_stat_card("Partially on disk, need review")
        self.card_watched = self._create_stat_card("Watched titles")
        self.card_removed = self._create_stat_card("Removed, records kept")
        self.card_reclaim = self._create_stat_card("Watched files (potential reclaim)", reclaim=True)
        for card in (self.card_on_disk, self.card_partial, self.card_watched, self.card_removed, self.card_reclaim):
            cards.addWidget(card, 1)
        layout.addLayout(cards)

        panel = QFrame()
        panel.setObjectName("storage_panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(24, 24, 24, 24)
        panel_layout.setSpacing(12)
        table_head = QHBoxLayout()
        table_titles = QVBoxLayout()
        table_titles.setSpacing(6)
        table_titles.addWidget(self._label("Largest anime collections", "storage_panel_title"))
        table_sub = self._label("File paths, watch status, health and reclaimable space", "storage_secondary")
        table_sub.setWordWrap(True)
        table_titles.addWidget(table_sub)
        table_head.addLayout(table_titles, 1)
        self.reclaim_btn = self._button("Show potential reclaim")
        self.reclaim_btn.setObjectName("storage_reclaim")
        self.reclaim_btn.clicked.connect(lambda: self.filter_requested.emit("RECLAIM"))
        table_head.addWidget(self.reclaim_btn)
        panel_layout.addLayout(table_head)
        self.table = StorageTable(0, 6)
        self.table.setObjectName("storage_table")
        self.table.setHorizontalHeaderLabels(["Anime", "Seasons / files / size", "Watch status", "Health", "Potential reclaim", "Actions"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setMinimumHeight(300)
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(110)
        header.setFixedHeight(44)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        for column in range(1, 6):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        panel_layout.addWidget(self.table, 1)
        note = self._label("Potential reclaim counts watched files only. Files are never deleted without your confirmation.", "storage_secondary")
        note.setWordWrap(True)
        panel_layout.addWidget(note)
        layout.addWidget(panel, 1)

    def _create_stat_card(self, title, reclaim=False):
        card = QFrame()
        card.setObjectName("storage_panel")
        box = QVBoxLayout(card)
        box.setContentsMargins(18, 18, 18, 18)
        box.setSpacing(8)
        value = self._label("0", "val_label")
        value.setProperty("reclaim", reclaim)
        box.addWidget(value)
        caption = self._label(title, "storage_caption")
        caption.setWordWrap(True)
        box.addWidget(caption)
        return card

    def refresh(self):
        stats = db.get_library_stats()
        anime_bytes = stats.get("total_bytes", 0)
        snapshot=db.current_refresh_view()
        disk = snapshot['disk'] if snapshot and 'disk' in snapshot else disk_snapshot()
        total, used, free = disk["total"], disk["used"], disk["free"]
        self.drive_label.setText("Library drive " + disk["label"] if total else "Library storage")
        self.free_big_label.setText(format_bytes(free) if total else "Unavailable")
        self.capacity_sub_label.setText(f"free of {format_bytes(total)}" if total else "Library drives are offline" if disk["configured"] else "Add a library folder in Settings")
        self.capacity_sub_label.setToolTip("Unavailable roots: " + ", ".join(disk["unavailable"]) if disk["unavailable"] else disk["label"])
        self.capacity_bar.set_values(anime_bytes, used, total)
        self.legend_anime.setText(f"Anime library  {format_bytes(anime_bytes)}")
        self.legend_other.setText("Other files  " + (format_bytes(max(0, used - anime_bytes)) if total else "unavailable"))
        self.legend_free.setText("Free space  " + (format_bytes(free) if total else "unavailable"))
        for card, key in ((self.card_on_disk, "on_disk"), (self.card_partial, "partially_on_disk"), (self.card_watched, "watched_count"), (self.card_removed, "watched_removed")):
            card.findChild(QLabel, "val_label").setText(f"{stats.get(key, 0):,}")
        reclaim = format_bytes(stats.get("potential_reclaim_bytes", 0))
        self.card_reclaim.findChild(QLabel, "val_label").setText(reclaim)
        self.reclaim_btn.setToolTip(f"Show watched titles with {reclaim} potentially reclaimable")
        records = [f for f in db.get_all_franchises(sort_by="total_size_bytes", sort_order="DESC") if f.get("storage_state") in ("ON_DISK", "PARTIALLY_ON_DISK")]
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            seasons = db.get_seasons_for_franchise(record["id"])
            files = sum(len(json.loads(s.get("video_files_json") or "[]")) for s in seasons)
            size = format_bytes(record.get("total_size_bytes") or 0)
            self.table.setRowHeight(row, 80)
            for col, width in enumerate((240, 174, 130, 176, 150, 192)):
                item = QTableWidgetItem("")
                item.setSizeHint(QSize(width, 80))
                self.table.setItem(row, col, item)
            self.table.setCellWidget(row, 0, self._create_title_cell(record))
            self._text_cell(row, 1, f"{len(seasons)} seasons \u00b7 {size}\n{files:,} files")
            watch = {"WATCHED": "Watched", "WATCHING": "Watching", "PLAN_TO_WATCH": "Plan to watch", "DROPPED": "Dropped"}.get(record.get("watch_status"), (record.get("watch_status") or "Not set").replace("_", " ").title())
            self._text_cell(row, 2, watch)
            health, detail, tone = snapshot['storage_health'][record['id']] if snapshot and record['id'] in snapshot.get('storage_health',{}) else self._health(record, seasons)
            self._text_cell(row, 3, health, detail, tone)
            self._text_cell(row, 4, size if record.get("watch_status") == "WATCHED" else "\u2014")
            actions = QWidget()
            box = QHBoxLayout(actions)
            box.setContentsMargins(8, 8, 8, 8)
            box.setSpacing(8)
            for text, callback in (("Open", lambda checked=False, fid=record["id"]: self.anime_clicked.emit(fid)), ("Delete...", lambda checked=False, fid=record["id"]: self._delete_anime(fid))):
                button = self._button(text)
                button.setMinimumWidth(76)
                button.setObjectName("storage_delete" if text.startswith("Delete") else "storage_open")
                button.clicked.connect(callback)
                box.addWidget(button)
            self.table.setCellWidget(row, 5, actions)
        self.table.resizeColumnsToContents()
        self.table.fit_title()
        self.table.setUpdatesEnabled(True)

    @staticmethod
    def _health(record, seasons):
        continuous=db.uses_continuous_episodes(record)
        inventory = episode_inventory(seasons, continuous=continuous)
        results = list(inventory["seasons"].values())
        missing = len(inventory["missing_episodes"]) if continuous else sum(len(r["missing_episodes"]) for r in results)
        repeats = sum(len(r["duplicate_episodes"]) for r in results)
        detail = f"Episode gaps: {missing}; repeated episode numbers: {repeats}. Repeated numbers may be different versions, not identical files."
        if missing:
            return "Missing episodes", detail, "warning"
        if repeats:
            return "Review versions", detail, "warning"
        if record.get("storage_state") == "PARTIALLY_ON_DISK":
            return "Partially on disk", detail, "warning"
        if results and all(r["range_verified"] for r in results):
            return "Healthy", detail, "success"
        return "Range unverified", "No verified complete episode range. " + detail, "neutral"

    def _text_cell(self, row, column, text, tooltip=None, tone=None):
        cell = QWidget()
        box = QHBoxLayout(cell)
        box.setContentsMargins(8, 8, 8, 8)
        label = self._label(text, "storage_pill" if tone else "storage_cell_text")
        label.setToolTip(tooltip or text)
        if tone:
            label.setProperty("tone", tone)
        box.addWidget(label, 0, Qt.AlignVCenter)
        box.addStretch()
        self.table.setCellWidget(row, column, cell)

    def _create_title_cell(self, record):
        cell = QWidget()
        box = QHBoxLayout(cell)
        box.setContentsMargins(8, 8, 8, 8)
        box.setSpacing(12)
        thumb = self._label("", "storage_thumb")
        thumb.setFixedSize(36, 54)
        cover = record.get("cover_filename")
        if cover and refresh_image_exists(COVERS_DIR / cover):
            thumb.setPixmap(refresh_pixmap(COVERS_DIR / cover).scaled(36, 54, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        box.addWidget(thumb)
        labels = QVBoxLayout()
        labels.setSpacing(3)
        for text, name in ((record.get("display_title") or "Anime", "storage_anime_title"), (record.get("root_folder_path") or "Folder not set", "storage_path")):
            label = ElidedLabel(text)
            label.setObjectName(name)
            labels.addWidget(label)
        state = self._label("On disk" if record.get("storage_state") == "ON_DISK" else "Partially on disk", "storage_path")
        labels.addWidget(state)
        box.addLayout(labels, 1)
        return cell

    def _delete_anime(self, franchise_id: int):
        franchise = db.get_franchise(franchise_id)
        if not franchise:
            return
        seasons = db.get_seasons_for_franchise(franchise_id)
        dialog = DeleteConfirmDialog(franchise, seasons, self)
        dialog.deletion_confirmed.connect(lambda fid, info:self.data_changed.emit())
        dialog.exec_()
