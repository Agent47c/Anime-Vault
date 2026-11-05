import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from app.api import server
from app.ui.main_window import MainWindow


class StartupExitTests(unittest.TestCase):
    def test_api_configuration_works_without_console_streams(self):
        with patch('sys.stdout', None), patch('sys.stderr', None), patch('app.api.server.threading.Thread.start'):
            server.start_server()
            server.stop_server()

    def test_scan_is_visible_but_does_not_block_exit_as_a_file_move(self):
        worker = Mock()
        worker.isRunning.return_value = True
        page = SimpleNamespace(_worker=worker)
        window = SimpleNamespace(organizer_page=page, _navigation_pages=[])
        self.assertIs(MainWindow._active_task_page(window), page)
        self.assertIsNone(MainWindow._active_task_page(window, protect_only=True))

    def test_actual_file_moves_still_protected(self):
        worker = Mock()
        worker.isRunning.return_value = True
        page = SimpleNamespace(_batch_worker=worker)
        window = SimpleNamespace(organizer_page=page, _navigation_pages=[])
        self.assertIs(MainWindow._active_task_page(window, protect_only=True), page)
