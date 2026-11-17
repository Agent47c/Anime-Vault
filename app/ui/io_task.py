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


def start(dialog, operation, success, *, major=False, operation_title=None):
    current=getattr(dialog,'_apply_worker',None)
    if current and current.isRunning():
        return
    from app.ui.components.message_boxes import AppMessageBox as QMessageBox
    worker=IOTask(operation)
    track(worker)
    dialog._apply_worker=worker
    dialog.setEnabled(False)
    from app.ui.components.operation_progress import watch
    progress = watch(dialog, worker, operation_title or dialog.windowTitle() or 'Processing files', major=major)
    def done(value):
        if progress is not None: progress.finish()
        if sip.isdeleted(dialog):
            return
        # The operation has returned. A success callback may intentionally start
        # the next shared workflow task before QThread.finished is delivered.
        if getattr(dialog,'_apply_worker',None) is worker:
            dialog._apply_worker=None
        dialog.setEnabled(True)
        success(value)
    def failed(message):
        if progress is not None: progress.finish()
        if sip.isdeleted(dialog):
            return
        dialog.setEnabled(True)
        QMessageBox.warning(dialog,'Operation could not finish',message)
    def finished():
        if getattr(dialog,'_apply_worker',None) is worker:
            dialog._apply_worker=None
        _active.discard(worker)
        worker.deleteLater()
    worker.succeeded.connect(done)
    worker.failed.connect(failed)
    worker.finished.connect(finished)
    worker.start()
