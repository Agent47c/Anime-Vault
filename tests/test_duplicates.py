import json
import unittest
from pathlib import Path
import test_ui_regressions as support
from app import db
from app.core.duplicates import find_duplicates, delete_duplicate


class DuplicateTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def add_season(self, number, files):
        folder = Path(self.temp.name) / f"Season {number}"
        folder.mkdir(exist_ok=True)
        for name, content in files.items():
            (folder / name).write_bytes(content)
        sid = db.upsert_season({
            "franchise_id": self.fid, "season_number": number,
            "title_display": f"Season {number}", "season_folder_path": str(folder),
            "video_files_json": json.dumps(list(files)), "storage_state": "ON_DISK",
        })
        return folder, sid

    def test_same_episode_in_other_season_and_other_encode_are_not_duplicates(self):
        self.add_season(1, {"Show - 10.mkv": b"same", "Show - 10v2.mkv": b"diff"})
        self.add_season(2, {"Show - 10.mkv": b"same"})
        groups, errors = find_duplicates()
        self.assertEqual((groups, errors), ([], []))

    def test_verified_deletion_retains_copy_and_updates_inventory(self):
        folder, sid = self.add_season(1, {"Show - 10.mkv": b"same", "Show - 10 copy.mkv": b"same"})
        groups, errors = find_duplicates()
        self.assertEqual(errors, [])
        self.assertEqual(len(groups), 1)
        group = groups[0]
        delete_duplicate(group, group["files"][1])
        self.assertTrue(Path(group["files"][0]["path"]).is_file())
        self.assertFalse(Path(group["files"][1]["path"]).exists())
        self.assertEqual(len(json.loads(db.get_season(sid)["video_files_json"])), 1)

    def test_changed_keeper_prevents_deletion(self):
        folder, _ = self.add_season(1, {"Show - 10.mkv": b"same", "Show - 10 copy.mkv": b"same"})
        groups, _ = find_duplicates()
        group = groups[0]
        Path(group["files"][0]["path"]).write_bytes(b"changed")
        with self.assertRaises(ValueError):
            delete_duplicate(group, group["files"][1])
        self.assertTrue(Path(group["files"][1]["path"]).is_file())
