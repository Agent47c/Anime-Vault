"""Startup focus and busy state must not masquerade as a held mouse press."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from PyQt5.QtCore import Qt,QEvent
from PyQt5.QtGui import QFocusEvent
from PyQt5.QtWidgets import QMainWindow,QPushButton
import test_ui_regressions as support
from app.ui.theme import apply_theme
from app.ui.components.title_bar import AppTitleBar
from app.ui.components.neumorphic import install
from app.ui.main_window import MainWindow

class StartupControlTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def tearDown(self):apply_theme(self.app,'dark');support.Regressions.tearDown(self)

    def test_caption_buttons_are_not_startup_tab_stops(self):
        apply_theme(self.app,'manga_light');window=QMainWindow();bar=AppTitleBar(window)
        self.addCleanup(window.deleteLater)
        for button in (bar.minimize_button,bar.maximize_button,bar.close_button):
            self.assertEqual(button.focusPolicy(),Qt.NoFocus)
            self.assertIsNone(button.graphicsEffect())

    def test_window_activation_does_not_set_hover_but_keyboard_tab_does(self):
        apply_theme(self.app,'manga_light');button=QPushButton('Refresh');install(button)
        self.addCleanup(button.deleteLater);motion=button.graphicsEffect().motion
        motion.eventFilter(button,QFocusEvent(QEvent.FocusIn,Qt.ActiveWindowFocusReason))
        self.assertEqual(motion.animation.endValue(),0.)
        motion.eventFilter(button,QFocusEvent(QEvent.FocusIn,Qt.TabFocusReason))
        self.assertEqual(motion.animation.endValue(),1.)

    def test_busy_refresh_mirrors_label_and_restores_enabled_state(self):
        original=QPushButton('Refresh');header=QPushButton('Refresh')
        self.addCleanup(original.deleteLater);self.addCleanup(header.deleteLater)
        window=SimpleNamespace(refresh_button=original,manga_header=SimpleNamespace(refresh=header),
            _show_scan_progress=Mock(),_apply_refresh_snapshot=Mock(),_refresh_failed=Mock(),_finish_refresh=Mock())
        with patch('app.ui.refresh.RefreshWorker') as worker:
            MainWindow._start_refresh(window,new_only=True)
            self.assertEqual(header.text(),'Checking…');self.assertFalse(header.isEnabled())
            worker.return_value.start.assert_called_once()
        MainWindow._finish_refresh(window)
        self.assertEqual(header.text(),'Refresh');self.assertTrue(header.isEnabled())
