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
    QCheckBox, QMessageBox, QComboBox, QApplication, QGridLayout,
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
from app.core.text_import import read_text_list, title_key, ImportIndex
from app.ui.dialogs.rematch_dialog import RematchDialog


class ParseAndMatchWorker(QThread):
    """Background worker that parses lines from a .txt file and queries AniList for candidates."""
    item_matched = pyqtSignal(dict)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, filepath: str, rematch_existing=False):
        super().__init__()
        self.filepath=filepath;self.rematch_existing=rematch_existing

    def run(self):
        from app.core.import_preview import preview_lines
        try:
            results=[]
            for item in preview_lines(read_text_list(self.filepath),online=not is_offline(),
                    rematch_existing=self.rematch_existing,cancelled=self.isInterruptionRequested):
                results.append(item);self.item_matched.emit(item)
            self.finished.emit(results)
        except Exception as error:self.error.emit(str(error))


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
        hint = text("One anime per line. Numbered lists such as 1) Anime title are supported.")
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
        self.rematch_existing=QCheckBox('Find metadata for existing unmatched titles')
        self.rematch_existing.setChecked(prefs.enabled('import_rematch_existing'))
        self.rematch_existing.toggled.connect(lambda checked:prefs.save('import_rematch_existing',checked))
        self.rematch_existing.setToolTip('Only unambiguous matches are selected automatically. Nothing changes until Apply.')
        body.addWidget(self.rematch_existing)
        self.result_filter=QComboBox();self.result_filter.addItems(['All titles','Already in library','New / needs match','Duplicate lines'])
        self.result_filter.currentIndexChanged.connect(self._filter_rows)
        field(body,'Show imported titles',self.result_filter)
        counts=QGridLayout();counts.setSpacing(12)
        self._count_labels={}
        for index,(key,caption) in enumerate((('existing','Already in library'),('matched','Metadata matched'),('review','Need review'),('unmatched','Not found'))):
            tile,labels=card();value=text('0','workflow_metric');labels.addWidget(value);labels.addWidget(text(caption))
            self._count_labels[key]=value;counts.addWidget(tile,index//2,index%2)
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

        self._worker = ParseAndMatchWorker(filepath,rematch_existing=self.rematch_existing.isChecked())
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
        if item["status"]=="DUPLICATE":selected=False;checkbox.setEnabled(False)
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
        ready = status in ("MATCHED", "MERGED", "CUSTOM_SAVED", "EXISTING_MATCHED", "DUPLICATE")
        row.setMinimumHeight(84 if ready else 112 if not media else 88)
        label = ('Duplicate line' if status=='DUPLICATE' else 'Existing · Match found' if status=='EXISTING_MATCHED' else
                 'Already in library' if status=='MERGED' else 'Saved' if status=='CUSTOM_SAVED' else
                 'Existing · Review' if item.get('existing_id') else f"{item['confidence']}% · Matched" if status=='MATCHED' else
                 'Lookup failed' if status=='ERROR' else f"{item['confidence']}% · Review" if media else 'Not found')
        if item.get('error'):row.setToolTip(item['error'])
        pill = text(label, "workflow_match")
        pill.setWordWrap(False)
        pill.setProperty("tone", "success" if ready else "warning" if media else "danger")
        layout.addWidget(pill, 0, Qt.AlignVCenter)
        if not ready or (item.get('existing_id') and not item.get('existing_provider')):
            actions = QVBoxLayout()
            actions.setSpacing(6)
            actions.addWidget(button("Choose match", lambda checked=False, it=item: self._review_item(it)))
            if not media and not item.get('existing_id'):
                actions.addWidget(button("Add custom", lambda checked=False, it=item: self._add_custom(it)))
            layout.addLayout(actions)
        row.import_item=item
        self.items_layout.addWidget(row)
        self._filter_rows()

    def _filter_rows(self,*_):
        mode=self.result_filter.currentIndex()
        for index in range(self.items_layout.count()):
            row=self.items_layout.itemAt(index).widget()
            if row is None:continue
            item=row.import_item
            visible=(mode==0 or mode==1 and bool(item.get('existing_id')) or
                     mode==2 and not item.get('existing_id') and item['status']!='DUPLICATE' or
                     mode==3 and item['status']=='DUPLICATE')
            row.setVisible(visible)

    def _refresh_rows(self):
        self._clear_items()
        for item in self.parsed_items:
            self._render_item(item)
        self._refresh_summary()

    def _review_item(self, item):
        picker = RematchDialog(None, parent=self, selection_only=True)
        picker.search_input.setText(item["raw_title"])
        def chosen(media):
            item.update({"matched_title": anilist_client.resolve_display_title(media), "anilist_media": media, "existing_id": item.get("existing_id"), "status": "EXISTING_MATCHED" if item.get("existing_id") else "MATCHED", "update_metadata": bool(item.get("existing_id")), "safe_match": True, "confidence": 100, "enabled": True})
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
        matched=sum(it.get('status') in ('MATCHED','EXISTING_MATCHED') for it in self.parsed_items)
        review=sum(it.get('status') in ('REVIEW','AMBIGUOUS','ERROR') for it in self.parsed_items)
        existing=sum(bool(it.get('existing_id')) for it in self.parsed_items)
        unmatched=sum(it.get('status')=='NOT_FOUND' and not it.get('existing_id') for it in self.parsed_items)
        duplicates=sum(it.get('status')=='DUPLICATE' for it in self.parsed_items)
        for key,value in (('existing',existing),('matched',matched),('review',review),('unmatched',unmatched)):
            self._count_labels[key].setText(str(value))
        selected=sum(bool(it.get('enabled')) for it in self.parsed_items)
        self.summary_lbl.setText(f'{total} lines · {existing} already in library · {duplicates} duplicates skipped · {selected} selected')
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
            f"{merged} existing entries updated with {self.import_status_combo.currentText()} status and any confirmed metadata")
        self.import_completed.emit()
        self.accept()
