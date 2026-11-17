"""Real worker lifecycle, truthful totals and GUI-thread progress adapters."""
import unittest
from threading import Event
from unittest.mock import patch
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QWidget
from app.ui.components.operation_progress import OperationProgress, watch
from app.ui.theme import apply_theme
import test_ui_regressions as support


class SampleWorker(QThread):
    progress = pyqtSignal(str, int, int)
    def __init__(self):
        super().__init__(); self.release = Event()
    def run(self):
        self.msleep(230)
        self.progress.emit('Checking file 2', 2, 4)
        self.release.wait(10)


class ProgressTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    @classmethod
    def setUpClass(cls): support.Regressions.setUpClass.__func__(cls)
    def tearDown(self):
        apply_theme(self.app, 'dark')
        support.Regressions.tearDown(self)

    def test_unknown_total_and_bounds_are_truthful_in_both_themes(self):
        for theme in ('manga_light', 'dark'):
            apply_theme(self.app, theme)
            owner = QWidget(); dialog = OperationProgress(owner, 'Scanning folders')
            self.addCleanup(owner.deleteLater)
            dialog.report('Enumerating files', 50, 0)
            self.assertEqual(dialog.bar.maximum(), 0)
            self.assertEqual(dialog.processed.text(), 'Total not yet known')
            dialog.report('Checked files', 90, 20)
            self.assertEqual(dialog.circle.current, 20)
            self.assertEqual(dialog.bar.value(), 20)
            dialog.finish(); self.assertFalse(dialog.circle.timer.isActive())

    def test_real_worker_shows_updates_and_releases_progress_card(self):
        owner = QWidget(); owner.show(); self.addCleanup(owner.deleteLater)
        worker = SampleWorker(); dialog = watch(owner, worker, 'Scanning folders', worker.progress, major=True)
        worker.start()
        try:
            QTest.qWait(285)
            self.assertTrue(dialog.isVisible())
            self.assertEqual(dialog.circle.current, 2)
            self.assertEqual(dialog.message.text(), 'Checking file 2')
            worker.release.set()
            while worker.isRunning(): QTest.qWait(20)
            QTest.qWait(30)
            self.assertEqual(owner._operation_progress_cards, [])
        finally: worker.release.set(); worker.wait()

    def test_short_task_never_flashes_a_stale_window(self):
        owner = QWidget(); self.addCleanup(owner.deleteLater)
        class FastWorker(QThread):
            def run(self): pass
        worker = FastWorker(); dialog = watch(owner, worker, 'Preparing files', major=True)
        worker.start(); worker.wait(); QTest.qWait(230)
        self.assertFalse(owner._operation_progress_cards)

    def test_count_first_adapter_and_legacy_finished_signal(self):
        owner = QWidget(); self.addCleanup(owner.deleteLater)
        class LegacyWorker(QThread):
            finished = pyqtSignal(dict)
            progress = pyqtSignal(int, int, str)
            def run(self):
                self.progress.emit(3, 5, 'Moving third file')
                self.finished.emit({'moved': 3})
        worker = LegacyWorker(); dialog = watch(owner, worker, 'Moving files', worker.progress, order='counts_first', major=True)
        observed = []
        # Inspect queued UI state before the underlying thread-finished cleanup.
        worker.finished.connect(lambda result: observed.append((dialog.circle.current,dialog.message.text())))
        worker.start(); worker.wait(); QTest.qWait(230)
        self.assertEqual(observed, [(3, 'Moving third file')])
        self.assertFalse(owner._operation_progress_cards)

    def test_routine_tasks_only_use_footer_and_restore_overlapping_message(self):
        from app.ui.components.refresh_progress import RefreshProgress
        from app.ui.components.operation_progress import MinorProgress
        from PyQt5.QtWidgets import QDialog
        owner=QWidget();owner.refresh_progress=RefreshProgress(owner);self.addCleanup(owner.deleteLater)
        owner.refresh_progress.begin('metadata','Refreshing metadata')
        worker=SampleWorker(); progress=watch(owner,worker,'Loading episode list',worker.progress)
        self.assertIsInstance(progress,MinorProgress)
        self.assertFalse(owner.findChildren(QDialog))
        self.assertIn('Loading episode list',owner.refresh_progress.toolTip())
        worker.start()
        try:
            QTest.qWait(280)
            self.assertFalse(owner.findChildren(QDialog))
            self.assertIn('Checking file 2',owner.refresh_progress.toolTip())
            worker.release.set()
            while worker.isRunning():QTest.qWait(20)
            QTest.qWait(20)
            self.assertEqual(owner.refresh_progress.toolTip(),'Refreshing metadata')
        finally:worker.release.set();worker.wait()

    def test_leaving_a_page_does_not_leave_a_stuck_footer_task(self):
        from app.ui.components.refresh_progress import RefreshProgress
        from PyQt5.QtCore import QCoreApplication,QEvent
        host=QWidget();host.refresh_progress=RefreshProgress(host);self.addCleanup(host.deleteLater)
        page=QWidget(host);worker=SampleWorker();watch(page,worker,'Loading details')
        worker.start()
        try:
            page.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
            self.assertTrue(host.refresh_progress.tasks)
            worker.release.set()
            while worker.isRunning():QTest.qWait(20)
            QTest.qWait(20);self.assertFalse(host.refresh_progress.tasks)
        finally:worker.release.set();worker.wait()
