import unittest
from unittest.mock import patch
from PyQt5.QtTest import QTest
from app.ui.theme import apply_theme
from app.ui.pages.release_search_page import ConfirmCoverage
from app.ui.downloads import DownloadsDrawer
import test_ui_regressions as support
class IngestScreens(unittest.TestCase):
 setUp=support.Regressions.setUp
 @classmethod
 def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
 def tearDown(self):apply_theme(self.app,'dark');support.Regressions.tearDown(self)
 def test_confirm_two_entries_keeps_distinct_numbers_and_callback(self):
  apply_theme(self.app,'manga_light');result=[]
  entries=[dict(title='Demo - 6',episodes=[6]),dict(title='Demo - 7',episodes=[7])]
  context=dict(title='Demo',fid=self.fid,season=1,local={},pending={})
  page=ConfirmCoverage(None,entries,context,result.append);self.addCleanup(page.deleteLater)
  self.assertEqual(page.objectName(),'confirm_selected');self.assertEqual(len(page.episode_inputs),2)
  page.apply();self.assertEqual([r['episodes'] for r in result[0]],[[6],[7]])
 def test_manga_manual_has_only_ingest_with_original_controls(self):
  apply_theme(self.app,'manga_light')
  with patch('app.ui.downloads.service.jobs',return_value=[]):page=DownloadsDrawer(fid=self.fid)
  self.addCleanup(page.deleteLater);self.addCleanup(page.timer.stop)
  self.assertEqual(page.objectName(),'manual_ingest');self.assertTrue(page.save_button.isHidden())
  self.assertTrue(page._ingest_configuration.isHidden());self.assertFalse(page.timer.isActive())
  self.assertIsNotNone(page.source);self.assertIn('source',page.controls)
  page.source.setText('magnet:?xt=urn:btih:test');self.assertEqual(page.source.text(),'magnet:?xt=urn:btih:test')
 def test_settings_configuration_stays_separate(self):
  apply_theme(self.app,'manga_light');page=DownloadsDrawer(fid=self.fid,settings_only=True);self.addCleanup(page.deleteLater)
  self.assertFalse(hasattr(page,'_ingest_configuration'));self.assertFalse(hasattr(page,'source'))
