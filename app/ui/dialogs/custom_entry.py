"""
Custom anime entry creator and editor dialog with Twilight Sakura presentation.
Allows manual anime creation/editing + Episode 1 thumbnail grabber.
"""

import json

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import COVERS_DIR
from app.ui.dialogs.drawer import DrawerDialog
from app.ui.entry_import_style import (
    StatusDot,
    TwilightComboBox,
    action_button,
    apply_input_palettes,
    build_twilight_chrome,
    center_modal_show,
    dialog_qss,
    field_block,
    palette,
    plain_label,
    refresh_chrome_scale,
)
from app.ui.home_style import px
from app.ui.icons import icon


_WATCH_STATUSES = (
    ("Watched", "WATCHED"),
    ("Watching", "WATCHING"),
    ("Plan to watch", "PLAN_TO_WATCH"),
    ("Dropped", "DROPPED"),
)

_RATING_LABELS = {
    10: "Masterpiece",
    9: "Great",
    8: "Very good",
    7: "Good",
    6: "Fine",
    5: "Average",
    4: "Below average",
    3: "Poor",
    2: "Very poor",
    1: "Appalling",
}


class CustomEntryDialog(DrawerDialog):
    """Dialog for creating custom anime entries or editing existing ones."""

    centered_workflow = True
    workflow_width = 900
    entry_saved = pyqtSignal(int)  # franchise_id

    def __init__(self, franchise_data: dict = None, parent=None):
        super().__init__(parent)
        self.franchise_data = franchise_data
        self.is_edit = franchise_data is not None
        self.custom_cover_path = None
        self._rating_readout = None
        self._browse_btn = None

        self.setObjectName("custom_entry_dialog")
        self.setWindowTitle("Edit Anime Entry" if self.is_edit else "Add Custom Anime")
        self.setMinimumWidth(480)
        self.setMinimumHeight(600)
        self.resize(self.workflow_width, 820)
        self.setModal(True)

        self._setup_ui()
        self.refresh_home_style()

        if self.is_edit:
            self._populate_fields()

    def _setup_ui(self):
        title = "Edit anime entry" if self.is_edit else "Add custom entry"
        subtitle = (
            "Update titles, details and artwork in your library."
            if self.is_edit
            else "Keep unmatched anime in your library with your own details"
        )
        glyph = "\u8a73\u7d30" if self.is_edit else "\u8ffd\u52a0"
        body, self.save_btn = build_twilight_chrome(
            self, title, subtitle, glyph, "Save entry", self._save
        )
        self.footer_note_layout.addWidget(
            plain_label("Display title is required · Changes apply on Save", "entry_field_helper", word_wrap=False)
        )
        self.footer_note_layout.addStretch()

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(22)
        top_row.addLayout(self._build_poster_column())
        top_row.addWidget(self._build_titles_card(), 1)
        body.addLayout(top_row)

        self.synopsis_input = QTextEdit()
        self.synopsis_input.setPlaceholderText("Write a brief overview of the anime's plot or premises...")
        self.synopsis_input.setMinimumHeight(88)
        self.synopsis_input.setMaximumHeight(112)
        field_block(body, "Synopsis", self.synopsis_input)

        status_rating = QHBoxLayout()
        status_rating.setContentsMargins(0, 0, 0, 0)
        status_rating.setSpacing(20)

        self.watch_status_combo = TwilightComboBox()
        for label, value in _WATCH_STATUSES:
            self.watch_status_combo.addItem(label, value)
        status_col = QVBoxLayout()
        status_col.setContentsMargins(0, 0, 0, 0)
        field_block(status_col, "Watch status", self.watch_status_combo)
        status_col.addStretch()
        status_rating.addLayout(status_col, 1)
        status_rating.addLayout(self._build_rating_column(), 1)
        body.addLayout(status_rating)

        folder_row = QWidget()
        folder_row.setObjectName("twilight_field_inner")
        folder_layout = QHBoxLayout(folder_row)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(8)
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Root folder path (optional)")
        folder_layout.addWidget(self.folder_input, 1)
        self._browse_btn = action_button("Browse", self._browse_folder, object_name="folder_browse_btn")
        folder_layout.addWidget(self._browse_btn)
        field_block(body, "Linked folder" if self.is_edit else "Anime folder", folder_row)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Personal notes" if self.is_edit else "Optional")
        self.notes_input.setMinimumHeight(96)
        self.notes_input.setMaximumHeight(124)
        field_block(body, "Notes", self.notes_input)

        if not self.is_edit:
            banner = QFrame()
            banner.setObjectName("entry_sync_banner")
            banner_layout = QHBoxLayout(banner)
            banner_layout.setContentsMargins(14, 12, 14, 12)
            banner_layout.setSpacing(10)
            banner_layout.addWidget(StatusDot("review", size=8), 0, Qt.AlignTop)
            banner_text = QVBoxLayout()
            banner_text.setContentsMargins(0, 0, 0, 0)
            banner_text.setSpacing(2)
            banner_text.addWidget(plain_label("Automatic sync policy", "sync_banner_title"))
            banner_text.addWidget(
                plain_label(
                    "Custom entries without an AniList link are skipped during metadata refresh.",
                    "workflow_hint",
                )
            )
            banner_layout.addLayout(banner_text, 1)
            body.addWidget(banner)

        body.addStretch()

    def _build_poster_column(self):
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(10)
        col.addWidget(plain_label("POSTER ARTWORK", "entry_section_kicker", word_wrap=False))

        self.cover_preview = QLabel("No image yet")
        self.cover_preview.setObjectName("workflow_poster")
        self.cover_preview.setFixedSize(156, 234)
        self.cover_preview.setAlignment(Qt.AlignCenter)
        self.cover_preview.setWordWrap(True)
        self.cover_preview.setAccessibleName("Poster artwork preview")
        col.addWidget(self.cover_preview)

        col.addWidget(action_button("Choose image", self._pick_cover_image, object_name="poster_action_btn"))
        col.addWidget(action_button("Grab episode 1 frame", self._grab_thumbnail, object_name="poster_action_btn"))
        col.addStretch()
        return col

    def _build_titles_card(self):
        frame = QFrame()
        frame.setObjectName("twilight_section_card")
        box = QVBoxLayout(frame)
        box.setContentsMargins(18, 16, 18, 16)
        box.setSpacing(14)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(8)
        head.addWidget(StatusDot("coral", size=7), 0, Qt.AlignVCenter)
        section_title = "Title information" if self.is_edit else "Title information and details"
        head.addWidget(plain_label(section_title, "entry_section_heading", word_wrap=False), 1)
        box.addLayout(head)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)

        self.display_title_input = QLineEdit()
        self.display_title_input.setPlaceholderText("e.g. Frieren: Beyond Journey's End")
        col_0 = QVBoxLayout()
        col_0.setContentsMargins(0, 0, 0, 0)
        field_block(col_0, "Display title *" if not self.is_edit else "Display title", self.display_title_input)
        grid.addLayout(col_0, 0, 0)

        self.title_en_input = QLineEdit()
        self.title_en_input.setPlaceholderText("Official English title")
        col_1 = QVBoxLayout()
        col_1.setContentsMargins(0, 0, 0, 0)
        field_block(col_1, "English title", self.title_en_input)
        grid.addLayout(col_1, 0, 1)

        self.title_romaji_input = QLineEdit()
        self.title_romaji_input.setPlaceholderText("e.g. Sousou no Frieren")
        col_2 = QVBoxLayout()
        col_2.setContentsMargins(0, 0, 0, 0)
        field_block(col_2, "Romaji title", self.title_romaji_input)
        grid.addLayout(col_2, 1, 0)

        self.title_native_input = QLineEdit()
        self.title_native_input.setObjectName("entry_native_input")
        self.title_native_input.setPlaceholderText("e.g. \u846c\u9001\u306e\u30d5\u30ea\u30fc\u30ec\u30f3")
        col_3 = QVBoxLayout()
        col_3.setContentsMargins(0, 0, 0, 0)
        field_block(col_3, "Japanese title", self.title_native_input, badge_text="\u65e5\u672c\u8a9e\u30bf\u30a4\u30c8\u30eb")
        grid.addLayout(col_3, 1, 1)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        box.addLayout(grid)

        self.genres_input = QLineEdit()
        self.genres_input.setPlaceholderText("Comma-separated genres")
        field_block(box, "Genres", self.genres_input, helper="Separate multiple genres with commas.")
        return frame

    def _build_rating_column(self):
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(6)
        if self.is_edit:
            self.rating_combo = TwilightComboBox()
            self.rating_combo.addItem("No rating", 0)
            for value in range(1, 11):
                self.rating_combo.addItem(str(value), value)
            field_block(col, "Rating", self.rating_combo)
            col.addStretch()
            return col

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(8)
        head.addWidget(plain_label("Your rating", "entry_field_label", word_wrap=False))
        head.addStretch()
        self._rating_readout = plain_label("Not rated", "entry_rating_badge", word_wrap=False)
        head.addWidget(self._rating_readout)
        col.addLayout(head)

        self.rating_choices = QButtonGroup(self)
        self.rating_choices.setExclusive(False)
        rating_widget = QWidget()
        rating_widget.setObjectName("twilight_field_inner")
        rating_row = QHBoxLayout(rating_widget)
        rating_row.setContentsMargins(0, 0, 0, 0)
        rating_row.setSpacing(4)
        for rating in range(1, 11):
            control = QPushButton(str(rating))
            control.setObjectName("entry_rating")
            control.setAutoDefault(False)
            control.setDefault(False)
            control.setMinimumSize(32, 38)
            control.setCheckable(True)
            control.setCursor(Qt.PointingHandCursor)
            control.setAccessibleName(f"Rate {rating} out of 10")
            self.rating_choices.addButton(control, rating)
            rating_row.addWidget(control, 1)
        self.rating_choices.buttonClicked.connect(self._select_rating)
        col.addWidget(rating_widget)
        col.addWidget(plain_label("Click a score pill to toggle rating.", "entry_field_helper"))
        col.addStretch()
        return col

    def refresh_home_style(self):
        """Reapply Twilight Sakura styles and scaled metrics on theme/scale changes."""
        c = palette()
        self.setProperty("animevaultOwnScaledStyle", True)
        self.setStyleSheet(dialog_qss(self.objectName()))
        apply_input_palettes(self)
        refresh_chrome_scale(self)
        if hasattr(self, "cover_preview"):
            self.cover_preview.setFixedSize(px(156), px(234))
        if hasattr(self, "rating_choices"):
            for btn in self.rating_choices.buttons():
                btn.setMinimumSize(px(30), px(38))
        if self._browse_btn is not None:
            self._browse_btn.setIcon(icon("organizer", c["muted"]))
        if hasattr(self, "save_btn"):
            self.save_btn.setIcon(icon("check", c["on_coral"]))

    def showEvent(self, event):
        center_modal_show(self, event, super().showEvent)

    def _select_rating(self, selected):
        for button in self.rating_choices.buttons():
            if button is not selected:
                button.setChecked(False)
        self._update_rating_readout()

    def _update_rating_readout(self):
        if self._rating_readout is None or not hasattr(self, "rating_choices"):
            return
        rating = self.rating_choices.checkedId()
        if rating > 0:
            self._rating_readout.setText(f"{rating} / 10 ({_RATING_LABELS.get(rating, '')})")
        else:
            self._rating_readout.setText("Not rated")

    def _set_cover_pixmap(self, pixmap):
        w = max(140, self.cover_preview.width() - 6)
        h = max(210, self.cover_preview.height() - 6)
        self.cover_preview.setPixmap(pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.cover_preview.setProperty("has_image", "true")
        self.cover_preview.style().unpolish(self.cover_preview)
        self.cover_preview.style().polish(self.cover_preview)

    def _populate_fields(self):
        """Fill in fields from existing franchise data."""
        d = self.franchise_data
        self.display_title_input.setText(d.get("display_title", ""))
        self.title_en_input.setText(d.get("title_en", "") or "")
        self.title_romaji_input.setText(d.get("title_romaji", "") or "")
        self.title_native_input.setText(d.get("title_native", "") or "")
        self.synopsis_input.setPlainText(d.get("synopsis", "") or "")

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
            self._update_rating_readout()
        self.notes_input.setPlainText(d.get("user_notes", "") or "")
        self.folder_input.setText(d.get("root_folder_path", "") or "")

        if d.get("cover_filename"):
            cover_path = COVERS_DIR / d["cover_filename"]
            if cover_path.is_file():
                self._set_cover_pixmap(QPixmap(str(cover_path)))

    def _pick_cover_image(self):
        """Open file dialog to pick a custom cover image."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cover Image", "", "Images (*.jpg *.jpeg *.png *.webp *.bmp)"
        )
        if path:
            self.custom_cover_path = path
            self._set_cover_pixmap(QPixmap(path))

    def _grab_thumbnail(self):
        """Extract a frame from Episode 1 video using FFmpeg."""
        folder = self.folder_input.text().strip()
        if not folder:
            QMessageBox.information(
                self, "No Folder", "Please set the root folder first to find Episode 1."
            )
            return

        from app.core.entry_service import grab_frame
        from app.ui.io_task import start

        start(self, lambda: grab_frame(folder), self._frame_ready)

    def _frame_ready(self, result):
        self.custom_cover_path, image = result
        self._set_cover_pixmap(QPixmap.fromImage(image))

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Anime Folder")
        if folder:
            self.folder_input.setText(folder)

    def _save(self):
        """Save the custom entry to the database."""
        display_title = self.display_title_input.text().strip()
        if not display_title:
            QMessageBox.warning(self, "Required", "Display Title is required.")
            return

        genres_text = self.genres_input.text().strip()
        genres_list = [g.strip() for g in genres_text.split(",") if g.strip()] if genres_text else []

        rating = (
            self.rating_combo.currentData()
            if hasattr(self, "rating_combo")
            else self.rating_choices.checkedId()
        )

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
        worker = getattr(self, "_apply_worker", None)
        if worker and worker.isRunning():
            return
        super().reject()
