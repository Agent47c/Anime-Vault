"""Saved settings affect their existing workflows without modifying media."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from app import db, preferences as prefs
from app.core import anilist_client
from app.ui.theme import apply_theme
from app.ui.pages.settings_page import SettingsPage


class PreferencesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patches = [patch.object(db, "DATA_DIR", root), patch.object(db, "DB_PATH", root / "library.db"), patch.object(db, "COVERS_DIR", root / "covers"), patch.object(db, "EXPORTS_DIR", root / "exports")]
        for item in self.patches:
            item.start()
        db.init_db()

    def tearDown(self):
        self.app.processEvents()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_preferences_persist_and_theme_follows_windows(self):
        prefs.save("reduce_motion", True)
        self.assertEqual(prefs.motion_duration(220), 0)
        db.set_state("text_scale", "1.3")
        with patch.object(prefs, "windows_light_theme", return_value=True):
            apply_theme(self.app, "system")
        self.assertEqual(self.app.property("animevaultTheme"), "light")
        self.assertEqual(self.app.property("animevaultScale"), 1.3)
        prefs.save("decorations", False)
        apply_theme(self.app, "dark")
        self.assertFalse(self.app.property("animevaultDecorations"))

    def test_settings_switch_keyboard_and_existing_controls(self):
        apply_theme(self.app, "dark")
        page = SettingsPage()
        page.show()
        switches = [w for w in page.findChildren(__import__("app.ui.components.settings_switch", fromlist=["SettingsSwitch"]).SettingsSwitch) if w.accessibleName() == "Reduce motion"]
        self.assertEqual(len(switches), 1)
        QTest.keyClick(switches[0], Qt.Key_Space)
        self.assertTrue(prefs.enabled("reduce_motion"))
        self.assertEqual(page.player_combo.count(), 6)
        self.assertGreaterEqual(page.player_combo.findData('potplayer'),0)
        self.assertEqual(page.schedule_combo.count(), 4)
        self.assertNotIn("streaming", " ".join(label.text().lower() for label in page.findChildren(__import__("PyQt5.QtWidgets", fromlist=["QLabel"]).QLabel)))
        page.hide()
        page.deleteLater()

    def test_search_mature_filter_and_title_preference(self):
        response = {"Page": {"media": [{"id": 1, "isAdult": True}, {"id": 2, "isAdult": False}]}}
        prefs.save("allow_mature", False)
        with patch.object(anilist_client, "_graphql_request", return_value=response):
            self.assertEqual([row["id"] for row in anilist_client.search_anime("title")], [2])
        prefs.save("prefer_english", False)
        self.assertEqual(anilist_client.resolve_display_title({"title": {"english": "English", "romaji": "Romaji"}}), "Romaji")

    def test_import_duplicate_policy_skips_existing_and_repeated_lines(self):
        from app.ui.dialogs.watched_import_dialog import ParseAndMatchWorker
        root = Path(self.temp.name)
        file = root / "watched.txt"
        file.write_text("Example Show\nExample Show\n", encoding="utf-8")
        db.upsert_franchise({"display_title": "Example Show"})
        worker = ParseAndMatchWorker(str(file))
        output = []
        worker.finished.connect(output.append)
        with patch("app.ui.dialogs.watched_import_dialog.is_offline", return_value=True):
            worker.run()
        self.assertEqual([item['status'] for item in output[0]],['MERGED','DUPLICATE'])
        self.assertTrue(all(not item['enabled'] for item in output[0]))
        prefs.save("import_ignore_duplicates", False)
        output.clear()
        worker.run()
        self.assertEqual(len(output[0]), 2)
        self.assertTrue(all(item["status"] == "MERGED" for item in output[0]))

    def test_flat_detection_off_does_not_plan_unnumbered_season_moves(self):
        from app.core.organizer import inspect_anime_folder, DEFAULT_RULES
        root = Path(self.temp.name) / "Example"
        root.mkdir()
        (root / "Example - 01.mkv").write_bytes(b"video")
        result = inspect_anime_folder(str(root), rules={**DEFAULT_RULES, "treat_direct_as_season_1": False})
        self.assertFalse(result["moves"])
        self.assertTrue((root / "Example - 01.mkv").exists())

    def test_manual_schedule_starts_no_automatic_scan(self):
        from app.ui.main_window import MainWindow
        from app.ui.pages.organizer_page import OrganizerPage
        db.set_state("scan_schedule", "manual")
        with patch.object(MainWindow, "_check_new_anime") as scan, patch.object(MainWindow, "_setup_tray"), patch.object(MainWindow, "_restore_geometry"), patch.object(OrganizerPage, "_start_scan"), patch("app.ui.artwork.cached_online", return_value=False):
            window = MainWindow()
            self.app.processEvents()
            scan.assert_not_called()
            self.assertFalse(window._scan_schedule_timer.isActive())
            db.set_state("scan_schedule", "hourly")
            window._apply_settings_preferences()
            self.assertEqual(window._scan_schedule_timer.interval(), 3600000)
            self.assertTrue(window._scan_schedule_timer.isActive())
            window.hide()
            window._scan_schedule_timer.stop()
            window._task_timer.stop()
            window.deleteLater()


if __name__ == "__main__":
    unittest.main()
