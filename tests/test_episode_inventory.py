import json
import unittest
from pathlib import Path
from unittest.mock import patch
import test_ui_regressions as regression_support
from app import db
from app.core.parser import extract_episode_numbers, analyze_season_health
from app.core.scanner import collect_video_groups, _update_on_disk_info
from app.core.library_health import movie_inventory, episode_inventory, season_health


class EpisodeInventoryTests(unittest.TestCase):
    setUp = regression_support.Regressions.setUp
    tearDown = regression_support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        regression_support.Regressions.setUpClass.__func__(cls)

    def video(self, relative):
        path = Path(self.temp.name) / "anime" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"video")
        return path

    def test_continuous_episode_gaps_across_folders(self):
        from app.core.library_health import episode_inventory
        first = {"id": 1, "relation_type": "SEASON", "storage_state": "ON_DISK",
                 "season_folder_path": "first", "video_files_json": '["Episode 01.mkv", "Episode 02.mkv"]'}
        second = {**first, "id": 2, "season_folder_path": "second",
                  "video_files_json": '["Episode 02.mkv", "Episode 04.mkv"]'}
        coverage = episode_inventory([first, second], continuous=True)
        self.assertEqual(coverage["unique_episode_count"], 3)
        self.assertEqual(coverage["missing_episodes"], [3])
        self.assertEqual(coverage["folder_ranges"], {1: (1, 2), 2: (2, 4)})

    def test_absolute_arc_range_does_not_start_at_one(self):
        result = analyze_season_health([f"One Piece - {ep:03}.mkv" for ep in range(63, 78)], folder_name="Season 02 EP 063-077")
        self.assertEqual(result["missing_episodes"], [])
        self.assertEqual(result["found_count"], 15)
        self.assertEqual(result["expected_total"], 15)

    def test_unknown_boundaries_only_report_internal_gaps(self):
        result = analyze_season_health(["One Piece - 1001.mkv", "EP.1003.v0.1234.1080p.mp4"])
        self.assertEqual(result["missing_episodes"], [1002])
        self.assertFalse(result["range_verified"])
        self.assertIsNone(result["expected_total"])

    def test_conflicting_folder_range_is_unverified(self):
        result = analyze_season_health([f"One Piece - {ep}.mkv" for ep in range(579, 629) if ep not in (580, 590)], folder_name="Season 16 EP579-587")
        self.assertEqual(result["missing_episodes"], [580, 590])
        self.assertFalse(result["range_verified"])
        self.assertIn("conflicts", result["range_note"])

    def test_multi_episode_files_and_versions(self):
        self.assertEqual(extract_episode_numbers("Show S02E01-E02.mkv"), [1, 2])
        self.assertEqual(extract_episode_numbers("[Group] Show - 063v2 [1080p][ABC123].mkv"), [63])
        self.assertEqual(extract_episode_numbers("EP.1117.v0.1725156908.1080p.mp4"), [1117])
        for name in ("Show - Movie 09.mkv", "Show - 1023SP.mkv", "Show SP6.mkv", "[1080p][12345678].mkv"):
            self.assertEqual(extract_episode_numbers(name), [], name)

    def test_nested_paths_and_same_basename_survive_repeated_scan(self):
        a = self.video("Season 20 A/Nested/Show - 1001.mkv")
        b = self.video("Season 20 B/Show - 1001.mkv")
        root = a.parents[2]
        _update_on_disk_info(self.fid, str(root))
        _update_on_disk_info(self.fid, str(root))
        seasons = [s for s in db.get_seasons_for_franchise(self.fid) if s["storage_state"] == "ON_DISK"]
        self.assertEqual(len(seasons), 1)
        saved = json.loads(seasons[0]["video_files_json"])
        self.assertEqual(len(saved), 2)
        self.assertEqual(seasons[0]["size_bytes"], 10)
        self.assertTrue(all((Path(seasons[0]["season_folder_path"]) / name).is_file() for name in saved))
        b.unlink()
        _update_on_disk_info(self.fid, str(root))
        self.assertEqual(sum(len(json.loads(s["video_files_json"])) for s in db.get_seasons_for_franchise(self.fid)), 1)

    def test_movies_specials_and_reedits_are_not_main_episodes(self):
        self.video("Season 02 EP063-077/Show - 063.mkv")
        self.video("Movies/Show Movie 01.mkv")
        self.video("Show Film Red.mkv")
        self.video("Show SP6.mkv")
        self.video("Alternate edition/Alternate edition - 01.mkv")
        self.video("Alternate edition - 02.mkv")
        groups = collect_video_groups(str(Path(self.temp.name) / "anime"))
        counts = {g["key"]: len(g["files"]) for g in groups}
        self.assertEqual(counts["movies"], 2)
        self.assertEqual(counts["specials"], 1)
        self.assertEqual(counts["collection:alternateedition"], 2)

    def test_unreleased_movies_never_count_as_missing(self):
        media = {"relations": {"edges": [{"node": {"id": i, "format": "MOVIE", "title": {"english": f"Movie {i}"}, "status": status}} for i, status in enumerate(["FINISHED", "NOT_YET_RELEASED", None], 1)]}}
        report = movie_inventory([], media)
        self.assertEqual(report["released_count"], 1)
        self.assertEqual(len(report["not_matched"]), 1)
        self.assertEqual(len(report["upcoming"]), 1)
        self.assertEqual(len(report["unknown_release"]), 1)

    def test_season_relative_numbers_do_not_fill_another_seasons_gaps(self):
        seasons = [{"id": 1, "relation_type": "SEASON", "storage_state": "ON_DISK", "episodes_total": 3, "video_files_json": json.dumps(["S01E01.mkv", "S01E03.mkv"])}, {"id": 2, "relation_type": "SEASON", "storage_state": "ON_DISK", "episodes_total": 3, "video_files_json": json.dumps(["S02E01.mkv", "S02E02.mkv", "S02E03.mkv"])}]
        result = episode_inventory(seasons)
        self.assertEqual(result["unique_episode_count"], 5)
        self.assertEqual(result["seasons"][1]["missing_episodes"], [2])

    def test_absolute_root_episode_can_fill_an_arc_gap(self):
        seasons = [{"id": 1, "relation_type": "SEASON", "storage_state": "ON_DISK", "episode_start": 63, "episode_end": 65, "video_files_json": json.dumps(["Show - 063.mkv", "Show - 065.mkv"])}, {"id": 2, "relation_type": "SEASON", "storage_state": "ON_DISK", "video_files_json": json.dumps(["Show - 064.mkv"])}]
        result = episode_inventory(seasons)
        self.assertEqual(result["unique_episode_count"], 3)
        self.assertEqual(result["seasons"][1]["missing_episodes"], [])

    def test_delete_only_selected_indexed_files_in_shared_root(self):
        from app.ui.dialogs.delete_confirm import DeleteConfirmDialog
        selected = self.video("Season 1/Show - 001.mkv")
        other = self.video("Season 2/Show - 002.mkv")
        root = selected.parents[1]
        sid = db.upsert_season({"franchise_id": self.fid, "season_folder_path": str(root), "video_files_json": json.dumps([selected.relative_to(root).as_posix()]), "storage_state": "ON_DISK"})
        dialog = DeleteConfirmDialog(db.get_franchise(self.fid), [db.get_season(sid)])
        dialog._execute_delete()
        self.assertFalse(selected.exists())
        self.assertTrue(other.exists())
        self.assertTrue(root.exists())
        dialog.deleteLater()

    def test_streaming_nested_file_paths_and_rejecting_traversal(self):
        import asyncio
        from fastapi import HTTPException
        from app.api.server import serve_video
        file = self.video("Season 20/Nested/Show - 1001.mkv")
        root = Path(self.temp.name) / "anime"
        relative = file.relative_to(root).as_posix()
        sid = db.upsert_season({"franchise_id": self.fid, "season_folder_path": str(root), "video_files_json": json.dumps([relative])})
        response = asyncio.run(serve_video(sid, relative))
        self.assertEqual(Path(response.path).resolve(), file.resolve())
        with self.assertRaises(HTTPException):
            asyncio.run(serve_video(sid, "../outside.mkv"))


if __name__ == "__main__":
    unittest.main()
