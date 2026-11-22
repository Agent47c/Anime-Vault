import io,json,zipfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtTest import QTest
import test_ui_regressions as support
from app import db,preferences


class ExperienceFollowupTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def test_saved_limits_reconfigure_existing_engine_without_new_submission(self):
        from app.core import downloads,builtin_torrents
        engine=Mock()
        with patch.object(builtin_torrents,'_engine',engine):
            config=downloads.save_settings({'enabled':True,'destination':self.temp.name,'download_limit_kib':2000,'upload_limit_kib':15})
        engine.configure.assert_called_once_with(config)
        self.assertEqual(downloads.settings()['download_limit_kib'],2000)

    def test_picker_presets_and_custom_do_not_round_user_limit(self):
        from app.ui.components.rate_limit import RateLimitPicker
        widget=RateLimitPicker();self.addCleanup(widget.deleteLater)
        self.assertEqual(widget.presets.maxVisibleItems(),6)
        self.assertEqual([widget.presets.itemData(i) for i in range(widget.presets.count())],[0,512,1024,1536,2048,2560,3072,None])
        for value in (0,512,1024,1536,2000,15):widget.setValue(value);self.assertEqual(widget.value(),value)
        widget.custom.clear()
        with self.assertRaises(ValueError):widget.value()

    def test_window_restores_maximized_and_normal_rectangle(self):
        from app.ui.main_window import MainWindow
        first=QMainWindow();second=QMainWindow();self.addCleanup(first.deleteLater);self.addCleanup(second.deleteLater)
        first.setGeometry(10,20,1200,800);first.showMaximized();self.app.processEvents()
        MainWindow._save_geometry(first);MainWindow._restore_geometry(second)
        self.assertEqual(db.get_state('window_maximized'),'1');self.assertTrue(second.isMaximized())
        first.hide();second.hide()

    def test_shared_header_menu_anchors_to_visible_button(self):
        from PyQt5.QtWidgets import QWidget,QPushButton
        from PyQt5.QtCore import QPoint
        from app.ui.components.vault_menu import VaultMenu
        host=QWidget();host.resize(760,600);self.addCleanup(host.deleteLater)
        old=QPushButton(host);old.move(100,50);old.hide()
        visible=QPushButton(host);visible.setGeometry(700,50,44,44)
        menu=VaultMenu(old);menu.add_item('Settings',lambda:None);menu.anchor_widget=visible
        host.show();menu.popup(visible.mapToGlobal(QPoint(0,44)));QTest.qWait(30)
        self.assertGreater(menu.x(),host.mapToGlobal(QPoint(300,0)).x())
        self.assertLessEqual(menu.geometry().right(),menu._bounds().right())
        menu.close();host.hide()

    def test_full_profile_restores_all_db_state_resume_and_optional_caches(self):
        from app.core import profile_backup as backup,builtin_torrents
        root=Path(self.temp.name);cover=root/'covers'/'custom.png';cover.write_bytes(b'original image fixture')
        resume=root/'builtin-downloads'/'job.resume';resume.parent.mkdir();resume.write_bytes(b'original resume fixture')
        (resume.parent/'do-not-back-up.mkv').write_bytes(b'video fixture')
        db.update_franchise_field(self.fid,'user_notes','Original note');db.set_state('downloads.jobs','[{"id":"saved-job"}]');db.set_state('window_maximized','1')
        with patch.object(builtin_torrents,'_engine',None):
            archive=backup.create_backup(True)
            with zipfile.ZipFile(archive) as z:
                self.assertIn('covers/custom.png',z.namelist());self.assertNotIn('builtin-downloads/do-not-back-up.mkv',z.namelist())
            db.update_franchise_field(self.fid,'user_notes','changed');cover.write_bytes(b'changed');resume.write_bytes(b'changed')
            safety=backup.restore_backup(archive)
        self.assertTrue(Path(safety).is_file());self.assertEqual(db.get_franchise(self.fid)['user_notes'],'Original note')
        self.assertEqual(cover.read_bytes(),b'original image fixture');self.assertEqual(resume.read_bytes(),b'original resume fixture')
        self.assertEqual(db.get_state('window_maximized'),'1');self.assertIn('saved-job',db.get_state('downloads.jobs'))

    def test_cache_backup_is_opt_in_and_traversal_restore_is_rejected(self):
        from app.core import profile_backup as backup,builtin_torrents
        root=Path(self.temp.name);(root/'covers'/'sample.png').write_bytes(b'fixture')
        with patch.object(builtin_torrents,'_engine',None):
            archive=backup.create_backup(False)
        with zipfile.ZipFile(archive) as z:self.assertFalse(any(n.startswith('covers/') for n in z.namelist()))
        evil=root/'evil.zip'
        with zipfile.ZipFile(evil,'w') as z:z.writestr('../escaped.txt','bad')
        with self.assertRaises(ValueError):backup.restore_backup(evil)
        self.assertIsNotNone(db.get_franchise(self.fid));self.assertFalse((root.parent/'escaped.txt').exists())

    def test_next_page_fetches_only_missing_cache_without_manual_refresh(self):
        from app.core import release_news as news
        response={'Page':{'media':[{'id':8}], 'pageInfo':{'hasNextPage':False}}}
        with patch.object(news.api,'_graphql_request',return_value=response) as request:
            self.assertEqual(news.discover(page=2,fetch_missing=True)[0][0]['id'],8)
            news.discover(page=2,fetch_missing=True)
        self.assertEqual(request.call_count,1)

    def test_adult_only_query_and_preferences_are_enforced(self):
        from app.core import release_news as news
        response={'Page':{'media':[{'id':1,'isAdult':True},{'id':2,'isAdult':False}], 'pageInfo':{}}}
        self.assertFalse(preferences.enabled('allow_mature'))
        self.assertEqual(news.discover(adult_only=True),([],False))
        preferences.save('allow_mature',True)
        with patch.object(news.api,'_graphql_request',return_value=response) as request:
            self.assertEqual([m['id'] for m in news.discover(force=True,adult_only=True)[0]],[1])
            self.assertIs(request.call_args.args[1]['adult'],True)

    def test_adult_controls_and_genre_change_immediately(self):
        from app.ui.pages.release_news_page import ReleaseNewsPage
        with patch.object(ReleaseNewsPage,'load'):page=ReleaseNewsPage()
        self.addCleanup(page.deleteLater)
        self.assertTrue(page.adult_filter.isHidden());self.assertNotIn('Hentai',[v for _,v in page.genre_filter.items])
        preferences.save('allow_mature',True);page.apply_preferences()
        self.assertFalse(page.adult_filter.isHidden());self.assertIn('Hentai',[v for _,v in page.genre_filter.items])
        preferences.save('allow_mature',False);page.apply_preferences()
        self.assertTrue(page.adult_filter.isHidden());self.assertFalse(page.adult_only.isChecked())
        # Preference changes start asynchronous cache reloads. Finish them while
        # this test's temporary database still exists (Windows keeps it locked).
        from app.ui.io_task import running
        page.stop()
        for worker in running():
            worker.requestInterruption();self.assertTrue(worker.wait(2000))
        self.app.processEvents()

    def test_all_twenty_cards_are_in_scroll_range_and_details_show_romaji_plot(self):
        from app.ui.pages.release_news_page import ReleaseNewsPage,NewsArtwork
        with patch.object(ReleaseNewsPage,'load'):page=ReleaseNewsPage()
        self.addCleanup(page.deleteLater);page.resize(1280,720);page.show()
        with patch.object(NewsArtwork,'start'):
            page.render(([{'id':i,'title':{'english':'Example '+str(i)}} for i in range(1,21)],False))
            self.app.processEvents();QTest.qWait(20)
            self.assertEqual(len(page._discovery_cards),20)
            bar=page.scroll.verticalScrollBar();self.assertGreater(bar.maximum(),0);bar.setValue(bar.maximum());self.app.processEvents()
            last=page._discovery_cards[-1];self.assertLessEqual(last.mapTo(page.scroll.viewport(),last.rect().bottomRight()).y(),page.scroll.viewport().height()+2)
            page.media_id=9;page.render({'Media':{'id':9,'title':{'english':'English title','romaji':'Romaji name'},'description':'This is the plot.','genres':['Fantasy']},'Page':{}})
            self.assertEqual(page.release_title.text(),'English title')
            from PyQt5.QtWidgets import QLabel
            labels=[l.text() for l in page.findChildren(QLabel)];self.assertIn('Romaji name',labels);self.assertIn('This is the plot.',labels)
        page.hide()
