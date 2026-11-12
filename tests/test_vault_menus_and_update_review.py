"""Menu commands stay intact; stale/empty update views recover without blocking."""
import time,unittest
from contextlib import closing
from unittest.mock import patch,Mock
from PyQt5.QtCore import Qt,QPoint,QRect,QCoreApplication,QEvent
from PyQt5.QtWidgets import QWidget,QPushButton,QLabel,QMainWindow,QLineEdit
from PyQt5.QtTest import QTest
import test_ui_regressions as support
from app import db
from app.core.update_review import read_changes
from app.ui.pages.update_review_page import UpdateReviewPage


class VaultMenuUpdateTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def seed(self):
        with closing(db.get_connection()) as c:
            c.execute('UPDATE franchises SET has_new_update=1, update_details=? WHERE id=?',('Episode 21 airing soon',self.fid));c.commit()

    def wait(self,page):
        end=time.monotonic()+6
        while (page._worker is not None or not page.status.text().startswith(('Saved updates loaded','Update check complete','Offline','One Piece','Could not'))) and time.monotonic()<end:QTest.qWait(10)
        self.assertIsNone(page._worker)

    def test_empty_cached_view_reads_current_database_without_network(self):
        self.seed()
        with patch('app.core.anilist_client.get_anime_by_id') as request:
            page=UpdateReviewPage(None,'One Piece',[],[self.fid]);page.show();self.wait(page)
            self.assertTrue(any('Episode 21' in label.text() for label in page.findChildren(QLabel)))
            request.assert_not_called();self.assertTrue(page.refresh_button.isEnabled())
            page.reject();page.deleteLater()

    def test_explicit_refresh_uses_existing_updater_and_persists_changes(self):
        self.seed()
        media=dict(id=21,title=dict(english='ONE PIECE'),nextAiringEpisode=dict(episode=22),relations=dict(edges=[]))
        with patch('app.config.is_offline',return_value=False),patch('app.core.anilist_client.get_anime_by_id',return_value=media) as request:
            result=read_changes([self.fid],True)
        request.assert_called_once_with(21);self.assertTrue(result['refreshed'])
        self.assertIn('Episode 22 · Broadcast time unverified',result['changes']);self.assertIn('Episode 22',db.get_franchise(self.fid)['update_details'])

    def test_online_error_and_offline_mode_keep_previous_changes(self):
        self.seed()
        for offline in (True,False):
            with self.subTest(offline=offline),patch('app.config.is_offline',return_value=offline),patch('app.core.anilist_client.get_anime_by_id',return_value=None),patch('app.core.anilist_client.last_error',return_value='Request timed out'):
                result=read_changes([self.fid],True)
                self.assertIn('Episode 21 airing soon',result['changes']);self.assertTrue(result['warnings']);self.assertFalse(result['refreshed'])

    def test_refresh_button_checks_and_renders_the_new_episode(self):
        self.seed();page=UpdateReviewPage(None,'One Piece',[],[self.fid]);page.show();self.wait(page)
        media=dict(id=21,title=dict(english='ONE PIECE'),nextAiringEpisode=dict(episode=22),relations=dict(edges=[]))
        changed=[];page.refreshed.connect(lambda:changed.append(True))
        with patch('app.config.is_offline',return_value=False),patch('app.core.anilist_client.get_anime_by_id',return_value=media) as request:
            page.refresh_button.click();self.wait(page)
        request.assert_called_once_with(21);self.assertEqual(changed,[True])
        self.assertTrue(any('Episode 22' in label.text() for label in page.findChildren(QLabel)))
        self.assertFalse(page.progress.isVisible());page.reject();page.deleteLater()

    def test_closing_review_during_load_does_not_reopen_it(self):
        from PyQt5 import sip
        import test_tab_navigation_memory as navigation_support
        from app.ui.navigation import navigate
        from app.ui.io_task import running
        host=navigation_support.TabNavigationMemoryTests.host(self);root=host.stacked_widget.currentWidget()
        def delayed(*args):time.sleep(.08);return dict(changes=['Episode 21 airing soon'],warnings=[],refreshed=False)
        with patch('app.core.update_review.read_changes',side_effect=delayed):
            page=UpdateReviewPage(host,'One Piece',[],[self.fid]);navigate(page);QTest.qWait(10);page.reject()
            end=time.monotonic()+5
            while not sip.isdeleted(page) and time.monotonic()<end:
                QTest.qWait(10);QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
        self.assertIs(host.stacked_widget.currentWidget(),root);self.assertTrue(sip.isdeleted(page))

    def test_open_details_beside_refresh_keeps_series_identity_and_back_path(self):
        import test_tab_navigation_memory as navigation_support
        from app.ui.navigation import navigate,switch_tab
        from app.ui.pages.detail_modal import DetailModal
        host=navigation_support.TabNavigationMemoryTests.host(self);host.resize(1280,850);switch_tab(host,2)
        other=db.upsert_franchise(dict(anilist_id=22,display_title='Another series'))
        page=UpdateReviewPage(host,'One Piece',[],[other,self.fid],franchise_id=self.fid)
        navigate(page);self.wait(page);self.app.processEvents()
        self.assertLess(page.details_button.x(),page.refresh_button.x())
        self.assertLessEqual(abs(page.details_button.geometry().center().y()-page.refresh_button.geometry().center().y()),1)
        page.details_button.click();detail=host.stacked_widget.currentWidget().workflow
        self.assertIsInstance(detail,DetailModal);self.assertEqual(detail.franchise_id,self.fid)
        end=time.monotonic()+5
        while not hasattr(detail,'franchise') and time.monotonic()<end:QTest.qWait(10)
        self.assertEqual(detail.franchise['id'],self.fid)
        detail._navigation_header.back.click()
        self.assertIs(host.stacked_widget.currentWidget().workflow,page)
        self.assertTrue(page.refresh_button.isEnabled());page.reject()

    def test_header_menu_preserves_commands_keyboard_and_window_bounds(self):
        from app.ui.components.home_header import HomeHeader
        host=QMainWindow();host.top_search_input=QLineEdit();host.coll_counts={}
        for name in ('_on_nav_clicked','_on_collection_clicked','_request_refresh','_open_custom_entry_dialog','_open_watched_import_dialog'):setattr(host,name,Mock())
        header=HomeHeader(host);host.setCentralWidget(header);host.resize(1280,720);host.show();self.app.processEvents()
        menu=header.options.menu();menu.popup(header.options.mapToGlobal(QPoint(0,44)));QTest.qWait(30)
        bounds=QRect(host.mapToGlobal(QPoint()),host.size()).intersected(host.screen().availableGeometry()).adjusted(8,8,-8,-8)
        self.assertTrue(bounds.contains(menu.geometry()))
        labels=[a.text() for a in menu.actions()]
        for text in ('Add anime','Import watched TXT list','Settings','Refresh local library','Refresh and sync with internet'):self.assertIn(text,labels)
        QTest.keyClick(menu,Qt.Key_End)
        self.assertEqual(menu.activeAction().text(),'Refresh and sync with internet')
        next(a for a in menu.actions() if a.text()=='Add anime').trigger();host._open_custom_entry_dialog.assert_called_once()
        menu.hide();host.hide();host.deleteLater()

    def test_context_commands_target_the_original_series_and_keep_select(self):
        from app.ui.pages.library_page import LibraryPage
        from app.ui.components.vault_menu import VaultMenu
        with patch.object(LibraryPage,'_request_home_facts'),patch.object(LibraryPage,'_refresh_airing_week'):
            page=LibraryPage();record=dict(db.get_franchise(self.fid));commands=[];selected=[]
            page.context_action.connect(lambda fid,command:commands.append((fid,command)))
            def choose(menu,point):
                labels=[a.text() for a in menu.actions()]
                self.assertIn('Select',labels);self.assertIn('Move to Recycle Bin…',labels)
                next(a for a in menu.actions() if a.text()=='Choose episode…').trigger()
            with patch.object(VaultMenu,'exec_',choose):page.show_series_menu(record,page,QPoint(1,1),lambda:selected.append(True))
            self.assertEqual(commands,[(self.fid,'episodes')]);self.assertFalse(selected)
            page.deleteLater()

    def test_context_selection_keeps_original_id_and_releases_closed_menus(self):
        from app.ui.pages.library_page import LibraryPage
        from app.ui.components.vault_menu import VaultMenu
        from PyQt5.QtGui import QContextMenuEvent
        with patch.object(LibraryPage,'_request_home_facts'),patch.object(LibraryPage,'_refresh_airing_week'):
            page=LibraryPage();page._set_view_mode('grid');page.resize(1280,850);page.show();self.app.processEvents()
            card=page._cards[0];original=card.franchise_id
            def choose(menu,point):
                # A virtual slot may rebind while the menu's event loop runs.
                card.franchise_id=original+10000
                next(a for a in menu.actions() if a.text()=='Select').trigger()
            with patch.object(VaultMenu,'exec_',choose):
                card.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Mouse,QPoint(5,5),card.mapToGlobal(QPoint(5,5))))
            self.assertIn(original,page.selected_fids);self.assertNotIn(original+10000,page.selected_fids)
            QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
            self.assertFalse(page.findChildren(VaultMenu));page.close();page.deleteLater()
