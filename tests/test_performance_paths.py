"""Prevent expensive rebuilds and network access on local UI operations."""
import unittest
from unittest.mock import patch, Mock
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QFrame, QMainWindow
from PyQt5.QtCore import Qt
import test_ui_regressions as support
from app import db
from app.ui.pages.library_page import LibraryPage
from app.core.library_index import LibraryIndex
from app.ui.theme import apply_theme
from app.ui.artwork import ArtworkLoader
_request_artwork = ArtworkLoader.request


class PerformancePathTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def library(self):
        with patch("app.ui.artwork.ArtworkLoader.request"):
            return LibraryPage()

    def test_grid_sort_and_filter_reuse_widgets_without_database_or_image_reads(self):
        other = db.upsert_franchise({"display_title": "Other", "storage_state": "ON_DISK"})
        db.update_franchise_field(self.fid, "storage_state", "NOT_DOWNLOADED")
        page = self.library()
        before = {c.franchise_id: c for c in page._cards}
        with patch.object(db, "get_all_franchises", side_effect=AssertionError("Unexpected DB read")), patch("app.ui.components.poster_card.refresh_pixmap", side_effect=AssertionError("Unexpected image decode")):
            page._sort_order = "DESC"
            page.refresh_display()
            page.activate_filter("ON_DISK")
            self.assertEqual([c.franchise_id for c in page._cards], [other])
            page.activate_filter("")
        self.assertTrue(all(before[c.franchise_id] is c for c in page._cards))
        page.deleteLater()

    def test_numeric_sort_uses_aggregated_series_size_and_rating(self):
        arc = db.upsert_franchise({"display_title": "Arc", "total_size_bytes": 8})
        db.update_franchise_field(self.fid, "total_size_bytes", 2)
        db.update_franchise_field(self.fid, "user_rating", 9)
        other = db.upsert_franchise({"display_title": "Other", "total_size_bytes": 7, "user_rating": 6})
        db.group_with_series(arc, self.fid)
        index = LibraryIndex()
        self.assertEqual(index.select(sort_by="total_size_bytes", sort_order="DESC")[0]["total_size_bytes"], 10)
        self.assertEqual(index.select(sort_by="user_rating", sort_order="DESC")[0]["id"], self.fid)
        self.assertEqual(index.select(sort_by="total_size_bytes", sort_order="ASC")[0]["id"], other)

    def test_compact_sort_reorders_existing_row_widgets(self):
        db.upsert_franchise({"display_title": "Alpha"})
        page = self.library()
        page.view_mode = "compact"
        page.refresh_display()
        table = page.compact_table
        original = {table.item(r, 0).data(Qt.UserRole): table.cellWidget(r, 2) for r in range(table.rowCount())}
        page._sort_order = "DESC"
        page.refresh_display()
        self.assertTrue(all(original[table.item(r, 0).data(Qt.UserRole)] is table.cellWidget(r, 2) for r in range(table.rowCount())))
        page.deleteLater()

    def test_library_refresh_invalidates_cached_values(self):
        page = self.library()
        db.update_franchise_field(self.fid, "user_rating", 10)
        with patch("app.ui.artwork.ArtworkLoader.request"):
            page.refresh()
        self.assertEqual(page._library_index.select()[0]["user_rating"], 10)
        page.deleteLater()

    def test_local_scan_does_not_check_connectivity_or_match_with_api(self):
        from app.core.scanner import scan_watched_directories
        root = Path(self.temp.name) / "library"
        show = root / "New series"
        show.mkdir(parents=True)
        (show / "Show - 01.mkv").write_bytes(b"video")
        db.add_watched_directory(str(root))
        with patch("app.core.scanner.is_offline", side_effect=AssertionError("Network check")), patch("app.core.matching.auto_match_indexed_folders") as match:
            result = scan_watched_directories(allow_network=False)
        match.assert_not_called()
        self.assertEqual(result["new"], 1)

    def test_local_snapshot_blocks_hero_artwork_network_request(self):
        from app.ui.artwork import ArtworkLoader
        loader = ArtworkLoader()
        with db.refresh_view({"allow_network": False}), patch.object(loader.pool, "start") as start:
            _request_artwork(loader, {"id": self.fid, "anilist_id": 21}, allow_network=True, banner_only=True)
        start.assert_not_called()

    def test_internet_sync_is_explicit_in_refresh_worker(self):
        from app.ui.refresh import RefreshWorker
        for internet in (False, True):
            worker = RefreshWorker(allow_network=internet, sync_internet=internet)
            snapshots = []
            worker.ready.connect(snapshots.append)
            with patch("app.core.updater.UpdaterThread.run") as update, patch("app.ui.refresh.disk_snapshot", return_value={}):
                worker.run()
            self.assertEqual(update.call_count, int(internet))
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(snapshots[0]["allow_network"], internet)
            snapshots[0]["connection"].close()

    def test_refresh_menu_has_local_and_internet_choices(self):
        from app.ui.main_window import MainWindow
        window = QMainWindow()
        window._on_search_text_changed = Mock()
        window._request_refresh = Mock()
        window._open_custom_entry_dialog = Mock()
        header = MainWindow._create_top_header(window)
        actions = window.refresh_button.menu().actions()
        self.assertEqual(len(actions), 2)
        actions[0].trigger()
        window._request_refresh.assert_called_with(internet=False)
        actions[1].trigger()
        window._request_refresh.assert_called_with(internet=True)
        header.deleteLater()
        window.deleteLater()

    def test_health_is_not_recalculated_for_update_actions(self):
        from app.ui.pages.updates_page import UpdatesPage
        with patch.object(UpdatesPage, "_read_health", return_value=[]) as health:
            page = UpdatesPage()
            page.refresh()
            health.assert_not_called()
            page._select_filter("Health")
            health.assert_called_once()
        page.deleteLater()

    def test_theme_change_defers_hidden_sections_until_shown(self):
        apply_theme(self.app, "dark")
        window = QWidget()
        window.setProperty("animevaultScopedWindow", True)
        layout = QVBoxLayout(window)
        visible, hidden = QFrame(), QFrame()
        for section in (visible, hidden):
            section.setProperty("animevaultThemeScope", True)
            layout.addWidget(section)
        hidden.hide()
        window.show()
        self.app.processEvents()
        original = hidden.property("animevaultScopeStyle")
        apply_theme(self.app, "light")
        self.assertIsNotNone(visible.property("animevaultScopeStyle"))
        self.assertEqual(hidden.property("animevaultScopeStyle"), original)
        hidden.show()
        self.app.processEvents()
        self.assertEqual(hidden.property("animevaultScopeStyle"), visible.property("animevaultScopeStyle"))
        window.hide()
        window.deleteLater()


    def test_update_commit_does_not_block_the_gui_event_loop(self):
        import time
        from PyQt5.QtCore import QTimer
        from PyQt5.QtTest import QSignalSpy
        from app.ui.pages.updates_page import UpdatesPage
        db.publish_updates(self.fid, "Current update")
        page = UpdatesPage()
        finished = QSignalSpy(page.action_finished)
        ticks = []
        timer = QTimer()
        timer.setInterval(5)
        timer.timeout.connect(lambda: ticks.append(True))
        timer.start()
        with patch("app.ui.pages.updates_page.UpdateActionWorker.perform", side_effect=lambda *args: time.sleep(.15)):
            page._start_update_action(self.fid, "watched")
            self.assertTrue(finished.wait(5000))
        timer.stop()
        self.assertGreater(len(ticks), 2)
        page.deleteLater()

    def test_replaced_cover_invalidates_an_existing_poster(self):
        db.update_franchise_field(self.fid, "cover_filename", "example.jpg")
        with patch("app.ui.refresh.artwork_version", return_value=(1, 100)):
            page = self.library()
        original = page._cards[0]
        with patch("app.ui.refresh.artwork_version", return_value=(2, 100)), patch("app.ui.artwork.ArtworkLoader.request"):
            page.refresh()
        self.assertIsNot(page._cards[0], original)
        page.deleteLater()
