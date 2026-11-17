import json
import unittest
from unittest.mock import patch
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

    def test_batch_hashes_unchanged_keeper_once_but_each_copy_fully(self):
        from app.core import duplicates
        self.add_season(1,{f'Show - 10 copy{i}.mkv':b'same' for i in range(3)})
        group=find_duplicates()[0][0];cache={}
        with patch.object(duplicates,'digest',wraps=duplicates.digest) as hashed,patch.object(duplicates,'send2trash',side_effect=lambda name:Path(name).unlink()):
            for copy in group['files'][1:]:delete_duplicate(group,copy,verified_keepers=cache)
        self.assertEqual(hashed.call_count,3)
        self.assertEqual([str(c.args[0]) for c in hashed.call_args_list].count(group['files'][0]['path']),1)
        self.assertTrue(Path(group['files'][0]['path']).is_file())

    def test_cached_keeper_change_stops_later_deletion(self):
        from app.core import duplicates
        self.add_season(1,{f'Show - 10 copy{i}.mkv':b'same' for i in range(3)})
        group=find_duplicates()[0][0];cache={}
        with patch.object(duplicates,'send2trash',side_effect=lambda name:Path(name).unlink()):
            delete_duplicate(group,group['files'][1],verified_keepers=cache)
            Path(group['files'][0]['path']).write_bytes(b'changed')
            with self.assertRaises(ValueError):delete_duplicate(group,group['files'][2],verified_keepers=cache)
        self.assertTrue(Path(group['files'][2]['path']).is_file())

    def test_recycle_does_not_resolve_unrelated_episode_inventory(self):
        from app.core import file_operations,identity
        folder,sid=self.add_season(1,{'Show - 10.mkv':b'same','Show - 10 copy.mkv':b'same'})
        unrelated=Path(self.temp.name)/'Other';unrelated.mkdir()
        names=[f'Unrelated - {n}.mkv' for n in range(1000)]
        other=db.upsert_season(dict(franchise_id=self.fid,season_number=2,title_display='Other',
            season_folder_path=str(unrelated),video_files_json=json.dumps(names),size_bytes=1000,storage_state='ON_DISK'))
        with patch.object(identity,'path_key',wraps=identity.path_key) as resolved:
            file_operations.recycle_file(folder/'Show - 10 copy.mkv',recycle=lambda name:Path(name).unlink())
        self.assertFalse(any('Unrelated - ' in str(call.args[0]) for call in resolved.call_args_list))
        self.assertLessEqual(resolved.call_count,4)
        self.assertEqual(len(json.loads(db.get_season(sid)['video_files_json'])),1)
        self.assertEqual(json.loads(db.get_season(other)['video_files_json']),names)

    def test_keeper_changed_during_candidate_verification_is_not_recycled(self):
        from app.core import duplicates
        self.add_season(1,{f'Show - 10 copy{i}.mkv':b'same' for i in range(2)})
        group=find_duplicates()[0][0];original=duplicates.digest
        def checking(path,cancelled):
            value=original(path,cancelled)
            if str(path)==group['files'][1]['path']:Path(group['files'][0]['path']).write_bytes(b'changed')
            return value
        with patch.object(duplicates,'digest',side_effect=checking),patch.object(duplicates,'send2trash') as recycled:
            with self.assertRaises(ValueError):delete_duplicate(group,group['files'][1],verified_keepers={})
        recycled.assert_not_called()
        self.assertTrue(Path(group['files'][1]['path']).is_file())
