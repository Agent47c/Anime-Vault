from app.preferences import motion_duration
from app.ui.refresh import refresh_pixmap, refresh_image_exists
"""
Poster Card component.
Recreates the exact visual design from the UI Reference mockups:
- Translucent top-left status pill (On disk, Partial, Removed)
- Top-right tag pills (New, 18+)
- Japanese Kanji watermark on fallback gradients
- Clean title + star rating + GB subline
- Rich hover state and Romaji/Japanese tooltips
"""

from html import escape

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSizePolicy,
    QFrame,
)
from PyQt5.QtGui import (
    QPixmap, QFont, QColor, QPainter, QPainterPath, QCursor,
    QLinearGradient, QTextLayout, QTextOption,
)
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPoint, QPropertyAnimation, QEasingCurve, QEvent

from app.config import COVERS_DIR

# Rich gradient palettes matching the reference mockup
GRADIENT_PRESETS = [
    ("#1e40af", "#3b82f6", "葬"),  # Deep blue
    ("#4c1d95", "#7c3aed", "俺"),  # Indigo / purple
    ("#831843", "#db2777", "癒"),  # Magenta / ruby
    ("#78350f", "#d97706", "霊"),  # Amber / gold
    ("#3b1d11", "#78350f", "巨"),  # Brown / bronze
    ("#7f1d1d", "#dc2626", "鬼"),  # Crimson
    ("#064e3b", "#059669", "道"),  # Emerald
    ("#1f2937", "#4b5563", "界"),  # Slate
]


