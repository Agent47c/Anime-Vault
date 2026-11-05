"""Manual Organizer scans, saved previews and readable button states."""
import unittest
from unittest.mock import patch, Mock
from PyQt5.QtWidgets import QMainWindow,QPushButton,QStyleOptionButton,QStyle
from app import db
from app.ui.pages.organizer_page import OrganizerPage,OrganizerReviewDialog,ScannerWorker
from app.ui.main_window import MainWindow
from app.ui.organizer_cache import save_preview,configuration
from app.ui.theme import apply_theme
import test_ui_regressions as support


class OrganizerManualUiTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def results(self):
        item = {'anime_name':'Example','folder_path':self.temp.name,'video_count':12,
                'status_badge':'Organized','status_reason':'Structured','moves':[]}
        return {'all':[item],'organized':[item],'unorganized':[],'unclassified_loose':[]}

    def test_opening_and_revisiting_organizer_never_starts_scan(self):
        with patch.object(ScannerWorker,'start') as start:
            page=OrganizerPage()
            page.show()
            self.app.processEvents()
            page.hide()
            page.show()
            self.app.processEvents()
            start.assert_not_called()
            self.assertIn('Scan now',page.top_status_badge.text())
            page.close()
            page.deleteLater()

    def test_saved_preview_restores_without_scanning_and_manual_button_still_works(self):
        page=OrganizerPage()
        data=self.results()
        save_preview(data,configuration(page._rules))
        page.deleteLater()
        with patch.object(ScannerWorker,'start') as start:
            restored=OrganizerPage()
            self.assertEqual(restored._data,data)
            self.assertIn('Saved preview',restored.top_status_badge.text())
            start.assert_not_called()
            restored.scan_btn.click()
            start.assert_called_once()
            restored.deleteLater()

    def test_changed_roots_keep_cached_preview_but_require_manual_rescan(self):
        page=OrganizerPage()
        data=self.results()
        save_preview(data,configuration(page._rules))
        page.deleteLater()
        db.add_watched_directory(self.temp.name)
        with patch.object(ScannerWorker,'start') as start:
            restored=OrganizerPage()
            self.assertEqual(restored._data,data)
            self.assertTrue(restored._preview_stale)
            self.assertFalse(restored.organize_btn.isEnabled())
            start.assert_not_called()
            restored.deleteLater()

    def test_review_button_text_fits_with_large_text_and_focus(self):
        db.set_state('text_scale','1.3')
        apply_theme(self.app,'dark')
        page=OrganizerPage()
        page._data=self.results()
        page._current_tab='organized'
        page._render_table()
        page.resize(1280,850)
        page.show()
        self.app.processEvents()
        button=page.table.cellWidget(0,3).findChild(QPushButton)
        before=button.size()
        button.setFocus()
        self.app.processEvents()
        self.assertEqual(button.size(),before)
        option=QStyleOptionButton()
        option.initFrom(button)
        rect=button.style().subElementRect(QStyle.SE_PushButtonContents,option,button)
        self.assertGreaterEqual(rect.width(),button.fontMetrics().horizontalAdvance(button.text()))
        self.assertGreaterEqual(button.height(),44)
        page.close()
        page.deleteLater()

    def test_refresh_busy_labels_fit_with_dropdown_and_large_text(self):
        db.set_state('text_scale','1.3')
        apply_theme(self.app,'dark')
        window=QMainWindow()
        window._on_search_text_changed=Mock()
        window._request_refresh=Mock()
        window._open_custom_entry_dialog=Mock()
        header=MainWindow._create_top_header(window)
        window.setCentralWidget(header)
        window.resize(1280,100)
        window.show()
        self.app.processEvents()
        for label in ('Refresh','Refreshing…','Checking…'):
            button=window.refresh_button
            button.setText(label)
            option=QStyleOptionButton()
            option.initFrom(button)
            option.features|=QStyleOptionButton.HasMenu
            rect=button.style().subElementRect(QStyle.SE_PushButtonContents,option,button)
            self.assertGreaterEqual(rect.width(),button.fontMetrics().horizontalAdvance(label))
        self.assertEqual(len(window.refresh_button.menu().actions()),2)
        window.close()
        window.deleteLater()

    def test_review_close_control_uses_vector_cross_not_a_font_glyph(self):
        from app.ui.components.close_button import CloseButton
        dialog=OrganizerReviewDialog(self.results()['all'][0],{})
        close=dialog.findChild(CloseButton)
        self.assertIsNotNone(close)
        self.assertEqual(close.text(),'')
        self.assertEqual(close.accessibleName(),'Close organization review')
        close.click()
        self.assertEqual(dialog.result(),dialog.Rejected)
        dialog.deleteLater()
