"""Per-anime update choices persist and restore independently."""
import unittest
import test_ui_regressions as support
from PyQt5.QtWidgets import QPushButton, QComboBox
from PyQt5.QtTest import QSignalSpy
from app import db
from app.ui.pages.updates_page import UpdatesPage, UpdateCard


class UpdateChoiceTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def test_later_and_not_interested_survive_refresh_and_restart(self):
        for choice in ("later", "not_interested", "muted"):
            db.publish_updates(self.fid, "Season 2 released")
            db.set_update_disposition(self.fid, choice)
            db.init_db()
            self.assertEqual(db.update_disposition(self.fid), choice)
            self.assertIsNone(db.publish_updates(self.fid, "Season 3 announced"))
            record = db.get_franchise(self.fid)
            self.assertFalse(record["has_new_update"])
            self.assertEqual(record["update_details"], "Season 3 announced")
            db.set_update_disposition(self.fid, "new")
            self.assertTrue(db.get_franchise(self.fid)["has_new_update"])

    def test_restore_does_not_affect_other_saved_anime_or_dismissals(self):
        other = db.upsert_franchise({"display_title": "Other anime"})
        db.publish_updates(self.fid, "Old change")
        db.dismiss_updates(self.fid)
        db.publish_updates(self.fid, "Old change | New change")
        db.set_update_disposition(self.fid, "later")
        db.set_update_disposition(other, "not_interested")
        db.set_update_disposition(self.fid, "new")
        self.assertEqual(db.get_franchise(self.fid)["update_details"], "New change")
        self.assertEqual(db.update_disposition(other), "not_interested")

    def test_restore_button_only_on_saved_cards_and_dropdown_is_removed(self):
        db.publish_updates(self.fid, "Season 2 released")
        page = UpdatesPage()
        self.assertFalse(page.findChildren(QComboBox))
        card = page.list_widget.findChild(UpdateCard)
        self.assertNotIn("Restore updates", [b.text() for b in card.findChildren(QPushButton)])
        finished = QSignalSpy(page.action_finished)
        next(b for b in card.findChildren(QPushButton) if b.text() == "Later").click()
        self.assertTrue(finished.wait(5000))
        self.assertEqual(db.update_disposition(self.fid), "later")
        self.assertEqual(page._updates, [])
        self.app.processEvents()
        page._select_filter("Later")
        saved = [page.list_layout.itemAt(i).widget() for i in range(page.list_layout.count()) if isinstance(page.list_layout.itemAt(i).widget(), UpdateCard)]
        self.assertEqual(len(saved), 1)
        restore = next(b for b in saved[0].findChildren(QPushButton) if b.text() == "Restore updates")
        finished = QSignalSpy(page.action_finished)
        restore.click()
        self.assertTrue(finished.wait(5000))
        self.assertEqual(db.update_disposition(self.fid), "new")
        self.assertTrue(db.get_franchise(self.fid)["has_new_update"])
        page.deleteLater()

    def test_legacy_muted_anime_remain_accessible(self):
        db.set_state(f"muted_updates:{self.fid}", "1")
        self.assertEqual(db.update_disposition(self.fid), "muted")
        page = UpdatesPage()
        page._select_filter("Muted")
        self.assertEqual(len(page._saved_updates), 1)
        db.set_update_disposition(self.fid, "new")
        self.assertFalse(db.updates_muted(self.fid))
        page.deleteLater()


    def test_watched_and_ignore_dismisses_current_updates_but_allows_new_changes(self):
        db.publish_updates(self.fid, "Season 2 released")
        page = UpdatesPage()
        card = page.list_layout.itemAt(0).widget()
        finished = QSignalSpy(page.action_finished)
        next(button for button in card.findChildren(QPushButton) if button.text() == "Watched and ignore").click()
        self.assertTrue(finished.wait(5000))
        self.assertEqual(db.get_franchise(self.fid)["watch_status"], "WATCHED")
        self.assertFalse(db.get_franchise(self.fid)["has_new_update"])
        db.init_db()
        self.assertIsNone(db.publish_updates(self.fid, "Season 2 released"))
        self.assertEqual(db.publish_updates(self.fid, "Season 2 released | Season 3 announced"), "Season 3 announced")
        self.assertFalse(db.updates_muted(self.fid))
        page.deleteLater()

    def test_watched_and_ignore_includes_grouped_seasons_and_keeps_notes_and_files(self):
        other = db.upsert_franchise({"display_title": "Other anime", "watch_status": "WATCHING"})
        arc = db.upsert_franchise({"display_title": "Training arc", "user_notes": "Keep note"})
        db.group_with_series(arc, self.fid)
        season = db.upsert_season({"franchise_id": arc, "title_display": "Season 2", "video_files_json": '["episode-01.mkv"]', "storage_state": "ON_DISK"})
        db.publish_updates(arc, "Current announcement")
        db.set_update_disposition(arc, "later")
        db.mark_watched_and_ignore_updates(self.fid)
        self.assertEqual(db.get_franchise(arc)["watch_status"], "WATCHED")
        self.assertEqual(db.get_franchise(arc)["user_notes"], "Keep note")
        self.assertEqual(db.get_season(season)["video_files_json"], '["episode-01.mkv"]')
        self.assertEqual(db.get_franchise(other)["watch_status"], "WATCHING")
        self.assertIsNone(db.publish_updates(arc, "Current announcement"))
        self.assertEqual(db.publish_updates(arc, "New season"), "New season")
