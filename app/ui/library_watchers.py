"""Debounced opt-in OS folder events and incremental TXT imports."""
from PyQt5.QtCore import QObject,QTimer,QFileSystemWatcher
from app import db,preferences
from app.ui.io_task import IOTask,track


class LibraryWatchers(QObject):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.worker=None;self.paths_worker=None;self.stopped=False;self.pending_reload=False;self.signature=None
        self.watcher=QFileSystemWatcher(self)
        self.debounce=QTimer(self);self.debounce.setSingleShot(True);self.debounce.setInterval(1800)
        self.watcher.directoryChanged.connect(lambda _:self.debounce.start())
        self.debounce.timeout.connect(self.scan)
        self.import_timer=QTimer(self);self.import_timer.setInterval(60000)
        self.import_timer.timeout.connect(self.import_lists)
        self.reload()

    def reload(self):
        if self.stopped:return
        if self.paths_worker:self.pending_reload=True;return
        enabled=preferences.enabled('folder_watchers')
        def paths():
            if not enabled:return []
            from contextlib import closing
            from pathlib import Path
            with closing(db.get_connection()) as conn:
                candidates=[row[0] for row in conn.execute('SELECT folder_path FROM watched_directories UNION SELECT season_folder_path FROM seasons WHERE season_folder_path IS NOT NULL')]
            return [path for path in candidates if not worker.isInterruptionRequested() and Path(path).is_dir()]
        worker=IOTask(paths);self.paths_worker=worker;track(worker)
        worker.succeeded.connect(self.loaded_paths);worker.finished.connect(self.paths_finished);worker.start()
        if preferences.enabled('list_watchers'): self.import_timer.start()
        else:
            self.import_timer.stop()
            if self.worker:self.worker.requestInterruption()

    def loaded_paths(self,paths):
        if self.stopped:return
        signature=tuple(sorted(set(paths)))
        if signature==self.signature:return
        self.signature=signature
        if self.watcher.directories():self.watcher.removePaths(self.watcher.directories())
        self.pending=list(signature)[:5000];self.add_chunk()

    def paths_finished(self):
        self.paths_worker.deleteLater();self.paths_worker=None
        if self.pending_reload:self.pending_reload=False;self.reload()

    def add_chunk(self):
        if self.stopped or getattr(self.window,'_shutdown_pending',False): return
        chunk,self.pending=self.pending[:20],self.pending[20:]
        if chunk: self.watcher.addPaths(chunk)
        if self.pending: QTimer.singleShot(0,self.add_chunk)

    def scan(self):
        if not getattr(self.window,'_shutdown_pending',False):
            self.window._start_refresh(scan_library=True,allow_network=False)

    def import_lists(self):
        if self.worker or getattr(self.window,'_shutdown_pending',False): return
        from app.core.import_lists import refresh
        worker=IOTask(lambda:refresh(worker.isInterruptionRequested));self.worker=worker;track(worker)
        worker.succeeded.connect(lambda changed:self.window._on_data_updated() if changed else None)
        worker.failed.connect(lambda message:self.window.statusBar().showMessage('Import list: '+message,10000))
        worker.finished.connect(self.finished);worker.start()

    def finished(self):
        self.worker.deleteLater();self.worker=None

    def stop(self):
        self.stopped=True
        self.debounce.stop();self.import_timer.stop()
        if self.watcher.directories(): self.watcher.removePaths(self.watcher.directories())
