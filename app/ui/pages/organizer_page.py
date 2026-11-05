from app.ui.components.design import MotifHeader, ElidedLabel
from app.ui.navigation import navigate
"""
Organizer Page — Replicating the redesigned AnimeVault Organizer UI:
- Kanji watermark "整理" in top-right
- Library roots card with watched folders, removal, add root, and drop zone
- Detection rules card with modern toggle switches
- Organization preview card with tabs: Needs organization, Already organized, All
- Table of anime items with checkboxes, folder paths, file counts, proposed season badges, and Review actions
- Review drawer/modal allowing file-by-file inspection and per-anime organizing
- Safe background batch organizing with progress reporting and SQLite synchronization
"""

import os
from PyQt5.QtCore import QTimer
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QFileDialog, QTableWidget, QTableWidgetItem,
    QProgressBar, QMessageBox, QHeaderView, QCheckBox, QLineEdit,
    QDialog, QComboBox, QAbstractItemView, QTabWidget, QSizePolicy,
)
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QPen
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize

from app import db
from app.core.organizer import (
    inspect_all_library,
    find_missing_library_files,
    inspect_anime_folder,
    execute_organize_anime,
    execute_organize_batch,
    DEFAULT_RULES,
)


class ToggleSwitch(QCheckBox):
    """Modern iOS/Figma style toggle switch matching the mockup."""
    def __init__(self, checked=True, parent=None):
        super().__init__(parent)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(44, 24)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        checked = self.isChecked()

        # Background track
        bg_color = QColor("#8e75ff") if checked else QColor("#222638")
        painter.setBrush(bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 12, 12)

        # Thumb
        painter.setBrush(QColor("#0b0c10" if checked else "#8e94a8"))
        thumb_x = rect.width() - 20 if checked else 4
        painter.drawEllipse(thumb_x, 4, 16, 16)
        painter.end()


class OrganizerWorker(QThread):
    """Background worker for batch file organizing."""
    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, items, rules):
        super().__init__()
        self.items = items
        self.rules = rules

    def run(self):
        try:
            res = execute_organize_batch(
                self.items,
                rules=self.rules,
                progress_callback=lambda name, cur, tot: self.progress.emit(name, cur, tot),
            )
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))


class ScannerWorker(QThread):
    """Background worker for library scanning."""
    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    stopped = pyqtSignal()

    def __init__(self, rules, find_missing=False, repair_ids=None):
        super().__init__()
        self.rules = rules
        self.find_missing = find_missing
        self.repair_ids = repair_ids

    def _scan_progress(self, name, current, total):
        if self.isInterruptionRequested():
            raise InterruptedError("Scan cancelled for app shutdown")
        self.progress.emit(name, current, total)

    def run(self):
        try:
            if self.repair_ids is not None:
                from app.core.identity import approve_repair
                failures, repaired = [], 0
                for candidate_id in self.repair_ids:
                    if self.isInterruptionRequested():
                        break
                    try:
                        approve_repair(candidate_id)
                        repaired += 1
                    except (OSError, ValueError) as error:
                        failures.append(str(error))
                self.finished.emit({'recovery': {'recovered': repaired, 'unresolved': len(self.repair_ids) - repaired,
                                                'unavailable': 0, 'paths_repaired': 0, 'operation_errors': failures}})
                return
            if self.find_missing:
                self.finished.emit({"recovery": find_missing_library_files(self.isInterruptionRequested)})
                return
            from app.ui.organizer_cache import configuration, save_preview
            config = configuration(self.rules)
            res = inspect_all_library(
                rules=self.rules,
                progress_callback=self._scan_progress,
            )
            if not self.isInterruptionRequested():
                res['_configuration'] = config
                save_preview(res, config)
                self.finished.emit(res)
        except InterruptedError:
            self.stopped.emit()
        except Exception as e:
            self.error.emit(str(e))



