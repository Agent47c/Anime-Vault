"""Release previews and exit choices survive the new presentation."""
import unittest
from datetime import date
from unittest.mock import patch
from PyQt5.QtWidgets import QLabel
import test_ui_regressions as support
from app import db
from app.ui.components.airing_count import AiringDay
from app.ui.main_window import QuitConfirmDialog


class DayAndQuitTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def test_day_shows_release_details_and_keeps_clickable_preview(self):
        entries = [{"fid": self.fid, "title": "First series", "episode": 5, "time": "23:00"}, {"fid": self.fid, "title": "Second release", "episode": 6, "time": "23:30"}]
        day = AiringDay(date(2026, 11, 5), True, "Thursday", entries)
        day.resize(180, 130)
        day.show()
        self.app.processEvents()
        labels = [label.text() for label in day.findChildren(QLabel)]
        self.assertIn("+1 more", labels)
        self.assertTrue(any("EP 5" in label for label in labels))
        day.release_button._show_preview()
        self.assertIsNotNone(day.release_button.preview)
        selected = []
        day.selected.connect(selected.append)
        day.release_button._choose(entries[0])
        self.assertEqual(selected, [entries[0]])
        day.hide()
        day.deleteLater()

    def test_day_hover_lift_respects_reduced_motion(self):
        day = AiringDay(date(2026, 11, 5), False, "Day", [])
        day.resize(180, 130)
        day.show()
        self.app.processEvents()
        with patch("app.preferences.motion_duration", return_value=0):
            day._lift(True)
            self.assertEqual(day.surface.pos().y(), 0)
            day._lift(False)
            self.assertEqual(day.surface.pos().y(), 4)
        day.hide()
        day.deleteLater()

    def test_quit_radio_choice_and_remember_use_existing_preference(self):
        with patch("app.ui.main_window.server.api_base_url", return_value=None):
            dialog = QuitConfirmDialog()
        dialog.exit_radio.setChecked(True)
        self.assertEqual(dialog.confirm_button.text(), "Exit completely")
        dialog.remember_cb.setChecked(True)
        dialog.confirm_button.click()
        self.assertEqual(dialog.choice, "exit")
        self.assertEqual(db.get_state("quit_preference"), "exit")
        dialog.deleteLater()

    def test_cancel_quit_does_not_save_a_preference(self):
        dialog = QuitConfirmDialog()
        dialog.remember_cb.setChecked(True)
        dialog.cancel_button.click()
        self.assertIsNone(dialog.choice)
        self.assertIsNone(db.get_state("quit_preference"))
        dialog.deleteLater()
