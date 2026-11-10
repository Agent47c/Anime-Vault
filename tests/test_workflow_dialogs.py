"""Workflow presentation adapters and approved import/recycle behavior."""
import json
from pathlib import Path
from unittest.mock import patch
import unittest
import test_ui_regressions as support
from app import db
from app.core.recycle import recycle_selected
from PyQt5.QtWidgets import QAbstractButton


class WorkflowTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def wait_write(self,dialog):
        from PyQt5.QtTest import QTest
        import time
        end=time.monotonic()+5
        while getattr(dialog,'_apply_worker',None) is not None and time.monotonic()<end:
            QTest.qWait(5)
        self.assertIsNone(getattr(dialog,'_apply_worker',None),'IO worker did not finish')

    def season(self):
        folder = Path(self.temp.name) / "selected"
        folder.mkdir()
        video = folder / "Show - 01.mkv"
        video.write_bytes(b"temporary test video")
        other = folder / "Show - 02.mkv"
        other.write_bytes(b"unselected test video")
        sid = db.upsert_season({"franchise_id": self.fid, "season_folder_path": str(folder), "video_files_json": json.dumps([video.name]), "storage_state": "ON_DISK", "size_bytes": video.stat().st_size})
        return db.get_season(sid), video, other

    def test_recycle_failure_keeps_file_and_inventory(self):
        season, video, other = self.season()
        with patch("app.core.recycle.send2trash", side_effect=OSError("permission denied")):
            result = recycle_selected(self.fid, [season])
        self.assertTrue(result["failures"])
        self.assertEqual(result["recycled"], [])
        self.assertTrue(video.exists())
        self.assertTrue(other.exists())
        self.assertIn(video.name, json.loads(db.get_season(season["id"])["video_files_json"]))

    def test_changed_preview_file_is_never_recycled(self):
        season, video, other = self.season()
        stat = video.stat()
        signatures = {str(video.resolve()): (stat.st_size, stat.st_mtime_ns)}
        video.write_bytes(b"replaced content")
        with patch("app.core.recycle.send2trash") as recycle:
            result = recycle_selected(self.fid, [season], signatures=signatures)
        recycle.assert_not_called()
        self.assertTrue(result["failures"])
        self.assertTrue(video.exists())

    def test_recycle_unchecked_keeps_existing_watch_status(self):
        season, video, other = self.season()
        db.update_franchise_field(self.fid, "watch_status", "WATCHING")
        with patch("app.core.recycle.send2trash", side_effect=lambda path: Path(path).unlink()) as recycle:
            result = recycle_selected(self.fid, [season], mark_watched=False)
        recycle.assert_called_once_with(str(video.resolve()))
        self.assertEqual(db.get_franchise(self.fid)["watch_status"], "WATCHING")
        self.assertEqual(db.get_season(season["id"])["storage_state"], "WATCHED_REMOVED")
        self.assertTrue(other.exists())

    def test_import_applies_selected_status_and_unchecked_items_are_ignored(self):
        from app.ui.dialogs.watched_import_dialog import WatchedImportDialog
        dialog = WatchedImportDialog()
        dialog.import_status_combo.setCurrentIndex(dialog.import_status_combo.findData("PLAN_TO_WATCH"))
        for title, enabled in (("New title", True), ("Not selected", False)):
            dialog.parsed_items.append({"raw_title": title, "matched_title": title, "notes": "note", "raw_line": title, "existing_id": None, "anilist_media": None, "enabled": enabled})
        with patch("app.ui.dialogs.watched_import_dialog.QMessageBox.information"):
            dialog._apply_all_matches()
            self.wait_write(dialog)
        self.assertEqual(db.find_franchise_by_title("New title")["watch_status"], "PLAN_TO_WATCH")
        self.assertIsNone(db.find_franchise_by_title("Not selected"))
        dialog.deleteLater()

    def test_custom_entry_retains_extra_fields_and_status(self):
        from app.ui.dialogs.custom_entry import CustomEntryDialog
        dialog = CustomEntryDialog()
        dialog.display_title_input.setText("Custom title")
        dialog.title_en_input.setText("English title")
        dialog.watch_status_combo.setCurrentIndex(dialog.watch_status_combo.findData("DROPPED"))
        dialog.notes_input.setPlainText("Personal notes\nSecond line")
        dialog._save()
        self.wait_write(dialog)
        record = db.find_franchise_by_title("Custom title")
        self.assertEqual(record["watch_status"], "DROPPED")
        self.assertEqual(record["title_en"], "English title")
        self.assertEqual(record["user_notes"], "Personal notes\nSecond line")
        dialog.deleteLater()

    def test_edit_drawer_populates_and_saves_all_existing_fields(self):
        from app.ui.dialogs.custom_entry import CustomEntryDialog
        db.update_franchise_field(self.fid, "title_en", "English")
        db.update_franchise_field(self.fid, "title_romaji", "Romaji")
        db.update_franchise_field(self.fid, "title_native", "Native")
        db.update_franchise_field(self.fid, "user_rating", 8)
        db.update_franchise_field(self.fid, "user_notes", "Old notes")
        dialog = CustomEntryDialog(db.get_franchise(self.fid))
        self.assertEqual(dialog.rating_combo.currentData(), 8)
        self.assertEqual(dialog.title_romaji_input.text(), "Romaji")
        dialog.rating_combo.setCurrentIndex(dialog.rating_combo.findData(0))
        dialog.notes_input.setPlainText("Updated notes")
        dialog._save()
        self.wait_write(dialog)
        record = db.get_franchise(self.fid)
        self.assertIsNone(record["user_rating"])
        self.assertEqual(record["title_en"], "English")
        self.assertEqual(record["title_native"], "Native")
        self.assertEqual(record["user_notes"], "Updated notes")
        dialog.deleteLater()

    def test_rematch_preserves_multiple_releases_and_picker_does_not_save(self):
        from app.ui.dialogs.rematch_dialog import RematchDialog
        db.set_continuous_episodes(self.fid, False)
        with patch.object(RematchDialog, "_start_search"):
            dialog = RematchDialog(self.fid)
        for mid in (200, 201):
            result = dialog._create_result_card({"id": mid, "title": {"english": str(mid)}}, str(mid))
            next(b for b in result.findChildren(QAbstractButton) if b.accessibleName().startswith("Select ")).click()
        self.assertEqual(set(dialog.selections), {200, 201})
        dialog.deleteLater()
        picker = RematchDialog(None, selection_only=True)
        media = {"id": 999, "title": {"english": "Choice"}}
        picker.selections[999] = (media, None)
        chosen = []
        picker.match_chosen.connect(chosen.append)
        picker._apply_match()
        self.assertEqual(chosen, [media])
        self.assertIsNone(db.get_franchise_by_anilist_id(999))
        picker.deleteLater()


if __name__ == "__main__":
    unittest.main()