class PosterCard(QFrame):
    """Clickable poster card replicating the UI Reference designs."""

    clicked = pyqtSignal(int)  # franchise_id

    CARD_WIDTH = 166
    POSTER_HEIGHT = 249
    HOVER_LIFT = 5

    def __init__(self, franchise_data: dict, parent=None):
        super().__init__(parent)
        self.franchise_data = franchise_data
        self.franchise_id = franchise_data["id"]
        self.setObjectName("poster_card")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedWidth(self.CARD_WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)

        self._setup_ui()
        self._setup_tooltip()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(8)

        # 1. Poster Container (with embedded top badges)
        poster_slot = QWidget()
        poster_slot.setFixedSize(self.CARD_WIDTH, self.POSTER_HEIGHT + self.HOVER_LIFT)
        self.poster_label = QLabel(poster_slot)
        self.poster_label.move(0, self.HOVER_LIFT)
        self.poster_label.setFixedSize(self.CARD_WIDTH, self.POSTER_HEIGHT)
        self.poster_label.setScaledContents(False)

        # Generate the poster pixmap (either loaded image or gradient + kanji watermark)
        pixmap = self._create_poster_pixmap()
        self.poster_label.setPixmap(pixmap)
        layout.addWidget(poster_slot)
        self._lift = QPropertyAnimation(self.poster_label, b"pos", self)
        self._lift.setDuration(140)
        self._lift.setEasingCurve(QEasingCurve.OutCubic)

        # 2. Text Details below poster
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(2, 0, 2, 0)
        text_layout.setSpacing(3)

        # Title
        raw_title = self.franchise_data.get("display_title") or "Unknown Title"
        self.title_label = QLabel(raw_title)
        self.title_label.setObjectName("card_title")
        self.title_label.installEventFilter(self)
        self.title_label.setStyleSheet("color: #f3f4f6; font-size: 13px; font-weight: 600;")
        self.title_label.setTextFormat(Qt.PlainText)
        self._raw_title = raw_title
        self._update_title()
        text_layout.addWidget(self.title_label)

        # Subline: Star Rating & Storage Info
        subline_parts = []
        rating = self.franchise_data.get("user_rating")
        if rating:
            subline_parts.append(f"★ {rating}")

        storage_state = self.franchise_data.get("storage_state", "ON_DISK")
        size_bytes = self.franchise_data.get("total_size_bytes", 0) or 0

        if storage_state == "WATCHED_REMOVED":
            subline_parts.append("Watched, removed")
        elif storage_state == "PARTIALLY_ON_DISK":
            if size_bytes >= 1024 ** 3:
                subline_parts.append(f"{size_bytes / (1024 ** 3):.1f} of disk")
            else:
                subline_parts.append("Partially on disk")
        elif size_bytes > 0:
            if size_bytes >= 1024 ** 3:
                subline_parts.append(f"{size_bytes / (1024 ** 3):.1f} GB")
            else:
                subline_parts.append(f"{size_bytes / (1024 ** 2):.0f} MB")
        else:
            subline_parts.append("Not on disk")

        subline_text = " · ".join(subline_parts) if subline_parts else "No details"
        self.subline_label = QLabel(subline_text)
        self.subline_label.setStyleSheet("color: #b0b3c2; font-size: 11px; font-weight: 500;")
        if self.franchise_data.get("release_count", 1) > 1:
            self.subline_label.setText(f"{self.franchise_data['release_count']} releases · " + subline_text)
        else:
            self.subline_label.hide()

        layout.addWidget(text_container)

    def _update_title(self):
        if getattr(self, "_updating_title", False):
            return
        self._updating_title = True
        self.title_label.ensurePolished()
        raw_title = self._raw_title
        font_metrics = self.title_label.fontMetrics()
        width = self.CARD_WIDTH - 4
        title = " ".join(raw_title.split()) or "Unknown Title"
        wrapped = QTextLayout(title, self.title_label.font())
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        wrapped.setTextOption(option)
        wrapped.beginLayout()
        first = wrapped.createLine()
        first.setLineWidth(width)
        length = len(title.encode("utf-16-le")[:2 * first.textLength()].decode("utf-16-le"))
        wrapped.endLayout()
        remainder = title[length:].lstrip()
        if remainder:
            title = title[:length].rstrip() + "\n" + font_metrics.elidedText(remainder, Qt.ElideRight, width)
        self.title_label.setText(title)
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.title_label.setFixedHeight(2 * font_metrics.lineSpacing() + 2)
        self._updating_title = False

    def eventFilter(self, obj, event):
        if obj is getattr(self, "title_label", None) and event.type() == QEvent.FontChange and hasattr(self, "_raw_title"):
            self._update_title()
        return super().eventFilter(obj, event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.FontChange and hasattr(self, "_raw_title"):
            self._update_title()

    def _create_poster_pixmap(self) -> QPixmap:
        """Create a rounded poster pixmap with baked badges and watermark."""
        target_pixmap = QPixmap(self.CARD_WIDTH, self.POSTER_HEIGHT)
        target_pixmap.fill(Qt.transparent)

        painter = QPainter(target_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # Create rounded clipping path
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.CARD_WIDTH, self.POSTER_HEIGHT, 14, 14)
        painter.setClipPath(path)

        # Check if actual cover exists
        cover = self.franchise_data.get("cover_filename")
        cover_path = COVERS_DIR / cover if cover else None
        has_image = cover_path and refresh_image_exists(cover_path)

        if has_image:
            img = refresh_pixmap(cover_path)
            if not img.isNull():
                scaled = img.scaled(
                    self.CARD_WIDTH, self.POSTER_HEIGHT,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation,
                )
                x = max(0, (scaled.width() - self.CARD_WIDTH) // 2)
                y = max(0, (scaled.height() - self.POSTER_HEIGHT) // 2)
                painter.drawPixmap(0, 0, scaled, x, y, self.CARD_WIDTH, self.POSTER_HEIGHT)
            else:
                has_image = False

        if not has_image:
            # Deterministic gradient preset based on franchise_id
            idx = self.franchise_id % len(GRADIENT_PRESETS)
            c1, c2, kanji = GRADIENT_PRESETS[idx]

            # If native title has kanji, use its first character
            native = self.franchise_data.get("title_native")
            if native and len(native) > 0:
                for ch in native:
                    if ord(ch) > 0x4E00:
                        kanji = ch
                        break

            # Draw vertical gradient
            grad = QLinearGradient(0, 0, 0, self.POSTER_HEIGHT)
            grad.setColorAt(0, QColor(c1))
            grad.setColorAt(1, QColor(c2))
            painter.fillRect(0, 0, self.CARD_WIDTH, self.POSTER_HEIGHT, grad)

            # Draw huge subtle Kanji watermark in the bottom center
            painter.setPen(QColor(255, 255, 255, 235))
            kanji_font = QFont("Segoe UI", 52, QFont.Bold)
            painter.setFont(kanji_font)
            painter.drawText(
                QRectF(0, 0, self.CARD_WIDTH, self.POSTER_HEIGHT),
                Qt.AlignCenter,
                (self.franchise_data.get("display_title") or "ア")[0].upper(),
            )

        # Dark gradient vignette at top for badge legibility
        top_vignette = QLinearGradient(0, 0, 0, 60)
        top_vignette.setColorAt(0, QColor(0, 0, 0, 110))
        top_vignette.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillRect(0, 0, self.CARD_WIDTH, 60, top_vignette)

        # -------------------------------------------------------------------
        # Badges (Top-Left & Top-Right)
        # -------------------------------------------------------------------
        # Reset clipping for sharp badge rendering within boundaries
        painter.setClipping(False)

        # 1. Top-Left Badge: Storage status
        storage_state = self.franchise_data.get("storage_state", "ON_DISK")
        if storage_state == "ON_DISK":
            dot_color = QColor("#22c55e")  # Green
            status_text = "On disk"
        elif storage_state == "PARTIALLY_ON_DISK":
            dot_color = QColor("#f59e0b")  # Amber
            status_text = "Partial"
        else:
            dot_color = QColor("#94a3b8")  # Slate
            status_text = "Removed"

        # Storage details remain available in the detail view.

        # 2. Top-Right Badge: 'New' or '18+'
        is_adult = self.franchise_data.get("is_adult")
        has_update = self.franchise_data.get("has_new_update")

        if is_adult:
            self._draw_tag_pill(painter, self.CARD_WIDTH - 38, 10, "18+", QColor("#4c0519"), QColor("#df2545"))
        elif has_update:
            self._draw_tag_pill(painter, self.CARD_WIDTH - 46, 10, "New", QColor("#df2545"), QColor("#ffffff"))

        painter.end()
        return target_pixmap

    def _draw_storage_pill(self, painter: QPainter, x: int, y: int, text: str, dot_color: QColor):
        """Draw translucent status pill (e.g., ● On disk)."""
        font = QFont("Segoe UI", 8, QFont.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(text)
        pill_width = text_width + 24
        pill_height = 20

        # Translucent background
        painter.setBrush(QColor(14, 16, 24, 210))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(x, y, pill_width, pill_height), 10, 10)

        # Indicator dot
        painter.setBrush(dot_color)
        painter.drawEllipse(QRectF(x + 7, y + 6, 7, 7))

        # Text
        painter.setPen(QColor("#f3f4f6"))
        painter.drawText(QRectF(x + 18, y, text_width + 4, pill_height), Qt.AlignVCenter, text)

    def _draw_tag_pill(self, painter: QPainter, x: int, y: int, text: str, bg_color: QColor, text_color: QColor):
        """Draw tag badge pill (e.g. New or 18+)."""
        font = QFont("Segoe UI", 8, QFont.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(text)
        pill_width = text_width + 14
        pill_height = 20

        painter.setBrush(bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(x, y, pill_width, pill_height), 8, 8)

        painter.setPen(text_color)
        painter.drawText(QRectF(x, y, pill_width, pill_height), Qt.AlignCenter, text)

    def _setup_tooltip(self):
        """Rich HTML tooltip displaying Romaji and Japanese titles on hover."""
        title_en = self.franchise_data.get("display_title") or self.franchise_data.get("title_en") or "Unknown Title"
        title_romaji = self.franchise_data.get("title_romaji", "")
        title_native = self.franchise_data.get("title_native", "")
        genres = self.franchise_data.get("genres", "[]")

        tooltip_lines = [f"<b style='color:#df2545; font-size:13px;'>{escape(title_en)}</b>"]
        if title_romaji and title_romaji != title_en:
            tooltip_lines.append(f"<span style='color:#9ca3af;'>Romaji:</span> {escape(title_romaji)}")
        if title_native:
            tooltip_lines.append(f"<span style='color:#9ca3af;'>Japanese:</span> {escape(title_native)}")

        try:
            import json
            genre_list = json.loads(genres) if isinstance(genres, str) else genres
            if genre_list:
                tooltip_lines.append(f"<span style='color:#898d9f;'>Genres:</span> {', '.join(genre_list[:4])}")
        except Exception:
            pass

        self.setToolTip("<br>".join(tooltip_lines))

    def _animate_lift(self, raised):
        self._lift.setDuration(motion_duration(140))
        self._lift.stop()
        self._lift.setStartValue(self.poster_label.pos())
        self._lift.setEndValue(QPoint(0, 0 if raised else self.HOVER_LIFT))
        self._lift.start()

    def enterEvent(self, event):
        super().enterEvent(event)
        self._animate_lift(True)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._animate_lift(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.franchise_id)
            event.accept()
        else:
            super().mousePressEvent(event)
