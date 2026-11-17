import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from app import db
from app.ui.main_window import MainWindow


class NavigationSnapshotTests(unittest.TestCase):
    def test_repeated_dirty_tab_navigation_uses_memory_without_worker(self):
        connection=sqlite3.connect(':memory:');self.addCleanup(connection.close)
        snapshot={'connection':connection}
        def rendered():self.assertIs(db.current_refresh_view(),snapshot)
        page=Mock();page.refresh.side_effect=rendered
        host=SimpleNamespace(stacked_widget=Mock(),_dirty_pages={page},
            _cached_refresh_snapshot=snapshot,_start_refresh=Mock())
        host.stacked_widget.widget.return_value=page
        with patch('app.ui.refresh.RefreshWorker') as worker,patch('app.core.storage.disk_snapshot') as disk:
            for i in range(5):MainWindow._refresh_dirty_page(host,0)
        self.assertEqual(page.refresh.call_count,1)
        worker.assert_not_called();disk.assert_not_called();host._start_refresh.assert_not_called()

    def test_initial_navigation_waits_for_initial_load(self):
        page=Mock();host=SimpleNamespace(stacked_widget=Mock(),_dirty_pages={page},_start_refresh=Mock())
        host.stacked_widget.widget.return_value=page
        MainWindow._refresh_dirty_page(host,0)
        host._start_refresh.assert_not_called();page.refresh.assert_not_called()

    def test_completed_snapshot_is_retained_and_replaced_connection_is_closed(self):
        old=sqlite3.connect(':memory:');current=sqlite3.connect(':memory:');self.addCleanup(current.close)
        snapshot={'connection':current}
        host=SimpleNamespace(_cached_refresh_snapshot={'connection':old},_refresh_snapshot=snapshot,
            refresh_button=Mock(),_refresh_pending=False)
        MainWindow._finish_refresh(host)
        self.assertIs(host._cached_refresh_snapshot,snapshot)
        self.assertEqual(current.execute('SELECT 1').fetchone()[0],1)
        with self.assertRaises(sqlite3.ProgrammingError):old.execute('SELECT 1')
