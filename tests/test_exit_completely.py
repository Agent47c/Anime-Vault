"""Tests ensuring Exit Completely cleanly shuts down and never lingers in background."""
import unittest
from unittest.mock import Mock, patch
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import test_ui_regressions as support
from app.ui.main_window import MainWindow


class ExitCompletelyTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def test_force_exit_triggers_clean_shutdown(self):
        with patch.object(MainWindow, "_check_new_anime"), \
             patch("app.ui.pages.organizer_page.OrganizerPage._start_scan"):
            window = MainWindow()

        # Mock tray_icon and server
        window.tray_icon = Mock()
        with patch("app.api.server.stop_server") as mock_stop_server, \
             patch("os._exit") as mock_os_exit, \
             patch.object(QTimer, "singleShot") as watchdog, \
             patch.object(window, "_cleanup_and_exit", return_value=False) as cleanup, \
             patch.object(QApplication, "quit") as mock_quit:

            window._force_exit()

            cleanup.assert_called_once()
            self.assertEqual(watchdog.call_args.args[0],2500)
            self.assertTrue(window.tray_icon.hide.called)
            self.assertFalse(window.isVisible())

        window.deleteLater()

    def test_finish_pending_exit_watchdog_enforces_os_exit(self):
        with patch.object(MainWindow, "_check_new_anime"), \
             patch("app.ui.pages.organizer_page.OrganizerPage._start_scan"):
            window = MainWindow()

        window.tray_icon = Mock()
        window._shutdown_ticks = 25  # Exceeded watchdog ticks

        with patch("os._exit") as mock_os_exit, \
             patch("app.api.server.stop_server"), \
             patch("app.core.downloads.shutdown_builtin"), \
             patch.object(QApplication, "closeAllWindows"), \
             patch.object(QApplication, "quit"):

            window._finish_pending_exit()
            mock_os_exit.assert_called_with(0)

        window.deleteLater()


if __name__ == "__main__":
    unittest.main()

