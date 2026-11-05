"""
Custom anime entry creator dialog.
Allows manual anime creation + Episode 1 thumbnail grabber.
"""

import subprocess
import tempfile
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QButtonGroup, QFileDialog,
    QGroupBox, QFormLayout, QMessageBox, QScrollArea, QWidget,
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, pyqtSignal

from app import db
from app.ui.components.design import MotifHeader
from app.ui.components.workflow import chrome, card, field, text, button
from app.config import COVERS_DIR, VIDEO_EXTENSIONS


from app.ui.dialogs.drawer import DrawerDialog


class CustomEntryDialog(DrawerDialog):
    """Dialog for creating custom anime entries or editing existing ones."""

    entry_saved = pyqtSignal(int)  # franchise_id

    def __init__(self, franchise_data: dict = None, parent=None):
        super().__init__(parent)
        self.franchise_data = franchise_data
        self.is_edit = franchise_data is not None
        self.custom_cover_path = None

        title = "Edit Anime Entry" if self.is_edit else "Add Custom Anime"
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)
        self.setModal(True)

        self._setup_ui()

        if self.is_edit:
            self._populate_fields()

    def _setup_ui(self):
        if self.is_edit:
            self._setup_edit_ui()
            return
        title = "Edit anime entry" if self.is_edit else "Add custom entry"
        body, self.save_btn = chrome(self, title,
            "Edit your library details." if self.is_edit else "Keep unmatched anime in your library with your own details",
            "\u8a73\u7d30" if self.is_edit else "\u8ffd\u52a0", "Save entry", self._save)
        self.display_title_input = QLineEdit()
        self.display_title_input.setPlaceholderText("English title")
        field(body, "Display title", self.display_title_input)
        artwork = QWidget()
        cover = QHBoxLayout(artwork)
        cover.setContentsMargins(0, 0, 0, 0)
        cover.setSpacing(20)
        self.cover_preview = QLabel("No image yet")
        self.cover_preview.setObjectName("workflow_poster")
        self.cover_preview.setFixedSize(140, 210)
        self.cover_preview.setAlignment(Qt.AlignCenter)
        cover.addWidget(self.cover_preview)
        controls = QVBoxLayout()
        controls.setSpacing(10)
        controls.addStretch()
        controls.addWidget(button("Choose image", self._pick_cover_image))
        controls.addWidget(button("Grab episode 1 frame", self._grab_thumbnail))
        cover.addLayout(controls, 1)
        field(body, "Poster artwork", artwork)
        self.watch_status_combo = QComboBox()
        self.watch_status_combo.addItems(["WATCHED", "WATCHING", "PLAN_TO_WATCH", "DROPPED"])
        for index, label in enumerate(("Watched", "Watching", "Plan to watch", "Dropped")):
            self.watch_status_combo.setItemData(index, label, Qt.DisplayRole)
            self.watch_status_combo.setItemData(index, ("WATCHED", "WATCHING", "PLAN_TO_WATCH", "DROPPED")[index], Qt.UserRole)
        field(body, "Watch status", self.watch_status_combo)
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Optional")
        self.notes_input.setFixedHeight(124)
        field(body, "Notes", self.notes_input)
        if not self.is_edit:
            note, note_layout = card()
            note_layout.addWidget(text("Custom entries without an AniList link are skipped during metadata refresh."))
            body.addWidget(note)
        more, extras = card()
        extras.addWidget(text("Title information and details", "workflow_row_title"))
        for attr, label in (("title_en_input", "English title"), ("title_romaji_input", "Romaji title"), ("title_native_input", "Japanese title")):
            control = QLineEdit()
            setattr(self, attr, control)
            field(extras, label, control)
        self.synopsis_input = QTextEdit()
        self.synopsis_input.setFixedHeight(124)
        field(extras, "Synopsis", self.synopsis_input)
        self.genres_input = QLineEdit()
        self.genres_input.setPlaceholderText("Comma-separated genres")
        field(extras, "Genres", self.genres_input)
        self.rating_choices = QButtonGroup(self)
        self.rating_choices.setExclusive(False)
        rating_widget = QWidget()
        rating_row = QHBoxLayout(rating_widget)
        rating_row.setContentsMargins(0, 0, 0, 0)
        rating_row.setSpacing(3)
        for rating in range(1, 11):
            control = QPushButton(str(rating))
            control.setObjectName("entry_rating")
            control.setFixedSize(34, 36)
            control.setCheckable(True)
            control.setAccessibleName(f"Rate {rating} out of 10")
            self.rating_choices.addButton(control, rating)
            rating_row.addWidget(control)
        self.rating_choices.buttonClicked.connect(self._select_rating)
        field(extras, "Your rating", rating_widget)
        body.addWidget(more)
        folder_row = QWidget()
        folder_layout = QHBoxLayout(folder_row)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Root folder path (optional)")
        folder_layout.addWidget(self.folder_input, 1)
        folder_layout.addWidget(button("Browse", self._browse_folder))
        field(body, "Anime folder", folder_row)
        body.addStretch()

    def _setup_edit_ui(self):
        body, self.save_btn = chrome(self, "Edit anime entry", "Update titles, details and artwork in your library.", "\u8a73\u7d30", "Save entry", self._save)
        def panel(label):
            frame, box = card()
            frame.setObjectName("workflow_edit_panel")
            box.setContentsMargins(20, 20, 20, 20)
            box.setSpacing(20)
            box.addWidget(text(label, "workflow_row_title"))
            body.addWidget(frame)
            return box
        titles = panel("Title information")
        for attribute, label in (("display_title_input", "Display title"), ("title_en_input", "English title"), ("title_romaji_input", "Romaji title"), ("title_native_input", "Japanese title")):
            control = QLineEdit()
            setattr(self, attribute, control)
            field(titles, label, control)
        details = panel("Details")
        self.synopsis_input = QTextEdit()
        self.synopsis_input.setFixedHeight(124)
        field(details, "Synopsis", self.synopsis_input)
        self.genres_input = QLineEdit()
        field(details, "Genres (comma separated)", self.genres_input)
        self.watch_status_combo = QComboBox()
        for label, value in (("Watched", "WATCHED"), ("Watching", "WATCHING"), ("Plan to watch", "PLAN_TO_WATCH"), ("Dropped", "DROPPED")):
            self.watch_status_combo.addItem(label, value)
        field(details, "Watch status", self.watch_status_combo)
        self.rating_combo = QComboBox()
        self.rating_combo.addItem("No rating", 0)
        for value in range(1, 11):
            self.rating_combo.addItem(str(value), value)
        field(details, "Rating", self.rating_combo)
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Personal notes")
        self.notes_input.setFixedHeight(124)
        field(details, "Notes", self.notes_input)
        artwork = panel("Cover image")
        row = QHBoxLayout()
        row.setSpacing(20)
        self.cover_preview = QLabel("No image yet")
        self.cover_preview.setObjectName("workflow_poster")
        self.cover_preview.setFixedSize(140, 210)
        self.cover_preview.setAlignment(Qt.AlignCenter)
        row.addWidget(self.cover_preview)
        controls = QVBoxLayout()
        controls.setSpacing(10)
        controls.addStretch()
        controls.addWidget(button("Choose image", self._pick_cover_image))
        controls.addWidget(button("Grab episode 1 frame", self._grab_thumbnail))
        row.addLayout(controls, 1)
        artwork.addLayout(row)
        folder = panel("Anime folder")
        wrapper = QWidget()
        path_row = QHBoxLayout(wrapper)
        path_row.setContentsMargins(0, 0, 0, 0)
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Root folder path (optional)")
        path_row.addWidget(self.folder_input, 1)
        path_row.addWidget(button("Browse", self._browse_folder))
        field(folder, "Linked folder", wrapper)
        body.addStretch()

    def _select_rating(self, selected):
        for button in self.rating_choices.buttons():
            if button is not selected:
                button.setChecked(False)

    def _populate_fields(self):
        """Fill in fields from existing franchise data."""
        d = self.franchise_data
        self.display_title_input.setText(d.get("display_title", ""))
        self.title_en_input.setText(d.get("title_en", "") or "")
        self.title_romaji_input.setText(d.get("title_romaji", "") or "")
        self.title_native_input.setText(d.get("title_native", "") or "")
        self.synopsis_input.setPlainText(d.get("synopsis", "") or "")

        import json
        genres = d.get("genres", "[]")
        if isinstance(genres, str):
            try:
                genres = json.loads(genres)
            except (json.JSONDecodeError, TypeError):
                genres = []
        self.genres_input.setText(", ".join(genres))

        ws = d.get("watch_status", "WATCHED")
        idx = self.watch_status_combo.findData(ws)
        if idx >= 0:
            self.watch_status_combo.setCurrentIndex(idx)

        rating = d.get("user_rating")
        if hasattr(self, "rating_combo"):
            self.rating_combo.setCurrentIndex(max(0, self.rating_combo.findData(rating or 0)))
        elif rating and self.rating_choices.button(rating):
            self.rating_choices.button(rating).setChecked(True)
        self.notes_input.setPlainText(d.get("user_notes", "") or "")
        self.folder_input.setText(d.get("root_folder_path", "") or "")

        # Show existing cover
        if d.get("cover_filename"):
            cover_path = COVERS_DIR / d["cover_filename"]
            if cover_path.is_file():
                pixmap = QPixmap(str(cover_path)).scaled(
                    140, 210, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.cover_preview.setPixmap(pixmap)

    def _pick_cover_image(self):
        """Open file dialog to pick a custom cover image."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cover Image", "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp)"
        )
        if path:
            self.custom_cover_path = path
            pixmap = QPixmap(path).scaled(
                140, 210, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.cover_preview.setPixmap(pixmap)

    def _grab_thumbnail(self):
        """Extract a frame from Episode 1 video using FFmpeg."""
        folder = self.folder_input.text().strip()
        if not folder:
            QMessageBox.information(
                self, "No Folder",
                "Please set the root folder first to find Episode 1."
            )
            return

        from app.core.entry_service import grab_frame
        from app.ui.io_task import start
        start(self, lambda: grab_frame(folder), self._frame_ready)

    def _frame_ready(self, result):
        self.custom_cover_path, image = result
        self.cover_preview.setPixmap(QPixmap.fromImage(image))

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Anime Folder"
        )
        if folder:
            self.folder_input.setText(folder)

    def _save(self):
        """Save the custom entry to the database."""
        import json

        display_title = self.display_title_input.text().strip()
        if not display_title:
            QMessageBox.warning(self, "Required", "Display Title is required.")
            return

        genres_text = self.genres_input.text().strip()
        genres_list = [g.strip() for g in genres_text.split(",") if g.strip()] if genres_text else []

        rating = self.rating_combo.currentData() if hasattr(self, "rating_combo") else self.rating_choices.checkedId()

        data = {
            "display_title": display_title,
            "title_en": self.title_en_input.text().strip() or None,
            "title_romaji": self.title_romaji_input.text().strip() or None,
            "title_native": self.title_native_input.text().strip() or None,
            "synopsis": self.synopsis_input.toPlainText().strip(),
            "genres": json.dumps(genres_list),
            "watch_status": self.watch_status_combo.currentData(),
            "user_rating": rating if rating > 0 else None,
            "user_notes": self.notes_input.toPlainText().strip(),
            "root_folder_path": self.folder_input.text().strip() or None,
            "is_custom": 1,
        }

        from app.core.entry_service import save_entry
        from app.ui.io_task import start
        previous = dict(self.franchise_data) if self.is_edit else None
        cover = self.custom_cover_path
        start(self, lambda: save_entry(data, previous, cover), self._saved)

    def _saved(self, fid):
        self.entry_saved.emit(fid)
        self.accept()

    def reject(self):
        worker = getattr(self, '_apply_worker', None)
        if worker and worker.isRunning():
            return
        super().reject()
