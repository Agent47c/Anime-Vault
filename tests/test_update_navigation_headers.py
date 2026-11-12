"""Update review routing, shared breadcrumbs and header/theme consistency."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from contextlib import closing
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout
import test_ui_regressions as support
import test_tab_navigation_memory as navigation_support
from app import db
from app.ui.navigation import navigate, switch_tab, set_navigation_title


class UpdateNavigationHeaderTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown
    host = navigation_support.TabNavigationMemoryTests.host

    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def test_back_and_dynamic_breadcrumb_share_one_row(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout
        host=self.host();host.resize(1100,700)
        dialog=QDialog(host);dialog.setWindowTitle('Anime Details');dialog.dispose_on_leave=True
        QVBoxLayout(dialog).addWidget(QLabel('Details content'))
        navigate(dialog);set_navigation_title(dialog,'Overgeared');self.app.processEvents()
        header=dialog._navigation_header
        self.assertEqual(header.breadcrumb.text(),'Library / Overgeared')
        self.assertLessEqual(abs(header.back.geometry().center().y()-header.breadcrumb.geometry().center().y()),1)
        self.assertFalse(header.back.icon().isNull())
        self.assertGreater(header.breadcrumb.x(),header.back.geometry().right())
        dialog.reject()

    def test_updates_actions_share_title_row_with_status_below(self):
        from app.ui.pages.updates_page import UpdatesPage
        page=UpdatesPage();self.addCleanup(page.deleteLater)
        page.resize(1100,680);page.show();self.app.processEvents()
        buttons={button.text():button for button in page.findChildren(QPushButton)}
        labels={label.text() for label in page.findChildren(QLabel)}
        self.assertNotIn('AniList metadata',labels)
        self.assertTrue(page.status_pill.text().startswith('AniList · '))
        title=page.findChild(QLabel,'transfer_heading')
        positions=[]
        for name in ('New episode updates','New anime releases','Refresh metadata'):
            button=buttons[name];point=button.mapTo(page,button.rect().center());positions.append(point)
            self.assertLessEqual(button.mapTo(page,QPoint(button.width(),0)).x(),page.width())
        self.assertLessEqual(max(p.y() for p in positions)-min(p.y() for p in positions),1)
        self.assertTrue(positions[0].x()<positions[1].x()<positions[2].x())
        self.assertLess(title.mapTo(page,QPoint()).y(),page.status_pill.mapTo(page,QPoint()).y())
        page.close()

    def test_library_update_opens_changes_and_back_returns_to_updates(self):
        from app.ui.main_window import MainWindow
        from app.ui.pages.updates_page import UpdatesPage
        with closing(db.get_connection()) as connection:
            connection.execute('UPDATE franchises SET has_new_update=1, update_details=? WHERE id=?',('Episode 19 airing soon',self.fid));connection.commit()
        host=self.host();root=host.stacked_widget.widget(2)
        page=UpdatesPage(root);QVBoxLayout(root).addWidget(page)
        host.updates_page=page;host._update_nav_selection=Mock()
        host.library_page=SimpleNamespace(_library_index=SimpleNamespace(groups=[dict(id=self.fid,display_title='One Piece',series_member_ids=[self.fid])]))
        MainWindow._open_update_changes(host,self.fid)
        wrapper=host.stacked_widget.currentWidget()
        self.assertEqual(wrapper.workflow.windowTitle(),'View changes')
        self.assertEqual(wrapper.workflow._navigation_header.breadcrumb.text(),'Updates / One Piece / View changes')
        self.assertTrue(any('Episode 19' in label.text() for label in wrapper.workflow.findChildren(QLabel)))
        wrapper.workflow.reject()
        self.assertIs(host.stacked_widget.currentWidget(),root)
        switch_tab(host,0);switch_tab(host,2)
        self.assertIs(host.stacked_widget.currentWidget(),root)

    def test_update_card_click_reviews_changes_not_anime_details(self):
        from app.ui.pages.updates_page import UpdatesPage
        page=UpdatesPage();self.addCleanup(page.deleteLater)
        record=db.get_franchise(self.fid);record.update(has_new_update=1,update_details='Episode 19 airing soon',_update_disposition='new')
        page._updates=[record];page._render_cards();card=page._update_card_pool[self.fid][1]
        with patch.object(card,'_show_changes') as changes:
            card.clicked.emit(self.fid)
        changes.assert_called_once()

    def test_library_new_update_posters_use_update_navigation(self):
        from app.ui.pages.library_page import LibraryPage
        with closing(db.get_connection()) as connection:
            connection.execute('UPDATE franchises SET has_new_update=1, update_details=? WHERE id=?',('Episode 19 airing soon',self.fid));connection.commit()
        with patch.object(LibraryPage,'_request_home_facts'),patch.object(LibraryPage,'_refresh_airing_week'):
            page=LibraryPage()
            self.addCleanup(page.deleteLater)
            updates=[];details=[]
            page.update_clicked.connect(updates.append);page.card_clicked.connect(details.append)
            page._release_card_pool[self.fid][1].clicked.emit(self.fid)
            self.assertEqual(updates,[self.fid]);self.assertEqual(details,[])

    def test_organizer_title_keeps_space_beside_actions(self):
        from app.ui.pages.organizer_page import OrganizerPage
        page=OrganizerPage();self.addCleanup(page.deleteLater)
        page.resize(1100,680);page.show();self.app.processEvents()
        title=page.findChild(QLabel,'organizer_title')
        self.assertGreaterEqual(title.width(),title.fontMetrics().horizontalAdvance(title.text()))
        self.assertGreater(page.scan_btn.mapTo(page,QPoint()).x(),title.mapTo(page,QPoint()).x())
        page.close()

    def test_release_news_uses_library_palette_in_dark_and_light(self):
        from app.ui.home_style import colors
        from app.ui.five_screen_style import qss
        previous=self.app.property('animevaultTheme')
        try:
            for theme in ('dark','light'):
                self.app.setProperty('animevaultTheme',theme)
                c=colors();style=qss('release_news')
                self.assertIn('background:'+c['panel'],style)
                self.assertIn('background:'+c['raised'],style)
                self.assertIn('color:'+c['text'],style)
        finally:self.app.setProperty('animevaultTheme',previous)
