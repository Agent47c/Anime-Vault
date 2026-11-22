"""Visible live native-extension heartbeat; saved registration is not a connection."""
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget,QHBoxLayout,QLabel
from app.ui.components.manga_shell import ApiStatusDot
from app.ui.io_task import IOTask,track


class ExtensionConnection(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.worker=None
        row=QHBoxLayout(self);row.setContentsMargins(0,0,0,0);row.setSpacing(8)
        self.indicator=ApiStatusDot();self.label=QLabel();self.label.setWordWrap(True)
        row.addWidget(self.indicator);row.addWidget(self.label,1)
        self.indicator.clicked.connect(self.check)
        self.timer=QTimer(self);self.timer.setInterval(3000);self.timer.timeout.connect(self.check)
        self.present({})

    def present(self,state):
        connected=bool(state.get('connected'))
        message='Chrome extension connected' if connected else 'Chrome extension disconnected — open Chrome and enable the Anime Vault extension'
        if connected and not state.get('enabled'):message+=' · Website capture is off'
        self.label.setText(message);self.indicator.set_connection(connected,message+'\nClick to check again')
        self.setAccessibleName(message)

    def check(self):
        if self.worker is not None or not self.isVisible():return
        from app.core.source_bridge import connection
        from PyQt5 import sip
        worker=IOTask(connection);self.worker=worker;track(worker)
        def ready(state):
            if not sip.isdeleted(self):self.present(state)
        def failed(_):
            if not sip.isdeleted(self):self.present({})
        def finished():
            if not sip.isdeleted(self) and self.worker is worker:self.worker=None
            worker.deleteLater()
        worker.succeeded.connect(ready);worker.failed.connect(failed);worker.finished.connect(finished);worker.start()

    def showEvent(self,event):
        super().showEvent(event);self.timer.start();self.check()

    def hideEvent(self,event):
        self.timer.stop();super().hideEvent(event)
