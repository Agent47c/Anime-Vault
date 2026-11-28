"""Tests ensuring Exit Completely cleanly shuts down and never lingers in background."""
import unittest
from unittest.mock import Mock, patch
from PyQt5.QtWidgets import QApplication
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

        window.tray_icon = Mock()
        with patch("os._exit") as mock_os_exit, \
             patch.object(window, "_cleanup_and_exit", return_value=False) as cleanup:

            window._force_exit()

            cleanup.assert_called_once()
            mock_os_exit.assert_not_called()
            self.assertTrue(window.tray_icon.hide.called)
            self.assertFalse(window.isVisible())

        window.deleteLater()

    def test_tray_exit_waits_for_native_helper_without_reentering_shutdown(self):
        with patch.object(MainWindow, "_check_new_anime"), \
             patch("app.ui.pages.organizer_page.OrganizerPage._start_scan"):
            window = MainWindow()

        window.tray_icon = Mock()
        window._shutdown_ticks = 25  # Beyond the deadline for other workers.
        window._shutdown_pending = True
        window._torrent_shutdown_worker = Mock()

        with patch("os._exit") as mock_os_exit, \
             patch("app.api.server.stop_server") as stop_server, \
             patch("app.core.downloads.shutdown_builtin") as shutdown, \
             patch.object(QApplication, "closeAllWindows"), \
             patch.object(QApplication, "quit"), \
             patch.object(window, '_running_threads', return_value=[window._torrent_shutdown_worker]) as running:

            window._force_exit()
            window._finish_pending_exit()
            mock_os_exit.assert_not_called()
            stop_server.assert_not_called()
            running.return_value = []
            window._finish_pending_exit()
            shutdown.assert_not_called()  # The GUI never takes the downloader's lock.
            stop_server.assert_called_once_with()
            mock_os_exit.assert_called_with(0)

        window.deleteLater()


if __name__ == "__main__":
    unittest.main()

