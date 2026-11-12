"""Twilight Sakura presentation and shared chrome for Add/Edit Entry and TXT Importer."""
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QLinearGradient, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from app.config import COVERS_DIR
from app.ui.button_system import unified
from app.ui.components.close_button import CloseButton
from app.ui.components.design import MotifHeader
from app.ui.components.smooth_scroll import SmoothScrollArea
from app.ui.home_style import colors, load_fonts, px
from app.ui.icons import icon


_font_fallbacks_registered = False


def palette():
    """Return Twilight Sakura palette adapted for dark, light, and high-contrast themes."""
    global _font_fallbacks_registered
    load_fonts()
    if not _font_fallbacks_registered:
        QFont.insertSubstitutions("Plus Jakarta Sans", ["Yu Gothic UI", "Yu Gothic", "MS Gothic", "Segoe UI"])
        QFont.insertSubstitutions("JetBrains Mono", ["Yu Gothic UI", "Yu Gothic", "Segoe UI"])
        _font_fallbacks_registered = True
    app = QApplication.instance()
    c = dict(colors())
    high_contrast = bool(app and app.property("animevaultHighContrast"))
    light = bool(app and app.property("animevaultTheme") == "light")
    if high_contrast:
        c.update(
            card=c["raised"],
            line_light=c["line"],
            muted_dim=c["muted"],
            coral_soft=c["raised"],
            coral_border=c["coral"],
            indigo=c["text"],
            indigo_soft=c["raised"],
            indigo_border=c["line"],
            ok_soft=c["raised"],
            ok_border=c["line"],
            amber_soft=c["raised"],
            amber_border=c["line"],
            danger=c["coral"],
            danger_soft=c["raised"],
            danger_border=c["coral"],
            primary_end=c["coral"],
        )
        return c
    if light:
        c.update(
            panel="#ffffff",
            card="#faf6fa",
            raised="#f1e9f1",
            line="#d8c9d9",
            line_light="#c1adc4",
            muted_dim="#786a82",
            coral="#d92659",
            primary_end="#b0284b",
            on_coral="#ffffff",
            coral_soft="rgba(217, 38, 89, 0.10)",
            coral_border="rgba(217, 38, 89, 0.30)",
            indigo="#4338ca",
            indigo_soft="rgba(67, 56, 202, 0.10)",
            indigo_border="rgba(67, 56, 202, 0.28)",
            ok="#087b60",
            ok_soft="rgba(8, 123, 96, 0.10)",
            ok_border="rgba(8, 123, 96, 0.28)",
            amber="#925408",
            amber_soft="rgba(146, 84, 8, 0.10)",
            amber_border="rgba(146, 84, 8, 0.28)",
            danger="#be123c",
            danger_soft="rgba(190, 18, 60, 0.10)",
            danger_border="rgba(190, 18, 60, 0.28)",
        )
        return c
    # Default Twilight Sakura dark tokens aligned with reference screens.
    c.update(
        bg="#14121d",
        panel="#191724",
        card="#1f1c2e",
        raised="#262335",
        line="#2a263a",
        line_light="#39344d",
        text="#f5f3f8",
        muted="#9b94b0",
        muted_dim="#78708d",
        coral="#f43f5e",
        primary_end="#e11d48",
        on_coral="#ffffff",
        coral_soft="rgba(244, 63, 94, 0.14)",
        coral_border="rgba(244, 63, 94, 0.36)",
        indigo="#a5b4fc",
        indigo_soft="rgba(99, 102, 241, 0.15)",
        indigo_border="rgba(99, 102, 241, 0.34)",
        ok="#34d399",
        ok_soft="rgba(16, 185, 129, 0.12)",
        ok_border="rgba(16, 185, 129, 0.30)",
        amber="#fbbf24",
        amber_soft="rgba(245, 158, 11, 0.12)",
        amber_border="rgba(245, 158, 11, 0.30)",
        danger="#fb7185",
        danger_soft="rgba(244, 63, 94, 0.12)",
        danger_border="rgba(244, 63, 94, 0.30)",
    )
    return c


