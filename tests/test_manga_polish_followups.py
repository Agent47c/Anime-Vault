import unittest
from unittest.mock import patch
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
import test_ui_regressions as support
from app import db
from app.ui.theme import apply_theme
class PolishTests(unittest.TestCase):
 setUp=support.Regressions.setUp
 @classmethod
 def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
 def tearDown(self):apply_theme(self.app,'dark');support.Regressions.tearDown(self)
 def test_update_hierarchy_keeps_actions_in_more(self):
  from app.ui.pages.updates_page import UpdateCard
  apply_theme(self.app,'manga_light');r=dict(db.get_franchise(self.fid),update_details='Episode 7 airing soon')
  card=UpdateCard(r);self.addCleanup(card.deleteLater);card.resize(1400,260);card.show();QTest.qWait(20)
  buttons={b.text():b for b in card.findChildren(QPushButton) if b.isVisible()}
  self.assertIn('Find Download Files',buttons);self.assertIn('View changes',buttons);self.assertIn('Later',buttons)
  self.assertEqual([a.text() for a in buttons['More'].menu().actions()],['Not interested','Mute anime','Watched and ignore','Dismiss'])
  self.assertEqual(buttons['Remove anime'].property('role'),'destructive')
 def test_banner_placeholder_is_hidden(self):
  from app.ui.pages.release_news_page import ReleaseNewsPage
  apply_theme(self.app,'manga_light')
  with patch.object(ReleaseNewsPage,'load'):page=ReleaseNewsPage(media_id=21)
  self.addCleanup(page.deleteLater);self.addCleanup(page.stop)
  page.release_hero(dict(id=21,title={'english':'Demo'},description='Plot'))
  self.assertTrue(page.release_banner.isHidden());self.assertTrue(page.presets_button.isHidden())
 def test_genre_popup_is_transient_and_no_apply_panel(self):
  from app.ui.pages.release_news_page import ReleaseNewsPage
  apply_theme(self.app,'manga_light')
  with patch.object(ReleaseNewsPage,'load'):page=ReleaseNewsPage()
  self.addCleanup(page.deleteLater);self.addCleanup(page.stop)
  page.genre_filter.showPopup();popup=page.genre_filter.popup
  self.assertTrue(popup.windowFlags() & Qt.Popup)
  self.assertFalse(any(b.isVisible() and b.text() in ('Apply filters','Clear tags','Cancel','Done') for b in popup.findChildren(QPushButton)))
  page.genre_filter.hidePopup()
 def test_continuous_episode_number_is_independent_of_destination_and_editable(self):
  from app.ui.pages.release_search_page import ConfirmCoverage
  from app.core import download_discovery,downloads
  result=[];context=dict(title='Demo',fid=self.fid,season=1,continuous=True,local={},pending={})
  page=ConfirmCoverage(None,dict(title='Demo - 177',episodes=[177]),context,result.append)
  self.assertFalse(page.continuous.isChecked());page.continuous.setChecked(True)
  self.addCleanup(page.deleteLater)
  page.season.setValue(2);page.apply()
  self.assertEqual(result[0]['episode_keys'],['EPISODE:ABS:177'])
  self.assertEqual(result[0]['season'],2)
  self.assertTrue(db.uses_continuous_episodes(db.get_series(self.fid)))
  stored={};downloads._apply_download_context(stored,result[0])
  self.assertEqual(stored['episode_keys'],['EPISODE:ABS:177']);self.assertTrue(stored['continuous'])
  result.clear();page.episode_inputs[0].setText('178');page.apply()
  self.assertEqual(result[0]['episode_keys'],['EPISODE:ABS:178'])
  page.continuous.setChecked(False);result.clear();page.apply()
  self.assertEqual(result[0]['episode_keys'],['EPISODE:S2:178'])
  self.assertTrue(db.uses_continuous_episodes(db.get_series(self.fid)))
  self.assertTrue(download_discovery.library_context(self.fid)['continuous'])
 def test_invalid_or_overlapping_episode_numbers_do_not_save_preference(self):
  from app.ui.pages.release_search_page import ConfirmCoverage
  db.set_continuous_episodes(self.fid,False);result=[]
  context=dict(title='Demo',fid=self.fid,season=1,continuous=False,local={},pending={})
  page=ConfirmCoverage(None,[dict(title='Demo - 177',episodes=[177]),dict(title='Demo - 178',episodes=[178])],context,result.append)
  self.addCleanup(page.deleteLater);page.continuous.setChecked(True)
  page.episode_inputs[1].setText('177');page.apply()
  self.assertFalse(result);self.assertFalse(db.uses_continuous_episodes(db.get_series(self.fid)))
  page.episode_inputs[1].setText('178');page.apply()
  self.assertEqual([e['episode_keys'] for e in result[0]],[['EPISODE:ABS:177'],['EPISODE:ABS:178']])
 def test_organizer_keeps_review_separate_and_does_not_preselect_moves(self):
  from app.ui.pages.organizer_page import OrganizerPage
  from app.ui.components.neumorphic_tabs import NeumorphicTabBar
  from PyQt5.QtWidgets import QLabel
  apply_theme(self.app,'manga_light');page=OrganizerPage();self.addCleanup(page.deleteLater)
  item=dict(anime_name='Demo',video_count=1,status_badge='Download ready',is_organized=False,download_job_id='example')
  page._on_scan_finished(dict(unorganized=[item],organized=[],all=[item]))
  page._preview_stale=True;page._render_table();page.resize(1000,850);page.show();QTest.qWait(20)
  self.assertFalse(page._selected_items);self.assertFalse(page.organize_btn.isEnabled())
  cell=page.table.cellWidget(0,3);review=cell.findChild(QPushButton)
  self.assertTrue(review.isEnabled());self.assertGreaterEqual(cell.width(),review.width()+20)
  label=page.table.cellWidget(0,2).findChild(QLabel)
  self.assertGreaterEqual(label.width(),label.fontMetrics().horizontalAdvance(label.text())+12)
  self.assertIsInstance(page.organizer_tabs.tabBar(),NeumorphicTabBar)
  page._switch_tab('all');page._switch_tab('unorganized');self.assertFalse(page._selected_items)
 def test_submission_retains_absolute_identity_and_physical_season(self):
  from app.core import download_discovery as discovery,downloads
  entry=dict(title='Demo - 177',magnet='magnet:?xt=urn:btih:'+'a'*40,episode_keys=['EPISODE:ABS:177'],season=1,continuous=True)
  context=dict(pending=set(),local={})
  with patch.object(discovery,'library_context',return_value=context) as lookup,patch.object(downloads,'add_download',return_value='staging/Season 01') as add:
   self.assertEqual(discovery.submit(self.fid,[entry]),['staging/Season 01'])
  self.assertEqual(add.call_args.args[2],1);self.assertEqual(add.call_args.kwargs['context']['episode_keys'],['EPISODE:ABS:177'])
  lookup.assert_called_with(self.fid,1,continuous=True)
 def test_each_file_has_its_own_season_and_no_redundant_title_tooltip(self):
  from app.ui.pages.release_search_page import ConfirmCoverage
  from PyQt5.QtWidgets import QLabel
  result=[];entries=[dict(title='Demo S01E06',episodes=[6],season=1),dict(title='Demo S02E06',episodes=[6],season=2)]
  page=ConfirmCoverage(None,entries,dict(title='Demo',fid=self.fid,season=1,continuous=False,local={},pending={}),result.append)
  self.addCleanup(page.deleteLater);page.apply()
  self.assertEqual([r['episode_keys'] for r in result[0]],[['EPISODE:S1:6'],['EPISODE:S2:6']])
  self.assertEqual(page.continuous.text(),'Continuous episode numbering')
  for label in page.findChildren(QLabel):
   if label.text() in ('Demo S01E06','Demo S02E06'):self.assertFalse(label.toolTip())
  self.assertIn('Season 02',page.assignment_labels[1].text())
 def test_cached_update_cards_restore_sakura_material_on_family_change(self):
  from app.ui.pages.updates_page import UpdatesPage
  apply_theme(self.app,'manga_light')
  with patch.object(UpdatesPage,'refresh'):page=UpdatesPage()
  self.addCleanup(page.deleteLater)
  page._updates=[dict(db.get_franchise(self.fid),update_details='Episode 7 airing soon')]
  page._saved_updates=[];page._health_records=[];page._health=[]
  page._render_cards();manga=page._update_card_pool[self.fid][1]
  apply_theme(self.app,'dark');page.refresh_home_style()
  sakura=page._update_card_pool[self.fid][1]
  self.assertIsNot(sakura,manga);self.assertEqual(sakura.layout().contentsMargins().right(),12)
  apply_theme(self.app,'light');page.refresh_home_style()
  self.assertIs(page._update_card_pool[self.fid][1],sakura)
