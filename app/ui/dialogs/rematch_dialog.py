"""
Rematch Dialog — Replicating the #rematchDrawer from ui.html.
Allows manual searching and relinking of AniList metadata without
renaming or altering local folders on disk.
"""

from typing import List, Dict
from pathlib import Path
from difflib import SequenceMatcher

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QScrollArea, QWidget, QFrame, QProgressBar, QMessageBox, QSizePolicy, QCheckBox, QRadioButton, QButtonGroup,
)
from PyQt5.QtGui import QPixmap, QColor, QPainter
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRectF

from app.ui.components.design import MotifHeader
from app.ui.components.workflow import chrome, card as workflow_card, field, text, button, thumbnail
from app import db
from app.config import COVERS_DIR, OFFLINE_MODE
from app.core import anilist_client
from app.core.parser import normalize_for_matching


class ResultTitle(QLabel):
    """Show one line while keeping the full title available on hover."""

    def __init__(self, title):
        super().__init__()
        self.full_title = " ".join(title.split())
        self.setTextFormat(Qt.PlainText)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setToolTip(self.full_title)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setText(self.fontMetrics().elidedText(
            self.full_title, Qt.ElideRight, self.contentsRect().width()
        ))


class AniListSearchWorker(QThread):
    """Background worker for querying AniList without UI freezes."""
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, query: str):
        super().__init__()
        self.query = query

    def run(self):
        try:
            with anilist_client.cancellable(self.isInterruptionRequested):
                results = anilist_client.search_anime(self.query, per_page=6)
                for media in results:
                    if self.isInterruptionRequested():
                        return
                    media["_preview_cover"] = anilist_client.download_cover(media, "preview-" + str(media["id"]))
                if not self.isInterruptionRequested():
                    self.results_ready.emit(results)
        except InterruptedError:
            pass
        except Exception as e:
            self.error_occurred.emit(str(e))


from app.ui.dialogs.drawer import DrawerDialog


