"""Consistent, explicit open-folder action with a full-path tooltip."""
from pathlib import Path
from PyQt5.QtCore import Qt,QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QPushButton,QSizePolicy

class FolderButton(QPushButton):
    def __init__(self,path,parent=None):
        self.path=str(path)
        super().__init__('Open folder · '+(Path(path).name or str(path)),parent)
        self.setToolTip(self.path);self.setAccessibleName('Open folder '+self.path);self.setProperty('role','folder');self.setCursor(Qt.PointingHandCursor);self.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed)
        self.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(self.path)))