class OrganizerReviewDialog(QDialog):
    """Review Drawer/Dialog for inspecting individual anime proposed moves."""
    def __init__(self, anime_item: Dict[str, Any], rules: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.anime_item = anime_item
        self.rules = rules
        self.setWindowTitle(f"Review Organization — {anime_item.get('anime_name')}")
        self.setMinimumSize(850, 560)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        # Header
        top_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        t_lbl = QLabel(self.anime_item.get("anime_name", "Anime"))
        t_lbl.setStyleSheet("font-size: 20px; font-weight: 700; color: #f3f4f6;")
        title_box.addWidget(t_lbl)

        sub_lbl = QLabel(self.anime_item.get("status_reason", ""))
        sub_lbl.setStyleSheet("font-size: 12px; color: #b0b3c2;")
        title_box.addWidget(sub_lbl)
        top_row.addLayout(title_box)

        top_row.addStretch()

        from app.ui.components.close_button import CloseButton
        close_btn = CloseButton(self)
        close_btn.setFixedSize(44, 44)
        close_btn.setStyleSheet('QPushButton#close_icon_button { min-width: 44px; max-width: 44px; min-height: 44px; max-height: 44px; padding: 0; border: none; }')
        close_btn.setAccessibleName('Close organization review')
        close_btn.setToolTip('Close review')
        close_btn.clicked.connect(self.reject)
        top_row.addWidget(close_btn)
        layout.addLayout(top_row)

        # Folder path bar
        path_frame = QFrame()
        path_frame.setObjectName("organizer_path_frame")

        path_frame.setStyleSheet("""
            #organizer_path_frame {
                background-color: #111219;
                border: 1px solid #303139;
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        pf_layout = QHBoxLayout(path_frame)
        pf_layout.setContentsMargins(4, 2, 4, 2)
        pf_lbl = QLabel(f"📁 Folder: {self.anime_item.get('folder_path')}")
        pf_lbl.setStyleSheet("color: #a78bfa; font-size: 12px; font-weight: 600;")
        pf_layout.addWidget(pf_lbl)
        layout.addWidget(path_frame)

        # Table of files
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.verticalHeader().setDefaultSectionSize(64)
        self.table.setHorizontalHeaderLabels(["Include", "Source Filename", "Proposed Target", "Size"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setFixedHeight(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #14151c;
                border: 1px solid #303139;
                border-radius: 10px;
                gridline-color: transparent;
            }
            QTableWidget::item {
                padding: 6px 10px;
                border-bottom: 1px solid #1d1f29;
                color: #f3f4f6;
            }
        """)

        moves = self.anime_item.get("moves", [])
        self.table.setRowCount(len(moves))
        self.checkboxes = []

        for row_idx, m in enumerate(moves):
            cb = QCheckBox()
            cb.setChecked(not m.get("already_in_place", False))
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.setContentsMargins(10, 0, 0, 0)
            cb_layout.addWidget(cb)
            self.table.setCellWidget(row_idx, 0, cb_widget)
            self.checkboxes.append((cb, m))

            source_item = QTableWidgetItem(Path(m["source"]).name)
            self.table.setItem(row_idx, 1, source_item)

            target_rel = os.path.relpath(m["target"], self.anime_item["folder_path"])
            target_item = QTableWidgetItem(target_rel)
            if m.get("already_in_place"):
                target_item.setForeground(QColor("#22c55e"))
            else:
                target_item.setForeground(QColor("#a78bfa"))
            self.table.setItem(row_idx, 2, target_item)

            size_mb = m["size_bytes"] / (1024 * 1024)
            size_item = QTableWidgetItem(f"{size_mb:.1f} MB")
            size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row_idx, 3, size_item)

        layout.addWidget(self.table, 1)

        # Bottom actions
        bot_layout = QHBoxLayout()
        bot_layout.setSpacing(12)

        summary_lbl = QLabel(f"{len(moves)} files to organize")
        summary_lbl.setStyleSheet("color: #b0b3c2; font-size: 13px;")
        bot_layout.addWidget(summary_lbl)

        bot_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        bot_layout.addWidget(cancel_btn)

        self.organize_this_btn = QPushButton("⚡ Organize This Anime Now")
        self.organize_this_btn.setProperty("accent", True)
        self.organize_this_btn.setFixedHeight(38)
        self.organize_this_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #df2545, stop:1 #df2545);
                color: #ffffff;
                font-weight: 600;
                border-radius: 8px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ef3b59, stop:1 #fb7185);
            }
        """)
        self.organize_this_btn.clicked.connect(self._execute_this)
        bot_layout.addWidget(self.organize_this_btn)

        layout.addLayout(bot_layout)

    def _execute_this(self):
        # Filter moves by checked checkboxes
        selected_moves = [m for cb, m in self.checkboxes if cb.isChecked()]
        if not selected_moves:
            QMessageBox.information(self, "No Files", "No files selected to move.")
            return

        item_copy = dict(self.anime_item)
        item_copy["moves"] = selected_moves

        self.organize_this_btn.setEnabled(False)
        self.organize_this_btn.setText("Moving files...")

        self._organize_worker = OrganizerWorker([item_copy], self.rules)
        self._organize_worker.finished.connect(self._organization_finished)
        self._organize_worker.error.connect(self._organization_failed)
        self._organize_worker.start()

    def _organization_finished(self, result):
        from app.core.organizer import organization_summary
        if result.get("errors"):
            QMessageBox.warning(self, "Organization needs attention", organization_summary(result))
        else:
            QMessageBox.information(self, "Organization result", organization_summary(result))
        self.accept()

    def _organization_failed(self, message):
        QMessageBox.critical(self, "Organization failed", message)
        self.organize_this_btn.setEnabled(True)
        self.organize_this_btn.setText("Organize this anime")

    def reject(self):
        worker = getattr(self, "_organize_worker", None)
        if worker and worker.isRunning():
            return
        super().reject()


class OrganizerPage(QWidget):
    """Flawless Auto-Folder & Season Organizer Page matching the redesigned UI mockups."""
    data_changed = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = dict(DEFAULT_RULES)
        from app import preferences as prefs
        self._rules["treat_direct_as_season_1"] = prefs.enabled("flat_detection")
        self._rules["organize_without_confirmation"] = not prefs.enabled("preview_moves")
        self._data = {"unorganized": [], "organized": [], "all": []}
        self._current_tab = "unorganized"
        self._worker = None
        self._selected_items = set()
        self._preview_stale = False

        self._setup_ui()
        self._load_library_roots()
        from app.ui.organizer_cache import load_preview
        cached = load_preview(self._rules)
        if cached:
            self._on_scan_finished(cached[0], cached=True)
            if not cached[1]:
                self._mark_preview_stale('Saved preview needs updating — click Scan now')
        else:
            self.top_status_badge.setText('Ready — click Scan now')
        from app.ui.organizer_cache import configuration
        self._shown_config = configuration(self._rules)

    def showEvent(self, event):
        super().showEvent(event)
        # Reading configuration is cheap; entering this page never walks media.
        from app.ui.organizer_cache import configuration
        current = configuration(self._rules)
        if current != self._shown_config:
            self._load_library_roots()
            self._mark_preview_stale('Library configuration changed — click Scan now')
            self._shown_config = current

    def _setup_ui(self):
        from app.ui.pages.merge_page import MergePage
        shell = QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)
        self.organizer_tabs = QTabWidget()
        self.organizer_tabs.setObjectName("organizer_tabs")
        self.organizer_tabs.tabBar().setExpanding(False)
        self.organizer_tabs.tabBar().setDrawBase(False)
        shell.addWidget(self.organizer_tabs)
        self.season_tab = QWidget()
        self.organizer_tabs.addTab(self.season_tab, "Organize seasons and folders")
        self.merge_page = MergePage(self)
        self.organizer_tabs.addTab(self.merge_page, "Merge all anime into one root library")
        self.merge_page.data_changed.connect(self.data_changed.emit)
        self.merge_page.busy_changed.connect(self._merge_busy_changed)
        self.organizer_tabs.currentChanged.connect(self._organizer_tab_changed)
        main_layout = QVBoxLayout(self.season_tab)
        main_layout.setContentsMargins(32, 16, 32, 24)
        main_layout.setSpacing(20)

        # -------------------------------------------------------------------
        # 1. Top Header with Japanese Watermark Accent
        # -------------------------------------------------------------------
        header_frame = MotifHeader("\u6574\u7406")
        header_frame.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        title = QLabel("Season organizer")
        title.setObjectName("heading")
        title.setStyleSheet("font-size: 26px; font-weight: 700; color: #f3f4f6;")
        title_box.addWidget(title)

        desc = QLabel("Scan folders, detect seasons, preview changes and organize files safely")
        desc.setObjectName("subheading")
        desc.setStyleSheet("font-size: 13px; color: #b0b3c2;")
        title_box.addWidget(desc)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Ready to scan status pill
        self.top_status_badge = QLabel("Ready to scan")
        self.top_status_badge.setStyleSheet("""
            background-color: rgba(34, 197, 94, 0.12);
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.25);
            border-radius: 13px;
            padding: 0 12px;
            font-size: 12px;
            font-weight: 600;
        """)
        duplicates = QPushButton("Review duplicate files")
        duplicates.clicked.connect(self._review_duplicates)
        self.duplicates_btn = duplicates
        self.top_status_badge.setFixedHeight(26)
        self.top_status_badge.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        header_layout.addWidget(self.top_status_badge)

        main_layout.addWidget(header_frame)

        # -------------------------------------------------------------------
        # 2. Main Two-Column Layout (Left: Roots + Rules, Right: Preview Table)
        # -------------------------------------------------------------------
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Left Column (approx 340px)
        left_content = QWidget()
        left_col = QVBoxLayout(left_content)
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(16)

        # Card 1: Library Roots
        left_col.addWidget(self._create_roots_card())

        # Card 2: Detection Rules
        left_col.addWidget(self._create_rules_card())

        left_col.addStretch()
        self.controls_scroll = QScrollArea()
        self.controls_scroll.setWidgetResizable(True)
        self.controls_scroll.setFrameShape(QFrame.NoFrame)
        self.controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.controls_scroll.setMinimumWidth(290)
        self.controls_scroll.setWidget(left_content)
        content_layout.addWidget(self.controls_scroll, 5)

        # Right Column: Organization Preview Card
        self.preview_card = self._create_preview_card()
        self.preview_card.setMinimumHeight(540)
        self.preview_card.setMaximumHeight(620)
        content_layout.addWidget(self.preview_card, 7, Qt.AlignTop)

        main_layout.addLayout(content_layout, 1)

    def _review_duplicates(self):
        if self.merge_page.busy() or any(
            worker and worker.isRunning()
            for worker in (self._worker, getattr(self, "_batch_worker", None))
        ):
            return
        if getattr(self, "_duplicate_page", None) is not None:
            page = self._duplicate_page
            if page._busy():
                return
        from app.ui.pages.duplicate_page import DuplicatePage
        page = DuplicatePage(self)
        self._duplicate_page = page
        page.data_changed.connect(self.data_changed.emit)
        page.busy_changed.connect(self._duplicates_busy)
        navigate(page)

    def _duplicates_busy(self, busy):
        self._merge_busy_changed(busy)
        self.merge_page.setEnabled(not busy)

    def _merge_busy_changed(self, busy):
        for control in (self.organize_btn, self.scan_btn, self.find_missing_btn, self.table):
            control.setEnabled(not busy)
        if not busy:
            self._render_table()

    def _organizer_tab_changed(self, index):
        if index == 1 and not self.merge_page.busy() and self.merge_page.plan is None:
            self.merge_page.load_roots()

    # -----------------------------------------------------------------------
    # Left Card 1: Library Roots
    # -----------------------------------------------------------------------
    def _create_roots_card(self) -> QFrame:
        card = QFrame()
        card.setMinimumWidth(270)
        card.setObjectName("organizer_card")

        card.setStyleSheet("""
            #organizer_card {
                background-color: #14151c;
                border: 1px solid #303139;
                border-radius: 14px;
                padding: 0;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Library roots")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #f3f4f6; background: transparent;")
        layout.addWidget(title)

        sub = QLabel("Folders the organizer will scan.")
        sub.setStyleSheet("font-size: 12px; color: #b0b3c2; background: transparent;")
        layout.addWidget(sub)

        # Container for list of roots
        self.roots_list_layout = QVBoxLayout()
        self.roots_list_layout.setSpacing(8)
        layout.addLayout(self.roots_list_layout)

        # "+ Add library root" button
        add_root_btn = QPushButton("+ Add library root")
        add_root_btn.setCursor(Qt.PointingHandCursor)
        add_root_btn.setStyleSheet("""
            QPushButton {
                background-color: #1d1f29;
                color: #f3f4f6;
                border: 1px solid #383a44;
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #222638;
                border-color: #a78bfa;
            }
        """)
        add_root_btn.clicked.connect(self._add_library_root)
        layout.addWidget(add_root_btn, 0, Qt.AlignLeft)

        # Dashed Drop Zone
        drop_box = QFrame()
        drop_box.setFixedHeight(88)
        drop_box.setObjectName("organizer_drop_box")

        drop_box.setStyleSheet("""
            #organizer_drop_box {
                background-color: rgba(26, 31, 44, 0.4);
                border: 1px dashed #8e94a8;
                border-radius: 14px;
            }
        """)
        d_layout = QVBoxLayout(drop_box)
        d_layout.setAlignment(Qt.AlignCenter)
        d_lbl1 = QLabel("Drop anime folders here")
        d_lbl1.setStyleSheet("color: #b0b3c2; font-size: 11px; font-weight: 600; background: transparent;")
        d_lbl1.setAlignment(Qt.AlignCenter)
        d_lbl2 = QLabel("or choose Add library root")
        d_lbl2.setStyleSheet("color: #898d9f; font-size: 10px; background: transparent;")
        d_lbl2.setAlignment(Qt.AlignCenter)
        d_layout.addWidget(d_lbl1)
        d_layout.addWidget(d_lbl2)
        layout.addWidget(drop_box)

        # Scan now / Stop buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.scan_btn = QPushButton("Scan now")
        self.scan_btn.setCursor(Qt.PointingHandCursor)
        self.scan_btn.setFixedHeight(36)
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #df2545, stop:1 #df2545);
                color: #ffffff;
                font-weight: 600;
                font-size: 12px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ef3b59, stop:1 #fb7185);
            }
        """)
        self.scan_btn.clicked.connect(self._start_scan)
        self.scan_btn.setMinimumWidth(100)
        btn_row.addWidget(self.scan_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #1d1f29;
                color: #b0b3c2;
                border: 1px solid #383a44;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #222638;
                color: #f3f4f6;
            }
        """)
        self.stop_btn.clicked.connect(self._stop_scan)
        btn_row.addWidget(self.stop_btn)
        btn_row.addStretch()

        layout.addLayout(btn_row)
        self.find_missing_btn = QPushButton("Find missing files")
        self.find_missing_btn.setMinimumHeight(36)
        self.find_missing_btn.setToolTip("Search configured roots and review verified repair candidates. Filenames alone never relink history.")
        self.find_missing_btn.clicked.connect(lambda: self._start_scan(find_missing=True))
        extra_actions = QVBoxLayout()
        extra_actions.addWidget(self.find_missing_btn, 0, Qt.AlignLeft)
        extra_actions.addWidget(self.duplicates_btn, 0, Qt.AlignLeft)
        layout.addLayout(extra_actions)
        return card

    # -----------------------------------------------------------------------
    # Left Card 2: Detection Rules
    # -----------------------------------------------------------------------
    def _create_rules_card(self) -> QFrame:
        card = QFrame()
        card.setMinimumWidth(270)
        card.setObjectName("organizer_card")

        card.setStyleSheet("""
            #organizer_card {
                background-color: #14151c;
                border: 1px solid #303139;
                border-radius: 14px;
                padding: 0;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Detection rules")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #f3f4f6; background: transparent;")
        layout.addWidget(title)

        rules_defs = [
            ("treat_direct_as_season_1", "Treat direct video files as Season 1", "Files inside the root folder", True),
            ("detect_season_names", "Detect season names", "S01, Season 2, Part II, Roman numerals", True),
            ("detect_episode_numbers", "Detect episode numbers", "E01, - 01, Ep 12", True),
            ("keep_subtitles_fonts", "Keep subtitles and fonts", "Moved together with their episodes", True),
            ("organize_without_confirmation", "Organize without confirmation", "Off keeps a preview before any file moves", False),
        ]

        self.rule_switches = {}
        for key, name, hint, default in rules_defs:
            row = QHBoxLayout()
            row.setSpacing(10)

            t_box = QVBoxLayout()
            t_box.setSpacing(2)
            n_lbl = QLabel(name)
            n_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #f3f4f6; background: transparent;")
            h_lbl = QLabel(hint)
            h_lbl.setStyleSheet("font-size: 10px; color: #b0b3c2; background: transparent;")
            t_box.addWidget(n_lbl)
            t_box.addWidget(h_lbl)
            row.addLayout(t_box, 1)

            sw = ToggleSwitch(checked=self._rules.get(key, default))
            sw.setAccessibleName(name)
            sw.setAccessibleDescription(hint)
            sw.stateChanged.connect(lambda state, k=key: self._on_rule_toggled(k))
            self.rule_switches[key] = sw
            row.addWidget(sw)

            layout.addLayout(row)
            divider = QFrame()
            divider.setFrameShape(QFrame.HLine)
            divider.setStyleSheet("background: #2a2e3a; max-height: 1px; border: none;")
            layout.addWidget(divider)

        return card

    # -----------------------------------------------------------------------
    # Right Column: Organization Preview Card with Tabs
    # -----------------------------------------------------------------------
    def _create_preview_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("organizer_card")

        card.setStyleSheet("""
            #organizer_card {
                background-color: #14151c;
                border: 1px solid #303139;
                border-radius: 14px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)

        # Card Title
        top_row = QHBoxLayout()
        t_box = QVBoxLayout()
        t_box.setSpacing(2)
        p_title = QLabel("Organization preview")
        p_title.setStyleSheet("font-size: 17px; font-weight: 700; color: #f3f4f6; background: transparent;")
        p_sub = QLabel("Review proposed season assignments. No files move until you confirm.")
        p_sub.setStyleSheet("font-size: 12px; color: #b0b3c2; background: transparent;")
        t_box.addWidget(p_title)
        t_box.addWidget(p_sub)
        top_row.addLayout(t_box)

        top_row.addStretch()

        # Search filter within table
        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText("Filter anime...")
        self.search_filter.setMinimumWidth(120)
        self.search_filter.setMaximumWidth(220)
        self.search_filter.setStyleSheet("""
            QLineEdit {
                background-color: #1d1f29;
                border: 1px solid #383a44;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                color: #f3f4f6;
            }
        """)
        self.search_filter.textChanged.connect(self._render_table)


        layout.addLayout(top_row)

        # -------------------------------------------------------------------
        # Tabs Row (Needs organization, Already organized, All)
        # -------------------------------------------------------------------
        tabs_row = QHBoxLayout()
        tabs_row.setSpacing(8)

        self.tab_unorg_btn = QPushButton("Needs organization (0)")
        self.tab_org_btn = QPushButton("Already organized (0)")
        self.tab_all_btn = QPushButton("All (0)")

        for btn, tab_id in [
            (self.tab_unorg_btn, "unorganized"),
            (self.tab_org_btn, "organized"),
            (self.tab_all_btn, "all"),
        ]:
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.clicked.connect(lambda checked, t=tab_id: self._switch_tab(t))
            tabs_row.addWidget(btn)

        tabs_row.addStretch()

        # Select All checkbox
        self.select_all_cb = QCheckBox("Select all")
        self.select_all_cb.setCursor(Qt.PointingHandCursor)
        self.select_all_cb.setStyleSheet("color: #b0b3c2; font-size: 12px;")
        self.select_all_cb.stateChanged.connect(self._on_select_all_toggled)


        layout.addLayout(tabs_row)
        search_row = QHBoxLayout()
        search_row.addWidget(self.search_filter, 1)
        search_row.addStretch()
        search_row.addWidget(self.select_all_cb)
        layout.addLayout(search_row)

        # Table
        self.table = QTableWidget()
        self.table.setObjectName("organizer_preview_table")
        self.table.setMinimumHeight(306)
        self.table.setColumnCount(4)
        self.table.verticalHeader().setDefaultSectionSize(64)
        self.table.setHorizontalHeaderLabels(["Folder / Anime", "Files", "Proposed", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column, width in ((1, 76), (2, 126), (3, 116)):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.Fixed)
            self.table.setColumnWidth(column, width)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #14151c;
                border: 1px solid #303139;
                border-radius: 10px;
                gridline-color: transparent;
            }
            QTableWidget::item {
                padding: 0;
                border-bottom: 1px solid #1d1f29;
                color: #f3f4f6;
            }
            QTableWidget::item:hover {
                background-color: #1d1f29;
            }
            QTableWidget#organizer_preview_table QWidget#organizer_cell {
                background: transparent;
            }
        """)
        self.table.itemDoubleClicked.connect(self._on_table_double_clicked)
        layout.addWidget(self.table, 1)

        # Progress bar (visible during scanning/organizing)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1d1f29;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #df2545, stop:1 #df2545);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Bottom Bar: Summary stats + Organize selected files button
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(12)

        self.summary_label = QLabel("0 files · 0 folders to organize")
        self.summary_label.setStyleSheet("color: #b0b3c2; font-size: 13px; font-weight: 500;")
        bottom_bar.addWidget(self.summary_label)

        bottom_bar.addStretch()

        self.organize_btn = QPushButton("Organize selected files")
        self.organize_btn.setCursor(Qt.PointingHandCursor)
        self.organize_btn.setFixedHeight(42)
        self.organize_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #df2545, stop:1 #df2545);
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                border-radius: 10px;
                padding: 0 24px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ef3b59, stop:1 #fb7185);
            }
            QPushButton:disabled {
                background-color: #222638;
                color: #898d9f;
            }
        """)
        self.organize_btn.setEnabled(False)
        self.organize_btn.clicked.connect(self._execute_batch)
        bottom_bar.addWidget(self.organize_btn)

        layout.addLayout(bottom_bar)

        self._update_tab_styles()
        return card

    # -----------------------------------------------------------------------
    # Library Roots Management
    # -----------------------------------------------------------------------
    def _load_library_roots(self):
        # Clear existing rows in layout
        while self.roots_list_layout.count():
            item = self.roots_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        dirs = db.get_watched_directories()
        for d in dirs:
            row = QFrame()
            row.setObjectName("organizer_row")
            row.setFixedHeight(44)

            row.setStyleSheet("""
            #organizer_row {
                    background-color: #1d1f29;
                    border: 1px solid #383a44;
                    border-radius: 8px;
                    padding: 0;
                }
            """)
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(6, 4, 6, 4)
            r_layout.setSpacing(6)

            state = d.get('availability','UNSCANNED')
            suffix = ' · ' + state.title() if state in ('OFFLINE','INACCESSIBLE') else ''
            p_lbl = ElidedLabel(d["folder_path"] + suffix)
            p_lbl.setToolTip(d.get('scan_error') or d["folder_path"])
            p_lbl.setMinimumWidth(0)
            p_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            p_lbl.setStyleSheet("color: #f3f4f6; font-size: 12px; background: transparent; border: none; padding: 0;")
            r_layout.addWidget(p_lbl, 1)

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(28, 28)
            del_btn.setAccessibleName("Remove library root " + d["folder_path"])
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #b0b3c2;
                    border: none;
                    padding: 0;
                    font-size: 11px;
                }
                QPushButton:hover {
                    color: #ef4444;
                }
            """)
            del_btn.clicked.connect(lambda checked, did=d["id"]: self._remove_library_root(did))
            r_layout.addWidget(del_btn)

            self.roots_list_layout.addWidget(row)

    def _add_library_root(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Anime Library Root Directory")
        if folder:
            db.add_watched_directory(folder)
            self._load_library_roots()
            self._mark_preview_stale('Library roots changed — click Scan now')

    def _remove_library_root(self, dir_id: int):
        reply = QMessageBox.question(
            self, "Remove Root",
            "Remove this root folder from the organizer?\n"
            "Your files will not be deleted or modified.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db.remove_watched_directory(dir_id)
            self._load_library_roots()
            self._mark_preview_stale('Library roots changed — click Scan now')

    # -----------------------------------------------------------------------
    # Scanning & Tabs
    # -----------------------------------------------------------------------
    def _start_scan(self, find_missing=False, repair_ids=None):
        if self.merge_page.busy():
            return
        if self._worker and self._worker.isRunning():
            return
        if getattr(self, "_batch_worker", None) and self._batch_worker.isRunning():
            return

        self.find_missing_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.top_status_badge.setText("Looking for missing files?" if find_missing else "Scanning?")
        self.top_status_badge.setStyleSheet("""
            background-color: rgba(225, 43, 122, 0.15);
            color: #df2545;
            border: 1px solid rgba(225, 43, 122, 0.3);
            border-radius: 14px;
            padding: 4px 14px;
            font-size: 12px;
            font-weight: 600;
        """)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        # Collect current rules
        for k, sw in self.rule_switches.items():
            self._rules[k] = sw.isChecked()

        self._worker = ScannerWorker(dict(self._rules), find_missing, repair_ids)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.error.connect(self._on_scan_error)
        self._worker.stopped.connect(self._on_scan_stopped)
        self._worker.start()

    def _stop_scan(self):
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            self.top_status_badge.setText("Stopping?")

    def _on_scan_stopped(self):
        self.progress_bar.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.find_missing_btn.setEnabled(True)
        self.top_status_badge.setText("Scan stopped")

    def _on_scan_finished(self, results: dict, cached=False):
        self.find_missing_btn.setEnabled(True)
        if "recovery" in results:
            result = results["recovery"]
            self.progress_bar.setVisible(False)
            self.scan_btn.setEnabled(True)
            self.top_status_badge.setText(f"{result['recovered']} relinked ? {result['unresolved']} still missing")
            if result["unavailable"]:
                self.top_status_badge.setText(self.top_status_badge.text() + f" ? {result['unavailable']} locations unavailable")
            if result["paths_repaired"]:
                self.top_status_badge.setText(self.top_status_badge.text() + f" ? {result['paths_repaired']} paths repaired")
            if result['recovered'] or result['paths_repaired']:
                self._mark_preview_stale('Paths repaired — click Scan now to update the preview')
            self.top_status_badge.setToolTip('\n'.join(result.get('operation_errors', [])))
            if result.get('operation_errors'):
                self.top_status_badge.setText(self.top_status_badge.text() + f" · {len(result['operation_errors'])} operations need review")
            verified = [candidate for candidate in result.get('candidates', []) if candidate['evidence'] == 'SAME_FILE_SIGNATURE']
            # One target/file pairing must be unique across the entire review.
            from collections import Counter
            files = Counter(candidate['file_id'] for candidate in verified)
            targets = Counter(candidate['target'] for candidate in verified)
            verified = [candidate for candidate in verified if files[candidate['file_id']] == 1 and targets[candidate['target']] == 1]
            if result.get('candidates'):
                self.top_status_badge.setText(self.top_status_badge.text() + f" · {len(result['candidates'])} repair candidates")
            if verified:
                dialog = QMessageBox(self)
                dialog.setWindowTitle('Review path repairs')
                dialog.setText(f"{len(verified)} files have matching physical-file signatures. Apply these path repairs? Episode history and release links will be preserved.")
                dialog.setInformativeText('Review the paths under Show Details before approving. Filename-only matches remain unlinked.')
                dialog.setDetailedText('\n\n'.join(f"{c['source']}\n→ {c['target']}" for c in verified))
                dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                dialog.setDefaultButton(QMessageBox.No)
                if dialog.exec_() == QMessageBox.Yes:
                    QTimer.singleShot(0, lambda ids=[c['id'] for c in verified]: self._start_scan(repair_ids=ids))
            self.data_changed.emit()
            return
        self._preview_stale = False
        self._data = results
        self.progress_bar.setVisible(False)
        self.scan_btn.setEnabled(True)

        unorg_count = len(results.get("unorganized", []))
        org_count = len(results.get("organized", []))
        all_count = len(results.get("all", []))

        self.tab_unorg_btn.setText(f"Needs organization ({unorg_count})")
        self.tab_org_btn.setText(f"Already organized ({org_count})")
        self.tab_all_btn.setText(f"All ({all_count})")

        self.top_status_badge.setText(f"{unorg_count} need organization · {org_count} organized")
        self.top_status_badge.setStyleSheet("""
            background-color: rgba(34, 197, 94, 0.12);
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.25);
            border-radius: 14px;
            padding: 4px 14px;
            font-size: 12px;
            font-weight: 600;
        """)

        # Default select all unorganized
        self._selected_items = set(range(unorg_count))
        self._render_table()
        unknown = len(results.get("unclassified_loose", []))
        if unknown:
            self.top_status_badge.setText(self.top_status_badge.text() + f" · {unknown} loose videos need manual review")
        if cached:
            self.top_status_badge.setText('Saved preview · ' + self.top_status_badge.text())
            self.top_status_badge.setToolTip('Cached results are shown without scanning. Click Scan now after changing files outside the app.')
        else:
            from app.ui.organizer_cache import configuration
            self._shown_config = configuration(self._rules)
            if results.get('_configuration', self._shown_config) != self._shown_config:
                self._mark_preview_stale('Configuration changed during the scan — click Scan now')
            self.data_changed.emit()

    def _mark_preview_stale(self, message):
        from app.ui.organizer_cache import invalidate_preview
        invalidate_preview()
        self._preview_stale = True
        self.top_status_badge.setText(message)
        self._render_table()

    def _on_scan_error(self, err: str):
        self.progress_bar.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.find_missing_btn.setEnabled(True)
        self.top_status_badge.setText("Scan error")
        QMessageBox.warning(self, "Scan Error", f"Failed to scan library: {err}")

    def apply_settings_preferences(self):
        from app import preferences as prefs
        for key, value in (("treat_direct_as_season_1", prefs.enabled("flat_detection")), ("organize_without_confirmation", not prefs.enabled("preview_moves"))):
            self._rules[key] = value
            switch = self.rule_switches[key]
            switch.blockSignals(True)
            switch.setChecked(value)
            switch.blockSignals(False)

    def _on_rule_toggled(self, key: str):
        self._rules[key] = self.rule_switches[key].isChecked()
        from app import preferences as prefs
        if key == "treat_direct_as_season_1":
            prefs.save("flat_detection", self._rules[key])
        elif key == "organize_without_confirmation":
            prefs.save("preview_moves", not self._rules[key])
        self._mark_preview_stale('Detection rules changed — click Scan now')

    def _switch_tab(self, tab_id: str):
        self._current_tab = tab_id
        self._update_tab_styles()
        self._selected_items.clear()
        if tab_id == "unorganized":
            self._selected_items = set(range(len(self._data.get("unorganized", []))))
        self._render_table()

    def _update_tab_styles(self):
        buttons = [
            (self.tab_unorg_btn, "unorganized"),
            (self.tab_org_btn, "organized"),
            (self.tab_all_btn, "all"),
        ]
        for btn, tab_id in buttons:
            if self._current_tab == tab_id:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ffffff;
                        color: #111827;
                        border-radius: 16px;
                        font-weight: 700;
                        font-size: 12px;
                        padding: 0 16px;
                        border: none;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1d1f29;
                        color: #b0b3c2;
                        border: 1px solid #383a44;
                        border-radius: 16px;
                        font-weight: 500;
                        font-size: 12px;
                        padding: 0 16px;
                    }
                    QPushButton:hover {
                        color: #f3f4f6;
                        background-color: #222638;
                    }
                """)

    # -----------------------------------------------------------------------
    # Table Rendering
    # -----------------------------------------------------------------------
    def _render_table(self):
        items = self._data.get(self._current_tab, [])
        query = self.search_filter.text().strip().lower()

        filtered_items = []
        for idx, item in enumerate(items):
            if query:
                if query not in item.get("anime_name", "").lower() and query not in item.get("folder_path", "").lower():
                    continue
            filtered_items.append((idx, item))

        self.table.setRowCount(len(filtered_items))
        total_selected_files = 0
        total_selected_folders = 0

        for row_idx, (orig_idx, item) in enumerate(filtered_items):
            self.table.setRowHeight(row_idx, 64)
            # Column 0: Checkbox + Anime Name + Subtitle Path & Reason
            cell_widget = QWidget()
            cell_widget.setObjectName('organizer_cell')
            c_layout = QHBoxLayout(cell_widget)
            c_layout.setContentsMargins(8, 6, 8, 6)
            c_layout.setSpacing(12)

            cb = QCheckBox()
            is_checked = orig_idx in self._selected_items
            cb.setChecked(is_checked)
            cb.stateChanged.connect(lambda state, idx=orig_idx: self._on_item_checked(idx, state))
            c_layout.addWidget(cb)

            t_box = QVBoxLayout()
            t_box.setSpacing(2)

            name_lbl = ElidedLabel(item.get("anime_name", "Anime"))
            name_lbl.setToolTip(item.get("folder_path", ""))
            name_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #f3f4f6;")
            t_box.addWidget(name_lbl)

            sub_lbl = ElidedLabel(item.get("status_reason", ""))
            sub_lbl.setStyleSheet("font-size: 11px; color: #b0b3c2;")
            t_box.addWidget(sub_lbl)

            c_layout.addLayout(t_box, 1)
            self.table.setCellWidget(row_idx, 0, cell_widget)

            # Column 1: Files count
            vcount = item.get("video_count", 0)
            f_lbl = QLabel(f"{vcount} files")
            f_lbl.setAlignment(Qt.AlignCenter)
            f_lbl.setStyleSheet("font-size: 12px; color: #f3f4f6;")
            self.table.setCellWidget(row_idx, 1, f_lbl)

            # Column 2: Proposed Badge
            badge_text = item.get("status_badge", "Season 1")
            b_lbl = QLabel(badge_text)
            b_lbl.setAlignment(Qt.AlignCenter)
            if badge_text == "Organized":
                b_lbl.setStyleSheet("""
                    background-color: rgba(34, 197, 94, 0.15);
                    color: #22c55e;
                    border: 1px solid rgba(34, 197, 94, 0.3);
                    border-radius: 12px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                """)
            elif badge_text.startswith("Season"):
                b_lbl.setStyleSheet("""
                    background-color: rgba(142, 117, 255, 0.15);
                    color: #a78bfa;
                    border: 1px solid rgba(142, 117, 255, 0.3);
                    border-radius: 12px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                """)
            elif badge_text == "Matched":
                b_lbl.setStyleSheet("""
                    background-color: rgba(20, 184, 166, 0.15);
                    color: #14b8a6;
                    border: 1px solid rgba(20, 184, 166, 0.3);
                    border-radius: 12px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                """)
            else:
                b_lbl.setStyleSheet("""
                    background-color: rgba(245, 158, 11, 0.15);
                    color: #f59e0b;
                    border: 1px solid rgba(245, 158, 11, 0.3);
                    border-radius: 12px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                """)
            badge_cell = QWidget()
            badge_cell.setObjectName('organizer_cell')
            badge_layout = QHBoxLayout(badge_cell)
            badge_layout.setContentsMargins(4, 0, 4, 0)
            b_lbl.setFixedHeight(24)
            badge_layout.addWidget(b_lbl, 0, Qt.AlignVCenter)
            self.table.setCellWidget(row_idx, 2, badge_cell)

            # Column 3: Review Button
            rev_btn = QPushButton("Review")
            rev_btn.setObjectName('organizer_review')
            rev_btn.setAccessibleName('Review organization for ' + item.get('anime_name', 'anime'))
            rev_btn.setCursor(Qt.PointingHandCursor)
            rev_btn.setFixedHeight(44)
            rev_btn.setMinimumWidth(88)
            rev_btn.setEnabled(not self._preview_stale)
            if self._preview_stale:
                rev_btn.setToolTip('Click Scan now to update this preview before reviewing file moves.')
            rev_btn.clicked.connect(lambda checked, it=item: self._open_review_dialog(it))
            action_cell = QWidget()
            action_cell.setObjectName('organizer_cell')
            action_layout = QHBoxLayout(action_cell)
            action_layout.setContentsMargins(6, 0, 6, 0)
            action_layout.addWidget(rev_btn, 0, Qt.AlignVCenter)
            self.table.setCellWidget(row_idx, 3, action_cell)

            if is_checked:
                total_selected_files += vcount
                total_selected_folders += 1

        # Summary
        self.summary_label.setText(
            f"{total_selected_files} files · {total_selected_folders} folders selected"
        )
        self.organize_btn.setEnabled(total_selected_folders > 0 and self._current_tab != "organized" and not self._preview_stale)
        if self._current_tab == "organized":
            self.organize_btn.setText("Files already organized")
        else:
            self.organize_btn.setText(f"Organize {total_selected_folders} selected anime")

    def _on_item_checked(self, orig_idx: int, state: int):
        if state == Qt.Checked:
            self._selected_items.add(orig_idx)
        else:
            self._selected_items.discard(orig_idx)

        # Update summary
        items = self._data.get(self._current_tab, [])
        sel_folders = len(self._selected_items)
        sel_files = sum(items[i].get("video_count", 0) for i in self._selected_items if i < len(items))

        self.summary_label.setText(f"{sel_files} files · {sel_folders} folders selected")
        self.organize_btn.setEnabled(sel_folders > 0 and self._current_tab != "organized")
        if self._current_tab != "organized":
            self.organize_btn.setText(f"Organize {sel_folders} selected anime")

    def _on_select_all_toggled(self, state: int):
        items = self._data.get(self._current_tab, [])
        if state == Qt.Checked:
            self._selected_items = set(range(len(items)))
        else:
            self._selected_items.clear()
        self._render_table()

    def _on_table_double_clicked(self, item):
        row = item.row()
        filtered = self._data.get(self._current_tab, [])
        if row < len(filtered):
            self._open_review_dialog(filtered[row])

    def _open_review_dialog(self, item: Dict[str, Any]):
        if self._preview_stale:
            return
        if self._worker and self._worker.isRunning():
            return
        if self.merge_page.busy():
            return
        dlg = OrganizerReviewDialog(item, rules=self._rules, parent=self)
        def completed(result):
            if result == QDialog.Accepted:
                self.data_changed.emit()
                self._mark_preview_stale('Files changed — click Scan now to update the preview')
        navigate(dlg, completed)

    # -----------------------------------------------------------------------
    # Batch Organize Execution
    # -----------------------------------------------------------------------
    def _execute_batch(self):
        if self._worker and self._worker.isRunning():
            return
        if self.merge_page.busy():
            return
        items = self._data.get(self._current_tab, [])
        selected = [items[i] for i in sorted(self._selected_items) if i < len(items)]

        if not selected:
            return

        total_files = sum(it.get("video_count", 0) for it in selected)

        if not self._rules.get("organize_without_confirmation", False):
            reply = QMessageBox.question(
                self, "Confirm File Organization",
                f"You are about to organize {len(selected)} anime ({total_files} video files).\n\n"
                "Files will be safely organized into Season 1/, Season 2/ or Movies & OVAs/ folders.\n"
                "No video files will be deleted or overwritten.\n\n"
                "Proceed with organization?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self.organize_btn.setEnabled(False)
        self.organize_btn.setText("Organizing files...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(selected))
        self.progress_bar.setValue(0)

        self._batch_worker = OrganizerWorker(selected, self._rules)
        self._batch_worker.progress.connect(self._on_batch_progress)
        self._batch_worker.finished.connect(self._on_batch_finished)
        self._batch_worker.error.connect(self._on_batch_error)
        self._batch_worker.start()

    def _on_batch_progress(self, name: str, current: int, total: int):
        self.progress_bar.setValue(current)
        self.summary_label.setText(f"Organizing [{current}/{total}]: {name}...")

    def _on_batch_finished(self, result: dict):
        self.progress_bar.setVisible(False)
        from app.core.organizer import organization_summary
        message = organization_summary(result)
        if result.get("errors"):
            QMessageBox.warning(self, "Organization needs attention", message)
        else:
            QMessageBox.information(self, "Organization result", message)

        self.data_changed.emit()
        self._mark_preview_stale('Files processed — click Scan now to update the preview')

    def _on_batch_error(self, err: str):
        self.progress_bar.setVisible(False)
        self.organize_btn.setEnabled(True)
        QMessageBox.critical(self, "Organization Error", f"An error occurred: {err}")
