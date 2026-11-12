"""A release count with a clickable hover preview."""
from PyQt5.QtCore import Qt, QPoint, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QRectF
from PyQt5.QtGui import QCursor, QPainter, QFont, QColor
from PyQt5.QtWidgets import QPushButton, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QSizePolicy, QApplication
from app.config import COVERS_DIR
from app.ui.refresh import refresh_pixmap, refresh_image_exists


class _ReleasePreview(QFrame):
    def refresh_home_style(self):
        # Theme scopes can restyle top-level tools on Show. Retain the popup's
        # own row geometry instead of inheriting general button padding.
        if hasattr(self,'_preview_stylesheet') and self.styleSheet()!=self._preview_stylesheet:
            self.setStyleSheet(self._preview_stylesheet)
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
        from app.ui.home_style import colors,px
        c=colors()
        preview.setProperty('animevaultOwnScaledStyle',True)
        preview.setStyleSheet(f'''
            QFrame#airing_preview {{background:{c['panel']};border:1px solid {c['line']};border-radius:12px;}}
            QWidget#airing_preview_content, QScrollArea#airing_preview_scroll, QScrollArea#airing_preview_scroll > QWidget {{background:{c['panel']};border:none;}}
            QPushButton#airing_preview_item {{background:{c['raised']};border:1px solid {c['line']};border-radius:10px;padding:0;min-height:{px(76)-2}px;max-height:{px(76)-2}px;}}
            QPushButton#airing_preview_item:hover {{border-color:{c['coral']};border-left:3px solid {c['coral']};}}
            QPushButton#airing_preview_item QLabel {{background:transparent;border:none;color:{c['text']};font-family:'Plus Jakarta Sans';font-size:{px(13)}px;}}
            QLabel#airing_preview_title {{font-weight:600;}}
            QPushButton#airing_preview_item QLabel#airing_preview_meta {{color:{c['muted']};font-family:'JetBrains Mono';font-size:{px(11)}px;}}
        ''')
        preview._preview_stylesheet=preview.styleSheet()
        screen=self.screen().availableGeometry()
        popup_width=min(px(380),screen.width()-24)
        layout = QVBoxLayout(preview)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)
        content = QWidget()
        content.setObjectName("airing_preview_content")
        rows = QVBoxLayout(content)
        rows.setContentsMargins(0, 0, 0, 0);rows.setAlignment(Qt.AlignTop)
        rows.setSpacing(8)
        for entry in self.entries:
            item = QPushButton()
            item.setObjectName("airing_preview_item")
            item.setMinimumWidth(0)
            item.setFixedHeight(px(76))
            item.setFocusPolicy(Qt.NoFocus)
            item.setCursor(Qt.PointingHandCursor)
            item.clicked.connect(lambda checked=False, release=entry: self._choose(release))
            row = QHBoxLayout(item)
            row.setContentsMargins(8, 6, 8, 6)
            row.setSpacing(10)
            poster = QLabel()
            poster.setFixedSize(px(32), px(48))
            poster.setObjectName("airing_preview_poster")
            cover = entry.get("cover")
            if cover and refresh_image_exists(COVERS_DIR / cover):
                poster.setPixmap(refresh_pixmap(COVERS_DIR / cover).scaled(
                    px(32), px(48), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            row.addWidget(poster)
            words = entry["title"].split()
            short = " ".join(words[:8]) + ("\u2026" if len(words) > 8 else "")
            title = QLabel()
            title.setObjectName("airing_preview_title")
            text_width=popup_width-px(32)-64
            title.setFixedWidth(text_width)
            title.setTextFormat(Qt.PlainText)
            title.ensurePolished()
            title.setText(title.fontMetrics().elidedText(short, Qt.ElideRight, text_width))
            title.setToolTip(entry['title'])
            details = QVBoxLayout()
            details.setSpacing(4)
            details.setContentsMargins(0,0,0,0)
            details.setAlignment(Qt.AlignVCenter)
            details.addWidget(title)
            note = QLabel(f"EP {entry['episode']} / {entry['time']}"+(' · '+entry['download_label'] if entry.get('download_label') else ''))
            note.setObjectName("airing_preview_meta")
            note.setFixedWidth(text_width)
            note.setToolTip(note.text())
            note.setText(note.fontMetrics().elidedText(note.text(),Qt.ElideRight,text_width))
            details.addWidget(note)
            row.addLayout(details)
            for child in item.findChildren(QLabel):
                child.setAttribute(Qt.WA_TransparentForMouseEvents)
            rows.addWidget(item)
            title.ensurePolished();title.setText(title.fontMetrics().elidedText(short,Qt.ElideRight,text_width))
            note.ensurePolished();note.setText(note.fontMetrics().elidedText(note.toolTip(),Qt.ElideRight,text_width))
        scroll = QScrollArea()
        scroll.setObjectName("airing_preview_scroll")
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setFixedWidth(popup_width-16)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content.layout().activate()
        visible_rows=min(3,len(self.entries))
        required=visible_rows*px(76)+rows.spacing()*max(0,visible_rows-1)
        scroll.setFixedHeight(min(screen.height()-48,required))
        layout.addWidget(scroll)
        preview.setFixedSize(popup_width,scroll.height()+16)
        owner = getattr(self, "hover_owner", self)
        point = owner.mapToGlobal(QPoint(0, owner.height() + 6))
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
        self.dot.setVisible(bool(entries) and not today)
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
            meta.setToolTip(meta.text())
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
        if self.width() < 140:
            self.surface.layout().setContentsMargins(10, 10, 10, 10)
        else:
            self.surface.layout().setContentsMargins(14, 10, 14, 10)
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
