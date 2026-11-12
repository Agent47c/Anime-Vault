"""Shared popups expand for complete labels; screen-limited labels wrap."""
import unittest
from unittest.mock import patch
from PyQt5.QtCore import Qt,QRect,QPoint
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import QComboBox,QStyleOptionViewItem,QWidget,QPushButton
from PyQt5.QtTest import QTest
import test_ui_regressions as support
from app.ui.components.dropdowns import install_dropdown_style,dropdown_font,ContainedMenu
from app.core import release_news


class DropdownTextFit(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def combo(self,labels,width=170):
        install_dropdown_style(self.app);combo=QComboBox();combo.addItems(labels);combo.resize(width,44);combo.show();self.app.processEvents();combo.showPopup();QTest.qWait(30);return combo
    def test_common_labels_fit_without_truncation_at_both_text_sizes(self):
        labels=['Above hero banner','Above broadcast schedule','Above All anime','Minimize to tray','Exit completely','Sort User Rating (Highest)','Aired episodes','Scheduled episodes']
        try:
            for scale in (1.,1.3):
                self.app.setProperty('animevaultScale',scale);combo=self.combo(labels)
                try:
                    metrics=QFontMetrics(dropdown_font());available=combo.view().visualRect(combo.model().index(0,0)).width()-round(56*scale)
                    self.assertGreaterEqual(available,max(metrics.horizontalAdvance(label) for label in labels))
                    screen=combo.screen().availableGeometry();self.assertTrue(screen.contains(combo.view().window().geometry()))
                    self.assertEqual(combo.currentIndex(),0)
                    self.assertEqual(combo.view().horizontalScrollBar().maximum(),0)
                finally:combo.hidePopup();combo.close();combo.deleteLater()
        finally:self.app.setProperty('animevaultScale',1.)
    def test_short_menus_do_not_need_vertical_scrollbar(self):
        for labels in (['Always ask','Minimize to tray','Exit completely'],['All broadcasts','Aired episodes','Scheduled episodes'],['Watched','Watching','Plan to watch','Dropped']):
            combo=self.combo(labels)
            try:
                self.assertEqual(combo.view().verticalScrollBar().maximum(),0)
                last=combo.view().visualRect(combo.model().index(len(labels)-1,0))
                self.assertLessEqual(last.bottom(),combo.view().viewport().height())
            finally:combo.hidePopup();combo.close();combo.deleteLater()
    def test_header_menu_stays_inside_window_at_right_edge_and_after_resize(self):
        install_dropdown_style(self.app)
        window=QWidget();window.setGeometry(100,100,900,720)
        button=QPushButton(window);button.setGeometry(848,12,44,44)
        menu=ContainedMenu(button)
        labels=['Add anime','Import watched TXT list','Settings','Watching · 2','Watched','Plan to watch · 0','Dropped · 0','Watched, removed · 0','Refresh local library','Refresh and sync with internet']
        for label in labels:menu.addAction(label)
        window.show()
        try:
            for height in (720,320,720):
                window.resize(900,height)
                menu.popup(button.mapToGlobal(QPoint(0,44)));QTest.qWait(30)
                bounds=QRect(window.mapToGlobal(QPoint()),window.size()).adjusted(8,8,-8,-8)
                self.assertTrue(bounds.contains(menu.geometry()),(bounds,menu.geometry()))
                self.assertEqual([action.text() for action in menu.actions()],labels)
                self.assertLessEqual(menu.maximumHeight(),height-16)
                QTest.keyClick(menu,Qt.Key_End);QTest.qWait(10)
                self.assertEqual(menu.activeAction(),menu.actions()[-1])
                self.assertTrue(menu.rect().contains(menu.actionGeometry(menu.actions()[-1])))
                menu.hide()
        finally:window.close();window.deleteLater()
    def test_exceptionally_long_label_wraps_within_available_screen(self):
        text='A very long season title with complete details '+('and an additional arc name '*20)
        combo=self.combo([text,'Short item'])
        try:
            popup=combo.view().window();screen=QRect(0,0,320,650)
            self.app._dropdown_styler.fit_popup(popup,screen);QTest.qWait(20)
            self.assertLessEqual(popup.width(),screen.width()-16)
            option=QStyleOptionViewItem();option.rect=QRect(0,0,combo._dropdown_row_width,1)
            hint=combo.itemDelegate().sizeHint(option,combo.model().index(0,0))
            self.assertGreater(hint.height(),44)
            self.assertEqual(combo.itemText(0),text)
            self.assertTrue(screen.contains(popup.geometry()))
        finally:combo.hidePopup();combo.close();combo.deleteLater()
    def test_release_timeline_fetches_missing_selected_anime_once(self):
        result={'Media':{'id':1996,'title':{'english':'Selected release'}},'Page':{'airingSchedules':[]}}
        with patch.object(release_news.api,'_graphql_request',return_value=result) as request:
            self.assertEqual(release_news.timeline(1996),result)
            self.assertEqual(request.call_args.args[1]['id'],1996)
            self.assertEqual(release_news.timeline(1996),result);self.assertEqual(request.call_count,1)
            release_news.timeline(1996,force=True);self.assertEqual(request.call_count,2)
    def test_release_details_page_loads_selected_anime_without_check_updates(self):
        import time
        from app.ui.pages.release_news_page import ReleaseNewsPage
        result={'Media':{'id':1996,'title':{'english':'Correct selected anime'}},'Page':{'airingSchedules':[]}}
        with patch.object(release_news.api,'_graphql_request',return_value=result) as request:
            page=ReleaseNewsPage(media_id=1996);page.show()
            try:
                end=time.monotonic()+3
                while not hasattr(page,'_last_result') and time.monotonic()<end:QTest.qWait(10)
                self.assertEqual(page._last_result['Media']['id'],1996)
                self.assertEqual(page._cache_info['source'],'network');self.assertEqual(request.call_count,1)
            finally:page.reject();page.deleteLater()
