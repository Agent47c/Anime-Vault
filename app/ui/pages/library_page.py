from datetime import datetime, timedelta
from contextlib import closing
import json
from app.ui.refresh import refresh_pixmap, refresh_image_exists
"""
Library Page — Main view replicating the Anime Manager UI Reference mockup.
Includes:
- Hero "Resume Last Session" card with gradient & Japanese watermark
- Library header with stats (count, TB on disk)
- Filter pill chips (All, On disk, Partially on disk, Watched removed, Potential Reclaim, Has update)
- Sort dropdown & Grid/Compact list view toggles persisted via QSettings
- Responsive poster card grid AND dense Compact list view
- Multi-selection checkboxes and Batch actions bar
"""

import os
import json
import webbrowser
from pathlib import Path
from typing import Optional, List, Dict, Any

from PyQt5.QtWidgets import QMenu, QApplication
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QScrollArea, QGridLayout, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QCheckBox, QMessageBox, QStackedWidget, QSizePolicy,
)
from PyQt5.QtGui import QFont, QPainter, QColor, QLinearGradient, QPixmap, QPainterPath, QRadialGradient, QPen
from PyQt5.QtCore import QSize, Qt, pyqtSignal, QRectF, QSettings, QTimer

from app import db
from app.config import (
    COVERS_DIR, get_last_streaming_url, get_last_franchise_id, get_last_episode_path,
    is_offline, launch_video_file,
)
from app.ui.components.poster_card import PosterCard
from app.ui.components.design import ElidedLabel
from app.ui.components.filter_pill import FilterPill
from app.ui.components.airing_count import AiringCount, AiringDay
from app.ui.icons import icon
from app.ui.theme import COLORS
from app.ui.components.smooth_scroll import SmoothScrollArea
from app.ui.artwork import artwork_loader, valid_image
from app.ui.dialogs.delete_confirm import DeleteConfirmDialog


def section_heading(glyph, title):
    row = QHBoxLayout()
    row.setSpacing(10)
    chip = QLabel(glyph)
    chip.setObjectName("section_chip")
    chip.setAlignment(Qt.AlignCenter)
    chip.setFixedHeight(22)
    row.addWidget(chip)
    heading = QLabel(title)
    heading.setObjectName("library_heading")
    row.addWidget(heading)
    row.addStretch()
    return row, heading


