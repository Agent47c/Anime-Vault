"""Successful queue submission completes navigation and root actions fit."""
import unittest
from unittest.mock import patch,Mock
from PyQt5.QtCore import Qt,QPoint
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QStackedWidget,QDialog,QPushButton
from app import db
from app.ui.theme import apply_theme
from app.ui.navigation import navigate
from app.ui.pages.release_search_page import ReleaseSearchPage,DownloadReview
import test_ui_regressions as support


class DownloadReviewCompletionTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def tearDown(self):
        apply_theme(self.app,'dark');support.Regressions.tearDown(self)

    def search_page(self):
        apply_theme(self.app,'manga_light')
        host=QWidget();host.resize(1400,1000);layout=QVBoxLayout(host)
        host.stacked_widget=QStackedWidget();layout.addWidget(host.stacked_widget)
        for i in range(6):host.stacked_widget.addWidget(QWidget())
        def switch(index):host.stacked_widget.setCurrentIndex(index)
        host._on_nav_clicked=Mock(side_effect=switch)
        host.show();self.addCleanup(host.deleteLater)
        page=ReleaseSearchPage(host,self.fid);navigate(page)
        entry=dict(identity='release-6',title='Example - 06',episode_keys=['EPISODE:S1:6'],episodes=[6],
                   source='Test',status='Missing — Release Found',match_confirmed=True,season=1)
        page.context=dict(fid=self.fid,title='Example',local={},pending=[],missing=[],expected=[],boundaries={})
        page.results=[entry];page.model.selected={entry['identity']};page.render()
        return host,page,entry

    def test_success_closes_review_marks_queued_and_opens_downloads_without_sync_polling(self):
        host,page,entry=self.search_page()
        page.review();review=host.stacked_widget.currentWidget().workflow
        self.assertIsInstance(review,DownloadReview);review.checked.setChecked(True)
        def submitted(dialog,operation,success):success(['saved destination'])
        with patch('app.ui.pages.release_search_page.start',side_effect=submitted),patch('app.ui.downloads.monitor') as monitor:
            review.apply();review.apply()
            monitor.assert_not_called()
        self.assertEqual(review.result(),QDialog.Accepted)
        self.assertIs(host.stacked_widget.currentWidget(),host.stacked_widget.widget(5))
        host._on_nav_clicked.assert_called_once_with(5)
        self.assertFalse(page.model.selected);self.assertFalse(page.review_button.isEnabled())
        self.assertEqual(entry['status'],'Downloading or Queued')
        self.assertIn('EPISODE:S1:6',page.context['pending'])
        self.assertFalse(page.model.setData(page.model.index(0,0),Qt.Checked,Qt.CheckStateRole))
        self.assertFalse(page.model.flags(page.model.index(0,0))&Qt.ItemIsUserCheckable)

    def test_cancel_does_not_mark_release_as_submitted_or_change_tabs(self):
        host,page,entry=self.search_page();page.review()
        review=host.stacked_widget.currentWidget().workflow;review.reject()
        self.assertEqual(page.model.selected,{'release-6'})
        self.assertTrue(page.review_button.isEnabled());self.assertNotIn('_submitted',entry)
        host._on_nav_clicked.assert_not_called()

    def test_completion_leaves_other_results_available_for_review(self):
        host,page,entry=self.search_page()
        other={**entry,'identity':'release-7','episode_keys':['EPISODE:S1:7'],'episodes':[7]}
        page.results.append(other);page.model.selected.add('release-7')
        page.downloads_added([entry])
        self.assertEqual(page.model.selected,{'release-7'})
        self.assertTrue(page.review_button.isEnabled())
        self.assertNotIn('_submitted',other)
        self.assertTrue(page.model.flags(page.model.index(1,0))&Qt.ItemIsUserCheckable)

    def test_root_buttons_fit_parent_and_accept_window_mouse_hits(self):
        from app.ui.pages.organizer_page import OrganizerPage
        from app.ui.components.folder_button import FolderButton
        apply_theme(self.app,'manga_light');db.add_watched_directory(self.temp.name)
        page=OrganizerPage();self.addCleanup(page.deleteLater);page.resize(1400,1000);page.show();QTest.qWait(80)
        folder=page.findChild(FolderButton);remove=page.findChild(QPushButton,'remove_library_root')
        self.assertIsNotNone(folder);self.assertIsNotNone(remove)
        row=folder.parentWidget()
        for control in (folder,remove):
            self.assertTrue(row.rect().contains(control.geometry()),(row.size(),control.geometry()))
            point=control.mapTo(page,control.rect().center())
            self.assertIs(page.childAt(point),control)
        with patch('app.ui.components.folder_button.QDesktopServices.openUrl',return_value=True) as opened:
            QTest.mouseClick(page.windowHandle(),Qt.LeftButton,pos=folder.mapTo(page,folder.rect().center()))
            opened.assert_called_once()
        with patch('app.ui.pages.organizer_page.QMessageBox.question',return_value=16384) as asked:
            QTest.mouseClick(page.windowHandle(),Qt.LeftButton,pos=remove.mapTo(page,remove.rect().center()))
            asked.assert_called_once()
        self.assertEqual(db.get_watched_directories(),[])
