"""Comprehensive tests for adult content security, 3-question recovery, library filtering, and Sukebei sources."""
import unittest
from unittest.mock import patch, Mock
from PyQt5.QtWidgets import QApplication

import test_ui_regressions as support
from app import db
from app.core import adult_content as sec
from app.core import download_discovery as discovery
from app.core import source_bridge


class AdultContentSecurityTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def test_password_hashing_and_verification(self):
        self.assertFalse(sec.is_password_configured())
        sec.set_password("Secret123")
        self.assertTrue(sec.is_password_configured())
        self.assertTrue(sec.verify_password("Secret123"))
        self.assertFalse(sec.verify_password("WrongPassword"))
        self.assertFalse(sec.verify_password(""))

        # Test change password
        sec.change_password("Secret123", "NewSecret456")
        self.assertFalse(sec.verify_password("Secret123"))
        self.assertTrue(sec.verify_password("NewSecret456"))

        with self.assertRaises(ValueError):
            sec.change_password("WrongCurrent", "AnotherSecret")

    def test_three_security_questions_setup_and_recovery(self):
        qa = [
            {"question": "Favorite anime?", "answer": "Steins;Gate"},
            {"question": "First pet?", "answer": "Kuro"},
            {"question": "Birth city?", "answer": "Tokyo"},
        ]
        sec.set_password("MyPass99", qa)
        questions = sec.get_security_questions()
        self.assertEqual(len(questions), 3)
        self.assertEqual(questions[0], "Favorite anime?")

        # Check answers normalization and verification
        self.assertTrue(sec.verify_security_answers(["steins;gate", "KURO ", "  tokyo  "]))
        self.assertFalse(sec.verify_security_answers(["steins;gate", "WrongPet", "tokyo"]))

        # Reset password with correct answers
        sec.reset_password_with_answers(["Steins;Gate", "kuro", "tokyo"], "RecoveredPass123")
        self.assertTrue(sec.verify_password("RecoveredPass123"))

        # Rejection with wrong answers
        with self.assertRaises(ValueError):
            sec.reset_password_with_answers(["Wrong", "Wrong", "Wrong"], "FailPass")

    def test_unlock_lock_and_auto_lock_on_restart(self):
        sec.set_password("TestPass")
        sec.lock()
        self.assertFalse(sec.is_adult_unlocked())

        self.assertTrue(sec.unlock("TestPass"))
        self.assertTrue(sec.is_adult_unlocked())

        # Auto-lock on restart
        sec.set_auto_lock_on_restart(True)
        self.assertTrue(sec.get_auto_lock_on_restart())
        sec.initialize_session()
        self.assertFalse(sec.is_adult_unlocked())

        # If auto-lock on restart is disabled, remembers session state
        sec.set_auto_lock_on_restart(False)
        sec.unlock("TestPass")
        sec.initialize_session()
        self.assertTrue(sec.is_adult_unlocked())

    def test_library_and_db_filtering_excludes_adult_when_locked(self):
        sec.set_password("AdultGate")
        sec.lock()

        initial_locked = len(db.get_all_franchises())
        normal_id = db.upsert_franchise({
            "display_title": "Normal Anime",
            "is_adult": 0,
            "watch_status": "WATCHING",
            "storage_state": "ON_DISK",
            "total_size_bytes": 1000,
        })
        adult_id = db.upsert_franchise({
            "display_title": "Adult Anime 18+",
            "is_adult": 1,
            "watch_status": "WATCHING",
            "storage_state": "ON_DISK",
            "total_size_bytes": 2000,
        })

        # When locked: get_all_franchises and get_series_library must exclude adult_id
        locked_franchises = db.get_all_franchises()
        locked_ids = {f["id"] for f in locked_franchises}
        self.assertIn(normal_id, locked_ids)
        self.assertNotIn(adult_id, locked_ids)
        self.assertEqual(len(locked_franchises), initial_locked + 1)

        locked_groups = db.get_series_library()
        locked_group_fids = {mid for g in locked_groups for mid in g["series_member_ids"]}
        self.assertIn(normal_id, locked_group_fids)
        self.assertNotIn(adult_id, locked_group_fids)

        # Stats should count only visible (normal) titles
        stats = db.get_library_stats()
        self.assertEqual(stats["total_franchises"], initial_locked + 1)

        # When unlocked: adult_id is included
        sec.unlock("AdultGate")
        unlocked_franchises = db.get_all_franchises()
        unlocked_ids = {f["id"] for f in unlocked_franchises}
        self.assertIn(normal_id, unlocked_ids)
        self.assertIn(adult_id, unlocked_ids)
        self.assertEqual(len(unlocked_franchises), initial_locked + 2)

        unlocked_stats = db.get_library_stats()
        self.assertEqual(unlocked_stats["total_franchises"], initial_locked + 2)

    def test_sukebei_source_present_and_auto_selected_for_adult(self):
        sources = discovery.sources()
        sukebei = next((s for s in sources if "sukebei.nyaa.si" in s["url"]), None)
        self.assertIsNotNone(sukebei)
        self.assertEqual(sukebei["name"], "Sukebei (18+)")

    def test_source_bridge_multi_site_heartbeat_and_claims(self):
        sites = ["https://nyaa.si", "https://sukebei.nyaa.si"]
        source_bridge.heartbeat(sites, True)
        conn = source_bridge.connection()
        self.assertTrue(conn["connected"])
        self.assertTrue(conn["enabled"])
        self.assertEqual(conn["sites"], sites)

        # Enqueue with both nyaa and sukebei works
        id1 = source_bridge.enqueue("https://nyaa.si/?q=test1", "Nyaa")
        id2 = source_bridge.enqueue("https://sukebei.nyaa.si/?q=test2", "Sukebei")
        self.assertTrue(bool(id1 and id2))

        # Claiming matches any enabled site
        claimed1 = source_bridge.claim(sites)
        self.assertIsNotNone(claimed1)
        self.assertIn(claimed1["id"], (id1, id2))

        claimed2 = source_bridge.claim(sites)
        self.assertIsNotNone(claimed2)

    def test_adult_password_dialog_flows(self):
        from app.ui.dialogs.adult_password_dialog import AdultPasswordDialog

        # 1. Set initial
        dlg_initial = AdultPasswordDialog(mode=AdultPasswordDialog.MODE_SET_INITIAL)
        dlg_initial.new_pwd_input.setText("Initial123")
        dlg_initial.confirm_pwd_input.setText("Initial123")
        for i, (combo, edit) in enumerate(dlg_initial.qa_widgets):
            edit.setText(f"Answer{i}")
        dlg_initial._handle_save_initial()
        self.assertTrue(sec.is_password_configured())
        self.assertTrue(sec.is_adult_unlocked())

        # 2. Lock and unlock via dialog
        sec.lock()
        self.assertFalse(sec.is_adult_unlocked())

        dlg_unlock = AdultPasswordDialog(mode=AdultPasswordDialog.MODE_UNLOCK)
        dlg_unlock.pwd_input.setText("WrongPassword")
        dlg_unlock._handle_unlock()
        self.assertFalse(sec.is_adult_unlocked())
        self.assertFalse(dlg_unlock.error_label.isHidden())
        self.assertIn("Incorrect", dlg_unlock.error_label.text())

        dlg_unlock.pwd_input.setText("Initial123")
        dlg_unlock._handle_unlock()
        self.assertTrue(sec.is_adult_unlocked())
        dlg_unlock.close()

        # 3. Recover password via 3 security questions
        dlg_recover = AdultPasswordDialog(mode=AdultPasswordDialog.MODE_RECOVER)
        self.assertEqual(len(dlg_recover.answer_inputs), 3)
        for i, edit in enumerate(dlg_recover.answer_inputs):
            edit.setText(f"Answer{i}")
        dlg_recover.reset_new_pwd.setText("ResetPass456")
        dlg_recover.reset_confirm_pwd.setText("ResetPass456")
        dlg_recover._handle_recover()
        self.assertTrue(sec.verify_password("ResetPass456"))
        dlg_recover.close()


if __name__ == "__main__":
    unittest.main()
