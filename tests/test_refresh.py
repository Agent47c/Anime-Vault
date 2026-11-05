import sqlite3
import unittest
from unittest.mock import Mock, patch
import test_ui_regressions as support
from app import db
from app.core.storage import disk_snapshot
from app.ui.refresh import RefreshWorker
from app.ui.main_window import MainWindow


class RefreshTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def test_worker_snapshot_allows_reads_without_disk_database(self):
        worker = RefreshWorker()
        results, errors = [], []
        worker.ready.connect(results.append)
        worker.failed.connect(errors.append)
        disk = {'total': 100, 'used': 40, 'free': 60}
        with patch('app.ui.refresh.disk_snapshot', return_value=disk):
            worker.run()
        self.assertEqual(errors, [])
        snapshot = results[0]
        try:
            with db.refresh_view(snapshot), patch('app.db.sqlite3.connect', side_effect=AssertionError('Disk database read on GUI thread')):
                self.assertEqual(db.get_franchise(self.fid)['id'], self.fid)
                self.assertEqual(db.get_library_stats()['total_franchises'], 1)
                self.assertEqual(len(db.get_series_library()), 1)
                self.assertEqual(disk_snapshot(), disk)
                with self.assertRaises(RuntimeError):
                    db.update_franchise_field(self.fid, 'display_title', 'Forbidden')
        finally:
            snapshot['connection'].close()
        self.assertIsNone(db.current_refresh_view())

    def test_repeated_manual_refresh_is_ignored_while_busy(self):
        window = Mock()
        window._refresh_busy = True
        MainWindow._request_refresh(window)
        window._start_refresh.assert_not_called()

    def test_data_changes_are_coalesced_during_refresh(self):
        window = Mock()
        window._shutdown_pending = False
        window._refresh_busy = True
        window._refresh_pending = False
        MainWindow._start_refresh(window)
        self.assertTrue(window._refresh_pending)


    def test_startup_scan_only_indexes_new_anime(self):
        from pathlib import Path
        from app.core.scanner import index_local_folder, scan_watched_directories

        watched = Path(self.temp.name) / "library"
        existing = watched / "Existing"
        existing.mkdir(parents=True)
        (existing / "Existing - 01.mkv").write_bytes(b"video")
        index_local_folder(str(existing), "Existing")
        db.add_watched_directory(str(watched))
        with patch("app.core.scanner.is_offline") as online_check:
            self.assertEqual(scan_watched_directories(new_only=True)["scanned"], 0)
            online_check.assert_not_called()

        new_folder = watched / "New Anime"
        new_folder.mkdir()
        (new_folder / "New Anime - 01.mkv").write_bytes(b"video")
        with patch("app.core.scanner.is_offline", return_value=False), \
             patch("app.core.matching.client.search_anime", return_value=[]) as search:
            self.assertEqual(scan_watched_directories(new_only=True)["new"], 1)
            search.assert_called_once_with("New Anime", per_page=8)

    def test_airing_week_keeps_unchanged_cards(self):
        from datetime import datetime
        from app.ui.pages.library_page import LibraryPage

        page = LibraryPage()
        before = page.airing_week.itemAt(0).widget()
        page.refresh()
        self.assertIs(page.airing_week.itemAt(0).widget(), before)
        db.upsert_season({
            "franchise_id": self.fid, "title_display": "New airing",
            "next_airing_at": int(datetime.now().timestamp()), "next_airing_ep": 3,
        })
        page.refresh()
        self.assertIsNot(page.airing_week.itemAt(0).widget(), before)
        page.deleteLater()
