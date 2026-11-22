"""Tests verifying that file_locations.path_key UNIQUE constraint collisions never occur during moves, recycling, recovery, or download registration."""
import json
import os
import sqlite3
import sys
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_ui_regressions as support
from app import db
from app.core import identity, file_operations, download_queue


class FileLocationsUniqueTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def test_relocate_replaces_target_in_file_locations_without_unique_collision(self):
        sid = db.upsert_season(dict(franchise_id=self.fid, season_number=1, relation_type='SEASON', title_display='Season 1'))
        source = Path(self.temp.name) / "download" / "Episode 01.mkv"
        target = Path(self.temp.name) / "library" / "Episode 01.mkv"
        source.parent.mkdir(parents=True, exist_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"new video content")
        target.write_bytes(b"old video content")

        with closing(db.get_connection()) as conn, conn:
            # File 1 at source
            fid_1 = conn.execute("INSERT INTO physical_files(season_id, original_name, size_bytes, mtime_ns, device, inode, availability) VALUES (?, 'Episode 01.mkv', 100, 100, '1', '1', 'AVAILABLE')", (sid,)).lastrowid
            conn.execute("INSERT INTO file_locations VALUES (?, ?, ?)", (fid_1, str(source), identity.path_key(source)))

            # File 2 previously at target
            fid_2 = conn.execute("INSERT INTO physical_files(season_id, original_name, size_bytes, mtime_ns, device, inode, availability) VALUES (?, 'Episode 01.mkv', 200, 200, '1', '2', 'AVAILABLE')", (sid,)).lastrowid
            conn.execute("INSERT INTO file_locations VALUES (?, ?, ?)", (fid_2, str(target), identity.path_key(target)))

            # Now relocate source to target
            identity.relocate(conn, source, target)

            # Verification:
            # fid_1 should now have target location
            loc_1 = conn.execute("SELECT path, path_key FROM file_locations WHERE file_id = ?", (fid_1,)).fetchone()
            self.assertIsNotNone(loc_1)
            self.assertEqual(loc_1[1], identity.path_key(target))

            # fid_2 location must be removed and availability set to REPLACED
            loc_2 = conn.execute("SELECT path FROM file_locations WHERE file_id = ?", (fid_2,)).fetchone()
            self.assertIsNone(loc_2)
            avail_2 = conn.execute("SELECT availability FROM physical_files WHERE id = ?", (fid_2,)).fetchone()
            self.assertEqual(avail_2[0], "REPLACED")

    def test_recycle_file_removes_entry_from_file_locations(self):
        sid = db.upsert_season(dict(franchise_id=self.fid, season_number=1, relation_type='SEASON', title_display='Season 1'))
        file_path = Path(self.temp.name) / "to_recycle.mkv"
        file_path.write_bytes(b"content to recycle")
        sig = identity.signature(file_path)

        with closing(db.get_connection()) as conn, conn:
            fid = conn.execute("INSERT INTO physical_files(season_id, original_name, size_bytes, mtime_ns, device, inode, availability) VALUES (?, 'to_recycle.mkv', ?, ?, ?, ?, 'AVAILABLE')", (sid, *sig)).lastrowid
            conn.execute("INSERT INTO file_locations VALUES (?, ?, ?)", (fid, str(file_path), identity.path_key(file_path)))

        with patch("app.core.file_operations.send2trash") as mock_trash:
            # Simulate recycling
            def fake_trash(p):
                Path(p).unlink()
            mock_trash.side_effect = fake_trash
            file_operations.recycle_file(file_path, sig)

        with closing(db.get_connection()) as conn:
            loc = conn.execute("SELECT file_id FROM file_locations WHERE path_key = ?", (identity.path_key(file_path),)).fetchone()
            self.assertIsNone(loc, "Recycled file must not linger in file_locations")
            pf = conn.execute("SELECT availability FROM physical_files WHERE id = ?", (fid,)).fetchone()
            self.assertEqual(pf[0], "RECYCLED")

    def test_recover_operations_resolves_stuck_move_with_target_collision(self):
        sid = db.upsert_season(dict(franchise_id=self.fid, season_number=1, relation_type='SEASON', title_display='Season 1'))
        source = Path(self.temp.name) / "stuck_source.mkv"
        target = Path(self.temp.name) / "stuck_target.mkv"
        # Simulate that the physical file was already moved to target
        target.write_bytes(b"moved payload")
        expected = list(identity.signature(target))

        with closing(db.get_connection()) as conn, conn:
            # File 1 is the new download
            fid_1 = conn.execute("INSERT INTO physical_files(season_id, original_name, size_bytes, mtime_ns, device, inode, availability) VALUES (?, 'Episode.mkv', ?, ?, ?, ?, 'AVAILABLE')", (sid, *expected)).lastrowid
            conn.execute("INSERT INTO file_locations VALUES (?, ?, ?)", (fid_1, str(source), identity.path_key(source)))

            # File 2 is an old file that occupied the target
            fid_2 = conn.execute("INSERT INTO physical_files(season_id, original_name, size_bytes, mtime_ns, device, inode, availability) VALUES (?, 'Episode.mkv', 999, 999, '1', '999', 'AVAILABLE')", (sid,)).lastrowid
            conn.execute("INSERT INTO file_locations VALUES (?, ?, ?)", (fid_2, str(target), identity.path_key(target)))

            # File operation stuck in REVIEW with the error
            op_id = "test_stuck_op"
            conn.execute("INSERT INTO file_operations VALUES (?, 'MOVE', ?, ?, ?, 'REVIEW', 'UNIQUE constraint failed: file_locations.path_key', 100, 100)",
                         (op_id, str(source), str(target), json.dumps(expected)))

        res = file_operations.recover_operations()
        self.assertEqual(res["recovered"], 1)

        with closing(db.get_connection()) as conn:
            status = conn.execute("SELECT status, error FROM file_operations WHERE id = ?", (op_id,)).fetchone()
            self.assertEqual(status["status"], "COMPLETED")
            self.assertIsNone(status["error"])

            # File 1 should have target location
            loc_1 = conn.execute("SELECT path_key FROM file_locations WHERE file_id = ?", (fid_1,)).fetchone()
            self.assertIsNotNone(loc_1)
            self.assertEqual(loc_1[0], identity.path_key(target))

    def test_check_completed_files_reconciles_when_moved_to_intent_target(self):
        source = Path(self.temp.name) / "download" / "ep1.mkv"
        target = Path(self.temp.name) / "library" / "ep1.mkv"
        target.parent.mkdir(parents=True, exist_ok=True)
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"downloaded and moved data")
        size = source.stat().st_size
        file_operations.move_file(source,target)

        job = {
            "id": "job_reconcile",
            "indexed": True,
            "status": "Indexed",
            "verified_files": [{"path": str(source), "size": size}],
            "library_move_intent": [{"source": str(source), "target": str(target)}],
        }

        download_queue.check_completed_files(job)
        self.assertFalse(job.get("integrity_missing"))
        self.assertEqual(job["verified_files"][0]["path"], str(target))


if __name__ == "__main__":
    unittest.main()
