"""Right-aligned modal panel shared by the library editing workflows."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QWidget


class DrawerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self._shade = None
        self.finished.connect(self._clear_shade)

    def showEvent(self, event):
        if getattr(self,'full_page',False):
            QDialog.showEvent(self,event)
            return
        if getattr(self, "_embedded", False):
            QDialog.showEvent(self, event)
            return
        parent = self.parentWidget()
        if parent:
            window = parent.window()
            self._shade = QWidget(window)
            self._shade.setStyleSheet("background: rgba(0, 0, 0, 155);")
            self._shade.setGeometry(window.rect())
            self._shade.show()
            self._shade.raise_()
            origin = window.mapToGlobal(window.rect().topLeft())
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            self.setFixedSize(min(560, window.width() - 40), window.height())
            self.move(origin.x() + window.width() - self.width(), origin.y())
        super().showEvent(event)

    def _clear_shade(self, *_):
        if self._shade:
            self._shade.deleteLater()
            self._shade = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
