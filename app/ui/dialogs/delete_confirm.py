"""Recycle Bin confirmation with the existing three-step review flow."""
import json
from pathlib import Path
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QStackedWidget, QWidget, QFrame, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from app import db
from app.config import COVERS_DIR
from app.core.storage import format_bytes
from app.core.recycle import recycle_selected
from app.ui.components.workflow import chrome, card, text, button, thumbnail
from app.ui.dialogs.drawer import DrawerDialog
from PyQt5.QtGui import QPixmap


class RecycleWorker(QThread):
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fid, seasons, watched, signatures, parent=None):
        super().__init__(parent)
        self.fid, self.seasons, self.watched, self.signatures = fid, seasons, watched, signatures

    def run(self):
        self.result = None
        self.error = None
        try:
            self.result = recycle_selected(self.fid, self.seasons, self.watched, self.signatures)
        except Exception as error:
            self.error = str(error)


class DeleteConfirmDialog(QDialog):
    centered_workflow = True
    deletion_confirmed = pyqtSignal(int, str)

    def __init__(self, franchise_data, seasons=None, parent=None):
        super().__init__(parent)
        self.franchise_data = franchise_data
        self.seasons = seasons if seasons is not None else db.get_seasons_for_franchise(franchise_data["id"])
        self.setWindowTitle("Delete local files?")
        self.resize(580, 800)
        self.setMinimumSize(520, 500)
        self.setModal(True)
        self._apply_worker = None
        self._calculate_sizes()
        self._setup_ui()

    def _calculate_sizes(self):
        self.total_size = 0
        self.total_files = 0
        self.folders_to_delete = []
        self._file_signatures = {}
        for season in self.seasons:
            if season.get("storage_state") != "ON_DISK" or not season.get("season_folder_path"):
                continue
            folder = Path(season["season_folder_path"])
            if not folder.is_dir():
                continue
            self.folders_to_delete.append(str(folder))
            root = folder.resolve()
            for name in json.loads(season.get("video_files_json") or "[]"):
                try:
                    path = (root / name).resolve()
                    path.relative_to(root)
                    if path.is_file() and str(path) not in self._file_signatures:
                        stat = path.stat()
                        self._file_signatures[str(path)] = (stat.st_size, stat.st_mtime_ns)
                        self.total_files += 1
                        self.total_size += stat.st_size
                except (ValueError, OSError):
                    pass

    def _format_size(self, size):
        return format_bytes(size)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.stacked = QStackedWidget()
        root.addWidget(self.stacked)
        self.stacked.addWidget(self._build_step1())
        self.stacked.addWidget(self._build_step2())
        self.stacked.addWidget(self._build_step3())
        self.cancel_button.setFocus()

    def _step(self, title, subtitle, action, callback):
        page = QDialog()
        page.setWindowFlags(Qt.Widget)
        page.reject = self.reject
        body, primary = chrome(page, title, subtitle, "\u524a\u9664", action, callback)
        return page, body, primary

    def _build_step1(self):
        page, body, primary = self._step("Delete local files?", "Selected video files move to the Recycle Bin. Your library keeps the records.", "Review deletion", lambda: self.stacked.setCurrentIndex(1))
        self.cancel_button = page.cancel_button
        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        for number, caption in (("1", "Selected title"), (format_bytes(self.total_size), "Files to remove"), ("Kept", "Library records")):
            tile, labels = card()
            labels.addWidget(text(number, "workflow_metric"))
            labels.addWidget(text(caption))
            metrics.addWidget(tile, 1)
        body.addLayout(metrics)
        for folder in dict.fromkeys(self.folders_to_delete):
            tile = QFrame()
            tile.setObjectName("workflow_card")
            row = QHBoxLayout(tile)
            row.setContentsMargins(12, 12, 12, 12)
            thumb = thumbnail(self.franchise_data.get("display_title") or "Anime", self.franchise_data.get("cover_filename"), 40, 60)
            row.addWidget(thumb)
            titles = QVBoxLayout()
            titles.addWidget(text(self.franchise_data.get("display_title") or "Anime", "workflow_row_title"))
            path = text(folder)
            path.setToolTip(folder)
            titles.addWidget(path)
            row.addLayout(titles, 1)
            total = sum(size for path, (size, _) in self._file_signatures.items() if Path(folder).resolve() in Path(path).parents)
            size = text(format_bytes(total), "workflow_match")
            size.setWordWrap(False)
            row.addWidget(size, 0, Qt.AlignVCenter)
            body.addWidget(tile)
        self.mark_watched_checkbox = QCheckBox('Mark selected title as "Watched, removed"')
        self.mark_watched_checkbox.setChecked(True)
        body.addWidget(self.mark_watched_checkbox)
        note, labels = card()
        labels.addWidget(text("Space comes back after you empty the Recycle Bin.", "workflow_row_title"))
        labels.addWidget(text("Only the selected indexed videos are moved. Other files and library records are kept. If Windows cannot recycle a file, it remains in place and an error is shown."))
        body.addWidget(note)
        primary.setEnabled(self.total_files > 0)
        body.addStretch()
        return page

    def _build_step2(self):
        page, body, self.final_proceed_btn = self._step("Review selected files", "Confirm the file removal while preserving your library records.", "Continue to final step", lambda: self.stacked.setCurrentIndex(2))
        note, labels = card()
        labels.addWidget(text(f"{self.total_files:,} video files \u00b7 {format_bytes(self.total_size)}", "workflow_row_title"))
        labels.addWidget(text("Your library entry, poster, rating and notes are kept. The selected videos will be moved to the Recycle Bin."))
        body.addWidget(note)
        self.confirm_checkbox = QCheckBox("I reviewed the selected files and want to move them to the Recycle Bin.")
        self.confirm_checkbox.toggled.connect(self._on_checkbox_toggled)
        body.addWidget(self.confirm_checkbox)
        body.addWidget(button("Back", lambda: self.stacked.setCurrentIndex(0)), 0, Qt.AlignLeft)
        body.addStretch()
        self.final_proceed_btn.setEnabled(False)
        return page

    def _build_step3(self):
        page, body, self.delete_button = self._step("Final confirmation", "Move the selected video files to the Recycle Bin.", f"Move to Recycle Bin \u00b7 free {format_bytes(self.total_size)}", self._start_delete)
        from app.ui.icons import icon
        self.delete_button.setIcon(icon("trash", "#FFFFFF"))
        body.addWidget(text(f"{self.total_files:,} video files will leave their current locations. You can restore recycled files through Windows before emptying the bin."))
        body.addWidget(button("Back", lambda: self.stacked.setCurrentIndex(1)), 0, Qt.AlignLeft)
        self.delete_status = text("")
        body.addWidget(self.delete_status)
        body.addStretch()
        return page

    def _on_checkbox_toggled(self, checked):
        self.final_proceed_btn.setEnabled(checked)

    def _start_delete(self):
        if not self.confirm_checkbox.isChecked() or self._apply_worker and self._apply_worker.isRunning():
            return
        self.delete_button.setEnabled(False)
        self.delete_status.setText("Moving files to the Recycle Bin. Keep the app open...")
        self._apply_worker = RecycleWorker(self.franchise_data["id"], self.seasons, self.mark_watched_checkbox.isChecked(), self._file_signatures, self)
        self._apply_worker.finished.connect(self._recycle_worker_finished)
        self._apply_worker.start()

    def _recycle_worker_finished(self):
        if self._apply_worker.result is not None:
            self._deletion_finished(self._apply_worker.result)
        else:
            self._deletion_failed(self._apply_worker.error or "Unknown error")

    def _execute_delete(self):
        # Synchronous adapter retained for existing integrations and tests.
        result = recycle_selected(self.franchise_data["id"], self.seasons, self.mark_watched_checkbox.isChecked(), self._file_signatures)
        self._deletion_finished(result)

    def _deletion_finished(self, result):
        if result["failures"]:
            QMessageBox.warning(self, "Some files could not be recycled", "\n".join(result["failures"][:12]))
        self.deletion_confirmed.emit(self.franchise_data["id"], ", ".join(result["recycled"]))
        self.accept()

    def _deletion_failed(self, error):
        self.delete_button.setEnabled(True)
        self.delete_status.setText("Files could not be recycled: " + error)

    def reject(self):
        if self._apply_worker and self._apply_worker.isRunning():
            return
        super().reject()
