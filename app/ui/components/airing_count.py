"""A release count with a clickable hover preview."""
from PyQt5.QtCore import Qt, QPoint, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QRectF
from PyQt5.QtGui import QCursor, QPainter, QFont, QColor
from PyQt5.QtWidgets import QPushButton, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QSizePolicy, QApplication
from app.config import COVERS_DIR
from app.ui.refresh import refresh_pixmap, refresh_image_exists


class _ReleasePreview(QFrame):
    def enterEvent(self, event):
        self.parentWidget()._close_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.parentWidget()._close_timer.start()
        super().leaveEvent(event)


class AiringCount(QPushButton):
    selected = pyqtSignal(dict)

    def __init__(self, entries, parent=None):
        super().__init__(parent)
        self.entries = entries
        self.preview = None
        self.setFocusPolicy(Qt.TabFocus)
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(250)
        self._hover_timer.timeout.connect(self._show_preview)
        self.clicked.connect(self._show_preview)
        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.setInterval(350)
        self._close_timer.timeout.connect(self._close_if_outside)

    def enterEvent(self, event):
        super().enterEvent(event)
        self._close_timer.stop()
        if self.preview is None:
            self._hover_timer.start()

    def _show_preview(self):
        if not self.entries:
            return
        self._hover_timer.stop()
        self._close_timer.stop()
        if self.preview is not None:
            return
        preview = _ReleasePreview(self, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus)
        self.preview = preview
        preview.setObjectName("airing_preview")
        preview.setAttribute(Qt.WA_ShowWithoutActivating)
        preview.setFocusPolicy(Qt.NoFocus)
        layout = QVBoxLayout(preview)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)
        content = QWidget()
        content.setObjectName("airing_preview_content")
        rows = QVBoxLayout(content)
        rows.setContentsMargins(0, 0, 0, 0)
        rows.setSpacing(8)
        for entry in self.entries:
            item = QPushButton()
            item.setObjectName("airing_preview_item")
            item.setMinimumSize(314, 64)
            item.setFocusPolicy(Qt.NoFocus)
            item.setCursor(Qt.PointingHandCursor)
            item.clicked.connect(lambda checked=False, release=entry: self._choose(release))
            row = QHBoxLayout(item)
            row.setContentsMargins(8, 6, 8, 6)
            row.setSpacing(10)
            poster = QLabel()
            poster.setFixedSize(32, 48)
            poster.setObjectName("airing_preview_poster")
            cover = entry.get("cover")
            if cover and refresh_image_exists(COVERS_DIR / cover):
                poster.setPixmap(refresh_pixmap(COVERS_DIR / cover).scaled(
                    32, 48, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            row.addWidget(poster)
            words = entry["title"].split()
            short = " ".join(words[:8]) + ("\u2026" if len(words) > 8 else "")
            title = QLabel()
            title.setObjectName("airing_preview_title")
            title.setFixedWidth(240)
            title.setTextFormat(Qt.PlainText)
            title.ensurePolished()
            title.setText(title.fontMetrics().elidedText(short, Qt.ElideRight, 240))
            details = QVBoxLayout()
            details.setSpacing(4)
            details.addWidget(title)
            note = QLabel(f"EP {entry['episode']} / {entry['time']}")
            note.setObjectName("subheading")
            details.addWidget(note)
            row.addLayout(details)
            for child in item.findChildren(QLabel):
                child.setAttribute(Qt.WA_TransparentForMouseEvents)
            rows.addWidget(item)
        scroll = QScrollArea()
        scroll.setObjectName("airing_preview_scroll")
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setFixedWidth(330)
        scroll.setFixedHeight(min(420, content.sizeHint().height() + 4))
        layout.addWidget(scroll)
        preview.adjustSize()
        owner = getattr(self, "hover_owner", self)
        point = owner.mapToGlobal(QPoint(0, owner.height() + 6))
        screen = self.screen().availableGeometry()
        x = max(screen.left(), min(point.x(), screen.right() - preview.width()))
        y = point.y() if point.y() + preview.height() <= screen.bottom() else owner.mapToGlobal(QPoint()).y() - preview.height() - 6
        preview.move(x, max(screen.top(), y))
        preview.show()

    def _close_if_outside(self):
        point = QCursor.pos()
        owner = getattr(self, "hover_owner", self)
        over_count = owner.rect().contains(owner.mapFromGlobal(point))
        over_preview = self.preview is not None and self.preview.frameGeometry().contains(point)
        if not over_count and not over_preview:
            self._hide_preview()

    def _choose(self, entry):
        self._hide_preview()
        self.selected.emit(entry)

    def _hide_preview(self):
        self._hover_timer.stop()
        self._close_timer.stop()
        if self.preview is not None:
            self.preview.hide()
            self.preview.deleteLater()
            self.preview = None

    def leaveEvent(self, event):
        self._hover_timer.stop()
        self._close_timer.start()
        super().leaveEvent(event)

    def hideEvent(self, event):
        self._hide_preview()
        super().hideEvent(event)


class _DaySurface(QFrame):
    def __init__(self, glyph, parent):
        super().__init__(parent)
        self.glyph = glyph

    def paintEvent(self, event):
        super().paintEvent(event)
        app = QApplication.instance()
        if app.property("animevaultDecorations") is False:
            return
        from app.ui.theme import COLORS
        colors = COLORS.get(app.property("animevaultTheme"), COLORS["dark"])
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        font = QFont("Yu Gothic", 44, QFont.Bold)
        painter.setFont(font)
        color = QColor(colors["text_muted"])
        color.setAlpha(28)
        painter.setPen(color)
        painter.drawText(QRectF(self.width()-74, self.height()-70, 84, 90), Qt.AlignCenter, self.glyph)


class AiringDay(QWidget):
    """Compact schedule tile with an existing release preview and a hover lift."""
    selected = pyqtSignal(dict)

    def __init__(self, date, today, glyph, entries, parent=None):
        super().__init__(parent)
        from app.ui.components.design import ElidedLabel
        self.date, self.today = date, today
        self.setFixedHeight(130)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.surface = _DaySurface(glyph, self)
        self.surface.setObjectName("airing_day")
        self.surface.setProperty("today", today)
        self.surface.setFixedHeight(122)
        column = QVBoxLayout(self.surface)
        column.setContentsMargins(14, 10, 14, 10)
        column.setSpacing(10)
        headings = QHBoxLayout()
        headings.setSpacing(6)
        self.date_label = QLabel()
        self.date_label.setObjectName("airing_date")
        self.date_label.setToolTip(date.strftime("%A, %d %B %Y"))
        headings.addWidget(self.date_label)
        headings.addStretch()
        if today:
            badge = QLabel("TODAY")
            badge.setObjectName("airing_today_badge")
            headings.addWidget(badge)
        self.dot = QLabel()
        self.dot.setObjectName("airing_release_dot")
        self.dot.setFixedSize(6, 6)
        self.dot.setVisible(bool(entries))
        headings.addWidget(self.dot)
        column.addLayout(headings)
        self.release_button = AiringCount(entries, self.surface)
        self.release_button.hover_owner = self
        self.release_button.setObjectName("airing_release")
        self.release_button.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.release_button.setAccessibleName(f"{date.strftime('%A')}: {len(entries)} scheduled releases")
        self.release_button.selected.connect(self.selected.emit)
        self.release_button.setCursor(Qt.PointingHandCursor if entries else Qt.ArrowCursor)
        details = QVBoxLayout(self.release_button)
        details.setContentsMargins(0, 0, 0, 0)
        details.setSpacing(4)
        details.addStretch()
        if entries:
            first = entries[0]
            title = ElidedLabel(first["title"])
            title.setObjectName("airing_release_title")
            details.addWidget(title)
            meta = QLabel(f"EP {first.get('episode', '?')} \u00b7 {first.get('time', '')}")
            meta.setObjectName("airing_release_time")
            details.addWidget(meta)
            if len(entries) > 1:
                more = QLabel(f"+{len(entries)-1} more")
                more.setObjectName("airing_more")
                details.addWidget(more)
        else:
            empty = QLabel("No releases")
            empty.setObjectName("airing_empty")
            details.addWidget(empty)
        for label in self.release_button.findChildren(QLabel):
            label.setAttribute(Qt.WA_TransparentForMouseEvents)
        column.addWidget(self.release_button, 1)
        self.lift = QPropertyAnimation(self.surface, b"pos", self)
        self.lift.setEasingCurve(QEasingCurve.OutCubic)
        self.setAccessibleName(self.release_button.accessibleName())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.surface.resize(self.width(), 122)
        self.surface.move(0, 4)
        self.date_label.setText(self.date.strftime("%a").upper() + ("  " + self.date.strftime("%d") if not self.today or self.width() >= 150 else ""))
        self.dot.setVisible(bool(self.release_button.entries) and (not self.today or self.width() >= 160))

    def _lift(self, hovering):
        from app.preferences import motion_duration
        self.lift.stop()
        self.lift.setDuration(motion_duration(180))
        self.lift.setStartValue(self.surface.pos())
        self.lift.setEndValue(QPoint(0, 0 if hovering else 4))
        self.lift.start()

    def enterEvent(self, event):
        super().enterEvent(event)
        self._lift(True)
        self.release_button._close_timer.stop()
        if self.release_button.entries and self.release_button.preview is None:
            self.release_button._hover_timer.start()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._lift(False)
        self.release_button._hover_timer.stop()
        self.release_button._close_timer.start()
