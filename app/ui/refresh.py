"""Read the database, drive capacity and artwork away from the GUI thread."""
import os
import sqlite3
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from app import db
from app.config import COVERS_DIR
from app.core.storage import disk_snapshot


def image_key(path):
    return os.path.normcase(os.path.abspath(str(path)))


def artwork_version(filename):
    """A small cache key that also notices replacements using the same filename."""
    if not filename:
        return None
    path = COVERS_DIR / filename
    snapshot = db.current_refresh_view()
    if snapshot is not None and "image_versions" in snapshot:
        return snapshot["image_versions"].get(image_key(path))
    try:
        stat = path.stat()
        return stat.st_mtime_ns, stat.st_size
    except OSError:
        return None


def refresh_pixmap(path):
    snapshot = db.current_refresh_view()
    if snapshot is not None:
        return QPixmap.fromImage(snapshot["images"].get(image_key(path), QImage()))
    return QPixmap(str(path))


def refresh_image_exists(path):
    snapshot = db.current_refresh_view()
    if snapshot is not None:
        return not snapshot["images"].get(image_key(path), QImage()).isNull()
    return path.is_file()


class RefreshWorker(QThread):
    ready = pyqtSignal(object)
    failed = pyqtSignal(str)
    unchanged = pyqtSignal()

    progress = pyqtSignal(str, int, int)

    def __init__(self, parent=None, scan_library=False, new_only=False, allow_network=True, sync_internet=False):
        super().__init__(parent)
        self.scan_library = scan_library
        self.new_only = new_only
        self.allow_network = allow_network
        self.sync_internet = sync_internet
        self._updater = None

    def run(self):
        memory = sqlite3.connect(":memory:", check_same_thread=False)
        memory.row_factory = sqlite3.Row
        try:
            errors = []
            from app.core.file_operations import recover_operations
            recovery = recover_operations()
            errors.extend(recovery['errors'])
            if self.scan_library:
                from app.core.scanner import scan_watched_directories, ScanProgress

                def report(message, current, total):
                    if self.isInterruptionRequested():
                        raise InterruptedError
                    self.progress.emit(message, current, total)

                result = scan_watched_directories(progress_callback=report, scan_progress=ScanProgress(self.isInterruptionRequested), new_only=self.new_only, allow_network=self.allow_network)
                errors.extend(result["errors"])
                if self.new_only and not (result["new"] or result["updated"] or errors):
                    memory.close()
                    self.unchanged.emit()
                    return
            if self.isInterruptionRequested():
                memory.close()
                return
            if self.sync_internet and self.allow_network:
                from app.core.updater import UpdaterThread
                self._updater = UpdaterThread()
                self._updater.progress.connect(self.progress.emit)
                self._updater.run()
            if self.isInterruptionRequested():
                memory.close()
                return
            source = db.get_connection()
            try:
                source.backup(memory)
            finally:
                source.close()
            disk = disk_snapshot()
            images = {}
            image_versions = {}
            for row in memory.execute("SELECT cover_filename, banner_filename FROM franchises"):
                if self.isInterruptionRequested():
                    memory.close()
                    return
                for name in row:
                    if name:
                        path = COVERS_DIR / name
                        images[image_key(path)] = QImage(str(path))
                        try:
                            stat = path.stat()
                            image_versions[image_key(path)] = (stat.st_mtime_ns, stat.st_size)
                        except OSError:
                            image_versions[image_key(path)] = None
            self.ready.emit({"connection": memory, "disk": disk, "images": images, "scan_errors": errors, "allow_network": self.allow_network, "image_versions": image_versions})
        except InterruptedError:
            memory.close()
        except Exception as error:
            memory.close()
            self.failed.emit(str(error))

    def requestInterruption(self):
        super().requestInterruption()
        if self._updater is not None:
            self._updater.cancel()
