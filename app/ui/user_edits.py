"""App-owned, coalesced user edits; survives closing the details page."""
from contextlib import closing
from PyQt5.QtCore import QObject,QTimer,pyqtSignal
from PyQt5.QtWidgets import QApplication
from app import db
from app.ui.io_task import IOTask,track

class UserEdits(QObject):
    changed=pyqtSignal(object)
    failed=pyqtSignal(str)
    def __init__(self):
        super().__init__(QApplication.instance());self.pending={};self.worker=None
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.flush)
    def save(self,fid,fields,delay=0):
        db.validate_fields(fields,{'user_notes','user_rating','watch_status'})
        self.pending.setdefault(fid,{}).update(fields)
        self.timer.start(delay)
    def flush(self):
        self.timer.stop()
        if self.worker or not self.pending:return
        edits=self.pending;self.pending={}
        def persist():
            with closing(db.get_connection()) as conn,conn:
                for fid,fields in edits.items():
                    columns=','.join(key+'=?' for key in fields)
                    conn.execute('UPDATE franchises SET '+columns+' WHERE id=?',(*fields.values(),fid))
            return edits
        worker=IOTask(persist);self.worker=worker;track(worker)
        worker.succeeded.connect(self.changed.emit)
        def failed(message):
            for fid,fields in edits.items():self.pending[fid]={**fields,**self.pending.get(fid,{})}
            self.failed.emit('Could not save edits. Pending edits are retained for retry: '+message)
        worker.failed.connect(failed)
        def finished():
            self.worker=None;worker.deleteLater()
            if self.pending and not getattr(worker,'edit_failed',False):self.timer.start(0)
        def mark_failed(_):worker.edit_failed=True
        worker.failed.connect(mark_failed);worker.finished.connect(finished);worker.start()

_service=None
def user_edits():
    global _service
    if _service is None:_service=UserEdits()
    return _service
