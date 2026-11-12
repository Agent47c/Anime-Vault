"""Bounded player polling and app-wide Space handling outside text/controls."""
from PyQt5.QtCore import QObject,QTimer,QEvent,Qt,pyqtSignal
from PyQt5.QtWidgets import QApplication,QLineEdit,QTextEdit,QPlainTextEdit,QAbstractButton,QComboBox,QAbstractItemView,QAbstractSpinBox
from app.core import playback as service
from app.ui.io_task import IOTask,track


class PlaybackMonitor(QObject):
    changed=pyqtSignal(object)
    notice=pyqtSignal(str)
    def __init__(self):
        super().__init__(QApplication.instance());self.worker=None;self.state={};self.closing=False;self._revision=-1;self._last_path=None;self._toggle_pending=False
        self.timer=QTimer(self);self.timer.setInterval(1000);self.timer.timeout.connect(self.check);self.timer.start()
        QApplication.instance().aboutToQuit.connect(self.close)
    def check(self):
        if self.closing or self.worker:return
        if not service.active() and self._revision==service.revision():return
        self._revision=service.revision()
        def prepare():
            state=service.poll();path=state.get('path')
            if path and path!=self._last_path:
                from app import db
                from app.config import COVERS_DIR
                from app.core.image_profiles import load_cached_image
                record=db.get_franchise(state.get('fid')) if state.get('fid') else None
                if record:
                    name=record.get('banner_filename') or record.get('cover_filename')
                    from pathlib import Path
                    state={**state,'record':record,'available':Path(path).is_file(),'banner':load_cached_image(COVERS_DIR/name) if name else None}
                self._last_path=path
            return state
        worker=IOTask(prepare);self.worker=worker;track(worker)
        def ready(state):self.state=state;self.changed.emit(state)
        worker.succeeded.connect(ready);worker.failed.connect(self.notice.emit)
        worker.finished.connect(lambda:self._finished(worker));worker.start()
    def _finished(self,worker):
        if self.worker is worker:self.worker=None
        worker.deleteLater()
        if self._toggle_pending and not self.closing:
            self._toggle_pending=False;QTimer.singleShot(0,self.toggle)
    def toggle(self):
        if self.closing:return
        if self.worker:self._toggle_pending=not self._toggle_pending;return
        worker=IOTask(service.toggle);self.worker=worker;track(worker)
        worker.succeeded.connect(lambda _:QTimer.singleShot(0,self.check))
        worker.failed.connect(self.notice.emit);worker.finished.connect(lambda:self._finished(worker));worker.finished.connect(self.check);worker.start()
    def close(self):
        self.closing=True;self.timer.stop()

class HomePlaybackKeys(QObject):
    def __init__(self,window,monitor):
        super().__init__(window);self.window=window;self.monitor=monitor
    def eventFilter(self,obj,event):
        if event.type()!=QEvent.KeyPress or event.key()!=Qt.Key_Space or event.modifiers()!=Qt.NoModifier or event.isAutoRepeat():return False
        if not self.window.isActiveWindow() or QApplication.activePopupWidget():return False
        focus=QApplication.focusWidget()
        if isinstance(focus,(QLineEdit,QTextEdit,QPlainTextEdit,QAbstractButton,QComboBox,QAbstractItemView,QAbstractSpinBox)) or focus and focus.property('homePoster'):return False
        self.monitor.toggle();event.accept();return True

_monitor=None
def monitor():
    global _monitor
    if _monitor is None:_monitor=PlaybackMonitor()
    return _monitor
