"""Explicit major operations, quiet routine feedback and truthful API status."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch,Mock
from PyQt5.QtWidgets import QLabel,QWidget,QHBoxLayout,QPushButton
from PyQt5.QtTest import QTest
from app.ui.theme import apply_theme
from app.ui.components.manga_shell import ApiStatusDot,MangaFooter
import test_ui_regressions as support


class ProgressRoutingTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def tearDown(self):apply_theme(self.app,'dark');support.Regressions.tearDown(self)

    def test_api_dot_is_red_until_both_services_are_checked(self):
        dot=ApiStatusDot();self.addCleanup(dot.deleteLater)
        self.assertFalse(dot.connected);self.assertIn('unchecked',dot.toolTip())
        dot.set_status(dict(services={'AniList':True,'Jikan':False},description='Jikan unavailable'))
        self.assertFalse(dot.connected)
        dot.set_status(dict(services={'AniList':True,'Jikan':True},description='Both checked'))
        self.assertTrue(dot.connected);dot.set_checking();self.assertFalse(dot.connected)

    def test_footer_keeps_only_operation_and_live_download_summary(self):
        host=QWidget();host.status_pill=QLabel('API unchecked');host.scan_stats_label=QLabel('233 anime indexed');host.bottom_free_label=QLabel('138 GB free')
        library=QWidget(host);library.service_status_row=QHBoxLayout(library);host.library_page=library
        host.bottom_bar=QWidget(host);QHBoxLayout(host.bottom_bar)
        footer=MangaFooter(host);self.addCleanup(footer.deleteLater);self.addCleanup(host.deleteLater)
        footer.activate(True);footer.resize(1100,34);footer.show();QTest.qWait(10)
        self.assertTrue(host.status_pill.isHidden());self.assertTrue(host.bottom_free_label.isHidden())
        self.assertIs(host.scan_stats_label.parentWidget(),library)
        footer.update_downloads([dict(status='Downloading',download_rate=2048),dict(status='Seeding',download_rate=999),dict(status='Completed',download_rate=999)])
        self.assertEqual(footer.transfers.text(),'Speed: 2.00 KB/s · Downloading: 1')
        footer.set_operation('Loading anime details');self.assertEqual(footer.operation.full_text,'Loading anime details')
        footer.set_operation('');self.assertEqual(footer.operation.full_text,'Ready')
        footer.activate(False);self.assertFalse(host.status_pill.isHidden())

    def test_api_checks_validate_provider_responses_and_keep_partial_status(self):
        from app.core.api_status import check_services
        from app import config
        anilist=Mock();anilist.json.return_value={'data':{'__typename':'Query'}}
        jikan=Mock();jikan.json.return_value={'data':[]}
        with patch.object(config,'_is_offline',None),patch('app.core.api_status.requests.post',return_value=anilist),patch('app.core.api_status.requests.get',return_value=jikan):
            self.assertEqual(check_services()['services'],{'AniList':True,'Jikan':True})
            jikan.json.return_value={'error':'maintenance'}
            self.assertEqual(check_services()['services'],{'AniList':True,'Jikan':False})

    def test_dirty_tab_refresh_is_quiet_but_storage_refresh_is_explicitly_major(self):
        from app.ui.main_window import MainWindow
        window=QWidget();window.refresh_button=QPushButton('Refresh');window.manga_header=SimpleNamespace(refresh=QPushButton('Refresh'))
        self.addCleanup(window.deleteLater);self.addCleanup(window.refresh_button.deleteLater);self.addCleanup(window.manga_header.refresh.deleteLater)
        window._show_scan_progress=Mock();window._apply_refresh_snapshot=Mock();window._refresh_failed=Mock();window._finish_refresh=Mock()
        with patch('app.ui.refresh.RefreshWorker'),patch('app.ui.components.operation_progress.watch') as watch:
            MainWindow._start_refresh(window,allow_network=False);watch.assert_not_called()
            window._refresh_busy=False
            MainWindow._start_refresh(window,allow_network=False,major=True,operation_title='Refreshing storage')
            self.assertTrue(watch.call_args.kwargs['major']);self.assertEqual(watch.call_args.args[2],'Refreshing storage')

    def test_storage_request_keeps_its_major_intent_while_a_routine_refresh_finishes(self):
        from app.ui.main_window import MainWindow
        window=QWidget();window._refresh_busy=True;window.refresh_button=QPushButton('Refresh');window._start_refresh=Mock()
        self.addCleanup(window.deleteLater);self.addCleanup(window.refresh_button.deleteLater)
        MainWindow._start_refresh(window,allow_network=False,major=True,operation_title='Refreshing storage')
        MainWindow._finish_refresh(window);QTest.qWait(10)
        self.assertTrue(window._start_refresh.call_args.kwargs['major'])
        self.assertEqual(window._start_refresh.call_args.kwargs['operation_title'],'Refreshing storage')
