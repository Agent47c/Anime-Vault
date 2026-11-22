"""Notification choices reach both retained screens without a global refresh."""
import sqlite3,time,unittest
from contextlib import closing
from types import SimpleNamespace
from unittest.mock import patch,Mock
from PyQt5.QtTest import QSignalSpy
from PyQt5.QtWidgets import QLabel,QPushButton
import test_ui_regressions as support
from app import db
from app.core.library_index import LibraryIndex
from app.ui.pages.library_page import LibraryPage
from app.ui.components.home_hero import HomeHero
from app.ui.pages.updates_page import UpdatesPage,UpdateCard


class UpdateChoicePropagationTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def test_adult_visibility_keeps_pending_updates_and_syncs_retained_views(self):
        from app.core import adult_content
        from app.ui.main_window import MainWindow
        mature=db.upsert_franchise({'display_title':'Mature fixture','is_adult':True})
        for fid in (self.fid,mature):
            db.publish_updates(fid,'Season 2 announced')
        db.set_state('preference:allow_mature','1')
        with patch.object(LibraryPage,'_request_home_facts'),patch.object(LibraryPage,'_refresh_airing_week'),patch.object(HomeHero,'refresh'):
            home=LibraryPage()
            updates=UpdatesPage()
            self.addCleanup(home.deleteLater)
            self.addCleanup(updates.deleteLater)
            host=SimpleNamespace(library_page=home,updates_page=updates,organizer_page=Mock(),
                                 _dirty_pages={home,updates},_updater_thread=None,_refresh_metrics=Mock())
            for visible, expected in ((False,{self.fid}),(True,{self.fid,mature})):
                db.set_state('adult_lock.unlocked','1' if visible else '0')
                self.assertEqual(adult_content.is_adult_unlocked(),visible)
                MainWindow._apply_settings_preferences(host)
                self.assertEqual({row['id'] for row in updates._updates},expected)
                self.assertEqual(set(home._release_card_pool),expected)
                self.assertTrue(db.get_franchise(mature)['has_new_update'])
                self.assertFalse(host._dirty_pages)

    def test_saved_disposition_with_stale_flag_does_not_count_as_pending(self):
        db.publish_updates(self.fid,'Season 2 announced')
        db.set_state(f'update_disposition:{self.fid}','later')
        updates=UpdatesPage()
        self.addCleanup(updates.deleteLater)
        self.assertEqual(updates._updates,[])
        self.assertFalse(LibraryIndex().by_id[self.fid]['has_new_update'])

    def test_refresh_cannot_publish_snapshot_from_before_adult_lock(self):
        from app.ui.main_window import MainWindow
        connection=Mock()
        host=SimpleNamespace(_finish_refresh=Mock())
        oversized_visibility_snapshot={'connection':connection,'adult_visible':True}
        with patch('app.core.adult_content.is_adult_unlocked',return_value=False):
            MainWindow._apply_refresh_snapshot(host,oversized_visibility_snapshot)
        connection.close.assert_called_once()
        host._finish_refresh.assert_called_once()
        self.assertTrue(host._refresh_pending)

    def test_all_choices_remove_single_home_update_and_restore_without_refresh(self):
        db.publish_updates(self.fid,'Season 2 announced')
        with patch.object(LibraryPage,'_request_home_facts'),patch.object(LibraryPage,'_refresh_airing_week'),patch.object(HomeHero,'refresh'):
            home=LibraryPage()
        updates=UpdatesPage();updates.choices_changed.connect(home.apply_update_choices)
        self.addCleanup(home.deleteLater);self.addCleanup(updates.deleteLater)
        timings=[]
        for n,action in enumerate(('later','not_interested','muted','dismiss','watched')):
            with self.subTest(action=action):
                db.set_update_disposition(self.fid,'new');db.publish_updates(self.fid,f'Season {n+3} announced')
                updates.refresh(False);home.apply_update_choices({self.fid:db.get_franchise(self.fid)})
                self.assertIn(self.fid,home._release_card_pool)
                with patch.object(home,'refresh') as full,patch.object(home.hero_card,'refresh') as hero,patch.object(home,'_refresh_airing_week') as calendar:
                    done=QSignalSpy(updates.action_finished);start=time.monotonic();updates._start_update_action(self.fid,action)
                    self.assertTrue(done.wait(3000));timings.append(time.monotonic()-start)
                    self.assertNotIn(self.fid,home._release_card_pool)
                    self.assertEqual(len(updates._updates),0)
                    self.assertFalse(any(isinstance(updates.list_layout.itemAt(i).widget(),UpdateCard) for i in range(updates.list_layout.count())))
                    full.assert_not_called();hero.assert_not_called();calendar.assert_not_called()
                if action in ('later','not_interested','muted'):
                    # Restore into an already visible, previously empty active list.
                    updates._select_filter('All');done=QSignalSpy(updates.action_finished)
                    updates._start_update_action(self.fid,'new');self.assertTrue(done.wait(3000))
                    self.assertIn(self.fid,home._release_card_pool)
                    self.assertEqual(len(updates._updates),1)
                    self.assertTrue(any(isinstance(updates.list_layout.itemAt(i).widget(),UpdateCard) for i in range(updates.list_layout.count())))
        print(f'All update choices committed and propagated: max {max(timings)*1000:.1f} ms')

    def test_group_remains_new_until_all_members_suppressed(self):
        second=db.upsert_franchise({'display_title':'Another release'})
        for fid in (self.fid,second):db.publish_updates(fid,'Season 2 announced')
        index=LibraryIndex();index.groups=[dict(index.by_id[self.fid],series_member_ids=[self.fid,second])]
        index.apply_update_choices({self.fid:{'has_new_update':False}})
        self.assertTrue(index.groups[0]['has_new_update'])
        index.apply_update_choices({second:{'has_new_update':False}})
        self.assertFalse(index.groups[0]['has_new_update'])
        index.apply_update_choices({self.fid:{'has_new_update':True}})
        self.assertTrue(index.groups[0]['has_new_update'])

    def test_pending_snapshot_cannot_reintroduce_saved_choice(self):
        from app.ui.refresh import patch_update_choices
        db.publish_updates(self.fid,'Season 2 announced');index=LibraryIndex()
        memory=sqlite3.connect(':memory:');memory.row_factory=sqlite3.Row
        with closing(db.get_connection()) as source:source.backup(memory)
        self.addCleanup(memory.close)
        snapshot={'connection':memory,'library_index':index,'stats':{'unread':1}}
        patch_update_choices(snapshot,{self.fid:{'has_new_update':False,'update_details':'Season 2 announced','_update_disposition':'later'}})
        self.assertFalse(index.groups[0]['has_new_update'])
        with db.refresh_view(snapshot):
            self.assertFalse(db.get_franchise(self.fid)['has_new_update']);self.assertEqual(db.update_disposition(self.fid),'later')
        self.assertNotIn('stats',snapshot)
        # The real database was not written by the read-snapshot patch.
        self.assertTrue(db.get_franchise(self.fid)['has_new_update'])

    def test_shell_patches_cached_home_without_marking_it_dirty(self):
        from app.ui.main_window import MainWindow
        library=SimpleNamespace(apply_update_choices=Mock(return_value=True));storage=object()
        host=SimpleNamespace(library_page=library,storage_page=storage,_dirty_pages=set(),updates_page=SimpleNamespace(_updates=[]),findChild=lambda *args:None,coll_counts={})
        record={'watch_status':'WATCHED','_previous_watch_status':'WATCHED','has_new_update':False,'_update_disposition':'later'}
        MainWindow._on_update_choices_changed(host,{self.fid:record})
        library.apply_update_choices.assert_called_once();self.assertEqual(host._dirty_pages,set())
