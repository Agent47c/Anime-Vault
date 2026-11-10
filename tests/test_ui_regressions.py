"""Run with: python -m unittest discover -s tests -v"""
import gc
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from collections import namedtuple

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5 import sip
from PyQt5.QtCore import Qt, QEvent, QPointF, QCoreApplication, QBuffer, QIODevice
from PyQt5.QtGui import QFontDatabase, QMouseEvent, QImage
from PyQt5.QtWidgets import QApplication, QStyle, QStyleOptionButton
from app import db
from app.core import anilist_client
from app.core.storage import disk_snapshot
from app.core.updater import UpdaterThread
from app.ui.theme import apply_theme
from app.ui.pages.library_page import LibraryPage
from app.ui.pages.detail_modal import DetailModal
from app.ui.pages.updates_page import UpdateCard
from app.ui.components.smooth_scroll import SmoothScrollArea
from app.api.server import franchise_payload


class Regressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        for filename in ("segoeui.ttf", "segoeuib.ttf"):
            font = Path("C:/Windows/Fonts") / filename
            if font.exists():
                QFontDatabase.addApplicationFont(str(font))
        apply_theme(cls.app)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patches = [
            patch.object(db, "DATA_DIR", root),
            patch.object(db, "DB_PATH", root / "library.db"),
            patch.object(db, "COVERS_DIR", root / "covers"),
            patch.object(db, "EXPORTS_DIR", root / "exports"),
            patch("app.ui.artwork.cached_online", return_value=False),
            patch("app.ui.artwork.ArtworkLoader.request"),
        ]
        for item in self.patches:
            item.start()
        db.init_db()
        self.fid = db.upsert_franchise({"anilist_id": 21, "display_title": "One Piece", "synopsis": "A complete synopsis.\n\n" * 70})

    def tearDown(self):
        self.app.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        for item in reversed(self.patches):
            item.stop()
        gc.collect()
        self.temp.cleanup()

    def test_dismissal_survives_refresh_and_only_new_changes_return(self):
        old = "Season 2 — Released (Not in Library)"
        new = "Episode 12 airing soon"
        db.publish_updates(self.fid, old)
        db.dismiss_updates(self.fid)
        db.init_db()  # Reopen the persisted database, including idempotent migration.
        self.assertIsNone(db.publish_updates(self.fid, old))
        self.assertEqual(db.publish_updates(self.fid, old + " | " + new), new)
        self.assertIsNotNone(db.get_franchise(self.fid))

    def test_updater_does_not_republish_dismissed_changes(self):
        old = "Season 2 — Released (Not in Library)"
        db.publish_updates(self.fid, old)
        db.dismiss_updates(self.fid)
        worker = UpdaterThread()
        found = []
        worker.update_found.connect(lambda fid, details: found.append(details))
        with patch("app.core.release_calendar.refresh"), patch("app.core.updater.is_offline", return_value=False), patch.object(anilist_client, "get_anime_by_id", return_value={"id": 21, "title": {"english": "One Piece"}}), patch.object(worker, "_check_for_updates", return_value=old):
            worker.run()
        self.assertEqual(found, [])
        self.assertFalse(db.get_franchise(self.fid)["has_new_update"])

    def test_grid_reuses_posters_and_does_not_query_on_resize(self):
        for i in range(25):
            db.upsert_franchise({"display_title": f"Anime {i}"})
        page = LibraryPage()
        page.view_mode = "grid"
        page.refresh_display()
        page.resize(1200, 800)
        page.show()
        self.app.processEvents()
        original = list(page._cards)
        with patch.object(db, "get_all_franchises", side_effect=AssertionError("Resize must not query the DB")):
            page.resize(900, 800)
            page._reflow_grid()
        self.assertEqual(original, page._cards)
        self.assertIsInstance(page.page_scroll, SmoothScrollArea)
        self.assertIs(page.views_stack.widget(0), page.grid_container)
        self.assertGreater(page.page_scroll.verticalScrollBar().maximum(), 0)
        page.hide()
        page.deleteLater()

    def test_full_synopsis_rating_and_long_season_paths_fit(self):
        db.upsert_season({"franchise_id": self.fid, "title_display": "A season", "season_folder_path": "E:/" + "Very long folder/" * 30})
        dialog = DetailModal(self.fid)
        dialog.show()
        self.app.processEvents()
        self.assertEqual(dialog.right_scroll.widget().width(), dialog.right_scroll.viewport().width())
        self.assertGreater(dialog.synopsis_label.height(), 80)
        button = dialog.rating_buttons[-1]
        option = QStyleOptionButton()
        option.initFrom(button)
        contents = button.style().subElementRect(QStyle.SE_PushButtonContents, option, button)
        self.assertGreaterEqual(contents.width(), button.fontMetrics().horizontalAdvance("10"))
        dialog._set_rating(10)
        self.assertEqual(db.get_franchise(self.fid)["user_rating"], 10)
        self.assertIn("padding: 0", button.styleSheet())
        dialog.hide()
        dialog.deleteLater()

    def test_update_click_can_delete_card(self):
        card = UpdateCard(db.get_franchise(self.fid))
        def delete_card(_):
            card.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        card.clicked.connect(delete_card)
        event = QMouseEvent(QEvent.MouseButtonPress, QPointF(5, 5), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        card.mousePressEvent(event)
        self.assertTrue(sip.isdeleted(card))

    def test_real_volume_is_counted_once_and_missing_roots_are_explicit(self):
        root = Path(self.temp.name)
        child = root / "second-root"
        child.mkdir()
        db.add_watched_directory(str(root))
        db.add_watched_directory(str(child))
        db.add_watched_directory(str(root / "offline"))
        Usage = namedtuple("Usage", "total used free")
        with patch("app.core.storage.shutil.disk_usage", return_value=Usage(1000, 600, 400)) as usage:
            snapshot = disk_snapshot()
        self.assertEqual(usage.call_count, 1)
        self.assertEqual(snapshot["free"], 400)
        self.assertEqual(len(snapshot["unavailable"]), 1)

    def test_offline_drive_never_fabricates_capacity(self):
        db.add_watched_directory(str(Path(self.temp.name) / "offline"))
        snapshot = disk_snapshot()
        self.assertEqual(snapshot["total"], 0)
        self.assertTrue(snapshot["unavailable"])

    def test_banner_download_validates_image_before_replacing_cache(self):
        root = Path(self.temp.name)
        image = QImage(10, 10, QImage.Format_RGB32)
        image.fill(Qt.red)
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, "PNG")
        class Response:
            content = bytes(buffer.data())
            def raise_for_status(self):
                pass
        with patch.object(anilist_client, "COVERS_DIR", root), patch.object(anilist_client.requests, "get", return_value=Response()):
            filename = anilist_client.download_banner({"bannerImage": "https://example.test/banner.png"}, self.fid)
            self.assertFalse(QImage(str(root / filename)).isNull())
            Response.content = b"invalid image"
            self.assertIsNone(anilist_client.download_banner({"bannerImage": "https://example.test/bad.png"}, self.fid))
            self.assertFalse(QImage(str(root / filename)).isNull())

    def test_hero_uses_cover_when_banner_is_absent(self):
        from app.ui.pages.library_page import HeroResumeCard
        import app.ui.pages.library_page as library
        root = Path(self.temp.name)
        image = QImage(80, 120, QImage.Format_RGB32)
        image.fill(Qt.red)
        image.save(str(root / "poster.png"))
        with patch.object(library, "COVERS_DIR", root), patch.object(library, "artwork_loader") as loader:
            hero = HeroResumeCard()
            hero._load_banner({"id": self.fid, "cover_filename": "poster.png", "banner_filename": "missing.png"})
            self.assertFalse(hero._banner.isNull())
            loader.return_value.request.assert_called_with({"id": self.fid, "cover_filename": "poster.png", "banner_filename": "missing.png"}, allow_network=True, banner_only=True)
            hero.deleteLater()

    def test_missing_provider_banner_downloads_cover_fallback_without_requery(self):
        import time
        from app.ui.artwork import _Fetch
        media = {"id": 21, "bannerImage": None, "coverImage": {"large": "https://example.test/poster.png"}}
        record = {"id": self.fid, "anilist_id": 21, "metadata_json": json.dumps(media)}
        from unittest.mock import Mock
        signals = Mock()
        with patch("app.ui.artwork.valid_image", return_value=False), patch.object(db, "get_state", return_value=str(time.time())), patch.object(db, "set_state"), patch.object(db, "cache_media") as cache, patch.object(anilist_client, "get_anime_by_id") as fetch, patch.object(anilist_client, "download_cover", return_value="fallback.png"), patch.object(anilist_client, "download_banner", return_value=None):
            _Fetch(record, signals, banner_only=True).run()
            fetch.assert_not_called()
            cache.assert_called_once_with(self.fid, media, "fallback.png", None)
            signals.done.emit.assert_called_once_with(self.fid, True)

    def test_json_inspector_payload_is_structured(self):
        media = {"id": 21, "title": {"english": "One Piece"}, "description": "Story &amp; adventure", "genres": ["Adventure"]}
        db.cache_media(self.fid, media)
        db.publish_updates(self.fid, "A sequel — Announced")
        payload = franchise_payload(self.fid)
        self.assertEqual(payload["genres"], ["Adventure"])
        self.assertEqual(payload["synopsis"], "Story & adventure")
        self.assertEqual(payload["updates"], [{"title": "A sequel", "status": "Announced"}])
        self.assertNotIn("metadata_json", payload)
        self.assertEqual(json.loads(db.get_franchise(self.fid)["metadata_json"]), media)


if __name__ == "__main__":
    unittest.main()

