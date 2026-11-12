"""Explicit-search result navigation and boxed release filters."""
import unittest
from unittest.mock import patch
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QLineEdit,QScrollArea,QLabel,QPushButton,QApplication
from PyQt5.QtTest import QTest
import test_ui_regressions as support
from app import db,preferences
from app.ui.search_navigation import focus_results
from app.ui.components.tag_picker import TagPicker


class SearchFocusTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_default_on_setting_persists_and_disabled_does_not_move_focus_or_scroll(self):
        self.assertTrue(preferences.enabled('search_results_focus'))
        from app.ui.pages.settings_page import SettingsPage
        page=SettingsPage();self.assertTrue(page.search_results_focus_switch.isChecked())
        page.search_results_focus_switch.setChecked(False);page.deleteLater()
        self.assertFalse(preferences.enabled('search_results_focus'))
        reopened=SettingsPage();self.assertFalse(reopened.search_results_focus_switch.isChecked());reopened.deleteLater()
        owner,edit,scroll,target=self.scroller()
        try:
            edit.setFocus();focus_results(owner,target);QTest.qWait(20)
            self.assertEqual(scroll.verticalScrollBar().value(),0);self.assertTrue(edit.hasFocus())
            preferences.save('search_results_focus',True);focus_results(owner,target);QTest.qWait(20)
            self.assertGreater(scroll.verticalScrollBar().value(),0);self.assertTrue(target.hasFocus())
        finally:owner.close();owner.deleteLater()
    def scroller(self):
        owner=QWidget();layout=QVBoxLayout(owner);edit=QLineEdit();layout.addWidget(edit)
        scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();rows=QVBoxLayout(body)
        spacer=QWidget();spacer.setMinimumHeight(1000);rows.addWidget(spacer)
        target=QLabel('Search results');rows.addWidget(target);scroll.setWidget(body);layout.addWidget(scroll)
        owner.resize(600,400);owner.show();owner.activateWindow();QTest.qWait(20)
        return owner,edit,scroll,target
    def test_hidden_or_closed_owner_cannot_steal_focus(self):
        owner,edit,scroll,target=self.scroller();focus_results(owner,target);owner.hide();QTest.qWait(20)
        self.assertEqual(scroll.verticalScrollBar().value(),0);owner.deleteLater()
    def test_release_search_focuses_results_only_for_search_completion(self):
        from test_release_search_ui import ReleaseSearchUITests
        from app.ui.pages.release_search_page import ReleaseSearchPage
        page=ReleaseSearchPage(None,self.fid);page.resize(1100,720);page.show();page.activateWindow();QTest.qWait(20)
        result=dict(context=ReleaseSearchUITests.context(self),results=ReleaseSearchUITests.entries(self,2))
        try:
            page.query.setFocus();page.loaded(result);QTest.qWait(20);self.assertTrue(page.query.hasFocus())
            page.loaded(result,focus_results=True);QTest.qWait(20)
            self.assertTrue(page.table.hasFocus());self.assertGreater(page.scroll.verticalScrollBar().value(),0);self.assertFalse(page.model.selected)
            preferences.save('search_results_focus',False);page.scroll.verticalScrollBar().setValue(0);page.query.setFocus()
            page.loaded(result,focus_results=True);QTest.qWait(20);self.assertTrue(page.query.hasFocus());self.assertEqual(page.scroll.verticalScrollBar().value(),0)
        finally:page.reject();page.deleteLater()
    def test_group_live_typing_keeps_input_focus_but_enter_reveals_results(self):
        from app.ui.pages.group_series_page import GroupSeriesPage
        db.upsert_franchise(dict(display_title='Different series'))
        page=GroupSeriesPage(self.fid);page.show();page.activateWindow()
        end=__import__('time').monotonic()+3
        while getattr(page,'_apply_worker',None) and __import__('time').monotonic()<end:QTest.qWait(10)
        try:
            page.search.setFocus();page.search.setText('Different');QTest.qWait(20);self.assertTrue(page.search.hasFocus())
            QTest.keyClick(page.search,Qt.Key_Return);QTest.qWait(20);self.assertTrue(page.list.hasFocus());self.assertFalse(page.model.checked)
        finally:page.reject();page.deleteLater()

    def test_rematch_initial_results_keep_input_but_submitted_search_focuses_results(self):
        from app.ui.dialogs.rematch_dialog import RematchDialog,AniListSearchWorker
        with patch.object(AniListSearchWorker,'start'):page=RematchDialog(self.fid)
        page.show();page.activateWindow();QTest.qWait(20)
        result=[dict(id=77,title={'english':'Example Season 2'},format='TV')]
        try:
            page.search_input.setFocus();page._on_results_ready(result);QTest.qWait(20)
            self.assertTrue(page.search_input.hasFocus())
            page._focus_after_search=True;page._submitted_search_query=page.search_input.text().strip()
            page._on_results_ready(result);QTest.qWait(20);self.assertTrue(page.results_container.hasFocus());self.assertFalse(page.selections)
            page.search_input.setFocus();page.search_input.setText('A new unfinished query')
            page._on_results_ready(result);QTest.qWait(20);self.assertTrue(page.search_input.hasFocus())
        finally:page.reject();page.deleteLater()

    def test_boxed_tags_keep_multiple_values_and_show_selection_count(self):
        picker=TagPicker('Genres');picker.addItem('All genres');picker.addItem('Action','Action');picker.addItem('Fantasy','Fantasy');picker.resize(250,44);picker.show()
        try:
            picker.showPopup();QTest.qWait(20)
            picker.tag_buttons[1].click();picker.tag_buttons[2].click()
            self.assertEqual(picker.currentData(),('Action','Fantasy'));self.assertIn('2 selected',picker.text());self.assertEqual(picker.count_label.text(),'2 selected')
            self.assertTrue(picker.tag_buttons[1].isChecked());self.assertTrue(picker.tag_buttons[2].isChecked())
            for tag in picker.tag_buttons:self.assertGreaterEqual(tag.width(),tag.minimumSizeHint().width())
            picker.tag_buttons[0].click();self.assertIsNone(picker.currentData());self.assertIn('All genres',picker.text())
            QTest.keyClick(picker.popup,Qt.Key_Escape);self.assertFalse(picker.popup.isVisible())
        finally:picker.hidePopup();picker.close();picker.deleteLater()
    def test_sort_boxes_are_single_choice(self):
        picker=TagPicker('Sort',multiple=False);picker.addItems(['Premiere newest','Premiere earliest','Most popular']);picker.show()
        try:
            picker.showPopup();picker.tag_buttons[2].click()
            self.assertEqual(picker.currentIndex(),2);self.assertEqual(len(picker.selected),1);self.assertFalse(picker.popup.isVisible())
        finally:picker.close();picker.deleteLater()
    def test_multi_filter_query_uses_lists_and_omits_empty_format(self):
        from app.core import release_news as news
        with patch.object(news,'cached',return_value={'Page':{'media':[]}}) as cached:
            news.discover(genre=['Fantasy','Action'],theme=['Isekai','Reincarnation'],media_format=['TV','MOVIE'])
            query,values=cached.call_args.args[1:3]
            self.assertIn('genre_in:$genre',query);self.assertIn('tag_in:$tag',query);self.assertIn('format_in:$format',query)
            self.assertEqual(values['genre'],['Action','Fantasy']);self.assertEqual(values['format'],['TV','MOVIE'])
            news.discover()
            query,values=cached.call_args.args[1:3]
            self.assertNotIn('format:',query);self.assertNotIn('format',values);self.assertNotIn('$format',query)
            news.discover(announced=True)
            self.assertIn('status:NOT_YET_RELEASED',cached.call_args.args[1])
