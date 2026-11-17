import unittest
import sqlite3
from types import SimpleNamespace
from unittest.mock import Mock,patch
import test_ui_regressions as support
from app import db
from app.ui.main_window import MainWindow
from app.ui.pages.library_page import LibraryPage
from app.ui.pages.updates_page import UpdatesPage


class ImportVisibilityTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def test_committed_update_is_visible_without_waiting_for_general_refresh(self):
        db.publish_updates(self.fid,'Added to Watching — Release available (Not in Library)')
        library=LibraryPage();updates=UpdatesPage()
        self.addCleanup(library.deleteLater);self.addCleanup(updates.deleteLater)
        storage=object()
        host=SimpleNamespace(library_page=library,updates_page=updates,storage_page=storage,
            _dirty_pages={library,updates},_refresh_busy=True,_on_update_choices_changed=Mock(),_start_refresh=Mock())
        MainWindow._on_release_imported(host)
        self.assertTrue(any(r['id']==self.fid for r in updates._updates))
        self.assertTrue(library._library_index.by_id[self.fid]['has_new_update'])
        self.assertNotIn(updates,host._dirty_pages);self.assertNotIn(library,host._dirty_pages)
        self.assertTrue(host._release_import_refresh_pending)
        host._start_refresh.assert_not_called()

    def test_import_refresh_does_not_refresh_hero_or_calendar(self):
        page=Mock()
        with patch('app.core.library_index.LibraryIndex') as index:
            index.return_value.groups=[]
            LibraryPage.refresh_imported(page)
        page.hero_card.refresh.assert_not_called();page._refresh_airing_week.assert_not_called()
        page._refresh_release_cards.assert_called_once()

    def test_older_snapshot_finishing_reapplies_committed_imports(self):
        host=SimpleNamespace(_refresh_snapshot=None,_refresh_busy=True,
            _release_import_refresh_pending=True,refresh_button=Mock(),
            _refresh_pending=False,_on_release_imported=Mock())
        MainWindow._finish_refresh(host)
        self.assertFalse(host._refresh_busy);self.assertFalse(host._release_import_refresh_pending)
        host._on_release_imported.assert_called_once()

    def test_import_updates_retained_memory_database(self):
        memory=sqlite3.connect(':memory:');memory.row_factory=sqlite3.Row;self.addCleanup(memory.close)
        source=db.get_connection();source.backup(memory);source.close()
        imported=db.upsert_franchise(dict(anilist_id=99999,display_title='New import',watch_status='WATCHING'))
        db.publish_updates(imported,'Added to Watching — Release available')
        library=LibraryPage();updates=UpdatesPage()
        self.addCleanup(library.deleteLater);self.addCleanup(updates.deleteLater)
        snapshot={'connection':memory,'season_rows':[]}
        host=SimpleNamespace(library_page=library,updates_page=updates,storage_page=object(),
            _cached_refresh_snapshot=snapshot,_dirty_pages=set(),_refresh_busy=False,_on_update_choices_changed=Mock())
        MainWindow._on_release_imported(host)
        self.assertEqual(memory.execute('SELECT display_title FROM franchises WHERE id=?',(imported,)).fetchone()[0],'New import')
        self.assertIn(imported,snapshot['library_index'].by_id)
