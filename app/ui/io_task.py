"""App-owned worker for IO initiated by a drawer; callbacks stay on its GUI."""
from PyQt5.QtCore import QThread,pyqtSignal
from PyQt5.QtWidgets import QApplication
from PyQt5 import sip

_active = set()


def running():
    return [task for task in _active if task.isRunning()]


def track(worker):
    """Keep cancellation-aware app workers visible to shutdown after navigation."""
    _active.add(worker)
    worker.finished.connect(lambda: _active.discard(worker))


class IOTask(QThread):
    succeeded=pyqtSignal(object)
    failed=pyqtSignal(str)

    def __init__(self, operation):
        super().__init__(QApplication.instance())
        self.operation=operation

    def run(self):
        try:
            self.succeeded.emit(self.operation())
        except Exception as error:
            self.failed.emit(str(error))


def start(dialog, operation, success):
    current=getattr(dialog,'_apply_worker',None)
    if current and current.isRunning():
        return
    from PyQt5.QtWidgets import QMessageBox
    worker=IOTask(operation)
    track(worker)
    dialog._apply_worker=worker
    dialog.setEnabled(False)
    def done(value):
        if sip.isdeleted(dialog):
            return
        dialog.setEnabled(True)
        success(value)
    def failed(message):
        if sip.isdeleted(dialog):
            return
        dialog.setEnabled(True)
        QMessageBox.warning(dialog,'Operation could not finish',message)
    def finished():
        dialog._apply_worker=None
        _active.discard(worker)
        worker.deleteLater()
    worker.succeeded.connect(done)
    worker.failed.connect(failed)
    worker.finished.connect(finished)
    worker.start()
