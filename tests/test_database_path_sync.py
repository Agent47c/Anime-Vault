"""Tests verifying that database path is always synchronized to the local user database path upon loading and restoring."""
import os
import sqlite3
import tempfile
import unittest
import sys
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_ui_regressions as support
from app import db
from app.core import profile_backup


class DatabasePathSyncTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def test_init_db_syncs_database_path_to_local_db_path(self):
        # Verify that init_db records the active local database path in app_state
        db.init_db()
        self.assertEqual(db.get_state("database_path"), str(db.DB_PATH))
        self.assertEqual(db.get_state("database_local_path"), str(db.DB_PATH))
        self.assertEqual(db.get_state("data_directory"), str(db.DATA_DIR))
        self.assertEqual(db.get_database_path(), db.DB_PATH)
        self.assertEqual(db.get_stored_database_path(), str(db.DB_PATH))

    def test_restore_database_rewrites_foreign_database_path_to_local_user_path(self):
        # Create a foreign database file simulating an export/backup from another drive
        with tempfile.TemporaryDirectory() as foreign_dir:
            foreign_db_path = Path(foreign_dir) / "foreign_library.db"

            # Populate foreign DB with a schema, franchise, and foreign stored path
            with closing(sqlite3.connect(str(foreign_db_path))) as conn:
                conn.executescript(db._SCHEMA_SQL)
                conn.execute("INSERT INTO app_state(key, value) VALUES ('database_path', 'D:\\\\OldMachine\\\\AnimeVault\\\\library.db')")
                conn.execute("INSERT INTO app_state(key, value) VALUES ('data_directory', 'D:\\\\OldMachine\\\\AnimeVault')")
                conn.execute("INSERT INTO app_state(key, value) VALUES ('backup_directory', 'D:\\\\OldMachine\\\\AnimeVault\\\\backups')")
                conn.execute(
                    "INSERT INTO franchises(display_title, watch_status, user_notes) VALUES (?, ?, ?)",
                    ("Restored Anime Title", "WATCHING", "Restored note from foreign drive")
                )
                conn.commit()

            # Verify current local database has different title before restore
            fid = db.upsert_franchise({"display_title": "Local Old Anime", "user_notes": "Local note"})

            # Now restore from the foreign database path
            res = db.restore_database(str(foreign_db_path))
            self.assertTrue(res)

            # 1. The stored database path inside the database must be rewritten to the local user database path
            self.assertEqual(db.get_state("database_path"), str(db.DB_PATH))
            self.assertEqual(db.get_state("database_local_path"), str(db.DB_PATH))
            self.assertEqual(db.get_state("data_directory"), str(db.DATA_DIR))
            self.assertEqual(db.get_stored_database_path(), str(db.DB_PATH))

            # 2. Backup directory should be safely reset to local DATA_DIR / 'backups'
            self.assertEqual(db.get_state("backup_directory"), str(db.DATA_DIR / "backups"))

            # 3. Restored user data is preserved
            franchises = db.get_all_franchises()
            titles = [f["display_title"] for f in franchises]
            self.assertIn("Restored Anime Title", titles)
            restored = next(f for f in franchises if f["display_title"] == "Restored Anime Title")
            self.assertEqual(restored["user_notes"], "Restored note from foreign drive")

    def test_profile_backup_restore_rewrites_database_path(self):
        # Create a full profile backup archive
        archive_path = profile_backup.create_backup(include_caches=False)
        self.assertTrue(Path(archive_path).is_file())

        # Simulate restoring that archive
        safety = profile_backup.restore_backup(archive_path)
        self.assertTrue(Path(safety).is_file())

        # Check that the database path inside app_state matches local DB_PATH
        self.assertEqual(db.get_state("database_path"), str(db.DB_PATH))
        self.assertEqual(db.get_state("data_directory"), str(db.DATA_DIR))


if __name__ == "__main__":
    unittest.main()
