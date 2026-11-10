"""Worker-loaded details, disposable navigation and stale-result protection."""
import time
import threading
import unittest
from unittest.mock import patch
from PyQt5 import sip
from PyQt5.QtCore import QTimer,QEvent,QCoreApplication
from PyQt5.QtWidgets import QWidget,QStackedWidget,QVBoxLayout,QPushButton
from PyQt5.QtTest import QTest
import test_ui_regressions as support
from app import db
from app.ui.pages.detail_modal import DetailModal
from app.ui.detail_data import prepare_details
from app.ui.navigation import navigate
from app.ui.io_task import running


class DetailNavigationTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def wait(self,predicate):
        end=time.monotonic()+5
        while not predicate() and time.monotonic()<end:QTest.qWait(10)
        self.assertTrue(predicate())

    def host(self):
        host=QWidget();host.stacked_widget=QStackedWidget();QVBoxLayout(host).addWidget(host.stacked_widget)
        library=QWidget();host.stacked_widget.addWidget(library);host.resize(1200,850);host.show()
        self.addCleanup(host.deleteLater)
        return host,library

    def test_open_and_rematch_prepare_off_thread_with_live_heartbeat(self):
        threads=[];ticks=[]
        def slow(fid):
            threads.append(threading.get_ident());time.sleep(.15);return prepare_details(fid)
        host,library=self.host()
        with patch('app.ui.detail_data.prepare_details',side_effect=slow):
            started=time.monotonic();dialog=DetailModal(self.fid,host,async_load=True);navigate(dialog)
            self.assertLess(time.monotonic()-started,.1)
            timer=QTimer();timer.setInterval(10);timer.timeout.connect(lambda:ticks.append(time.monotonic()));timer.start()
            self.wait(lambda:hasattr(dialog,'poster_label'))
            self.assertGreater(len(ticks),6);self.assertNotIn(threading.get_ident(),threads)
            changes=[];dialog.data_changed.connect(lambda:changes.append(True))
            started=time.monotonic();dialog._on_rematched(self.fid)
            self.assertLess(time.monotonic()-started,.05)
            self.wait(lambda:bool(changes));timer.stop()
            dialog.reject();self.wait(lambda:not running())
        self.assertIs(host.stacked_widget.currentWidget(),library)

    def test_back_disposes_detail_without_rebuilding_library(self):
        host,library=self.host()
        for _ in range(3):
            dialog=DetailModal(self.fid,host);navigate(dialog)
            page=host.stacked_widget.currentWidget()
            back=next(b for b in page.findChildren(QPushButton) if b.text()=='Back');back.click()
            self.app.processEvents();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
            self.assertIs(host.stacked_widget.currentWidget(),library)
            self.assertEqual(host.stacked_widget.count(),1)
            self.assertTrue(sip.isdeleted(dialog));self.assertEqual(host._navigation_pages,[])

    def test_leaving_before_load_does_not_reopen_page_or_leak_snapshot(self):
        host,library=self.host();snapshots=[]
        def slow(fid):
            time.sleep(.1);data=prepare_details(fid);snapshots.append(data['snapshot']['connection']);return data
        with patch('app.ui.detail_data.prepare_details',side_effect=slow):
            dialog=DetailModal(self.fid,host,async_load=True);navigate(dialog);self.app.processEvents()
            dialog.reject();self.wait(lambda:bool(snapshots) and not running());QTest.qWait(20)
        self.assertIs(host.stacked_widget.currentWidget(),library)
        import sqlite3
        with self.assertRaises(sqlite3.ProgrammingError):snapshots[0].execute('SELECT 1')

    def test_worker_reuses_resolved_series_for_seasons_and_preserves_records(self):
        sid=db.upsert_season(dict(franchise_id=self.fid,season_number=1,title_display='Season 1'))
        with patch.object(db,'get_series',wraps=db.get_series) as resolve:
            data=prepare_details(self.fid)
        try:
            self.assertEqual(resolve.call_count,1);self.assertEqual(data['seasons'][0]['id'],sid)
            self.assertEqual(data['franchise']['id'],self.fid)
        finally:data['snapshot']['connection'].close()

    def test_refresh_worker_prepares_library_index_reused_by_ui(self):
        from app.ui.refresh import RefreshWorker
        from app.ui.pages.library_page import LibraryPage
        results=[];worker=RefreshWorker(allow_network=False);worker.ready.connect(results.append)
        worker.run();self.assertEqual(len(results),1);snapshot=results[0]
        page=LibraryPage()
        try:
            with db.refresh_view(snapshot),patch('app.core.library_index.LibraryIndex',side_effect=AssertionError('UI must reuse prepared index')):
                page.refresh()
                self.assertIs(page._library_index,snapshot['library_index'])
                self.assertIs(db.get_series_library(),snapshot['series_groups'])
        finally:page.deleteLater();snapshot['connection'].close()
