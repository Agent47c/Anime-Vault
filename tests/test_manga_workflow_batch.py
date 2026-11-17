"""Approved workflow additions and reusable master material regressions."""
import json,time,unittest
from unittest.mock import patch,Mock
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QPushButton
import test_ui_regressions as support
from app import db
from app.ui.theme import apply_theme


class MangaWorkflowTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def tearDown(self):apply_theme(self.app,'dark');support.Regressions.tearDown(self)

    def test_ignore_is_exact_and_durable_without_discarding_other_changes(self):
        from app.core.update_review import ignore_entry
        first='Season 2 — Announced (Not Yet Released)';second='Episode 8 airing soon'
        db.publish_updates(self.fid,first+' | '+second);ignore_entry(self.fid,first)
        self.assertEqual(db.get_franchise(self.fid)['update_details'],second)
        self.assertEqual(db.publish_updates(self.fid,first+' | '+second),second)
        ignore_entry(self.fid,'Unrelated event');self.assertEqual(db.get_franchise(self.fid)['update_details'],second)

    def test_broadcast_filters_use_exact_local_episode_and_aired_state(self):
        from app.ui.release_view_tools import filter_broadcasts
        now=time.time();rows=[dict(episode=1,airingAt=now-60),dict(episode=2,airingAt=now-30),dict(episode=3,airingAt=now+86400)]
        context=dict(season=2,local={'EPISODE:S2:1':'file.mkv'})
        self.assertEqual([r['episode'] for r in filter_broadcasts(rows,4,context,now)],[1])
        self.assertEqual([r['episode'] for r in filter_broadcasts(rows,5,context,now)],[2])
        self.assertEqual(filter_broadcasts(rows,5,{},now),[])
        self.assertEqual([r['episode'] for r in filter_broadcasts(rows,2,context,now)],[3])

    def test_presets_and_taxonomy_keep_adult_lock_and_apply_once(self):
        from app.ui.pages.release_news_page import ReleaseNewsPage
        from app.ui.release_view_tools import save_preset,presets,apply_preset
        apply_theme(self.app,'manga_light')
        with patch.object(ReleaseNewsPage,'load'):page=ReleaseNewsPage()
        self.addCleanup(page.deleteLater);self.addCleanup(page.stop)
        save_preset('Fantasy',dict(genres=['Fantasy','Hentai'],themes=['Isekai'],formats=['TV'],period=1,sort=3,adult=True,adult_only=True))
        self.assertIn('Fantasy',presets())
        page._adult_allowed=False
        with patch.object(page,'reset') as reset:apply_preset(page,presets()['Fantasy']);reset.assert_called_once()
        self.assertFalse(page.adult_filter.isChecked());self.assertFalse(page.adult_only.isChecked())
        self.assertEqual(page.genre_filter.currentData(),'Fantasy')
        page.genre_filter.showPopup();self.assertIsNotNone(page.genre_filter.popup)
        from PyQt5.QtTest import QSignalSpy
        changes=QSignalSpy(page.genre_filter.currentIndexChanged);page.genre_filter.toggle(1);self.assertEqual(len(changes),1)
        page.genre_filter.hidePopup()

    def test_single_screen_setup_reuses_all_fields_and_existing_operations(self):
        from app.ui.download_setup import DownloadSetup
        apply_theme(self.app,'manga_light');dialog=DownloadSetup();self.addCleanup(dialog.deleteLater)
        self.assertEqual(len(dialog._setup_pages),5);self.assertEqual(dialog.stack.count(),0)
        self.assertEqual(dialog._setup_grid.count(),5);dialog.extension.setText('a'*32)
        def immediate(dlg,operation,done):
            dlg._apply_worker=Mock();dlg._apply_worker.isRunning.return_value=False;done(operation())
        result={name:'OK' for name in ('extension','engine','folder','source')}
        with patch('app.ui.download_setup.start',side_effect=immediate),patch('app.core.chrome_bridge.register',return_value='Registered') as register,patch('app.core.downloads.save_settings',return_value={}) as save,patch('app.core.download_setup.checks',return_value=result) as check:
            dialog.test_all_steps()
            deadline=time.monotonic()+5
            while not dialog.checked and time.monotonic()<deadline:QTest.qWait(10)
            register.assert_called_once();self.assertEqual(save.call_count,3);check.assert_called_once();self.assertTrue(dialog.checked)
        apply_theme(self.app,'dark');dialog.refresh_home_style();self.assertEqual(dialog.stack.count(),5)

    def test_storage_sort_pages_use_cached_payload_and_return_to_sakura(self):
        from app.ui.pages.storage_page import StoragePage
        for i in range(9):db.upsert_franchise(dict(display_title=f'Collection {i}',storage_state='ON_DISK',total_size_bytes=i*1000,watch_status='WATCHED'))
        apply_theme(self.app,'manga_light');page=StoragePage();self.addCleanup(page.deleteLater)
        self.assertEqual(page.table.rowCount(),4)
        with patch.object(db,'get_all_franchises',side_effect=AssertionError('No rescan on pagination')):
            page._change_storage_page(1);self.assertEqual(page._storage_page,2);page.storage_sort.setCurrentIndex(2);self.assertEqual(page._storage_page,1)
        apply_theme(self.app,'dark');page.refresh_home_style();self.assertEqual(page.table.rowCount(),10)

    def test_master_depth_is_cached_and_disabled_previous_is_sunken(self):
        from app.ui.components.neumorphic import tile,NeumorphicEffect
        from app.ui.pages.library_page import LibraryPage
        apply_theme(self.app,'manga_light')
        with patch.object(LibraryPage,'_request_home_facts'):page=LibraryPage()
        self.addCleanup(page.deleteLater)
        self.assertIs(tile(True),tile(True));self.assertIsNot(tile(False),tile(True))
        self.assertIsInstance(page.pagination.previous.graphicsEffect(),NeumorphicEffect)
        self.assertFalse(page.pagination.previous.isEnabled())
        self.assertIsNone(page.pagination.graphicsEffect())
        apply_theme(self.app,'dark');page.refresh_home_style();self.assertIsNone(page.pagination.previous.graphicsEffect())
