import unittest
from unittest.mock import patch
from app.ui.theme import apply_theme
from app.ui.pages.duplicate_page import DuplicatePage
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLineEdit
from app.ui.dialogs.adult_password_dialog import AdultPasswordDialog
import test_ui_regressions as support
class TwelveTests(unittest.TestCase):
 setUp=support.Regressions.setUp
 @classmethod
 def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
 def tearDown(self):apply_theme(self.app,'dark');support.Regressions.tearDown(self)
 def test_inspect_protected_copy_is_read_only(self):
  page=DuplicatePage();self.addCleanup(page.deleteLater)
  files=[dict(path='a.mkv',title='Demo',episodes=[1],signature=(100,1,1)),dict(path='b.mkv',title='Demo',episodes=[1],signature=(100,1,2))]
  page._results(([dict(files=files,hash='existing')],[]))
  item=page.tree.topLevelItem(0).child(0).child(0);page.tree.setCurrentItem(item)
  self.assertTrue(page.inspect.isEnabled());self.assertEqual(page._selected(),[])
  with patch('app.ui.navigation.navigate') as nav:
   page._inspect();dialog=nav.call_args.args[0];self.addCleanup(dialog.deleteLater)
  self.assertEqual(page._selected(),[])
 def test_password_modes_keep_masking_and_validation(self):
  apply_theme(self.app,'manga_light')
  for mode in ('unlock','change'):
   page=AdultPasswordDialog(mode=mode);self.addCleanup(page.deleteLater)
   self.assertIn('Noto Serif',page.styleSheet())
   self.assertTrue(all(w.echoMode()==QLineEdit.Password for w in page.findChildren(QLineEdit)))
 def test_styles_restore_sakura(self):
  from app.ui.episode_selection_style import style
  from app.ui.review_reference_style import grouping_style
  from app.ui.merge_duplicate_style import qss
  apply_theme(self.app,'manga_light')
  for value in (style('season_numbers'),grouping_style(),qss('duplicate_page')):self.assertIn('Noto Serif',value)
  apply_theme(self.app,'dark');self.assertNotIn('Noto Serif',style('season_numbers'))
