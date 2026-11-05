import unittest
from unittest.mock import Mock, patch
import test_ui_regressions as support
from PyQt5.QtWidgets import QWidget, QStackedWidget, QVBoxLayout, QDialog
from app.ui.navigation import navigate
from app.ui.main_window import MainWindow
from app.config import get_always_admin, set_always_admin


class WorkflowTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def test_workflow_embeds_and_returns_without_modal_loop(self):
        host = QWidget()
        host.stacked_widget = QStackedWidget(host)
        QVBoxLayout(host).addWidget(host.stacked_widget)
        original = QWidget()
        host.stacked_widget.addWidget(original)
        dialog = QDialog(host)
        callback = Mock()
        host.show()
        navigate(dialog, callback)
        self.assertFalse(dialog.isWindow())
        self.assertFalse(dialog.isModal())
        self.assertIs(host.stacked_widget.currentWidget().workflow, dialog)
        dialog.accept()
        callback.assert_called_once_with(QDialog.Accepted)
        self.assertIs(host.stacked_widget.currentWidget(), original)
        host.hide()
        host.deleteLater()

    def test_rematch_cards_keep_compact_height(self):
        from app.ui.dialogs.rematch_dialog import RematchDialog
        with patch.object(RematchDialog, '_start_search'):
            dialog = RematchDialog(self.fid)
        card = dialog._create_result_card({'id': 200, 'title': {'english': 'A release'}, 'coverImage': {}}, 'release')
        self.assertLessEqual(card.minimumHeight(), 150)
        self.assertGreaterEqual(card.sizeHint().height(), card.minimumSizeHint().height())
        dialog.deleteLater()

    def test_close_is_blocked_while_task_runs(self):
        window = Mock()
        window._active_task_page.return_value = object()
        event = Mock()
        MainWindow.closeEvent(window, event)
        event.ignore.assert_called_once()
        window._cleanup_and_exit.assert_not_called()

    def test_admin_preference_can_be_enabled_and_disabled(self):
        self.assertFalse(get_always_admin())
        set_always_admin(True)
        self.assertTrue(get_always_admin())
        set_always_admin(False)
        self.assertFalse(get_always_admin())
