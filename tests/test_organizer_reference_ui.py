import unittest
from unittest.mock import patch
from PyQt5.QtWidgets import QFrame
import test_ui_regressions as support
from app.ui.pages.organizer_page import OrganizerPage,ScannerWorker


class OrganizerReferenceTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_reference_keeps_manual_scan_merge_and_duplicate_entry(self):
        with patch.object(ScannerWorker,'start') as scanner:
            page=OrganizerPage();page.resize(1200,900);page.show();self.app.processEvents();scanner.assert_not_called()
            self.assertEqual(page.organizer_tabs.count(),3);self.assertIs(page.organizer_tabs.widget(1),page.merge_page)
            self.assertEqual(page.organizer_tabs.tabText(2),'Review duplicate files');self.assertFalse(page.duplicates_btn.isVisible())
            self.assertEqual(len(page.rule_switches),5);self.assertGreater(page.preview_card.width(),page.width()*.8)
            page.scan_btn.click();scanner.assert_called_once();page.close();page.deleteLater()
    def test_theme_refresh_does_not_rebuild_or_change_rules(self):
        page=OrganizerPage();before=dict(page._rules);merge=page.merge_page
        self.app.setProperty('animevaultTheme','light');page.refresh_home_style()
        self.assertIn('#f7f3f6',page.season_tab.styleSheet());self.assertIs(page.merge_page,merge);self.assertEqual(page._rules,before)
        self.app.setProperty('animevaultTheme','dark');page.deleteLater()
    def test_duplicate_tab_is_manual_and_only_extra_copy_can_be_selected(self):
        from PyQt5.QtCore import Qt
        from app.ui.pages.duplicate_page import DuplicateWorker
        with patch.object(DuplicateWorker,'start') as start:
            page=OrganizerPage();page.organizer_tabs.setCurrentIndex(2);page.show();self.app.processEvents();start.assert_not_called()
            dup=page._duplicate_page;files=[dict(title='Example',path='a.mkv',episodes=[6]),dict(title='Example',path='b.mkv',episodes=[6])]
            dup._results(([dict(files=files)],[]));branch=dup.tree.topLevelItem(0).child(0)
            self.assertFalse(branch.child(0).flags() & Qt.ItemIsUserCheckable);self.assertFalse(dup._selected())
            branch.child(1).setCheckState(0,Qt.Checked);self.assertEqual(len(dup._selected()),1);self.assertTrue(dup.delete.isEnabled());page.close();page.deleteLater()
    def test_duplicate_scan_waits_for_merge(self):
        from app.ui.pages.duplicate_page import DuplicateWorker
        page=OrganizerPage()
        with patch.object(page.merge_page,'busy',return_value=True),patch.object(DuplicateWorker,'start') as start:page._duplicate_page._scan();start.assert_not_called()
        self.assertIn('Wait',page._duplicate_page.status.text());page.deleteLater()
