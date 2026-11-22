"""Read the database, drive capacity and artwork away from the GUI thread."""
import os
import sqlite3
import threading
from collections import OrderedDict
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from app import db
from app.config import COVERS_DIR
from app.core.storage import disk_snapshot

_decoded_images=OrderedDict()
_decoded_lock=threading.Lock()
_decoded_bytes=0
_thumbnail_pool=None


def thumbnail_pool():
    """Keep Python image readers out of Qt's native global rendering pool."""
    global _thumbnail_pool
    from PyQt5 import sip
    from PyQt5.QtCore import QThreadPool
    from PyQt5.QtWidgets import QApplication
    if _thumbnail_pool is None or sip.isdeleted(_thumbnail_pool):
        _thumbnail_pool=QThreadPool(QApplication.instance())
        _thumbnail_pool.setMaxThreadCount(2)
    return _thumbnail_pool

def cached_refresh_image(path,banner=False):
    """Version-aware bounded decoded cache; callers run in a worker."""
    global _decoded_bytes
    try:stat=path.stat()
    except OSError:return QImage()
    key=(image_key(path),stat.st_mtime_ns,stat.st_size,banner)
    with _decoded_lock:
        if key in _decoded_images:
            image=_decoded_images.pop(key);_decoded_images[key]=image
            return QImage(image)
    from app.core.image_profiles import load_cached_image
    width,height=(1280,720) if banner else (360,540)
    image=load_cached_image(path,max_size=(width,height))
    if image.isNull():return image
    with _decoded_lock:
        if key not in _decoded_images:
            _decoded_images[key]=image;_decoded_bytes+=image.sizeInBytes()
        while _decoded_bytes>128*1024**2 and _decoded_images:
            _,old=_decoded_images.popitem(last=False);_decoded_bytes-=old.sizeInBytes()
    return QImage(image)


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


def patch_update_choices(snapshot, records):
    """Keep a pending read snapshot consistent with already committed UI choices."""
    index=snapshot.get('library_index')
    if index:index.apply_update_choices(records)
    connection=snapshot['connection']
    for fid,record in records.items():
        fields={key:record[key] for key in ('has_new_update','update_details','watch_status') if key in record}
        if fields:connection.execute('UPDATE franchises SET '+','.join(key+'=?' for key in fields)+' WHERE id=?',(*fields.values(),fid))
        disposition=record.get('_update_disposition','new')
        for key,value in ((f'update_disposition:{fid}',disposition),(f'muted_updates:{fid}','0' if disposition=='new' else '1')):
            connection.execute('INSERT INTO app_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,value))
    snapshot.pop('stats',None)


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
                for column,name in enumerate(row):
                    if name:
                        path = COVERS_DIR / name
                        key=image_key(path)
                        if key in images:continue
                        images[key] = cached_refresh_image(path,banner=column==1)
                        try:
                            stat = path.stat()
                            image_versions[image_key(path)] = (stat.st_mtime_ns, stat.st_size)
                        except OSError:
                            image_versions[image_key(path)] = None
            snapshot={"connection": memory, "disk": disk, "images": images, "scan_errors": errors, "allow_network": self.allow_network, "image_versions": image_versions}
            snapshot['state']={row['key']:row['value'] for row in memory.execute('SELECT key,value FROM app_state')}
            snapshot['season_rows']=[dict(row) for row in memory.execute('SELECT * FROM seasons')]
            from app.core.library_index import LibraryIndex
            from app.core.adult_content import is_adult_unlocked
            with db.refresh_view(snapshot):
                snapshot['adult_visible']=is_adult_unlocked()
                snapshot['library_index']=LibraryIndex()
            snapshot['series_groups']=snapshot['library_index'].groups
            from app.core.home_facts import build_facts
            with db.refresh_view(snapshot):snapshot['home_facts']=build_facts(snapshot['library_index'])
            with db.refresh_view(snapshot):
                snapshot['stats']=db.get_library_stats()
                from app.ui.pages.storage_page import StoragePage
                snapshot['storage_health']={record['id']:StoragePage._health(record,db.get_seasons_for_franchise(record['id'])) for record in snapshot['library_index'].records if record.get('storage_state') in ('ON_DISK','PARTIALLY_ON_DISK')}
            self.ready.emit(snapshot)
        except InterruptedError:
            memory.close()
        except Exception as error:
            memory.close()
            self.failed.emit(str(error))

    def requestInterruption(self):
        super().requestInterruption()
        if self._updater is not None:
            self._updater.cancel()
