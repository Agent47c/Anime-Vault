"""Download missing artwork away from the GUI thread, with bounded retries."""
import json
import time
from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal
from PyQt5.QtGui import QImage
from app import db
from app.config import COVERS_DIR, cached_online, OFFLINE_MODE
from app.core import anilist_client


def needs_artwork(filename, media, kind):
    if not valid_image(filename):
        return True
    # User-selected/legacy artwork stays intact. Versioned provider assets
    # refresh when metadata supplies a new URL.
    if filename.startswith('anilist-') and media.get('id'):
        import hashlib
        cover = media.get('coverImage') or {}
        url = media.get('bannerImage') if kind == 'banner' else cover.get('extraLarge') or cover.get('large') or cover.get('medium')
        version = hashlib.sha256((url or 'absent').encode()).hexdigest()[:24]
        return filename != f"anilist-{media['id']}-{kind}-{version}.jpg"
    return False


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
            # An explicit null is a stable absence, not a reason to re-query.
            if not media or "bannerImage" not in media:
                media = anilist_client.get_anime_by_id(f["anilist_id"])
            if media:
                key = f"{f['id']}-{f['anilist_id']}"
                # A poster is the hero fallback when AniList has no wide banner.
                needs_cover = needs_artwork(f.get("cover_filename"),media,'cover') and (not self.banner_only or not media.get("bannerImage"))
                cover = anilist_client.download_cover(media, key) if needs_cover else None
                banner = anilist_client.download_banner(media, key) if needs_artwork(f.get('banner_filename'),media,'banner') else None
                current = db.get_franchise(f["id"])
                if current and current.get("anilist_id") == f.get("anilist_id") and (cover or banner or media != json.loads(f.get('metadata_json') or 'null')):
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
        attempt = (fid,franchise.get('anilist_id'),franchise.get('metadata_json'),banner_only)
        if time.monotonic() - self._attempts.get(attempt, -1000) < 300:
            return
        # Validation/decoding belongs to the worker, never a GUI paint/request.
        self._pending.add(fid)
        self._attempts[attempt] = time.monotonic()
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
