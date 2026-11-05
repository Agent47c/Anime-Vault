"""Download missing artwork away from the GUI thread, with bounded retries."""
import json
import time
from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal
from PyQt5.QtGui import QImage
from app import db
from app.config import COVERS_DIR, cached_online, OFFLINE_MODE
from app.core import anilist_client


class _Signals(QObject):
    done = pyqtSignal(int, bool)


class _Fetch(QRunnable):
    def __init__(self, franchise, signals, banner_only=False):
        super().__init__()
        self.franchise = franchise
        self.signals = signals
        self.banner_only = banner_only

    def run(self):
        f = self.franchise
        changed = False
        try:
            media = json.loads(f.get("metadata_json") or "null")
            if self.banner_only and media and not media.get("bannerImage"):
                checked = float(db.get_state(f"banner_absent:{f['anilist_id']}", "0"))
                if time.time() - checked < 86400:
                    if valid_image(f.get("cover_filename")):
                        return
                else:
                    media = anilist_client.get_anime_by_id(f["anilist_id"])
            elif not media or "bannerImage" not in media:
                media = anilist_client.get_anime_by_id(f["anilist_id"])
            if media:
                key = f"{f['id']}-{f['anilist_id']}"
                # A poster is the hero fallback when AniList has no wide banner.
                needs_cover = not valid_image(f.get("cover_filename")) and (not self.banner_only or not media.get("bannerImage"))
                cover = anilist_client.download_cover(media, key) if needs_cover else None
                banner = None if valid_image(f.get("banner_filename")) else anilist_client.download_banner(media, key)
                if self.banner_only and not media.get("bannerImage"):
                    db.set_state(f"banner_absent:{f['anilist_id']}", str(time.time()))
                current = db.get_franchise(f["id"])
                if current and current.get("anilist_id") == f.get("anilist_id"):
                    db.cache_media(f["id"], media, cover, banner)
                    changed = bool(cover or banner)
        except Exception:
            # Keep the local poster fallback usable while offline or on failure.
            pass
        finally:
            self.signals.done.emit(f["id"], changed)


def valid_image(filename):
    snapshot = db.current_refresh_view()
    if snapshot is not None:
        from app.ui.refresh import image_key
        return bool(filename and image_key(COVERS_DIR / filename) in snapshot["images"] and not snapshot["images"][image_key(COVERS_DIR / filename)].isNull())
    return bool(filename and not QImage(str(COVERS_DIR / filename)).isNull())


class ArtworkLoader(QObject):
    changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self._pending = set()
        self._attempts = {}
        self._signals = _Signals(self)
        self._signals.done.connect(self._finished)

    def request(self, franchise, *, allow_network=False, banner_only=False):
        fid = franchise["id"]
        snapshot = db.current_refresh_view()
        if snapshot is not None and snapshot.get("allow_network") is False:
            return
        if OFFLINE_MODE or not franchise.get("anilist_id") or (cached_online() is not True and not allow_network) or fid in self._pending:
            return
        if time.monotonic() - self._attempts.get(fid, -1000) < 300:
            return
        if valid_image(franchise.get("banner_filename")) and (banner_only or valid_image(franchise.get("cover_filename"))):
            return
        self._pending.add(fid)
        self._attempts[fid] = time.monotonic()
        self.pool.start(_Fetch(dict(franchise), self._signals, banner_only))

    def _finished(self, fid, changed):
        self._pending.discard(fid)
        if changed:
            self.changed.emit(fid)


_loader = None


def artwork_loader():
    global _loader
    if _loader is None:
        _loader = ArtworkLoader()
    return _loader