class HeroResumeCard(QFrame):
    """Hero banner card at the top of Library, matching the UI Reference."""

    resume_clicked = pyqtSignal()
    details_clicked = pyqtSignal(int)  # franchise_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("hero_resume_card")
        self.setFixedHeight(340)
        self.current_fid = None
        self._banner = QPixmap()
        self._scaled_banner = QPixmap()
        self._scaled_banner_size = None
        artwork_loader().changed.connect(self._artwork_changed)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(6)

        # Top Tag Row
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        tag = QLabel("\u7d9a\u304d \u00b7 CONTINUE WATCHING")
        tag.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 11px; font-weight: 700; letter-spacing: 0.5px;")
        top_row.addWidget(tag)

        self.offline_badge = QLabel("Available offline")
        self.offline_badge.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.15);
            color: #ffffff;
            border-radius: 10px;
            padding: 2px 10px;
            font-size: 10px;
            font-weight: 600;
        """)
        self.offline_badge.hide()
        top_row.addStretch()
        layout.addLayout(top_row)

        # Huge Anime Title
        self.title_label = ElidedLabel("Frieren: Beyond Journey's End")
        self.title_label.setStyleSheet("color: #ffffff; font-size: 52px; font-weight: 800;")
        layout.addWidget(self.title_label)

        # Subtitle: Season · Episode · URL
        self.sub_label = ElidedLabel("Season 1 · Episode 14 of 28 · 127.0.0.1:8765")
        self.sub_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 12px;")
        layout.addWidget(self.sub_label)

        layout.addSpacing(6)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.resume_btn = QPushButton("▶  Resume Episode 14")
        self.resume_btn.setCursor(Qt.PointingHandCursor)
        self.resume_btn.setFixedHeight(36)
        self.resume_btn.setObjectName("hero_resume_button")
        self.resume_btn.clicked.connect(self._on_resume)
        btn_row.addWidget(self.resume_btn)

        self.details_btn = QPushButton("Details")
        self.details_btn.setCursor(Qt.PointingHandCursor)
        self.details_btn.setFixedHeight(36)
        self.details_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.18);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 12px;
                padding: 0 18px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.28);
            }
        """)
        self.details_btn.clicked.connect(self._on_details)
        btn_row.addWidget(self.details_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def paintEvent(self, event):
        """Paint custom hero gradient with faded Japanese kanji watermark."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), 24, 24)
        painter.setClipPath(clip)
        background = QLinearGradient(0, 0, w, h)
        background.setColorAt(0, QColor("#4A3BB0"))
        background.setColorAt(.60, QColor("#171B3F"))
        background.setColorAt(1, QColor("#0E1020"))
        painter.fillRect(self.rect(), background)
        if not self._banner.isNull():
            if self._scaled_banner_size != (w, h):
                self._scaled_banner = self._banner.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self._scaled_banner_size = (w, h)
            image = self._scaled_banner
            painter.drawPixmap((w - image.width()) // 2, (h - image.height()) // 2, image)
        glow = QRadialGradient(w * .88, h, max(1, w * .55))
        glow.setColorAt(0, QColor(217, 45, 69, 153))
        glow.setColorAt(1, QColor(217, 45, 69, 0))
        painter.fillRect(self.rect(), glow)
        painter.setPen(QPen(QColor(255, 255, 255, 15), 2))
        decorated = QApplication.instance().property("animevaultDecorations") is not False
        for x in range(0, w + h, 28) if decorated else ():
            painter.drawLine(x, 0, x - round(h * .27), h)
        shade = QLinearGradient(0, 0, w, 0)
        shade.setColorAt(0, QColor("#0B0C10"))
        shade.setColorAt(.55, QColor(11, 12, 16, 153))
        shade.setColorAt(1, QColor(11, 12, 16, 0))
        painter.fillRect(self.rect(), shade)
        if not self._banner.isNull():
            painter.fillRect(self.rect(), QColor(0, 0, 0, 89))
        if not decorated:
            painter.end()
            return
        font = QFont("Yu Gothic")
        font.setPixelSize(300)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 26))
        painter.drawText(QRectF(w - 340, h - 245, 340, 310), Qt.AlignCenter, "\u7d9a")
        painter.setPen(QPen(QColor(255, 255, 255, 46), 1.5))
        for x in range(-18, w, 36):
            for radius in (11, 17):
                painter.drawArc(QRectF(x + 18 - radius, h - radius, 2 * radius, 2 * radius), 0, 180 * 16)
        painter.end()

    def _last_local_episode(self):
        episode = get_last_episode_path()
        if not episode or not Path(episode).is_file():
            return None, None
        key = os.path.normcase(os.path.abspath(episode))
        with closing(db.get_connection()) as connection:
            for season in connection.execute(
                "SELECT franchise_id, season_folder_path, video_files_json FROM seasons WHERE season_folder_path IS NOT NULL"
            ):
                folder = Path(season["season_folder_path"])
                if any(os.path.normcase(os.path.abspath(folder / name)) == key
                       for name in json.loads(season["video_files_json"] or "[]")):
                    record = db.get_franchise(season["franchise_id"])
                    if record:
                        return record, episode
        return None, None

    def _first_local_episode(self, fid):
        for season in sorted(db.get_series_seasons(fid), key=lambda row: row.get("season_number") or 999):
            folder = season.get("season_folder_path")
            if not folder or season.get("storage_state") != "ON_DISK":
                continue
            for name in json.loads(season.get("video_files_json") or "[]"):
                episode = Path(folder) / name
                if episode.is_file():
                    return str(episode)
        return None

    def refresh(self):
        """Keep the banner and playback action attached to the same anime."""
        record, episode = self._last_local_episode()
        if not record:
            fid = get_last_franchise_id()
            record = db.get_franchise(fid) if fid else None
        if not record:
            records = db.get_all_franchises(sort_by="total_size_bytes", sort_order="DESC")
            record = records[0] if records else None
        if not record:
            self.hide()
            return
        self.current_fid = record["id"]
        self._load_banner(record)
        self.title_label.set_full_text(record.get("display_title") or "Anime")
        self._resume_episode = episode or self._first_local_episode(self.current_fid)
        if self._resume_episode:
            self.sub_label.set_full_text("Last played: " + Path(episode).stem if episode else "Available locally on disk")
            self.resume_btn.setText("\u25b6  Resume episode" if episode else "\u25b6  Play episode")
            self.resume_btn.setEnabled(True)
        else:
            self.sub_label.set_full_text("No local episode available")
            self.resume_btn.setText("No local episode")
            self.resume_btn.setEnabled(False)
        self.show()

    def _load_banner(self, franchise):
        filename = franchise.get("banner_filename")
        self._banner = refresh_pixmap(COVERS_DIR / filename) if filename else QPixmap()
        if self._banner.isNull() and franchise.get("cover_filename"):
            self._banner = refresh_pixmap(COVERS_DIR / franchise["cover_filename"])
        self._scaled_banner_size = None
        artwork_loader().request(franchise, allow_network=True, banner_only=True)
        self.update()

    def _artwork_changed(self, fid):
        if fid == self.current_fid:
            self.refresh()

    def _on_resume(self):
        episode = getattr(self, "_resume_episode", None)
        if not episode:
            return
        if not Path(episode).is_file():
            self.refresh()
            QMessageBox.information(self, "Episode unavailable", "The episode could not be found. Check its location in anime details.")
            return
        try:
            launch_video_file(episode)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Could not play episode", str(error))

    def _on_details(self):
        if self.current_fid:
            self.details_clicked.emit(self.current_fid)


def _poster_key(record):
    fields = ("display_title", "title_en", "title_romaji", "title_native", "cover_filename", "storage_state", "has_new_update", "user_rating", "total_size_bytes", "release_count", "is_adult", "genres", "_cover_version")
    return tuple(record.get(key) for key in fields) + (tuple(record.get("series_member_ids", [])),)


class LibraryPage(QWidget):
    """Main library grid page replicating the UI Reference mockup."""

    card_clicked = pyqtSignal(int)  # franchise_id
    airing_clicked = pyqtSignal(dict)
    add_custom_clicked = pyqtSignal()
    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards = []
        self._card_pool = {}
        self._library_index = None
        self._grid_signature = None
        self._grid_columns = 0
        self._display_franchises = []
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(80)
        self._resize_timer.timeout.connect(self._reflow_grid)
        artwork_loader().changed.connect(self._artwork_changed)
        self._current_filter = ""
        self._search_query = ""
        self._sort_field = "display_title"
        self._sort_order = "ASC"
        self.selected_fids = set()

        # Load view mode from QSettings
        settings = QSettings("AnimeVault", "AnimeManager")
        from app import preferences as prefs
        self.view_mode = "compact" if prefs.enabled("compact_library") else settings.value("view_mode", "grid")

        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        page_scroll = SmoothScrollArea()
        self.page_scroll = page_scroll
        page_scroll.setWidgetResizable(True)
        page_scroll.setFrameShape(QFrame.NoFrame)
        page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        page_content = QWidget()
        layout = QVBoxLayout(page_content)
        page_scroll.setWidget(page_content)
        outer.addWidget(page_scroll)
        layout.setContentsMargins(28, 0, 28, 28)
        layout.setSpacing(16)

        # 1. Hero Resume Banner
        self.hero_card = HeroResumeCard(self)
        self.hero_card.details_clicked.connect(self.card_clicked.emit)
        layout.addWidget(self.hero_card)

        self.calendar_panel = QWidget()
        calendar_layout = QVBoxLayout(self.calendar_panel)
        calendar_layout.setContentsMargins(0, 0, 0, 0)
        calendar_layout.setSpacing(12)
        layout.addWidget(self.calendar_panel, 0, Qt.AlignLeft)
        airing_heading, airing_title = section_heading("\u653e\u9001", "Airing this week")
        airing_title.setText('Release calendar')
        calendar_layout.addLayout(airing_heading)
        self._calendar_offset = 0
        self.calendar_range = QLabel()
        self.calendar_range.setObjectName('subheading')
        calendar_controls = QHBoxLayout()
        calendar_controls.setSpacing(8)
        calendar_controls.addWidget(self.calendar_range)
        calendar_controls.addStretch()
        for text, delta in [('Previous week', -1), ('This week', 0), ('Next week', 1)]:
            button = QPushButton(text)
            button.setAccessibleName(text + ' in release calendar')
            button.clicked.connect(lambda checked=False, step=delta: self._change_calendar_week(step))
            calendar_controls.addWidget(button)
        calendar_layout.addLayout(calendar_controls)
        self.airing_week = QGridLayout()
        self._airing_week_signature = None
        self.airing_week.setSpacing(8)
        calendar_layout.addLayout(self.airing_week)

        release_heading, self.release_title = section_heading("\u65b0\u7740", "New seasons and episodes")
        self.release_heading_widget = QWidget()
        self.release_heading_widget.setLayout(release_heading)
        layout.addWidget(self.release_heading_widget)
        self.release_scroll = QScrollArea()
        self.release_scroll.setWidgetResizable(True)
        self.release_scroll.setFrameShape(QFrame.NoFrame)
        self.release_scroll.setFixedHeight(326)
        release_content = QWidget()
        self.release_layout = QHBoxLayout(release_content)
        self.release_layout.setContentsMargins(0, 0, 0, 8)
        self.release_layout.setSpacing(20)
        self.release_layout.setAlignment(Qt.AlignLeft)
        self.release_scroll.setWidget(release_content)
        layout.addWidget(self.release_scroll)

        # 2. Section Header & Controls Row
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        # Left: Library Title & Counts
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        all_heading, self.heading_label = section_heading("\u5168\u4f5c\u54c1", "All anime")
        title_box.addLayout(all_heading)

        self.stats_subtitle = QLabel("0 anime · 0 GB on disk")
        self.stats_subtitle.setStyleSheet("font-size: 13px; color: #b0b3c2;")
        title_box.addWidget(self.stats_subtitle)
        header_row.addLayout(title_box)

        header_row.addStretch()

        # Right: Sort Dropdown & View Mode Buttons
        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)

        # Sort Dropdown
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Name A to Z", "display_title|ASC")
        self.sort_combo.addItem("Name Z to A", "display_title|DESC")
        self.sort_combo.addItem("Sort  User Rating (Highest)", "user_rating|DESC")
        self.sort_combo.addItem("Sort  Disk Size (Largest)", "total_size_bytes|DESC")
        self.sort_combo.addItem("Sort  Recently Added", "created_at|DESC")
        self.sort_combo.addItem("Sort  Watch Status", "watch_status|ASC")
        self.sort_combo.setFixedHeight(36)
        self.sort_combo.setMinimumWidth(164)
        self.sort_combo.setToolTip("Sort anime by title, rating, size, date or watch status")
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        controls_row.addWidget(QLabel("Sort by"))
        controls_row.addWidget(self.sort_combo)

        # View Mode Toggle (Grid / Compact)
        view_toggle_frame = QFrame()
        view_toggle_frame.setStyleSheet("""
            QFrame {
                background-color: #15161d;
                border: 1px solid #303139;
                border-radius: 10px;
            }
        """)
        toggle_layout = QHBoxLayout(view_toggle_frame)
        toggle_layout.setContentsMargins(2, 2, 2, 2)
        toggle_layout.setSpacing(2)

        self.grid_btn = QPushButton()
        self.grid_btn.setFixedSize(40, 36)
        self.grid_btn.setIconSize(QSize(20, 20))
        self.grid_btn.setAccessibleName("Grid view")
        self.grid_btn.setCursor(Qt.PointingHandCursor)
        self.grid_btn.setToolTip("Standard Grid View")
        self.grid_btn.clicked.connect(lambda: self._set_view_mode("grid"))
        toggle_layout.addWidget(self.grid_btn)

        self.list_btn = QPushButton()
        self.list_btn.setFixedSize(40, 36)
        self.list_btn.setIconSize(QSize(20, 20))
        self.list_btn.setAccessibleName("List view")
        self.list_btn.setCursor(Qt.PointingHandCursor)
        self.list_btn.setToolTip("Compact List View")
        self.list_btn.clicked.connect(lambda: self._set_view_mode("compact"))
        toggle_layout.addWidget(self.list_btn)

        controls_row.addWidget(view_toggle_frame)
        layout.addLayout(header_row)

        # 3. Horizontal Filter Pills Row
        pills_layout = QHBoxLayout()
        pills_layout.setSpacing(8)

        self.pill_buttons = {}
        filters = [
            ("All", ""),
            ("Watching", "WATCHING"),
            ("Plan to watch", "PLAN_TO_WATCH"),
            ("On disk", "ON_DISK"),
            
            
            
            ("Has new update", "UPDATE"),
            ("Needs review", "REVIEW"),
        ]

        for label, val in filters:
            btn = FilterPill(label)
            btn.setProperty("pill", True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(38)
            if val == "":
                btn.setProperty("active", "true")
            btn.clicked.connect(lambda checked=False, v=val: self._on_filter_pill_clicked(v))
            self.pill_buttons[val] = btn
            pills_layout.addWidget(btn)

        pills_layout.addStretch()
        pills_layout.addLayout(controls_row)
        layout.addLayout(pills_layout)

        # 4. Batch Actions Bar (Visible when items selected)
        self.batch_bar = QFrame()
        self.batch_bar.setFixedHeight(44)
        self.batch_bar.setStyleSheet("""
            QFrame {
                background-color: #1a1e2b;
                border: 1px solid #8c6cff;
                border-radius: 10px;
                padding: 0 14px;
            }
        """)
        b_layout = QHBoxLayout(self.batch_bar)
        b_layout.setContentsMargins(12, 0, 12, 0)
        b_layout.setSpacing(12)

        self.batch_count_lbl = QLabel("0 selected")
        self.batch_count_lbl.setStyleSheet("color: #f3f4f6; font-size: 13px; font-weight: 700;")
        b_layout.addWidget(self.batch_count_lbl)

        mark_watched_btn = QPushButton("Mark Watched")
        mark_watched_btn.setFixedHeight(28)
        mark_watched_btn.setStyleSheet("background-color: #303139; color: #35cf91; border-radius: 6px; padding: 0 10px; font-weight: 600; font-size: 11px;")
        mark_watched_btn.clicked.connect(self._batch_mark_watched)
        b_layout.addWidget(mark_watched_btn)

        mark_watching_btn = QPushButton("Mark Watching")
        mark_watching_btn.setFixedHeight(28)
        mark_watching_btn.setStyleSheet("background-color: #303139; color: #ff70b3; border-radius: 6px; padding: 0 10px; font-weight: 600; font-size: 11px;")
        mark_watching_btn.clicked.connect(self._batch_mark_watching)
        b_layout.addWidget(mark_watching_btn)

        batch_del_btn = QPushButton("🗑 Delete Files...")
        batch_del_btn.setFixedHeight(28)
        batch_del_btn.setStyleSheet("background-color: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 6px; padding: 0 10px; font-weight: 600; font-size: 11px;")
        batch_del_btn.clicked.connect(self._batch_delete_files)
        b_layout.addWidget(batch_del_btn)

        b_layout.addStretch()

        clear_sel_btn = QPushButton("Clear Selection")
        clear_sel_btn.setFixedHeight(28)
        clear_sel_btn.setStyleSheet("background: transparent; color: #b0b3c2; border: none; font-size: 11px;")
        clear_sel_btn.clicked.connect(self._clear_selection)
        b_layout.addWidget(clear_sel_btn)

        self.batch_bar.setVisible(False)
        layout.addWidget(self.batch_bar)

        # 5. Stacked View Area (Grid View vs Compact Table View)
        self.views_stack = QStackedWidget()

        # Page 0: Grid Scroll
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 10, 0, 20)
        self.grid_layout.setHorizontalSpacing(20)
        self.grid_layout.setVerticalSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.views_stack.addWidget(self.grid_container)

        # Page 1: Compact Table
        self.compact_table = QTableWidget()
        self.compact_table.setColumnCount(7)
        self.compact_table.setHorizontalHeaderLabels(["", "", "TITLE", "STATUS", "SIZE", "RATING", "ACTION"])
        self.compact_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.compact_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.compact_table.verticalHeader().setVisible(False)
        self.compact_table.setShowGrid(False)
        self.compact_table.setFocusPolicy(Qt.NoFocus)
        self.compact_table.setStyleSheet("""
            QTableWidget {
                background-color: #14151c;
                border: 1px solid #303139;
                border-radius: 12px;
            }
            QTableWidget::item {
                border-bottom: 1px solid #1d1f29;
                padding: 6px;
            }
        """)

        header = self.compact_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.compact_table.setColumnWidth(0, 36)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.compact_table.setColumnWidth(1, 48)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.compact_table.setColumnWidth(6, 120)

        self.views_stack.addWidget(self.compact_table)
        layout.addWidget(self.views_stack, 1)

        self._update_toggle_buttons()

    def _set_view_mode(self, mode: str):
        self.view_mode = mode
        from app import preferences as prefs
        prefs.save("compact_library", mode == "compact")
        settings = QSettings("AnimeVault", "AnimeManager")
        settings.setValue("view_mode", mode)
        self._update_toggle_buttons()
        self.refresh_display()

    def _update_toggle_buttons(self):
        palette = COLORS.get(QApplication.instance().property("animevaultTheme"), COLORS["dark"])
        self.grid_btn.setIcon(icon("library", palette["text_primary"] if self.view_mode == "grid" else palette["text_secondary"]))
        self.list_btn.setIcon(icon("list", palette["text_primary"] if self.view_mode != "grid" else palette["text_secondary"]))
        if self.view_mode == "grid":
            self.grid_btn.setStyleSheet("border: none; border-radius: 6px; font-size: 15px; background-color: #303139; color: #ffffff;")
            self.list_btn.setStyleSheet("border: none; border-radius: 6px; font-size: 14px; background: transparent; color: #b0b3c2;")
            self.views_stack.setCurrentIndex(0)
        else:
            self.grid_btn.setStyleSheet("border: none; border-radius: 6px; font-size: 15px; background: transparent; color: #b0b3c2;")
            self.list_btn.setStyleSheet("border: none; border-radius: 6px; font-size: 14px; background-color: #303139; color: #ffffff;")
            self.views_stack.setCurrentIndex(1)

    def set_search_query(self, query: str):
        """Called when user types in the top master search bar."""
        self._search_query = query.strip()
        self.refresh_display()

    def _on_sort_changed(self):
        val = self.sort_combo.currentData()
        if val:
            parts = val.split("|")
            self._sort_field = parts[0]
            self._sort_order = parts[1]
        self.refresh_display()

    def _on_filter_pill_clicked(self, filter_val: str):
        self.activate_filter(filter_val)

    def activate_filter(self, filter_val: str):
        self._current_filter = filter_val
        for val, btn in self.pill_buttons.items():
            btn.setProperty("active", "true" if val == filter_val else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.refresh_display()

    def _change_calendar_week(self, step):
        self._calendar_offset = self._calendar_offset + step if step else 0
        self._refresh_airing_week()

    def _refresh_airing_week(self):
        today = datetime.now().date()
        monday = today - timedelta(days=today.weekday()) + timedelta(weeks=self._calendar_offset)
        dates = [monday + timedelta(days=offset) for offset in range(14)]
        self.calendar_range.setText(f"{dates[0]:%d %b} – {dates[-1]:%d %b %Y}")
        self.calendar_range.setToolTip('Two full weeks · local time. Previous releases are saved for 12 weeks. Sync with internet to update the schedule.')
        schedule = {date: {} for date in dates}

        def add(fid, title, stamp, episode, release_id=None, season_id=None):
            if not stamp:
                return
            try:
                airing = datetime.fromtimestamp(int(stamp))
                date = airing.date()
            except (OSError, OverflowError, TypeError, ValueError):
                return
            if date in schedule:
                schedule[date][(fid, release_id, episode)] = (title, airing.strftime("%H:%M"), season_id, stamp)

        with closing(db.get_connection()) as conn:
            for row in conn.execute(
                "SELECT franchise_id, title_display, next_airing_at, next_airing_ep, anilist_id, id FROM seasons WHERE next_airing_at IS NOT NULL"
            ):
                add(*tuple(row))
        for record in db.get_all_franchises():
            try:
                media = json.loads(record.get("metadata_json") or "{}") or {}
                next_episode = media.get("nextAiringEpisode") or {}
                add(record["id"], record["display_title"], next_episode.get("airingAt"), next_episode.get("episode"), record.get("anilist_id"))
            except (AttributeError, TypeError, ValueError):
                continue

        # Map provider releases only to currently linked local anime/seasons.
        # Cached history survives the provider's nextAiringEpisode moving on.
        from app.core.release_calendar import saved
        owners = {}
        for record in db.get_all_franchises():
            if record.get('anilist_id'):
                owners.setdefault(record['anilist_id'], (record['id'], record['display_title'], None))
        with closing(db.get_connection()) as conn:
            for row in conn.execute('SELECT anilist_id, franchise_id, title_display, id FROM seasons WHERE anilist_id IS NOT NULL'):
                owners[row[0]] = (row[1], row[2], row[3])
        for release in saved():
            owner = owners.get(release.get('mediaId'))
            if owner:
                fid, title, sid = owner
                add(fid, title, release.get('airingAt'), release.get('episode'), release.get('mediaId'), sid)

        signature = (today, tuple((date, tuple(schedule[date].items())) for date in dates))
        if signature == self._airing_week_signature:
            return
        self._airing_week_signature = signature
        while self.airing_week.count():
            self.airing_week.takeAt(0).widget().deleteLater()

        covers = {record["id"]: record.get("cover_filename") for record in db.get_all_franchises()}
        kanji = "\u6708\u706b\u6c34\u6728\u91d1\u571f\u65e5"
        for index, date in enumerate(dates):
            entries = schedule[date]
            preview_entries = [
                {"fid": fid, "release_id": release_id, "season_id": sid, "title": title, "episode": episode, "time": time, "cover": covers.get(fid), "airing_at": stamp}
                for (fid, release_id, episode), (title, time, sid, stamp) in entries.items()
            ]
            preview_entries.sort(key=lambda entry: (entry.get("airing_at") or 0, entry["title"]))
            day = AiringDay(date, date == today, kanji[date.weekday()], preview_entries)
            day.selected.connect(self.airing_clicked.emit)
            self.airing_week.addWidget(day, index // 7, index % 7, Qt.AlignTop)
            self.airing_week.setColumnStretch(index % 7, 1)

    def refresh(self):
        """Full refresh of stats and cards."""
        from app.core.library_index import LibraryIndex
        snapshot=db.current_refresh_view()
        self._library_index = snapshot.get('library_index') if snapshot else None
        if self._library_index is None:self._library_index=LibraryIndex()
        self.hero_card.refresh()
        self._refresh_airing_week()
        while self.release_layout.count():
            item = self.release_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        releases = [f for f in self._library_index.groups if f.get("has_new_update")]
        for f in releases:
            card = PosterCard(f)
            card.clicked.connect(self.card_clicked.emit)
            self.release_layout.addWidget(card)
        self.release_scroll.setVisible(bool(releases))
        self.release_heading_widget.setVisible(bool(releases))

        stats = db.get_library_stats()
        total_anime = len(self._library_index.groups)
        total_bytes = stats.get("total_size_bytes", 0)

        if total_bytes >= 1024 ** 4:
            size_str = f"{total_bytes / (1024 ** 4):.2f} TB"
        elif total_bytes >= 1024 ** 3:
            size_str = f"{total_bytes / (1024 ** 3):.1f} GB"
        else:
            size_str = f"{total_bytes / (1024 ** 2):.0f} MB"

        self.stats_subtitle.setText(f"{total_anime} anime · {size_str} on disk")
        self.refresh_display()

    def refresh_display(self):
        """Fetch filtered franchises and route to either Grid or Compact view."""
        storage_state = None
        if self._current_filter in ("ON_DISK", "PARTIALLY_ON_DISK", "WATCHED_REMOVED", "RECLAIM"):
            storage_state = self._current_filter

        if self._library_index is None:
            from app.core.library_index import LibraryIndex
            self._library_index = LibraryIndex()
        franchises = self._library_index.select(
            sort_by=self._sort_field,
            sort_order=self._sort_order,
            search=self._search_query,
            storage_state=storage_state,
            watch_status=self._current_filter if self._current_filter in ("WATCHING", "PLAN_TO_WATCH", "DROPPED", "WATCHED") else None,
        )

        if self._current_filter == "UPDATE":
            franchises = [f for f in franchises if f.get("has_new_update")]
        elif self._current_filter == 'REVIEW':
            franchises = [f for f in franchises if any(self._library_index.by_id[mid].get('needs_review') for mid in f['series_member_ids'])]

        if self.view_mode == "grid":
            self._render_grid(franchises)
        else:
            self._render_compact(franchises)

    def _render_grid(self, franchises: List[Dict]):
        self._display_franchises = franchises
        signature = [(record["id"], _poster_key(record)) for record in franchises]
        if signature != self._grid_signature:
            self.grid_container.setUpdatesEnabled(False)
            self.grid_container.setMinimumHeight(0)
            while self.grid_layout.count():
                item = self.grid_layout.takeAt(0)
                if item.widget():
                    item.widget().hide()
                    if not isinstance(item.widget(), PosterCard):
                        item.widget().deleteLater()
            self._cards = []
            for record in franchises:
                fingerprint = _poster_key(record)
                cached = self._card_pool.get(record["id"])
                if cached is None or cached[0] != fingerprint:
                    if cached is not None:
                        cached[1].deleteLater()
                    card = PosterCard(record, self.grid_container)
                    card.clicked.connect(self.card_clicked.emit)
                    self._card_pool[record["id"]] = (fingerprint, card)
                    if not valid_image(record.get("cover_filename")):
                        artwork_loader().request(record)
                else:
                    card = cached[1]
                self._cards.append(card)
                card.show()
            valid_ids = set(self._library_index.by_id) if self._library_index else {record["id"] for record in franchises}
            for fid in list(self._card_pool):
                if fid not in valid_ids:
                    self._card_pool.pop(fid)[1].deleteLater()
            if not franchises:
                empty = QLabel("No anime found matching your selection.")
                empty.setAlignment(Qt.AlignCenter)
                self.grid_layout.addWidget(empty, 0, 0)
            self._grid_signature = signature
            self._grid_columns = 0
            self.grid_container.setUpdatesEnabled(True)
        self._reflow_grid()

    def _reflow_grid(self):
        if not self._cards or self.view_mode != "grid":
            if not self._cards:
                self.views_stack.setMinimumHeight(100)
            return
        margins = self.page_scroll.widget().layout().contentsMargins()
        available = max(1,self.page_scroll.viewport().width() - margins.left() - margins.right())
        gap = self.grid_layout.horizontalSpacing()
        cols = max(1, (available + gap) // (PosterCard.CARD_WIDTH + gap))
        width, extra = divmod(max(1,available - gap * (cols - 1)),cols)
        for idx,card in enumerate(self._cards):
            card.set_card_width(width + (1 if idx % cols < extra else 0))
        if cols != self._grid_columns:
            self.grid_container.setUpdatesEnabled(False)
            while self.grid_layout.count():
                self.grid_layout.takeAt(0)
            for idx, card in enumerate(self._cards):
                self.grid_layout.addWidget(card, idx // cols, idx % cols)
            self._grid_columns = cols
            self.grid_container.setUpdatesEnabled(True)
        rows = (len(self._cards) + cols - 1) // cols
        height = rows * max(card.sizeHint().height() + 20 for card in self._cards) + 30
        self.grid_container.setMinimumHeight(height)
        self.views_stack.setMinimumHeight(height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Other library controls may have a wider minimum size; keep the calendar
        # inside the visible viewport rather than clipping its rightmost days.
        self.calendar_panel.setFixedWidth(max(400, self.width() - 70))
        self._resize_timer.start()

    def _artwork_changed(self, fid):
        franchise = db.get_franchise(fid)
        if not franchise:
            return
        if self._library_index is not None:
            self._library_index = None
        for card in self._cards:
            if card.franchise_id == fid:
                card.franchise_data = franchise
                card.poster_label.setPixmap(card._create_poster_pixmap())
        for i in range(self.release_layout.count()):
            card = self.release_layout.itemAt(i).widget()
            if isinstance(card, PosterCard) and card.franchise_id == fid:
                card.franchise_data = franchise
                card.poster_label.setPixmap(card._create_poster_pixmap())

    def _render_compact(self, franchises: List[Dict]):
        all_records = self._library_index.groups if self._library_index else franchises
        signature = [(record["id"], _poster_key(record)) for record in all_records]
        self.compact_table.setUpdatesEnabled(False)
        if signature != getattr(self, "_compact_signature", None):
            self._build_compact_rows(all_records)
            for row, record in enumerate(all_records):
                item = QTableWidgetItem("")
                item.setData(Qt.UserRole, record["id"])
                item.setForeground(QColor(Qt.transparent))
                self.compact_table.setItem(row, 0, item)
            self._compact_signature = signature
        order = {record["id"]: rank for rank, record in enumerate(franchises)}
        for row in range(self.compact_table.rowCount()):
            item = self.compact_table.item(row, 0)
            fid = item.data(Qt.UserRole)
            item.setText(f"{order.get(fid, len(order)):09d}")
            self.compact_table.setRowHidden(row, fid not in order)
            checkbox = self.compact_table.cellWidget(row, 0).findChild(QCheckBox)
            checkbox.blockSignals(True)
            checkbox.setChecked(fid in self.selected_fids)
            checkbox.blockSignals(False)
        self.compact_table.sortItems(0, Qt.AscendingOrder)
        self.compact_table.setUpdatesEnabled(True)

    def _build_compact_rows(self, franchises: List[Dict]):
        self.views_stack.setMinimumHeight(500)
        self.compact_table.setRowCount(0)
        self.compact_table.setRowCount(len(franchises))
        self.compact_table.setRowHeight(0, 56)

        for row_idx, f in enumerate(franchises):
            fid = f["id"]
            self.compact_table.setRowHeight(row_idx, 56)

            # 0. Selection Checkbox
            cb_cell = QWidget()
            cb_layout = QHBoxLayout(cb_cell)
            cb_layout.setContentsMargins(6, 0, 0, 0)
            cb = QCheckBox()
            cb.setChecked(fid in self.selected_fids)
            cb.stateChanged.connect(lambda state, i=fid: self._on_item_checked(i, bool(state)))
            cb_layout.addWidget(cb)
            self.compact_table.setCellWidget(row_idx, 0, cb_cell)

            # 1. Mini Thumbnail
            thumb_cell = QLabel()
            thumb_cell.setFixedSize(36, 48)
            thumb_cell.setStyleSheet("background-color: #1e293b; border-radius: 4px;")
            thumb_cell.setAlignment(Qt.AlignCenter)

            cover = f.get("cover_filename")
            cover_path = COVERS_DIR / cover if cover else None
            if cover_path and refresh_image_exists(cover_path):
                pix = refresh_pixmap(cover_path)
                if not pix.isNull():
                    thumb_cell.setPixmap(pix.scaled(36, 48, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            else:
                thumb_cell.setText("✦")
                thumb_cell.setStyleSheet("background-color: #303139; color: #8c6cff; font-weight: bold; border-radius: 4px;")
            self.compact_table.setCellWidget(row_idx, 1, thumb_cell)

            # 2. Title & Subtitle Info
            title_widget = QWidget()
            t_layout = QVBoxLayout(title_widget)
            t_layout.setContentsMargins(8, 6, 8, 6)
            t_layout.setSpacing(2)

            t_main = QLabel(f.get("display_title", "Unknown"))
            t_main.setStyleSheet("font-size: 13px; font-weight: 700; color: #f3f4f6;")
            t_layout.addWidget(t_main)

            sub_str = f.get("title_romaji") or f.get("title_native") or ""
            if sub_str and sub_str != f.get("display_title"):
                t_sub = QLabel(sub_str)
                t_sub.setStyleSheet("font-size: 11px; color: #b0b3c2;")
                t_layout.addWidget(t_sub)
            self.compact_table.setCellWidget(row_idx, 2, title_widget)

            # 3. Status Pill
            st = f.get("storage_state", "ON_DISK")
            st_lbl = QLabel()
            if st == "ON_DISK":
                st_lbl.setText("● On disk")
                st_lbl.setStyleSheet("color: #35cf91; font-size: 11px; font-weight: 600; padding: 4px 8px;")
            elif st == "WATCHED_REMOVED":
                st_lbl.setText("● Removed")
                st_lbl.setStyleSheet("color: #738097; font-size: 11px; font-weight: 600; padding: 4px 8px;")
            else:
                st_lbl.setText("● Partial")
                st_lbl.setStyleSheet("color: #f2b94b; font-size: 11px; font-weight: 600; padding: 4px 8px;")
            self.compact_table.setCellWidget(row_idx, 3, st_lbl)

            # 4. Size
            sz = f.get("total_size_bytes", 0) or 0
            if sz >= 1024 ** 3:
                sz_str = f"{sz / (1024 ** 3):.1f} GB"
            elif sz > 0:
                sz_str = f"{sz / (1024 ** 2):.0f} MB"
            else:
                sz_str = "—"
            sz_item = QTableWidgetItem(sz_str)
            sz_item.setForeground(QColor("#b0b3c2"))
            self.compact_table.setItem(row_idx, 4, sz_item)

            # 5. Rating
            rat = f.get("user_rating")
            rat_str = f"★ {rat}/10" if rat else "—"
            rat_item = QTableWidgetItem(rat_str)
            rat_item.setForeground(QColor("#f2b94b" if rat else "#898d9f"))
            self.compact_table.setItem(row_idx, 5, rat_item)

            # 6. Action: Details & Play
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 4, 8, 4)
            act_layout.setSpacing(6)

            det_btn = QPushButton("Details")
            det_btn.setFixedHeight(28)
            det_btn.setCursor(Qt.PointingHandCursor)
            det_btn.setStyleSheet("background-color: #1e2230; color: #f3f4f6; border: 1px solid #383a44; border-radius: 6px; font-size: 11px;")
            det_btn.clicked.connect(lambda checked=False, i=fid: self.card_clicked.emit(i))
            act_layout.addWidget(det_btn)

            self.compact_table.setCellWidget(row_idx, 6, act_widget)

    def _on_item_checked(self, fid: int, checked: bool):
        if checked:
            self.selected_fids.add(fid)
        else:
            self.selected_fids.discard(fid)
        self._update_batch_bar()

    def _update_batch_bar(self):
        count = len(self.selected_fids)
        self.batch_bar.setVisible(count > 0)
        self.batch_count_lbl.setText(f"{count} anime selected")

    def _clear_selection(self):
        self.selected_fids.clear()
        self._update_batch_bar()
        self.refresh_display()

    def _batch_mark_watched(self):
        for fid in self.selected_fids:
            db.update_franchise_field(fid, "watch_status", "WATCHED")
        self._clear_selection()
        self.refresh()
        self.data_changed.emit()

    def _batch_mark_watching(self):
        for fid in self.selected_fids:
            db.update_franchise_field(fid, "watch_status", "WATCHING")
        self._clear_selection()
        self.refresh()
        self.data_changed.emit()

    def _batch_delete_files(self):
        if not self.selected_fids:
            return
        QMessageBox.information(
            self,
            "Safe Deletion",
            f"To safely delete files for {len(self.selected_fids)} titles, please open Details for each title to review individual seasons."
        )
