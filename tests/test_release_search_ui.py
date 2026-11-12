"""Release search reference presentation retains existing selection and coverage."""
import unittest
from unittest.mock import patch
from PyQt5.QtCore import Qt,QPoint
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QPushButton,QWidget
import test_ui_regressions as support
from app.ui.pages.release_search_page import ReleaseSearchPage


class ReleaseSearchUITests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def page(self):
        page=ReleaseSearchPage(None,self.fid);page.resize(1450,1000);page.show();self.app.processEvents();return page
    def entries(self,count=1):
        return [dict(identity=str(i),title=f'[ASW] An anime release Season 2 - {i+1:02} [1080p HEVC]',episode_keys=[f'S2:EPISODE:{i+1}'],episodes=[i+1],quality='1080p',group='ASW',size='212 MiB',seeders=84,source='Example',status='Missing — Release Found') for i in range(count)]
    def context(self,season=2):
        return dict(fid=self.fid,title='The correct anime',aliases=['The correct anime'],continuous=False,season=season,local={},pending=[],expected=[],boundaries={'S2':12},download_aliases=[])
    def test_remembered_alias_is_scoped_and_does_not_override_conflicts(self):
        from app.core import download_discovery as d
        entry=dict(title='[ASW] Encoder Alternate Name - 05 [1080p]',identity='one',source='Test')
        ctx=self.context();self.assertEqual(d.classify(entry,ctx)['status'],'Match Uncertain')
        d.remember_download_alias(self.fid,2,'Encoder Alternate Name');ctx['download_aliases']=d.download_aliases(self.fid,2)
        self.assertEqual(d.classify(entry,ctx)['episode_keys'],['EPISODE:S2:5'])
        self.assertEqual(d.download_aliases(self.fid,3),[])
        for title in ('Encoder Alternate Name S03E05','Encoder Alternate Name - 15 [1080p]'):
            self.assertEqual(d.classify({**entry,'title':title},ctx)['status'],'Match Uncertain')
    def test_simple_confirmation_assigns_episode_range_and_remembers_title(self):
        from app.core import download_discovery as d
        from app.ui.pages.release_search_page import ConfirmCoverage
        from app.ui.dialogs.drawer import DrawerDialog
        values=[];dialog=ConfirmCoverage(None,dict(title='Encoder Name - 05',episodes=[5]),self.context(),values.append)
        self.assertNotIsInstance(dialog,DrawerDialog);self.assertTrue(dialog.centered_workflow)
        dialog.episode_inputs[0].setText('5, 6');dialog.remember.setChecked(True)
        dialog.apply();self.assertEqual(values[0]['episode_keys'],['EPISODE:S2:5','EPISODE:S2:6']);self.assertEqual(d.download_aliases(self.fid,2),['Encoder Name']);dialog.deleteLater()
    def test_confirmation_uses_checked_rows_without_highlighting_and_confirms_together(self):
        page=self.page();page.results=self.entries(2);page.context=self.context();page.model.selected={'0','1'};page.render();page.table.clearSelection()
        with patch('app.ui.pages.release_search_page.navigate') as nav:page.confirm_match()
        dialog=nav.call_args.args[0];self.assertEqual(len(dialog.episode_inputs),2)
        dialog.episode_inputs[0].setText('6');dialog.episode_inputs[1].setText('7');dialog.apply()
        self.assertEqual([r['episode_keys'] for r in page.results],[['EPISODE:S2:6'],['EPISODE:S2:7']]);self.assertEqual(page.model.selected,{'0','1'})
        dialog.deleteLater();page.reject();page.deleteLater()
    def test_duplicate_episode_assignments_require_correction(self):
        from app.ui.pages.release_search_page import ConfirmCoverage
        values=[];dialog=ConfirmCoverage(None,self.entries(2),self.context(),values.append)
        for edit in dialog.episode_inputs:edit.setText('6')
        dialog.apply();self.assertFalse(values);self.assertIn('same episode',dialog.validation.text());dialog.reject();dialog.deleteLater()
    def test_checkbox_and_keyboard_update_selection_and_review_count(self):
        page=self.page();page.results=self.entries();page.render();self.app.processEvents()
        index=page.model.index(0,0);rect=page.table.visualRect(index)
        QTest.mouseClick(page.table.viewport(),Qt.LeftButton,pos=QPoint(rect.left()+20,rect.center().y()))
        self.assertEqual(page.model.selected,{'0'});self.assertIn('(1)',page.review_button.text())
        page.table.setCurrentIndex(index);page.table.setFocus();QTest.keyClick(page.table,Qt.Key_Space)
        self.assertEqual(page.model.selected,set());page.reject();page.deleteLater()
    def test_existing_controls_and_full_tooltips_remain(self):
        page=self.page();page.results=self.entries();page.render()
        self.assertIn(page.results[0]['title'],page.model.index(0,0).data(Qt.ToolTipRole))
        labels={b.text() for b in page.findChildren(QPushButton)}
        for value in ('Confirm highlighted match','Download Missing Episodes','Paste magnet / torrent','Open source in Chrome','Use title','Cancel search'):self.assertIn(value,labels)
        with patch('app.ui.pages.release_search_page.IOTask') as task:self.assertIsNone(page._worker)
        task.assert_not_called();page.reject();page.deleteLater()
    def test_simplified_layout_keeps_actions_fixed_and_coverage_above_results(self):
        page=self.page();page.results=self.entries(100);page.render()
        try:
            for width,height in ((1450,1000),(1100,720)):
                page.resize(width,height);QTest.qWait(30)
                self.assertLess(page.availability_panel.y(),page.table.y())
                self.assertIs(page.action_panel.parentWidget(),page)
                position=page.action_panel.pos()
                page.scroll.verticalScrollBar().setValue(page.scroll.verticalScrollBar().maximum())
                QTest.qWait(10);self.assertEqual(page.action_panel.pos(),position)
                for control in page.action_buttons.values():
                    self.assertGreaterEqual(control.width(),control.minimumSizeHint().width())
                    self.assertTrue(control.isVisible())
                self.assertLessEqual(page.action_panel.geometry().right(),page.width())
                self.assertEqual(page.model.rowCount(),100)
        finally:page.reject();page.deleteLater()
    def test_episode_cards_use_existing_availability_without_invented_metadata(self):
        page=self.page();page.availability_model.rows=[dict(episode='S1:EPISODE:1',status='In Library'),dict(episode='S1:EPISODE:2',status='Missing — No Release Found')]
        page.show_episodes.setChecked(True);self.app.processEvents()
        self.assertTrue(page.availability.isVisible());self.assertEqual(page.availability_model.rowCount(),2)
        self.assertEqual(page.availability_model.index(1,1).data(),'Missing — No Release Found');page.reject();page.deleteLater()
    def test_large_result_list_stays_virtual_and_theme_is_scoped(self):
        page=self.page();before=len(page.findChildren(QWidget));page.results=self.entries(2000);page.render();self.app.processEvents()
        self.assertEqual(page.model.rowCount(),2000);self.assertLessEqual(len(page.findChildren(QWidget)),before+5)
        self.app.setProperty('animevaultTheme','light');page.refresh_home_style();self.assertIn('#f7f3f6',page.styleSheet())
        self.app.setProperty('animevaultTheme','dark');page.reject();page.deleteLater()
    def test_custom_query_survives_reopening_and_can_switch_back(self):
        page=self.page();query='[Other Group] Uchuu custom name 720p'
        page.query.setText(query);page.save_custom_query();page.reject();page.deleteLater()
        page=self.page();self.assertEqual(page.query.text(),query);self.assertTrue(page.title_choice.currentData(Qt.UserRole+1))
        page.title_choice.setCurrentIndex(1);normal=page.query.text();self.assertNotEqual(normal,query);page.reject();page.deleteLater()
        page=self.page();self.assertEqual(page.query.text(),normal);self.assertEqual(page.title_choice.itemData(0),query);page.reject();page.deleteLater()
    def test_custom_queries_are_isolated_by_anime_and_season(self):
        from app import db
        from app.core import download_queries as queries
        queries.save_custom_query(self.fid,2,'Season two custom');queries.save_custom_query(self.fid,3,'Season three custom')
        self.assertEqual(queries.custom_query(self.fid,2)['query'],'Season two custom');self.assertEqual(queries.custom_query(self.fid,3)['query'],'Season three custom')
        self.assertEqual(queries.custom_query(self.fid,None),{})
        other=db.upsert_franchise({'display_title':'Unrelated anime'});self.assertEqual(queries.custom_query(other,None),{})
    def test_empty_custom_query_does_not_replace_saved_value(self):
        from app.core import download_queries as queries
        page=self.page();page.query.setText('My custom search');page.save_custom_query();page.query.setText('   ');page.save_custom_query()
        self.assertIn('Enter your custom',page.status.text());self.assertEqual(queries.custom_query(self.fid,page.season.currentData())['query'],'My custom search');page.reject();page.deleteLater()
