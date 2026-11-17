import unittest
from pathlib import Path
from unittest.mock import patch
from PyQt5.QtWidgets import QPushButton
import test_ui_regressions as support
from app.ui.theme import apply_theme
from app.ui.pages.organizer_page import OrganizerPage,OrganizerReviewDialog


class OrganizerScreenshotFixes(unittest.TestCase):
    setUp=support.Regressions.setUp
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def tearDown(self):
        apply_theme(self.app,'dark');support.Regressions.tearDown(self)
    def item(self):return dict(anime_name='Demo',folder_path=str(Path(self.temp.name)/'anime'),moves=[],video_count=1,is_organized=False,status_badge='Season 1')
    def test_review_uses_light_master_instead_of_inline_dark_table(self):
        apply_theme(self.app,'manga_light');dialog=OrganizerReviewDialog(self.item(),{});self.addCleanup(dialog.deleteLater)
        self.assertEqual(dialog.table.styleSheet(),'');self.assertIn('#eef0f5',dialog.styleSheet())
    def test_result_changes_busy_caption_before_showing_alert(self):
        dialog=OrganizerReviewDialog(self.item(),{});self.addCleanup(dialog.deleteLater);dialog.organize_this_btn.setText('Moving files...')
        def shown(*args):self.assertEqual(dialog.organize_this_btn.text(),'Finished')
        with patch('app.ui.pages.organizer_page.QMessageBox.information',side_effect=shown):dialog._organization_finished(dict(moved=1,skipped=0,errors=[]))
    def test_stale_review_is_an_enabled_refresh_action(self):
        page=OrganizerPage();self.addCleanup(page.deleteLater);item=self.item()
        page._on_scan_finished(dict(unorganized=[item],organized=[],all=[item]))
        page._mark_preview_stale('Files changed')
        button=next(b for b in page.table.findChildren(QPushButton) if b.text()=='Refresh preview')
        self.assertTrue(button.isEnabled())
        with patch.object(page,'_start_scan') as scan:button.click()
        scan.assert_called_once()
