"""Shared header, scrolling body and fixed footer for library workflows."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QFrame, QWidget, QLabel, QScrollArea, QPushButton, QLayout, QSizePolicy, QApplication
from app.ui.components.design import MotifHeader
from app.ui.components.close_button import CloseButton
from app.ui.components.smooth_scroll import SmoothScrollArea


def text(value, role="workflow_hint"):
    label = QLabel(value)
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(True)
    label.setObjectName(role)
    return label


def button(label, callback, primary=False):
    control = QPushButton(label)
    control.setProperty("accent", primary)
    control.setCursor(Qt.PointingHandCursor)
    control.setMinimumHeight(44)
    control.clicked.connect(callback)
    return control


def chrome(dialog, title, subtitle, glyph, primary_label, callback):
    dialog.setObjectName("workflow_drawer")
    dialog.setAccessibleName(title)
    dialog.resize(560, 900)
    dialog.setMinimumWidth(480)
    root = QVBoxLayout(dialog)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)
    header = MotifHeader(glyph)
    header.setObjectName("workflow_header")
    header.setMinimumHeight(118)
    head = QVBoxLayout(header)
    head.setContentsMargins(26, 20, 26, 20)
    head.setSpacing(6)
    row = QHBoxLayout()
    row.addWidget(text(title, "workflow_title"), 1)
    close = CloseButton()
    close.setAccessibleName("Close " + title.lower())
    close.clicked.connect(dialog.reject)
    row.addWidget(close)
    head.addLayout(row)
    head.addWidget(text(subtitle))
    root.addWidget(header)
    scroll = SmoothScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    body = QWidget()
    body.setObjectName("workflow_body")
    box = QVBoxLayout(body)
    box.setContentsMargins(26, 24, 26, 24)
    box.setSpacing(16)
    box.setSizeConstraint(QLayout.SetMinimumSize)
    scroll.setWidget(body)
    root.addWidget(scroll, 1)
    footer = QFrame()
    footer.setObjectName("workflow_footer")
    foot = QHBoxLayout(footer)
    foot.setContentsMargins(26, 20, 26, 20)
    foot.setSpacing(12)
    foot.addStretch()
    cancel = button("Cancel", dialog.reject)
    cancel.setAutoDefault(False)
    foot.addWidget(cancel)
    primary = button(primary_label, callback, True)
    primary.setAutoDefault(False)
    dialog.setFocusProxy(cancel)
    cancel.setFocus()
    foot.addWidget(primary)
    root.addWidget(footer)
    dialog.cancel_button = cancel
    return box, primary


def card():
    frame = QFrame()
    frame.setObjectName("workflow_card")
    box = QVBoxLayout(frame)
    box.setContentsMargins(16, 14, 16, 14)
    box.setSpacing(4)
    return frame, box


def field(box, label, control):
    if type(control) is QWidget and not control.objectName():
        control.setObjectName("workflow_field")
    group = QWidget()
    group.setObjectName("workflow_field")
    layout = QVBoxLayout(group)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.addWidget(text(label, "workflow_field_label"))
    layout.addWidget(control)
    control.setAccessibleName(label)
    box.addWidget(group)


def thumbnail(title, filename=None, width=44, height=66):
    from PyQt5.QtGui import QPixmap, QPainter, QPainterPath, QLinearGradient, QColor
    from PyQt5.QtCore import QRectF
    from app.config import COVERS_DIR
    from app.ui.theme import COLORS
    colors = COLORS.get(QApplication.instance().property("animevaultTheme"), COLORS["dark"])
    pix = QPixmap(width * 2, height * 2)
    pix.setDevicePixelRatio(2)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, width, height), 8, 8)
    painter.setClipPath(path)
    source = QPixmap(str(COVERS_DIR / filename)) if filename else QPixmap()
    if not source.isNull():
        source = source.scaled(width * 2, height * 2, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        source.setDevicePixelRatio(2)
        painter.drawPixmap(round((width - source.width()/2)/2), round((height - source.height()/2)/2), source)
    else:
        gradient = QLinearGradient(0, 0, width, height)
        gradient.setColorAt(0, QColor(colors["accent_secondary"]))
        gradient.setColorAt(1, QColor(colors["bg_card"]))
        painter.fillRect(0, 0, width, height, gradient)
    painter.end()
    label = QLabel()
    label.setFixedSize(width, height)
    label.setPixmap(pix)
    label.setAccessibleName("Poster for " + title)
    return label
