"""Delayed title-bar styling must not recreate or access destroyed windows."""
import unittest
from unittest.mock import patch
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5 import sip
from app.ui.window_chrome import _native_handle, apply_title_bar


class WindowChromeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_missing_handle_is_skipped_without_creating_a_new_window(self):
        widget = QWidget()
        widget.show()
        self.app.processEvents()
        with patch.object(widget, "effectiveWinId", return_value=None), patch.object(widget, "winId") as create, patch.object(self.app, "platformName", return_value="windows"):
            self.assertIsNone(_native_handle(widget))
            apply_title_bar(widget, self.app)
            create.assert_not_called()
        widget.close()
        widget.deleteLater()

    def test_hidden_and_deleted_windows_are_skipped(self):
        widget = QWidget()
        with patch.object(widget, "effectiveWinId") as native:
            self.assertIsNone(_native_handle(widget))
            native.assert_not_called()
        sip.delete(widget)
        self.assertIsNone(_native_handle(widget))
        apply_title_bar(widget, self.app)


    def test_maximize_bounds_respect_taskbar_and_negative_monitor_coordinates(self):
        from app.ui.window_chrome import maximize_bounds
        self.assertEqual(maximize_bounds((0, 0, 1920, 1080), (0, 0, 1920, 1032)), (0, 0, 1920, 1032))
        self.assertEqual(maximize_bounds((-1920, 0, 0, 1080), (-1872, 0, 0, 1080)), (48, 0, 1872, 1080))

    def test_f11_fullscreen_restores_previous_window_mode(self):
        from PyQt5.QtWidgets import QMainWindow
        from app.ui.components.title_bar import AppTitleBar
        window = QMainWindow()
        bar = AppTitleBar(window)
        window.show()
        self.app.processEvents()
        self.assertEqual(bar.fullscreen_shortcut.key().toString(), "F11")
        self.assertIn("F11", bar.maximize_button.toolTip())
        bar.toggle_fullscreen()
        self.app.processEvents()
        self.assertTrue(window.isFullScreen())
        bar.toggle_fullscreen()
        self.app.processEvents()
        self.assertFalse(window.isFullScreen())
        self.assertFalse(window.isMaximized())
        bar.toggle_maximized()
        self.app.processEvents()
        self.assertTrue(window.isMaximized())
        bar.toggle_fullscreen()
        self.app.processEvents()
        self.assertTrue(window.isFullScreen())
        bar.toggle_fullscreen()
        self.app.processEvents()
        self.assertTrue(window.isMaximized())
        self.assertFalse(window.isFullScreen())
        window.close()
        window.deleteLater()
