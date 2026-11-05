"""
Watched TXT Importer Dialog — Replicating the #importDrawer from ui.html.
Allows importing anime watch history from text files with confidence scoring,
interactive ambiguous match review, and zero duplicate entries.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
from difflib import SequenceMatcher

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QProgressBar, QFileDialog,
    QCheckBox, QMessageBox, QComboBox, QApplication,
)
from PyQt5.QtGui import QColor, QFont, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from app.ui.components.design import MotifHeader
from app.ui.components.workflow import chrome, card, field, text, button, thumbnail
from app.ui.dialogs.rematch_dialog import ResultTitle
from app import db
from app import preferences as prefs
from app.config import is_offline, COVERS_DIR
from app.core import anilist_client
from app.core.parser import parse_txt_line, clean_title, normalize_for_matching
from app.ui.dialogs.rematch_dialog import RematchDialog


class ParseAndMatchWorker(QThread):
    """Background worker that parses lines from a .txt file and queries AniList for candidates."""
    item_matched = pyqtSignal(dict)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath

    def run(self):
        try:
            path = Path(self.filepath)
            if not path.is_file():
                self.error.emit(f"File not found: {self.filepath}")
                return

            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            results = []
            seen = set()

            for line in lines:
                if self.isInterruptionRequested():
                    break
                parsed = parse_txt_line(line)
                if not parsed or not parsed["title"]:
                    continue

                raw_title = parsed["title"]
                notes = parsed["notes"]
                norm_query = normalize_for_matching(raw_title)
                if prefs.enabled("import_ignore_duplicates") and norm_query in seen:
                    continue
                seen.add(norm_query)

                # 1. Check existing library
                existing = db.find_franchise_by_title(raw_title)
                if existing and prefs.enabled("import_ignore_duplicates"):
                    continue
                if existing:
                    item = {
                        "raw_line": line,
                        "raw_title": raw_title,
                        "notes": notes,
                        "matched_title": existing.get("display_title", raw_title),
                        "status": "MERGED",
                        "confidence": 100,
                        "anilist_media": None,
                        "existing_id": existing["id"],
                    }
                    results.append(item)
                    self.item_matched.emit(item)
                    continue

                # 2. Check AniList if online
                matched_media = None
                conf = 0
                matched_title = raw_title
                status = "NOT_FOUND"

                if not is_offline():
                    try:
                        search_res = anilist_client.search_anime(raw_title, per_page=1)
                        if search_res:
                            matched_media = search_res[0]
                            title_dict = matched_media.get("title") or {}
                            matched_title = title_dict.get("english") or title_dict.get("romaji") or raw_title
                            romaji = title_dict.get("romaji") or ""

                            r1 = SequenceMatcher(None, norm_query, normalize_for_matching(matched_title)).ratio()
                            r2 = SequenceMatcher(None, norm_query, normalize_for_matching(romaji)).ratio()
                            conf = int(max(r1, r2) * 100)

                            if conf >= 90:
                                status = "MATCHED"
                            elif conf >= 50:
                                status = "REVIEW"
                            else:
                                status = "AMBIGUOUS"
                    except Exception:
                        pass

                if matched_media:
                    matched_media["_preview_cover"] = anilist_client.download_cover(matched_media, "preview-" + str(matched_media["id"]))
                item = {
                    "raw_line": line,
                    "raw_title": raw_title,
                    "notes": notes,
                    "matched_title": matched_title,
                    "status": status,
                    "confidence": conf,
                    "anilist_media": matched_media,
                    "existing_id": None,
                }
                results.append(item)
                self.item_matched.emit(item)

            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


from app.ui.dialogs.drawer import DrawerDialog


class WatchedImportDialog(DrawerDialog):
    """Interactive Watched List Importer dialog."""

    import_completed = pyqtSignal()

    def __init__(self, initial_filepath: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.filepath = initial_filepath
        self.parsed_items: List[Dict[str, Any]] = []
        self._worker = None

        self.setWindowTitle("Import Watched List")
        self.resize(560, 900)
        self.setModal(True)
        self._setup_ui()
        if self.filepath:
            self._start_parse(self.filepath)

    def _setup_ui(self):
        self.setAcceptDrops(True)
        body, self.apply_btn = chrome(self, "Import watched list", "Import a TXT file and review AniList matches", "\u53d6\u8fbc", "Apply matches", self._apply_all_matches)
        self.apply_btn.setEnabled(False)
        zone = QFrame()
        zone.setObjectName("workflow_dropzone")
        drop = QVBoxLayout(zone)
        drop.setContentsMargins(16, 12, 16, 12)
        title = text("Drop a .txt file here", "workflow_row_title")
        title.setAlignment(Qt.AlignCenter)
        drop.addWidget(title)
        hint = text("One anime name per line, English or Japanese")
        hint.setAlignment(Qt.AlignCenter)
        drop.addWidget(hint)
        drop.addWidget(button("Choose TXT file", self._browse_file), 0, Qt.AlignHCenter)
        body.addWidget(zone)
        self.file_lbl = text(self.filepath or "")
        self.file_lbl.setVisible(bool(self.filepath))
        self.file_lbl.setToolTip(self.filepath or "")
        body.addWidget(self.file_lbl)
        self.import_status_combo = QComboBox()
        for label, value in (("Watched", "WATCHED"), ("Watching", "WATCHING"), ("Plan to watch", "PLAN_TO_WATCH"), ("Dropped", "DROPPED")):
            self.import_status_combo.addItem(label, value)
        field(body, "Status for imported titles", self.import_status_combo)
        counts = QHBoxLayout()
        counts.setSpacing(12)
        self._count_labels = {}
        for key, caption in (("matched", "Automatically matched"), ("review", "Need review"), ("unmatched", "Not found")):
            tile, labels = card()
            value = text("0", "workflow_metric")
            labels.addWidget(value)
            labels.addWidget(text(caption))
            self._count_labels[key] = value
            counts.addWidget(tile, 1)
        body.addLayout(counts)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        body.addWidget(self.progress_bar)
        self.items_container = QWidget()
        self.items_container.setObjectName("workflow_field")
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(8)
        body.addWidget(self.items_container)
        self.summary_lbl = text("")
        body.addWidget(self.summary_lbl)
        body.addStretch()

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
        self.file_lbl.setText(path)
        self.file_lbl.show()
        self.file_lbl.setToolTip(path)
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

        self._worker = ParseAndMatchWorker(filepath)
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

    def _render_item(self, item):
        row = QFrame()
        row.setObjectName("workflow_card")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        checkbox = QCheckBox()
        high = item.get("confidence", 0) >= 90
        skip_review = not prefs.enabled("import_review") and item.get("anilist_media") and item.get("confidence", 0) >= 50
        selected = item.get("enabled", item["status"] == "MERGED" or (prefs.enabled("import_auto") and bool(high or skip_review)))
        item["enabled"] = bool(selected)
        checkbox.setChecked(bool(selected))
        checkbox.setAccessibleName("Include " + item["raw_title"])
        def select(state):
            item["enabled"] = bool(state)
            self._refresh_summary()
        checkbox.stateChanged.connect(select)
        layout.addWidget(checkbox)
        media = item.get("anilist_media") or {}
        thumb = thumbnail(item["raw_title"], media.get("_preview_cover"), 40, 60)
        layout.addWidget(thumb)
        titles = QVBoxLayout()
        titles.setSpacing(3)
        title = ResultTitle(item["raw_title"])
        title.setObjectName("workflow_row_title")
        titles.addWidget(title)
        subtitle = ResultTitle("\u2192 " + item["matched_title"])
        subtitle.setObjectName("workflow_hint")
        titles.addWidget(subtitle)
        layout.addLayout(titles, 1)
        status = item["status"]
        ready = status in ("MATCHED", "MERGED", "CUSTOM_SAVED")
        row.setMinimumHeight(84 if ready else 112 if not media else 88)
        label = "Saved" if status == "CUSTOM_SAVED" else "In library" if status == "MERGED" else f"{item['confidence']}% \u00b7 Matched" if ready else f"{item['confidence']}% \u00b7 Review" if media else "Not found"
        pill = text(label, "workflow_match")
        pill.setWordWrap(False)
        pill.setProperty("tone", "success" if ready else "warning" if media else "danger")
        layout.addWidget(pill, 0, Qt.AlignVCenter)
        if not ready:
            actions = QVBoxLayout()
            actions.setSpacing(6)
            actions.addWidget(button("Choose match", lambda checked=False, it=item: self._review_item(it)))
            if not media:
                actions.addWidget(button("Add custom", lambda checked=False, it=item: self._add_custom(it)))
            layout.addLayout(actions)
        self.items_layout.addWidget(row)

    def _refresh_rows(self):
        self._clear_items()
        for item in self.parsed_items:
            self._render_item(item)
        self._refresh_summary()

    def _review_item(self, item):
        picker = RematchDialog(None, parent=self, selection_only=True)
        picker.search_input.setText(item["raw_title"])
        def chosen(media):
            item.update({"matched_title": anilist_client.resolve_display_title(media), "anilist_media": media, "existing_id": None, "status": "MATCHED", "confidence": 100, "enabled": True})
            self._refresh_rows()
        picker.match_chosen.connect(chosen)
        picker._start_search(item["raw_title"])
        from app.ui.navigation import navigate
        navigate(picker)

    def _add_custom(self, item):
        from app.ui.dialogs.custom_entry import CustomEntryDialog
        editor = CustomEntryDialog(parent=self)
        editor.display_title_input.setText(item["raw_title"])
        editor.watch_status_combo.setCurrentIndex(max(0, editor.watch_status_combo.findData(self.import_status_combo.currentData())))
        editor.notes_input.setPlainText(item.get("notes") or "")
        def saved(fid):
            record = db.get_franchise(fid)
            item.update({"matched_title": record["display_title"], "existing_id": fid, "status": "CUSTOM_SAVED", "enabled": False})
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
        matched = sum(it.get("status") in ("MATCHED", "MERGED", "CUSTOM_SAVED") for it in self.parsed_items)
        review = sum(it.get("status") in ("REVIEW", "AMBIGUOUS") for it in self.parsed_items)
        for key, value in (("matched", matched), ("review", review), ("unmatched", total - matched - review)):
            self._count_labels[key].setText(str(value))
        selected = sum(bool(it.get("enabled")) for it in self.parsed_items)
        self.summary_lbl.setText(f"{total} titles found \u00b7 {selected} selected")
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
        QMessageBox.information(self, "Import Complete",
            f"Successfully processed watched list:\n\n{imported} new titles added\n"
            f"{merged} existing titles updated with {self.import_status_combo.currentText()} status")
        self.import_completed.emit()
        self.accept()
