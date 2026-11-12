import unittest
from unittest.mock import Mock, patch
from app.ui.main_window import MainWindow


class NavigationTests(unittest.TestCase):
    def test_tab_switch_does_not_refresh_or_read_disk_metrics(self):
        window = Mock()
        with patch('app.ui.navigation.switch_tab') as switch:
            MainWindow._on_nav_clicked(window, 3)
            switch.assert_called_once_with(window, 3)
        window._update_nav_selection.assert_called_once_with(3)
        window.stacked_widget.setCurrentIndex.assert_not_called()
        window.stacked_widget.currentWidget.assert_not_called()
        window._refresh_metrics.assert_not_called()