class TwilightComboBox(QComboBox):
    """QComboBox with crisp painted vector chevron across all DPI scales and themes."""

    def paintEvent(self, event):
        super().paintEvent(event)
        c = palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(c["muted"]), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        cx = self.width() - px(16)
        cy = self.height() / 2.0
        half = px(4)
        painter.drawLine(int(cx - half), int(cy - half * 0.45), int(cx), int(cy + half * 0.55))
        painter.drawLine(int(cx), int(cy + half * 0.55), int(cx + half), int(cy - half * 0.45))


class TwilightCheckBox(QCheckBox):
    """Custom-painted checkbox so checked state displays a crisp checkmark in all themes."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        c = palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        box_size = px(18)
        y = (self.height() - box_size) / 2
        x = 1 if not self.text() else 2
        rect = QRectF(x, y, box_size, box_size)
        checked = self.isChecked()
        enabled = self.isEnabled()
        border_col = c["coral"] if checked and enabled else c["line_light"] if enabled else c["line"]
        fill_col = c["coral"] if checked and enabled else c["raised"] if enabled else c["bg"]
        painter.setPen(QPen(QColor(border_col), 1.4))
        painter.setBrush(QColor(fill_col))
        painter.drawRoundedRect(rect, px(5), px(5))
        if checked:
            painter.setPen(QPen(QColor(c["on_coral"]), 2.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            rx, ry = rect.x(), rect.y()
            painter.drawLine(int(rx + box_size * 0.24), int(ry + box_size * 0.52), int(rx + box_size * 0.43), int(ry + box_size * 0.72))
            painter.drawLine(int(rx + box_size * 0.43), int(ry + box_size * 0.72), int(rx + box_size * 0.78), int(ry + box_size * 0.30))
        if self.text():
            painter.setPen(QColor(c["text"] if enabled else c["muted"]))
            painter.setFont(self.font())
            painter.drawText(self.rect().adjusted(int(x + box_size + px(10)), 0, -2, 0), Qt.AlignVCenter | Qt.AlignLeft, self.text())
        if self.hasFocus():
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(c["coral"]), 1.5))
            painter.drawRoundedRect(QRectF(rect.adjusted(-2, -2, 2, 2)), px(6), px(6))


class StatusDot(QWidget):
    """Crisp circular indicator dot used in headers, KPI cards, and footer status cues."""

    def __init__(self, tone="coral", size=8, parent=None):
        super().__init__(parent)
        self.tone = tone
        self._size = size
        self.setFixedSize(px(size + 4), px(size + 4))

    def set_tone(self, tone):
        self.tone = tone
        self.update()

    def paintEvent(self, event):
        c = palette()
        color_map = {
            "coral": c["coral"],
            "existing": c["ok"],
            "matched": c["indigo"],
            "review": c["amber"],
            "unmatched": c["danger"],
            "muted": c["muted"],
        }
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        d = px(self._size)
        offset_x = (self.width() - d) / 2
        offset_y = (self.height() - d) / 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(color_map.get(self.tone, c["coral"])))
        painter.drawEllipse(QRectF(offset_x, offset_y, d, d))


def plain_label(value, object_name="workflow_hint", word_wrap=True):
    """Create a plain-text label safe against accidental rich-text interpretation."""
    label = QLabel(value)
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(word_wrap)
    label.setObjectName(object_name)
    return label


def action_button(label, callback, primary=False, object_name=None):
    """Create a Twilight Sakura dialog button with autoDefault disabled."""
    btn = QPushButton(label)
    if object_name:
        btn.setObjectName(object_name)
    btn.setProperty("accent", primary)
    btn.setAutoDefault(False)
    btn.setDefault(False)
    btn.setCursor(Qt.PointingHandCursor)
    btn.clicked.connect(callback)
    return btn


def field_block(parent_layout, label_text, control, helper=None, badge_text=None):
    """Add a labeled form field group cleanly without legacy drawer background overrides."""
    if type(control) is QWidget and not control.objectName():
        control.setObjectName("twilight_field_inner")
    group = QWidget()
    group.setObjectName("twilight_field")
    layout = QVBoxLayout(group)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    head = QHBoxLayout()
    head.setContentsMargins(0, 0, 0, 0)
    head.setSpacing(8)
    lbl = plain_label(label_text, "entry_field_label", word_wrap=False)
    head.addWidget(lbl)
    head.addStretch()
    if badge_text:
        head.addWidget(plain_label(badge_text, "entry_field_meta", word_wrap=False))
    layout.addLayout(head)
    layout.addWidget(control)
    if helper:
        layout.addWidget(plain_label(helper, "entry_field_helper"))
    control.setAccessibleName(label_text.rstrip(" *"))
    parent_layout.addWidget(group)
    return group


def poster_thumbnail(title, filename=None, width=40, height=58, tone="matched"):
    """Render a rounded poster thumbnail or Twilight Sakura placeholder matching row tone."""
    c = palette()
    pix = QPixmap(width * 2, height * 2)
    pix.setDevicePixelRatio(2)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, width, height), 6, 6)
    painter.setClipPath(path)
    source = QPixmap(str(COVERS_DIR / filename)) if filename else QPixmap()
    if not source.isNull():
        source = source.scaled(width * 2, height * 2, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        source.setDevicePixelRatio(2)
        painter.drawPixmap(round((width - source.width() / 2) / 2), round((height - source.height() / 2) / 2), source)
    else:
        grad = QLinearGradient(0, 0, width, height)
        if tone == "unmatched":
            grad.setColorAt(0, QColor(c["raised"]))
            grad.setColorAt(1, QColor(c["bg"]))
        elif tone == "muted":
            grad.setColorAt(0, QColor(c["raised"]))
            grad.setColorAt(1, QColor(c["card"]))
        else:
            grad.setColorAt(0, QColor(c["coral"]))
            grad.setColorAt(1, QColor(c["panel"]))
        painter.fillRect(0, 0, width, height, grad)
        if tone == "unmatched":
            painter.setPen(QColor(c["danger"]))
            font = painter.font()
            font.setPixelSize(px(15))
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QRectF(0, 0, width, height), Qt.AlignCenter, "?")
    painter.end()
    lbl = QLabel()
    lbl.setObjectName("import_row_thumb")
    lbl.setFixedSize(width, height)
    lbl.setPixmap(pix)
    lbl.setAccessibleName("Poster for " + title)
    return lbl


def build_twilight_chrome(dialog, title, subtitle, glyph, primary_label, callback, shortcut_text=None):
    """Build shared Twilight Sakura centered-modal header, scrollable body, and footer."""
    dialog.setAccessibleName(title)
    root = QVBoxLayout(dialog)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)

    header = MotifHeader(glyph)
    header.setObjectName("twilight_header")
    header.setMinimumHeight(px(82))
    head = QHBoxLayout(header)
    head.setContentsMargins(px(24), px(14), px(24), px(14))
    head.setSpacing(14)

    title_col = QVBoxLayout()
    title_col.setContentsMargins(0, 0, 0, 0)
    title_col.setSpacing(3)
    title_row = QHBoxLayout()
    title_row.setContentsMargins(0, 0, 0, 0)
    title_row.setSpacing(10)
    dot = StatusDot("coral", size=8)
    title_row.addWidget(dot, 0, Qt.AlignVCenter)
    title_row.addWidget(plain_label(title, "twilight_title", word_wrap=False), 0, Qt.AlignVCenter)
    if shortcut_text:
        badge = plain_label(shortcut_text, "twilight_shortcut_badge", word_wrap=False)
        title_row.addWidget(badge, 0, Qt.AlignVCenter)
    title_row.addStretch()
    title_col.addLayout(title_row)
    title_col.addWidget(plain_label(subtitle, "twilight_subtitle"))
    head.addLayout(title_col, 1)

    close_btn = CloseButton()
    close_btn.setFixedSize(px(36), px(36))
    close_btn.setAutoDefault(False)
    close_btn.setAccessibleName("Close " + title.lower())
    close_btn.clicked.connect(dialog.reject)
    head.addWidget(close_btn, 0, Qt.AlignVCenter)
    root.addWidget(header)

    scroll = SmoothScrollArea()
    scroll.setObjectName("twilight_scroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    body_widget = QWidget()
    body_widget.setObjectName("twilight_body")
    body_layout = QVBoxLayout(body_widget)
    body_layout.setContentsMargins(px(24), px(18), px(24), px(18))
    body_layout.setSpacing(14)
    body_layout.setSizeConstraint(QLayout.SetMinimumSize)
    scroll.setWidget(body_widget)
    root.addWidget(scroll, 1)

    footer = QFrame()
    footer.setObjectName("twilight_footer")
    foot = QHBoxLayout(footer)
    foot.setContentsMargins(px(24), px(14), px(24), px(14))
    foot.setSpacing(12)
    footer_note_host = QWidget()
    footer_note_host.setObjectName("twilight_footer_note")
    footer_note_layout = QHBoxLayout(footer_note_host)
    footer_note_layout.setContentsMargins(0, 0, 0, 0)
    footer_note_layout.setSpacing(8)
    foot.addWidget(footer_note_host, 1)

    cancel_btn = action_button("Cancel", dialog.reject, primary=False, object_name="twilight_cancel_btn")
    foot.addWidget(cancel_btn)
    primary_btn = action_button(primary_label, callback, primary=True, object_name="sakura_primary_btn")
    primary_btn.setIcon(icon("check", palette()["on_coral"]))
    dialog.setFocusProxy(cancel_btn)
    cancel_btn.setFocus()
    foot.addWidget(primary_btn)
    root.addWidget(footer)

    dialog.cancel_button = cancel_btn
    dialog.footer_note_layout = footer_note_layout
    return body_layout, primary_btn


def apply_input_palettes(dialog):
    """Ensure placeholder text keeps accessible contrast across dark, light, and HC themes."""
    from PyQt5.QtWidgets import QLineEdit, QTextEdit
    from PyQt5.QtGui import QPalette

    c = palette()
    placeholder = QColor(c["muted"])
    text = QColor(c["text"])
    for editor in dialog.findChildren(QLineEdit) + dialog.findChildren(QTextEdit):
        pal = editor.palette()
        pal.setColor(QPalette.PlaceholderText, placeholder)
        pal.setColor(QPalette.Text, text)
        editor.setPalette(pal)


def refresh_chrome_scale(dialog):
    """Keep CloseButton and StatusDot dimensions aligned with active text scale."""
    for close_btn in dialog.findChildren(CloseButton):
        close_btn.setFixedSize(px(36), px(36))
    for dot in dialog.findChildren(StatusDot):
        dot.setFixedSize(px(dot._size + 4), px(dot._size + 4))


def center_modal_show(dialog, event, base_show=None):
    """Center standalone parented dialogs over a dim backdrop; delegate embedded views."""
    from PyQt5.QtWidgets import QDialog

    if getattr(dialog, "_embedded", False) or getattr(dialog, "full_page", False):
        QDialog.showEvent(dialog, event)
        return
    parent = dialog.parentWidget()
    if parent:
        window = parent.window()
        if getattr(dialog, "_shade", None):
            dialog._shade.deleteLater()
        dialog._shade = QWidget(window)
        dialog._shade.setStyleSheet("background: rgba(0, 0, 0, 155);")
        dialog._shade.setGeometry(window.rect())
        dialog._shade.show()
        dialog._shade.raise_()
        origin = window.mapToGlobal(window.rect().topLeft())
        target_w = min(getattr(dialog, "workflow_width", 900), max(480, window.width() - 40))
        target_h = min(840, max(520, window.height() - 40))
        dialog.setMinimumSize(0, 0)
        dialog.setMaximumSize(16777215, 16777215)
        dialog.setFixedSize(target_w, target_h)
        dialog.move(
            origin.x() + max(0, (window.width() - target_w) // 2),
            origin.y() + max(0, (window.height() - target_h) // 2),
        )
    QDialog.showEvent(dialog, event)


@unified(lambda root_name: f"QDialog#{root_name}")
def dialog_qss(root_name):
    """Return scoped Twilight Sakura QSS for CustomEntryDialog and WatchedImportDialog."""
    c = palette()
    r = f"QDialog#{root_name}"
    return f"""
    {r} {{
        background: {c['panel']};
        color: {c['text']};
        border: 1px solid {c['line']};
        border-radius: {px(16)}px;
        font-family: "Plus Jakarta Sans";
        font-size: {px(13)}px;
    }}
    {r} QWidget#twilight_header {{
        background: {c['card']};
        border: none;
        border-bottom: 1px solid {c['line']};
        border-top-left-radius: {px(16)}px;
        border-top-right-radius: {px(16)}px;
    }}
    {r} QLabel#twilight_title {{
        color: {c['text']};
        background: transparent;
        border: none;
        font-size: {px(19)}px;
        font-weight: 700;
    }}
    {r} QLabel#twilight_subtitle {{
        color: {c['muted']};
        background: transparent;
        border: none;
        font-size: {px(12)}px;
    }}
    {r} QLabel#twilight_shortcut_badge {{
        color: {c['muted']};
        background: {c['raised']};
        border: 1px solid {c['line_light']};
        border-radius: {px(5)}px;
        padding: {px(2)}px {px(7)}px;
        font-family: "JetBrains Mono";
        font-size: {px(10)}px;
        font-weight: 600;
    }}
    {r} QScrollArea#twilight_scroll, {r} QScrollArea#twilight_scroll > QWidget, {r} QWidget#twilight_body {{
        background: {c['panel']};
        border: none;
    }}
    {r} QWidget#twilight_field, {r} QWidget#twilight_field_inner, {r} QWidget#twilight_footer_note {{
        background: transparent;
        border: none;
    }}
    {r} QLabel {{
        color: {c['text']};
        background: transparent;
        border: none;
        font-size: {px(13)}px;
    }}
    {r} QLabel#workflow_hint {{
        color: {c['muted']};
        font-size: {px(12)}px;
    }}
    {r} QLabel#workflow_row_title {{
        color: {c['text']};
        font-size: {px(14)}px;
        font-weight: 700;
    }}
    {r} QLabel#entry_section_heading {{
        color: {c['text']};
        font-size: {px(14)}px;
        font-weight: 700;
    }}
    {r} QLabel#entry_section_kicker {{
        color: {c['muted']};
        font-size: {px(11)}px;
        font-weight: 700;
    }}
    {r} QLabel#entry_field_label {{
        color: {c['text']};
        font-size: {px(12)}px;
        font-weight: 600;
    }}
    {r} QLabel#entry_field_meta {{
        color: {c['muted_dim']};
        font-family: "Yu Gothic UI";
        font-size: {px(11)}px;
    }}
    {r} QLabel#entry_field_helper {{
        color: {c['muted_dim']};
        font-size: {px(11)}px;
    }}
    {r} QLabel#entry_rating_badge {{
        color: {c['coral']};
        font-family: "JetBrains Mono";
        font-size: {px(11)}px;
        font-weight: 600;
    }}
    {r} QFrame#twilight_section_card, {r} QFrame#import_config_card {{
        background: {c['card']};
        border: 1px solid {c['line']};
        border-radius: {px(14)}px;
    }}
    {r} QFrame#entry_sync_banner {{
        background: {c['raised']};
        border: 1px solid {c['line_light']};
        border-radius: {px(12)}px;
    }}
    {r} QLabel#sync_banner_title {{
        color: {c['text']};
        font-size: {px(12)}px;
        font-weight: 700;
    }}
    {r} QLabel#workflow_poster {{
        background: {c['bg']};
        border: 2px dashed {c['line_light']};
        border-radius: {px(12)}px;
        color: {c['muted']};
        font-size: {px(12)}px;
    }}
    {r} QLabel#workflow_poster[has_image="true"] {{
        border: 1px solid {c['line_light']};
        padding: {px(2)}px;
    }}
    {r} QLineEdit, {r} QComboBox {{
        min-height: {px(40)}px;
        background: {c['bg']};
        color: {c['text']};
        border: 1px solid {c['line']};
        border-radius: {px(9)}px;
        padding: 0 {px(12)}px;
        font-size: {px(13)}px;
        selection-background-color: {c['coral']};
        selection-color: {c['on_coral']};
    }}
    {r} QLineEdit#entry_native_input {{
        font-family: "Yu Gothic UI";
    }}
    {r} QLineEdit:focus, {r} QComboBox:focus, {r} QTextEdit:focus {{
        border: 1.5px solid {c['coral']};
    }}
    {r} QComboBox:hover {{
        border-color: {c['line_light']};
    }}
    {r} QComboBox::drop-down {{
        border: none;
        width: {px(28)}px;
        subcontrol-origin: padding;
        subcontrol-position: top right;
    }}
    {r} QComboBox::down-arrow {{
        image: none;
        border: none;
        width: 0px;
        height: 0px;
    }}
    {r} QComboBox QAbstractItemView {{
        background: {c['raised']};
        color: {c['text']};
        border: 1px solid {c['line_light']};
        border-radius: {px(10)}px;
        padding: {px(4)}px;
        selection-background-color: {c['coral_soft']};
        selection-color: {c['text']};
    }}
    {r} QTextEdit {{
        background: {c['bg']};
        color: {c['text']};
        border: 1px solid {c['line']};
        border-radius: {px(10)}px;
        padding: {px(10)}px {px(12)}px;
        font-size: {px(13)}px;
    }}
    {r} QPushButton#poster_action_btn, {r} QPushButton#folder_browse_btn, {r} QPushButton#twilight_cancel_btn {{
        background: {c['raised']};
        color: {c['text']};
        border: 1px solid {c['line_light']};
        border-radius: {px(9)}px;
        min-height: {px(38)}px;
        padding: 0 {px(14)}px;
        font-size: {px(12)}px;
        font-weight: 600;
    }}
    {r} QPushButton#poster_action_btn:hover, {r} QPushButton#folder_browse_btn:hover, {r} QPushButton#twilight_cancel_btn:hover {{
        background: {c['card']};
        border-color: {c['coral']};
    }}
    {r} QPushButton#entry_rating {{
        min-width: 0;
        min-height: 0;
        padding: 0;
        background: {c['raised']};
        color: {c['muted']};
        border: 1px solid {c['line']};
        border-radius: {px(8)}px;
        font-family: "JetBrains Mono";
        font-size: {px(12)}px;
        font-weight: 700;
    }}
    {r} QPushButton#entry_rating:hover {{
        border-color: {c['coral']};
        color: {c['text']};
    }}
    {r} QPushButton#entry_rating:checked {{
        background: {c['coral']};
        color: {c['on_coral']};
        border: 1px solid {c['coral']};
    }}
    {r} QPushButton#close_icon_button {{
        min-width: {px(36)}px;
        max-width: {px(36)}px;
        min-height: {px(36)}px;
        max-height: {px(36)}px;
        padding: 0;
        border-radius: {px(18)}px;
        background: transparent;
        border: none;
    }}
    {r} QPushButton#sakura_primary_btn {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c['coral']}, stop:1 {c['primary_end']});
        color: {c['on_coral']};
        border: 1px solid {c['coral']};
        border-radius: {px(10)}px;
        min-height: {px(40)}px;
        padding: 0 {px(20)}px;
        font-size: {px(13)}px;
        font-weight: 700;
    }}
    {r} QPushButton#sakura_primary_btn:hover {{
        border-color: {c['text']};
    }}
    {r} QPushButton#sakura_primary_btn:disabled {{
        background: {c['raised']};
        color: {c['muted']};
        border-color: {c['line']};
    }}
    {r} QFrame#twilight_footer {{
        background: {c['bg']};
        border: none;
        border-top: 1px solid {c['line']};
        border-bottom-left-radius: {px(16)}px;
        border-bottom-right-radius: {px(16)}px;
    }}
    {r} QFrame#import_dropzone {{
        background: {c['card']};
        border: 1.5px dashed {c['line_light']};
        border-radius: {px(14)}px;
    }}
    {r} QFrame#import_file_strip {{
        background: {c['raised']};
        border: 1px solid {c['line_light']};
        border-radius: {px(10)}px;
    }}
    {r} QLabel#import_file_path {{
        color: {c['text']};
        font-family: "JetBrains Mono";
        font-size: {px(12)}px;
    }}
    {r} QFrame#import_switch_card {{
        background: {c['bg']};
        border: 1px solid {c['line']};
        border-radius: {px(9)}px;
        min-height: {px(40)}px;
    }}
    {r} QLabel#import_switch_label {{
        color: {c['text']};
        font-size: {px(12)}px;
        font-weight: 500;
    }}
    {r} QFrame#kpi_card {{
        background: {c['card']};
        border: 1px solid {c['line']};
        border-radius: {px(12)}px;
    }}
    {r} QLabel#kpi_caption {{
        color: {c['muted']};
        font-size: {px(11)}px;
        font-weight: 600;
    }}
    {r} QLabel#kpi_value {{
        color: {c['text']};
        font-family: "JetBrains Mono";
        font-size: {px(24)}px;
        font-weight: 700;
    }}
    {r} QLabel#kpi_value[tone="existing"] {{ color: {c['ok']}; }}
    {r} QLabel#kpi_value[tone="matched"] {{ color: {c['indigo']}; }}
    {r} QLabel#kpi_value[tone="review"] {{ color: {c['amber']}; }}
    {r} QLabel#kpi_value[tone="unmatched"] {{ color: {c['danger']}; }}
    {r} QProgressBar#import_progress {{
        background: {c['raised']};
        border: none;
        border-radius: {px(2)}px;
        min-height: {px(4)}px;
        max-height: {px(4)}px;
    }}
    {r} QProgressBar#import_progress::chunk {{
        background: {c['coral']};
        border-radius: {px(2)}px;
    }}
    {r} QFrame#import_row_card {{
        background: {c['card']};
        border: 1px solid {c['line']};
        border-radius: {px(12)}px;
    }}
    {r} QFrame#import_row_card:hover {{
        border-color: {c['line_light']};
        background: {c['raised']};
    }}
    {r} QFrame#import_row_card[tone="danger"] {{
        border-color: {c['danger_border']};
    }}
    {r} QLabel#import_status_pill {{
        border-radius: {px(11)}px;
        padding: {px(4)}px {px(10)}px;
        font-size: {px(11)}px;
        font-weight: 700;
        border: 1px solid {c['line_light']};
        background: {c['raised']};
        color: {c['muted']};
    }}
    {r} QLabel#import_status_pill[tone="existing"] {{
        background: {c['ok_soft']};
        color: {c['ok']};
        border-color: {c['ok_border']};
    }}
    {r} QLabel#import_status_pill[tone="matched"] {{
        background: {c['indigo_soft']};
        color: {c['indigo']};
        border-color: {c['indigo_border']};
    }}
    {r} QLabel#import_status_pill[tone="warning"] {{
        background: {c['amber_soft']};
        color: {c['amber']};
        border-color: {c['amber_border']};
    }}
    {r} QLabel#import_status_pill[tone="danger"] {{
        background: {c['danger_soft']};
        color: {c['danger']};
        border-color: {c['danger_border']};
    }}
    {r} QFrame#import_row_card QPushButton {{
        background: {c['raised']};
        color: {c['text']};
        border: 1px solid {c['line_light']};
        border-radius: {px(8)}px;
        min-height: {px(30)}px;
        padding: 0 {px(12)}px;
        font-size: {px(12)}px;
        font-weight: 600;
    }}
    {r} QFrame#import_row_card QPushButton:hover {{
        border-color: {c['coral']};
        color: {c['coral']};
    }}
    {r} QFrame#import_row_card QPushButton#row_custom_btn {{
        background: transparent;
        border-color: {c['line_light']};
    }}
    {r} QScrollBar:vertical {{
        width: {px(8)}px;
        background: transparent;
    }}
    {r} QScrollBar::handle:vertical {{
        background: {c['line_light']};
        border-radius: {px(4)}px;
        min-height: {px(24)}px;
    }}
    {r} QScrollBar::add-line:vertical, {r} QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    """
