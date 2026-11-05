"""Decorative surfaces shared by the final UI layouts."""
from PyQt5.QtCore import Qt, QRectF, QEvent
from PyQt5.QtGui import QColor, QFont, QPainter
from PyQt5.QtWidgets import QWidget, QLabel, QSizePolicy, QApplication


class MotifHeader(QWidget):
    def __init__(self, glyph, parent=None):
        super().__init__(parent)
        self.glyph = glyph
        self.setMinimumHeight(76)

    def paintEvent(self, event):
        super().paintEvent(event)
        if QApplication.instance().property("animevaultDecorations") is False:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        drawer = self.objectName() == "workflow_header"
        right = self.width() - (64 if drawer else min(200, self.width() // 3))
        for child in self.findChildren(QWidget):
            if child.isVisible() and child.focusPolicy() != Qt.NoFocus:
                left = child.mapTo(self, child.rect().topLeft()).x()
                if left > self.width() // 2:
                    right = min(right, left - 12)
        start = max(100 if drawer else self.width() // 2, right - (220 if drawer else 280))
        if right <= start:
            return
        for x in range(start, right, 9):
            painter.setPen(QColor(223, 37, 69, (x - start) // 24 + 7))
            for y in range(3, self.height(), 8):
                painter.drawPoint(x, y)
        font = QFont("Yu Gothic UI")
        font.setPixelSize(96 if drawer else 76)
        font.setWeight(QFont.Black)
        painter.setFont(font)
        painter.setPen(QColor(217, 45, 69, 32))
        painter.drawText(QRectF(start, -9, right - start, self.height() + 18),
                         Qt.AlignRight | Qt.AlignVCenter, self.glyph)


class ElidedLabel(QLabel):
    """Single-line table text with the original value available on hover."""

    def __init__(self, text):
        super().__init__()
        self.full_text = text
        self.setTextFormat(Qt.PlainText)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setToolTip(text)

    def set_full_text(self, text):
        self.full_text = text
        self.setToolTip(text)
        self._elide()

    def _elide(self):
        self.setText(self.fontMetrics().elidedText(self.full_text, Qt.ElideRight, self.contentsRect().width()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._elide()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.FontChange and hasattr(self, "full_text"):
            self._elide()
