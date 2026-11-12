"""A shared bottom-edge progress indicator for overlapping refresh workers."""
from PyQt5.QtWidgets import QProgressBar
from app.ui.home_style import colors


class RefreshProgress(QProgressBar):
    def __init__(self,parent=None):
        super().__init__(parent);self.tasks={};self.setObjectName('app_refresh_progress')
        self.setProperty('animevaultThemeScope',True);self.setProperty('animevaultOwnScaledStyle',True)
        self.setAccessibleName('Library refresh progress');self.setTextVisible(False);self.setFixedHeight(4)
        self.refresh_home_style();self.hide()

    def refresh_home_style(self):
        c=colors();self.setStyleSheet(f"QProgressBar#app_refresh_progress {{background:{c['raised']};border:none;border-radius:0;padding:0;}} QProgressBar#app_refresh_progress::chunk {{background:{c['coral']};border:none;}}")

    def begin(self,key,message):
        self.report(key,0,0,message)

    def report(self,key,current,total,message):
        self.tasks.pop(key,None);self.tasks[key]=(current,total,message);self._present()

    def finish(self,key):
        self.tasks.pop(key,None);self._present()

    def _present(self):
        if not self.tasks:self.hide();return
        current,total,message=next(reversed(self.tasks.values()))
        self.setRange(0,max(0,total))
        if total>0:self.setValue(max(0,min(current,total)))
        self.setToolTip(message);self.setAccessibleDescription(message);self.show()