class RematchDialog(DrawerDialog):
    """Manual AniList Rematch modal dialog."""

    match_chosen = pyqtSignal(object)
    rematched = pyqtSignal(int)  # Emits franchise_id

    def __init__(self, franchise_id: int, parent=None, season_id=None, selection_only=False):
        super().__init__(parent)
        self.full_page=not selection_only
        self.dispose_on_leave=not selection_only
        self.selection_only = selection_only
        self.franchise_id = franchise_id
        self.franchise = (db.get_series(franchise_id) if franchise_id is not None else None) or {}
        self.selections = {}
        self.continuous_episodes = db.uses_continuous_episodes(self.franchise) if self.franchise else False
        self.local_seasons = [
            season for season in db.get_series_seasons(franchise_id)
            if not self.continuous_episodes and season.get("storage_state") == "ON_DISK" and season.get("relation_type") == "SEASON"
        ]
        self._search_worker = None
        self._search_generation = 0
        self._queued_search = None
        self._search_closed = False

        self.setWindowTitle("Rematch Anime Metadata")
        self.resize(560, 900)
        self.setModal(True)
        self._setup_ui()
        # Initial search with existing title
        local_season = next((s for s in self.local_seasons if s["id"] == season_id), None)
        initial_query = self.franchise.get("display_title") or self.franchise.get("title_romaji") or ""
        if local_season and local_season.get("anilist_id"):
            initial_query = local_season["title_display"]
        if initial_query:
            self.search_input.setText(initial_query)
            self._start_search(initial_query)

    def _setup_ui(self):
        body, self.apply_btn = chrome(self, "Choose anime match" if self.selection_only else "Rematch anime",
            "Search AniList and replace the linked metadata only", "\u7167\u5408",
            "Choose match" if self.selection_only else "Apply match", self._apply_match)
        self.apply_btn.setEnabled(False)
        self.selection_group = QButtonGroup(self)
        self.selection_group.setExclusive(self.continuous_episodes or self.selection_only)
        if self.franchise:
            body.addWidget(text("Currently linked", "workflow_field_label"))
            linked, labels = workflow_card()
            labels.addWidget(text(self.franchise.get("display_title") or "Unknown anime", "workflow_row_title"))
            labels.addWidget(text(self.franchise.get("root_folder_path") or "No local folder linked"))
            body.addWidget(linked)
            from contextlib import closing
            with closing(db.get_connection()) as conn:
                unresolved = conn.execute('SELECT context_json,reason FROM matching_review WHERE local_id=?',(self.franchise_id,)).fetchone()
            if unresolved:
                import json
                evidence = json.loads(unresolved['context_json'])
                hint = text(unresolved['reason'] + '\nFile: ' + evidence.get('filename','') + '\nFolder: ' + evidence.get('folder',''))
                hint.setWordWrap(True)
                body.addWidget(hint)
                if evidence.get('files'):
                    from PyQt5.QtWidgets import QPlainTextEdit
                    body.addWidget(text(f"Files needing review ({len(evidence['files'])})",'workflow_field_label'))
                    files=QPlainTextEdit()
                    files.setReadOnly(True)
                    files.setAccessibleName('Files needing a metadata match')
                    files.setPlainText('\n'.join(evidence['files']))
                    files.setFixedHeight(120)
                    body.addWidget(files)
        search = QWidget()
        row = QHBoxLayout(search)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("English, Romaji or Japanese title")
        self.search_input.returnPressed.connect(self._on_search_clicked)
        row.addWidget(self.search_input, 1)
        row.addWidget(button("Search", self._on_search_clicked))
        field(body, "Search AniList", search)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        body.addWidget(self.progress_bar)
        self.search_status = text("Searching AniList...")
        self.search_status.hide()
        body.addWidget(self.search_status)
        body.addWidget(text("Results", "workflow_field_label"))
        self.results_container = QWidget()
        self.results_container.setObjectName("workflow_field")
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(8)
        self.results_layout.setAlignment(Qt.AlignTop)
        body.addWidget(self.results_container)
        note, labels = workflow_card()
        labels.addWidget(text("Your folder name stays unchanged.", "workflow_row_title"))
        labels.addWidget(text("Only the AniList ID, poster, display title and metadata link will change."))
        if not self.continuous_episodes and not self.selection_only:
            labels.addWidget(text("Select one or more releases, assigning each to its local season or Metadata only."))
        body.addWidget(note)
        self.status_lbl = text("Select a match" if self.selection_only else "Select one or more releases")
        body.addWidget(self.status_lbl)
        body.addStretch()

    def _on_search_clicked(self):
        query = self.search_input.text().strip()
        if query:
            self._start_search(query)

    def _start_search(self, query: str):
        self._search_generation += 1
        self.apply_btn.setEnabled(False)
        self.results_container.setEnabled(False)
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.requestInterruption()
            self._queued_search = query
            self.status_lbl.setText("Waiting for previous search to stop…")
            return
        if OFFLINE_MODE:
            self._clear_results()
            lbl = QLabel("Cannot search AniList while in Offline Mode.")
            lbl.setStyleSheet("color: #ef4444; font-size: 13px; padding: 20px;")
            lbl.setAlignment(Qt.AlignCenter)
            self.results_layout.addWidget(lbl)
            return

        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)
        self.search_status.show()
        self._update_selection_status()
        self.apply_btn.setEnabled(False)


        self._search_worker = AniListSearchWorker(query)
        self._search_worker.generation = self._search_generation
        self._search_worker.results_ready.connect(self._search_results)
        self._search_worker.error_occurred.connect(self._search_error)
        # Keep the worker alive if the user navigates away during a search.
        from PyQt5.QtWidgets import QApplication
        self._search_worker.setParent(QApplication.instance())
        from app.ui.io_task import track
        track(self._search_worker)
        self._search_worker.finished.connect(self._search_worker.deleteLater)
        self._search_worker.finished.connect(self._search_finished)
        self._search_worker.start()

    def _search_finished(self):
        if self.sender() is self._search_worker:
            self._search_worker = None
            query, self._queued_search = self._queued_search, None
            if query and not self._search_closed:
                self._start_search(query)

    def _search_results(self, results):
        if not self._search_closed and self.sender().generation == self._search_generation:
            self._on_results_ready(results)

    def _search_error(self, message):
        if not self._search_closed and self.sender().generation == self._search_generation:
            self._on_search_error(message)

    def _clear_results(self):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_results_ready(self, results: List[Dict]):
        self.results_container.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.search_status.hide()
        self._clear_results()

        if not results:
            self._update_selection_status()
            empty = QLabel("No anime found matching your query.")
            empty.setStyleSheet("color: #b0b3c2; font-size: 13px; padding: 20px;")
            empty.setAlignment(Qt.AlignCenter)
            self.results_layout.addWidget(empty)
            return

        self._update_selection_status()
        query_norm = normalize_for_matching(self.search_input.text().strip())

        for media in results:
            card = self._create_result_card(media, query_norm)
            self.results_layout.addWidget(card)

    def _on_search_error(self, err_msg: str):
        self.results_container.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.search_status.hide()
        self._update_selection_status()
        self._clear_results()
        err_lbl = QLabel(f"Failed to query AniList:\n{err_msg}")
        err_lbl.setStyleSheet("color: #ef4444; font-size: 12px; padding: 20px;")
        err_lbl.setAlignment(Qt.AlignCenter)
        self.results_layout.addWidget(err_lbl)

    def _create_result_card(self, media: Dict, query_norm: str) -> QWidget:
        result = QFrame()
        result.setObjectName("result_card")
        row = QHBoxLayout(result)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(12)
        single = self.continuous_episodes or self.selection_only
        result.setMinimumHeight(94 if single else 132)
        choice = QRadioButton() if single else QCheckBox()
        choice.setChecked(media["id"] in self.selections)
        self.selection_group.addButton(choice)
        row.addWidget(choice)
        thumb = thumbnail(anilist_client.resolve_display_title(media), media.get("_preview_cover"))
        row.addWidget(thumb)
        info = QVBoxLayout()
        info.setSpacing(4)
        titles = media.get("title") or {}
        title = anilist_client.resolve_display_title(media)
        heading = QLabel(title)
        heading.setTextFormat(Qt.PlainText);heading.setWordWrap(True)
        heading.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
        heading.setTextInteractionFlags(Qt.TextSelectableByMouse)
        heading.setObjectName("workflow_row_title")
        info.addWidget(heading)
        details = [value for value in (titles.get('romaji') if titles.get('romaji')!=title else None,titles.get("native"),str(media.get("seasonYear") or (media.get("startDate") or {}).get("year") or ""), media.get("format")) if value]
        if media.get('status')=='NOT_YET_RELEASED':details.append('Announced · Not released')
        subtitle = QLabel(" · ".join(details))
        subtitle.setTextFormat(Qt.PlainText);subtitle.setWordWrap(True)
        subtitle.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
        subtitle.setObjectName("workflow_hint")
        info.addWidget(subtitle)
        local = QComboBox()
        local.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        local.addItem("Metadata only", None)
        for season in self.local_seasons:
            label = f"Local season {season['season_number']} \u00b7 {season['title_display']}"
            local.addItem(label, season["id"])
            local.setItemData(local.count()-1, label + "\n" + (season.get("season_folder_path") or ""), Qt.ToolTipRole)
        default = self.selections.get(media["id"], (None, next((s["id"] for s in self.local_seasons if s.get("anilist_id") == media["id"]), None)))[1]
        local.setCurrentIndex(max(0, local.findData(default)))
        if media.get('status')=='NOT_YET_RELEASED':
            local.setCurrentIndex(0);local.setEnabled(False)
            local.setToolTip('Announced release. Metadata only; no local folder can be assigned yet.')
        if not single:
            info.addWidget(local)
        row.addLayout(info, 1)
        confidence = int(100 * max(SequenceMatcher(None, query_norm, normalize_for_matching(value)).ratio() for value in (title, titles.get("romaji") or title)))
        pill = text(f"{confidence}% match", "workflow_match")
        pill.setWordWrap(False)
        pill.setProperty("tone", "success" if confidence >= 80 else "warning" if confidence >= 50 else "danger")
        row.addWidget(pill, 0, Qt.AlignVCenter)
        choice.setAccessibleName("Select " + title)
        local.setAccessibleName("Local season for " + title)
        def update_selection():
            if choice.isChecked():
                self.selections[media["id"]] = (media, local.currentData())
            else:
                self.selections.pop(media["id"], None)
            result.setProperty("selected", choice.isChecked())
            result.style().unpolish(result)
            result.style().polish(result)
            self._update_selection_status()
        choice.toggled.connect(update_selection)
        local.currentIndexChanged.connect(update_selection)
        update_selection()
        return result

    def _update_selection_status(self):
        count = len(self.selections)
        self.apply_btn.setEnabled(count == 1 if self.continuous_episodes or self.selection_only else bool(count))
        self.status_lbl.setText(f"{count} selected" if count else "Select one or more releases")
        if not self.selection_only:self.apply_btn.setText(f"Review {count} seasons" if count>1 else "Apply match")
        self.status_lbl.setToolTip("\n".join(anilist_client.resolve_display_title(media) for media, _ in self.selections.values()))

    def _apply_match(self):
        if self.selection_only and len(self.selections) == 1:
            self.match_chosen.emit(next(iter(self.selections.values()))[0])
            self.accept()
            return
        if not self.selections or not self.franchise_id:
            return
        selections=list(self.selections.values())
        if len(selections)>1:
            from app.ui.io_task import start
            from app.ui.dialogs.match_review import prepare
            self.status_lbl.setText('Checking that the selected seasons belong together…')
            self.progress_bar.setRange(0,0);self.progress_bar.show()
            start(self,lambda:prepare(self.franchise_id,selections),self._show_match_review)
            worker=getattr(self,'_apply_worker',None)
            if worker:worker.finished.connect(lambda: self.progress_bar.hide() if getattr(self,'_apply_worker',None) in (None,worker) else None)
            return
        self._start_apply(selections)

    def _show_match_review(self,prepared):
        if getattr(self,'_embedded',False) and not self.isVisible():
            self.progress_bar.hide()
            return
        from app.ui.dialogs.match_review import MatchReview
        from app.ui.navigation import navigate
        self.progress_bar.hide()
        self._confirmation=MatchReview(prepared,self)
        self._confirmation.confirmed.connect(self._start_apply)
        navigate(self._confirmation)

    def _start_apply(self,selections):
        self.setEnabled(False)
        self.status_lbl.setText("Applying selected releases…")
        self.progress_bar.setRange(0,0);self.progress_bar.show()
        self._apply_worker = ApplyMatchWorker(self.franchise_id, selections)
        self._apply_worker.applied.connect(self._match_applied)
        self._apply_worker.failed.connect(self._match_failed)
        from app.ui.io_task import track
        track(self._apply_worker)
        worker=self._apply_worker
        worker.finished.connect(lambda: setattr(self,'_apply_worker',None) if getattr(self,'_apply_worker',None) is worker else None)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(self.progress_bar.hide)
        self._apply_worker.start()

    def _match_applied(self, fid):
        self.rematched.emit(fid)
        self.accept()

    def _match_failed(self, message):
        self.setEnabled(True)
        self.apply_btn.setEnabled(True)
        self.status_lbl.setText("Match could not be applied")
        QMessageBox.warning(self, "Apply match", message)

    def reject(self):
        if getattr(self, "_apply_worker", None) and self._apply_worker.isRunning():
            return
        self._search_closed = True
        self._queued_search = None
        if self._search_worker:
            self._search_worker.requestInterruption()
        super().reject()


class ApplyMatchWorker(QThread):
    applied = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, fid, selections):
        from PyQt5.QtWidgets import QApplication
        super().__init__(QApplication.instance())
        self.fid, self.selections = fid, selections

    def run(self):
        try:
            from app.core.matching import apply_release_match
            (media, season_id), *additional = self.selections
            fid = apply_release_match(self.fid, media, season_id, additional, use_local=season_id is not None)
            self.applied.emit(fid)
        except Exception as error:
            self.failed.emit(str(error))
