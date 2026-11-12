"""
Watched TXT Importer Dialog with Twilight Sakura presentation.
Allows importing anime watch history from text files with confidence scoring,
interactive ambiguous match review, and zero duplicate entries.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QMessageBox,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from app import db
from app import preferences as prefs
from app.config import is_offline
from app.core import anilist_client
from app.core.storage import format_bytes
from app.core.text_import import read_text_list
from app.ui.components.settings_switch import SettingsSwitch
from app.ui.dialogs.drawer import DrawerDialog
from app.ui.dialogs.rematch_dialog import RematchDialog, ResultTitle
from app.ui.entry_import_style import (
    StatusDot,
    TwilightCheckBox,
    TwilightComboBox,
    action_button,
    build_twilight_chrome,
    center_modal_show,
    dialog_qss,
    field_block,
    palette,
    plain_label,
    poster_thumbnail,
    refresh_chrome_scale,
)
from app.ui.home_style import px
from app.ui.icons import icon


_IMPORT_STATUSES = (
    ("Watched", "WATCHED"),
    ("Watching", "WATCHING"),
    ("Plan to watch", "PLAN_TO_WATCH"),
    ("Dropped", "DROPPED"),
)


class ParseAndMatchWorker(QThread):
    """Background worker that parses lines from a .txt file and queries AniList for candidates."""

    item_matched = pyqtSignal(dict)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, filepath: str, rematch_existing=False):
        super().__init__()
        self.filepath = filepath
        self.rematch_existing = rematch_existing

    def run(self):
        from app.core.import_preview import preview_lines

        try:
            results = []
            for item in preview_lines(
                read_text_list(self.filepath),
                online=not is_offline(),
                rematch_existing=self.rematch_existing,
                cancelled=self.isInterruptionRequested,
            ):
                results.append(item)
                self.item_matched.emit(item)
            self.finished.emit(results)
        except Exception as error:
            self.error.emit(str(error))


class WatchedImportDialog(DrawerDialog):
    """Interactive Watched List Importer dialog."""

    centered_workflow = True
    workflow_width = 980
    import_completed = pyqtSignal()

    def __init__(self, initial_filepath: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.filepath = initial_filepath
        self.parsed_items: List[Dict[str, Any]] = []
        self._worker = None

        self.setObjectName("watched_import_dialog")
        self.setWindowTitle("Import Watched List")
        self.setMinimumWidth(480)
        self.setMinimumHeight(600)
        self.resize(self.workflow_width, 840)
        self.setModal(True)
        self._setup_ui()
        self.refresh_home_style()
        if self.filepath:
            self._update_file_display(self.filepath)
            self._start_parse(self.filepath)

    def _setup_ui(self):
        self.setAcceptDrops(True)
        body, self.apply_btn = build_twilight_chrome(
            self,
            "Import watched list",
            "Import a TXT file and review AniList matches",
            "\u53d6\u8fbc",
            "Apply matches",
            self._apply_all_matches,
            shortcut_text="Ctrl + I",
        )
        self.apply_btn.setEnabled(False)
        self.footer_note_layout.addWidget(StatusDot("coral", size=7), 0, Qt.AlignVCenter)
        self.footer_note_layout.addWidget(
            plain_label("0 local files moved or deleted", "entry_field_helper", word_wrap=False),
            0,
            Qt.AlignVCenter,
        )
        self.footer_note_layout.addStretch()

        body.addWidget(self._build_dropzone())
        body.addWidget(self._build_config_bar())
        body.addLayout(self._build_kpi_row())

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("import_progress")
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        body.addWidget(self.progress_bar)

        list_header = QHBoxLayout()
        list_header.setContentsMargins(0, 4, 0, 0)
        list_header.setSpacing(12)
        list_header.addWidget(plain_label("Match review list", "entry_section_heading", word_wrap=False))
        list_header.addStretch()
        self.summary_lbl = plain_label("", "workflow_hint", word_wrap=False)
        list_header.addWidget(self.summary_lbl)
        body.addLayout(list_header)

        self.items_container = QWidget()
        self.items_container.setObjectName("twilight_field_inner")
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(8)
        body.addWidget(self.items_container)
        body.addStretch()

    def _build_dropzone(self):
        zone = QFrame()
        zone.setObjectName("import_dropzone")
        drop = QVBoxLayout(zone)
        drop.setContentsMargins(20, 16, 20, 16)
        drop.setSpacing(12)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(14)
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(3)
        text_col.addWidget(plain_label("Drop a .txt file here", "workflow_row_title"))
        text_col.addWidget(plain_label("One anime per line. Numbered lists such as 1) Anime title are supported."))
        top.addLayout(text_col, 1)
        self._browse_btn = action_button("Choose TXT file", self._browse_file, object_name="poster_action_btn")
        top.addWidget(self._browse_btn, 0, Qt.AlignVCenter)
        drop.addLayout(top)

        self._file_strip = QFrame()
        self._file_strip.setObjectName("import_file_strip")
        strip = QHBoxLayout(self._file_strip)
        strip.setContentsMargins(12, 8, 12, 8)
        strip.setSpacing(8)
        strip.addWidget(StatusDot("existing", size=7), 0, Qt.AlignVCenter)
        self.file_lbl = plain_label(self.filepath or "", "import_file_path")
        self.file_lbl.setVisible(bool(self.filepath))
        self.file_lbl.setToolTip(self.filepath or "")
        strip.addWidget(self.file_lbl, 1)
        self._file_size_lbl = plain_label("", "entry_field_meta", word_wrap=False)
        strip.addWidget(self._file_size_lbl, 0, Qt.AlignVCenter)
        self._file_strip.setVisible(bool(self.filepath))
        drop.addWidget(self._file_strip)
        return zone

    def _build_config_bar(self):
        card = QFrame()
        card.setObjectName("import_config_card")
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 14, 16, 14)
        row.setSpacing(14)

        col_status = QVBoxLayout()
        col_status.setContentsMargins(0, 0, 0, 0)
        self.import_status_combo = TwilightComboBox()
        for label, value in _IMPORT_STATUSES:
            self.import_status_combo.addItem(label, value)
        field_block(col_status, "Status for imported titles", self.import_status_combo)
        row.addLayout(col_status, 1)

        col_switch = QVBoxLayout()
        col_switch.setContentsMargins(0, 0, 0, 0)
        col_switch.setSpacing(6)
        col_switch.addWidget(plain_label("Metadata matching", "entry_field_label", word_wrap=False))
        switch_card = QFrame()
        switch_card.setObjectName("import_switch_card")
        switch_card.setToolTip("Only unambiguous matches are selected automatically. Nothing changes until Apply.")
        switch_row = QHBoxLayout(switch_card)
        switch_row.setContentsMargins(10, 4, 12, 4)
        switch_row.setSpacing(8)
        self.rematch_existing = SettingsSwitch(prefs.enabled("import_rematch_existing"))
        self.rematch_existing.setProperty("animevaultTwilightSwitch", True)
        self.rematch_existing.toggled.connect(lambda checked: prefs.save("import_rematch_existing", checked))
        self.rematch_existing.setAccessibleName("Find metadata for existing unmatched titles")
        self.rematch_existing.setToolTip("Only unambiguous matches are selected automatically. Nothing changes until Apply.")
        switch_row.addWidget(self.rematch_existing, 0, Qt.AlignVCenter)
        switch_row.addWidget(plain_label("Find metadata for existing unmatched titles", "import_switch_label"), 1)
        col_switch.addWidget(switch_card)
        row.addLayout(col_switch, 1)

        col_filter = QVBoxLayout()
        col_filter.setContentsMargins(0, 0, 0, 0)
        self.result_filter = TwilightComboBox()
        self.result_filter.addItems(["All titles", "Already in library", "New / needs match", "Duplicate lines"])
        self.result_filter.currentIndexChanged.connect(self._filter_rows)
        field_block(col_filter, "Show imported titles", self.result_filter)
        row.addLayout(col_filter, 1)
        return card

    def _build_kpi_row(self):
        counts = QHBoxLayout()
        counts.setContentsMargins(0, 0, 0, 0)
        counts.setSpacing(12)
        self._count_labels = {}
        for key, caption in (
            ("existing", "Already in library"),
            ("matched", "Metadata matched"),
            ("review", "Need review"),
            ("unmatched", "Not found"),
        ):
            tile = QFrame()
            tile.setObjectName("kpi_card")
            box = QVBoxLayout(tile)
            box.setContentsMargins(14, 12, 14, 12)
            box.setSpacing(6)
            top = QHBoxLayout()
            top.setContentsMargins(0, 0, 0, 0)
            top.setSpacing(7)
            top.addWidget(StatusDot(key, size=8), 0, Qt.AlignVCenter)
            top.addWidget(plain_label(caption, "kpi_caption", word_wrap=False), 1)
            box.addLayout(top)
            value = plain_label("0", "kpi_value", word_wrap=False)
            value.setProperty("tone", key)
            box.addWidget(value)
            self._count_labels[key] = value
            counts.addWidget(tile, 1)
        return counts

    def refresh_home_style(self):
        """Reapply Twilight Sakura styles and scaled metrics on theme/scale changes."""
        c = palette()
        self.setProperty("animevaultOwnScaledStyle", True)
        self.setStyleSheet(dialog_qss(self.objectName()))
        refresh_chrome_scale(self)
        if hasattr(self, "apply_btn"):
            self.apply_btn.setIcon(icon("check", c["on_coral"]))
        self.rematch_existing.update()
        if self.parsed_items:
            self._refresh_rows()

    def showEvent(self, event):
        center_modal_show(self, event, super().showEvent)

    def _update_file_display(self, path):
        self.file_lbl.setText(path)
        self.file_lbl.show()
        self.file_lbl.setToolTip(path)
        self._file_strip.show()
        target = Path(path)
        self._file_size_lbl.setText(format_bytes(target.stat().st_size) if target.is_file() else "")
        self._browse_btn.setText("Replace TXT file")

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile() and Path(urls[0].toLocalFile()).suffix.lower() == ".txt":
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile() and Path(urls[0].toLocalFile()).suffix.lower() == ".txt":
            self._load_file(urls[0].toLocalFile())
            event.acceptProposedAction()

    def _load_file(self, path):
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "Import in progress", "Wait for the current file to finish before choosing another.")
            return
        self.filepath = path
        self._update_file_display(path)
        self._start_parse(path)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Watched Anime Text File", "", "Text Files (*.txt);;All Files (*.*)"
        )
        if path:
            self._load_file(path)

    def _start_parse(self, filepath: str):
        self._parsing = True
        self._clear_items()
        self.parsed_items.clear()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)
        self.summary_lbl.setText("Analyzing list against AniList and local library...")
        for label in self._count_labels.values():
            label.setText("0")
        self.apply_btn.setEnabled(False)

        self._worker = ParseAndMatchWorker(filepath, rematch_existing=self.rematch_existing.isChecked())
        self._worker.item_matched.connect(self._add_item_row)
        self._worker.finished.connect(self._on_parse_finished)
        self._worker.error.connect(self._on_parse_error)
        self._worker.finished.connect(self._refresh_summary)
        self._worker.setParent(QApplication.instance())
        self._worker.start()

    def _clear_items(self):
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_item_row(self, item: Dict):
        self.parsed_items.append(item)
        self._render_item(item)
        self._refresh_summary()

    def _row_meta(self, item):
        status = item["status"]
        media = item.get("anilist_media") or {}
        ready = status in ("MATCHED", "MERGED", "CUSTOM_SAVED", "EXISTING_MATCHED", "DUPLICATE")
        label = (
            "Duplicate line" if status == "DUPLICATE" else
            "Existing · Match found" if status == "EXISTING_MATCHED" else
            "Already in library" if status == "MERGED" else
            "Saved" if status == "CUSTOM_SAVED" else
            "Existing · Review" if item.get("existing_id") else
            f"{item['confidence']}% · Matched" if status == "MATCHED" else
            "Lookup failed" if status == "ERROR" else
            f"{item['confidence']}% · Review" if media else
            "Not found"
        )
        pill_tone = (
            "existing" if status in ("MERGED", "CUSTOM_SAVED") else
            "matched" if status in ("MATCHED", "EXISTING_MATCHED") else
            "muted" if status == "DUPLICATE" else
            "warning" if media else
            "danger"
        )
        return ready, label, pill_tone

    def _render_item(self, item):
        row = QFrame()
        row.setObjectName("import_row_card")
        row.setMinimumHeight(px(74))
        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        checkbox = TwilightCheckBox()
        high = item.get("confidence", 0) >= 90
        skip_review = not prefs.enabled("import_review") and item.get("anilist_media") and item.get("confidence", 0) >= 50
        selected = item.get(
            "enabled",
            item["status"] == "MERGED" or (prefs.enabled("import_auto") and bool(high or skip_review)),
        )
        item["enabled"] = bool(selected)
        if item["status"] == "DUPLICATE":
            selected = False
            checkbox.setEnabled(False)
        checkbox.setChecked(bool(selected))
        checkbox.setAccessibleName("Include " + item["raw_title"])

        def select(state):
            item["enabled"] = bool(state)
            self._refresh_summary()

        checkbox.stateChanged.connect(select)
        layout.addWidget(checkbox, 0, Qt.AlignVCenter)

        media = item.get("anilist_media") or {}
        ready, label, pill_tone = self._row_meta(item)
        thumb_tone = "unmatched" if pill_tone == "danger" else "matched"
        thumb = poster_thumbnail(item["raw_title"], media.get("_preview_cover"), 40, 58, tone=thumb_tone)
        layout.addWidget(thumb, 0, Qt.AlignVCenter)

        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(3)
        title = ResultTitle(item["raw_title"])
        title.setObjectName("workflow_row_title")
        titles.addWidget(title)
        subtitle = ResultTitle("\u2192 " + item["matched_title"])
        subtitle.setObjectName("workflow_hint")
        titles.addWidget(subtitle)
        layout.addLayout(titles, 1)

        if pill_tone == "danger":
            row.setProperty("tone", "danger")
        if item.get("error"):
            row.setToolTip(item["error"])

        pill = plain_label(label, "import_status_pill", word_wrap=False)
        pill.setProperty("tone", pill_tone)
        layout.addWidget(pill, 0, Qt.AlignVCenter)

        if not ready or (item.get("existing_id") and not item.get("existing_provider")):
            actions = QHBoxLayout()
            actions.setContentsMargins(0, 0, 0, 0)
            actions.setSpacing(6)
            actions.addWidget(action_button("Choose match", lambda checked=False, it=item: self._review_item(it)))
            if not media and not item.get("existing_id"):
                actions.addWidget(
                    action_button(
                        "Add custom",
                        lambda checked=False, it=item: self._add_custom(it),
                        object_name="row_custom_btn",
                    )
                )
            layout.addLayout(actions)

        row.import_item = item
        self.items_layout.addWidget(row)
        row.setVisible(self._row_visible(item, self.result_filter.currentIndex()))

    @staticmethod
    def _row_visible(item, mode):
        return (
            mode == 0
            or mode == 1 and bool(item.get("existing_id"))
            or mode == 2 and not item.get("existing_id") and item["status"] != "DUPLICATE"
            or mode == 3 and item["status"] == "DUPLICATE"
        )

    def _filter_rows(self, *_):
        mode = self.result_filter.currentIndex()
        for index in range(self.items_layout.count()):
            row = self.items_layout.itemAt(index).widget()
            if row is not None:
                row.setVisible(self._row_visible(row.import_item, mode))

    def _refresh_rows(self):
        self._clear_items()
        for item in self.parsed_items:
            self._render_item(item)
        self._refresh_summary()

    def _review_item(self, item):
        picker = RematchDialog(None, parent=self, selection_only=True)
        picker.search_input.setText(item["raw_title"])

        def chosen(media):
            item.update(
                {
                    "matched_title": anilist_client.resolve_display_title(media),
                    "anilist_media": media,
                    "existing_id": item.get("existing_id"),
                    "status": "EXISTING_MATCHED" if item.get("existing_id") else "MATCHED",
                    "update_metadata": bool(item.get("existing_id")),
                    "safe_match": True,
                    "confidence": 100,
                    "enabled": True,
                }
            )
            self._refresh_rows()

        picker.match_chosen.connect(chosen)
        picker._start_search(item["raw_title"])
        from app.ui.navigation import navigate

        navigate(picker)

    def _add_custom(self, item):
        from app.ui.dialogs.custom_entry import CustomEntryDialog

        editor = CustomEntryDialog(parent=self)
        editor.display_title_input.setText(item["raw_title"])
        editor.watch_status_combo.setCurrentIndex(
            max(0, editor.watch_status_combo.findData(self.import_status_combo.currentData()))
        )
        editor.notes_input.setPlainText(item.get("notes") or "")

        def saved(fid):
            record = db.get_franchise(fid)
            item.update(
                {
                    "matched_title": record["display_title"],
                    "existing_id": fid,
                    "status": "CUSTOM_SAVED",
                    "enabled": False,
                }
            )
            self._refresh_rows()
            self.import_completed.emit()

        editor.entry_saved.connect(saved)
        from app.ui.navigation import navigate

        navigate(editor)

    def _on_parse_finished(self, results: List[Dict]):
        self._parsing = False
        self.progress_bar.setVisible(False)
        self.apply_btn.setEnabled(len(results) > 0)
        self._refresh_summary()

    def _refresh_summary(self):
        total = len(self.parsed_items)
        matched = sum(it.get("status") in ("MATCHED", "EXISTING_MATCHED") for it in self.parsed_items)
        review = sum(it.get("status") in ("REVIEW", "AMBIGUOUS", "ERROR") for it in self.parsed_items)
        existing = sum(bool(it.get("existing_id")) for it in self.parsed_items)
        unmatched = sum(it.get("status") == "NOT_FOUND" and not it.get("existing_id") for it in self.parsed_items)
        duplicates = sum(it.get("status") == "DUPLICATE" for it in self.parsed_items)
        for key, value in (("existing", existing), ("matched", matched), ("review", review), ("unmatched", unmatched)):
            self._count_labels[key].setText(str(value))
        selected = sum(bool(it.get("enabled")) for it in self.parsed_items)
        self.summary_lbl.setText(
            f"{total} lines · {existing} already in library · {duplicates} duplicates skipped · {selected} selected"
        )
        self.apply_btn.setText(f"Apply {selected} matches")
        self.apply_btn.setEnabled(selected > 0 and not getattr(self, "_parsing", False))

    def _on_parse_error(self, err: str):
        self._parsing = False
        self.progress_bar.setVisible(False)
        self.summary_lbl.setText("Error reading file.")
        QMessageBox.warning(self, "Import Error", f"Failed to read watched list:\n{err}")

    def reject(self):
        if getattr(self, "_apply_worker", None) and self._apply_worker.isRunning():
            return
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
        super().reject()

    def _apply_all_matches(self):
        from app.core.entry_service import apply_import
        from app.ui.io_task import start
        import copy

        items = copy.deepcopy(self.parsed_items)
        status = self.import_status_combo.currentData()
        start(self, lambda: apply_import(items, status), self._import_applied)

    def _import_applied(self, result):
        imported, merged = result
        QMessageBox.information(
            self,
            "Import Complete",
            f"Successfully processed watched list:\n\n{imported} new titles added\n"
            f"{merged} existing entries updated with {self.import_status_combo.currentText()} status and any confirmed metadata",
        )
        self.import_completed.emit()
        self.accept()
