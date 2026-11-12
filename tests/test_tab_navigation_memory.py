"""Tab switching retains workflows; explicit Back still releases them."""
import unittest
from pathlib import Path
from unittest.mock import patch
from PyQt5 import sip
from PyQt5.QtCore import QCoreApplication, QEvent
from PyQt5.QtWidgets import QWidget, QStackedWidget, QVBoxLayout, QDialog, QLineEdit, QLabel
import test_ui_regressions as support
from app.ui.navigation import navigate, switch_tab


class TabNavigationMemoryTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def host(self):
        host = QWidget()
        host.stacked_widget = QStackedWidget()
        QVBoxLayout(host).addWidget(host.stacked_widget)
        for _ in range(6):
            host.stacked_widget.addWidget(QWidget())
        host.show()
        self.addCleanup(host.deleteLater)
        return host

    def workflow(self, host):
        dialog = QDialog(host)
        dialog.dispose_on_leave = True
        field = QLineEdit('retained selection and text', dialog)
        QVBoxLayout(dialog).addWidget(field)
        navigate(dialog)
        return host.stacked_widget.currentWidget(), dialog, field

    def test_library_and_updates_restore_their_own_workflows(self):
        host = self.host()
        detail, dialog, field = self.workflow(host)
        field.setText('same detail, no rebuild')
        switch_tab(host, 2)
        news, news_dialog, _ = self.workflow(host)
        switch_tab(host, 4)
        switch_tab(host, 0)
        self.assertIs(host.stacked_widget.currentWidget(), detail)
        self.assertFalse(sip.isdeleted(dialog))
        self.assertEqual(field.text(), 'same detail, no rebuild')
        switch_tab(host, 2)
        self.assertIs(host.stacked_widget.currentWidget(), news)
        self.assertFalse(sip.isdeleted(news_dialog))
        news_dialog.reject()
        switch_tab(host, 4)
        switch_tab(host, 2)
        self.assertIs(host.stacked_widget.currentWidget(), host.stacked_widget.widget(2))
        dialog.reject()

    def test_nested_back_and_explicit_library_search_reset(self):
        host = self.host()
        detail, dialog, _ = self.workflow(host)
        child, child_dialog, _ = self.workflow(host)
        switch_tab(host, 3)
        switch_tab(host, 0)
        self.assertIs(host.stacked_widget.currentWidget(), child)
        child_dialog.reject()
        self.assertIs(host.stacked_widget.currentWidget(), detail)
        switch_tab(host, 4)
        switch_tab(host, 0)
        self.assertIs(host.stacked_widget.currentWidget(), detail)
        switch_tab(host, 0, restore=False)
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.assertTrue(sip.isdeleted(dialog))
        switch_tab(host, 4)
        switch_tab(host, 0)
        self.assertIs(host.stacked_widget.currentWidget(), host.stacked_widget.widget(0))

    def test_open_folder_uses_existing_moved_location_and_reports_failure(self):
        from app.ui.pages.downloads_page import DownloadsPage
        from types import SimpleNamespace
        folder = Path(self.temp.name)
        item = dict(id='job', library_destination=str(folder/'old'), root=str(folder), destination=str(folder/'staging'))
        page = SimpleNamespace(items=[item], selected=lambda:item, status=QLabel())
        with patch('app.ui.pages.downloads_page.QDesktopServices.openUrl', return_value=True) as opener:
            DownloadsPage.open_folder(page, False)
            self.assertEqual(Path(opener.call_args.args[0].toLocalFile()).resolve(), folder.resolve())
        with patch('app.ui.pages.downloads_page.QDesktopServices.openUrl', return_value=False):
            DownloadsPage.open_folder(page, 'job')
        self.assertIn('could not open', page.status.text())

    def test_open_folder_without_row_uses_configured_download_location(self):
        from app.ui.pages.downloads_page import DownloadsPage
        from types import SimpleNamespace
        page = SimpleNamespace(items=[], selected=lambda:None, status=QLabel())
        with patch('app.ui.pages.downloads_page.downloads.settings', return_value={'destination':self.temp.name}), patch('app.ui.pages.downloads_page.QDesktopServices.openUrl', return_value=True) as opener:
            DownloadsPage.open_folder(page)
            self.assertEqual(Path(opener.call_args.args[0].toLocalFile()).resolve(), Path(self.temp.name).resolve())
