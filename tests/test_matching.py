import unittest
from unittest.mock import patch
import test_ui_regressions as support
from app import db
from app.core.matching import apply_release_match
from PyQt5.QtWidgets import QPushButton, QAbstractButton


class MatchingTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def test_select_button_keeps_media_record(self):
        from app.ui.dialogs.rematch_dialog import RematchDialog
        with patch.object(RematchDialog, '_start_search'):
            dialog = RematchDialog(self.fid)
        media = {'id': 200, 'title': {'english': 'Part 2'}, 'coverImage': {}}
        card = dialog._create_result_card(media, 'part2')
        next(b for b in card.findChildren(QAbstractButton) if b.accessibleName() == 'Select Part 2').click()
        self.assertEqual(dialog.selections[200][0], media)
        dialog.deleteLater()

    def test_specific_release_merges_under_canonical_series(self):
        db.set_continuous_episodes(self.fid, False)
        canonical = db.upsert_franchise({'anilist_id': 100, 'display_title': 'Series'})
        sid = db.upsert_season({'franchise_id': self.fid, 'season_number': 2, 'relation_type': 'SEASON', 'storage_state': 'ON_DISK', 'video_files_json': '["S02E01.mkv"]'})
        root = {'id': 100, 'title': {'english': 'Series'}}
        release = {'id': 200, 'title': {'english': 'Series Part 2'}, 'episodes': 12, 'status': 'FINISHED', 'relations': {'edges': [{'relationType': 'PREQUEL', 'node': {'id': 100, 'format': 'TV'}}]}}
        with patch('app.core.matching.client.get_anime_by_id', return_value=root), patch('app.core.matching.client.download_cover', return_value=None), patch('app.core.matching.client.download_banner', return_value=None):
            destination = apply_release_match(self.fid, release, sid)
        self.assertEqual(destination, canonical)
        self.assertEqual(db.get_season(sid)['anilist_id'], 200)
        self.assertEqual(db.get_season(sid)['season_number'], 2)
        self.assertEqual(db.get_season(sid)['franchise_id'], canonical)
        self.assertEqual(db.get_franchise(canonical)['display_title'], 'Series')


    def test_two_releases_save_under_one_series(self):
        db.set_continuous_episodes(self.fid, False)
        sid = db.upsert_season({'franchise_id': self.fid, 'season_number': 1, 'relation_type': 'SEASON', 'storage_state': 'ON_DISK'})
        root = {'id': 100, 'title': {'english': 'Series'}, 'status': 'FINISHED'}
        sequel = {'id': 200, 'title': {'english': 'Series Part 2'}, 'status': 'NOT_YET_RELEASED', 'relations': {'edges': [{'relationType': 'PREQUEL', 'node': {'id': 100, 'format': 'TV'}}]}}
        with patch('app.core.matching.client.get_anime_by_id', return_value=root), patch('app.core.matching.client.download_cover', return_value=None), patch('app.core.matching.client.download_banner', return_value=None):
            destination = apply_release_match(self.fid, root, sid, [(sequel, None)])
        seasons = db.get_seasons_for_franchise(destination)
        self.assertEqual([(s['anilist_id'], s['storage_state']) for s in seasons], [(100, 'ON_DISK'), (200, 'NOT_DOWNLOADED')])

    def test_tv_rematch_does_not_promote_standalone_web_prequel(self):
        from app.core.matching import series_root
        tv = {"id": 21, "format": "TV", "relations": {"edges": [
            {"relationType": "PREQUEL", "node": {"id": 167404, "format": "ONA"}}
        ]}}
        with patch("app.core.matching.client.get_anime_by_id") as fetch:
            self.assertEqual(series_root(tv), tv)
            fetch.assert_not_called()

    def test_mute_survives_new_updates_until_restored(self):
        db.mute_updates(self.fid)
        self.assertIsNone(db.publish_updates(self.fid, 'New season'))
        self.assertTrue(db.updates_muted(self.fid))
        db.mute_updates(self.fid, False)
        self.assertEqual(db.publish_updates(self.fid, 'New season'), 'New season')

    def test_consolidation_relinks_folder_and_keeps_release_identity(self):
        from pathlib import Path
        from app.core.consolidation import sync_moved_inventory
        workspace = Path(self.temp.name)
        original = workspace / "old" / "Series"
        original.mkdir(parents=True)
        destination = workspace / "library"
        target = destination / "Series" / "Season 01" / "Episode 01.mkv"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"video")
        db.update_franchise_field(self.fid, "root_folder_path", str(original))
        sid = db.upsert_season({
            "franchise_id": self.fid, "anilist_id": 200, "season_number": 1,
            "season_folder_path": str(original), "scan_root": str(original),
            "title_display": "Matched release", "video_files_json": '["old.mkv"]',
        })
        sync_moved_inventory([{
            "source": str(original / "old.mkv"), "target": str(target),
            "series": "Series", "release": "Season 01",
        }], destination)
        self.assertEqual(db.get_franchise(self.fid)["root_folder_path"], str(destination / "Series"))
        season = db.get_season(sid)
        self.assertEqual(season["anilist_id"], 200)
        self.assertEqual(season["season_folder_path"], str(target.parent))
        self.assertEqual(season["title_display"], "Matched release")

    def test_find_missing_files_searches_all_roots_but_names_alone_require_review(self):
        from pathlib import Path
        from app.core.organizer import find_missing_library_files
        base = Path(self.temp.name)
        old_root, new_root = base / "old", base / "new"
        old_root.mkdir()
        target = new_root / "Series" / "Season 1" / "Episode 01.mkv"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"video")
        db.add_watched_directory(str(old_root))
        db.add_watched_directory(str(new_root))
        db.update_franchise_field(self.fid, "display_title", "Series")
        db.update_franchise_field(self.fid, "root_folder_path", str(old_root / "Series"))
        sid = db.upsert_season({
            "franchise_id": self.fid, "season_folder_path": str(old_root / "Series"),
            "title_display": "Season 1", "video_files_json": '["Episode 01.mkv"]',
        })
        duplicate = new_root / "Series" / "Copy" / target.name
        duplicate.parent.mkdir()
        duplicate.write_bytes(b"duplicate")
        self.assertEqual(find_missing_library_files()["unresolved"], 1)
        duplicate.unlink()
        result = find_missing_library_files()
        self.assertEqual(result["recovered"], 0)
        self.assertEqual(len(result['candidates']), 1)
        self.assertEqual(result['candidates'][0]['evidence'], 'NAME_ONLY_UNVERIFIED')
        self.assertEqual(db.get_season(sid)["season_folder_path"], str(old_root / 'Series'))

    def test_locate_season_indexes_files_and_preserves_metadata(self):
        from pathlib import Path
        root = Path(self.temp.name) / "Series" / "Season 4"
        root.mkdir(parents=True)
        episode = root / "Episode 01.mkv"
        episode.write_bytes(b"video")
        sid = db.upsert_season({
            "franchise_id": self.fid, "anilist_id": 200, "season_number": 4,
            "title_display": "Matched season", "storage_state": "NOT_DOWNLOADED",
        })
        db.update_season_folder(sid, str(root))
        season = db.get_season(sid)
        self.assertEqual(season["anilist_id"], 200)
        self.assertEqual(season["season_number"], 4)
        self.assertEqual(season["video_files_json"], '["Episode 01.mkv"]')
        self.assertEqual(season["size_bytes"], len(b"video"))
        self.assertEqual(season["storage_state"], "ON_DISK")
        self.assertEqual(Path(season["season_folder_path"]), root.resolve())

    def test_scan_matches_exact_series_and_preserves_numbered_folders(self):
        from pathlib import Path
        from app.core.scanner import scan_watched_directories

        watched = Path(self.temp.name) / "library"
        root = watched / "Exact Anime"
        for number in (1, 2, 4):
            folder = root / f"Season {number}"
            folder.mkdir(parents=True)
            (folder / "Episode 01.mkv").write_bytes(b"video")
        db.add_watched_directory(str(watched))
        first = {"id": 100, "format": "TV", "title": {"english": "Exact Anime"},
                 "relations": {"edges": [{"relationType": "SEQUEL", "node": {"id": 200, "format": "TV"}}]}}
        second = {"id": 200, "format": "TV", "title": {"english": "Exact Anime Season 2"},
                  "relations": {"edges": [{"relationType": "PREQUEL", "node": {"id": 100, "format": "TV"}}]}}
        wrong = {"id": 300, "format": "TV", "title": {"english": "Similar Anime"}}
        with patch("app.core.scanner.is_offline", return_value=False), \
             patch("app.core.matching.client.search_anime", return_value=[wrong, first]), \
             patch("app.core.matching.client.get_anime_by_id", return_value=second):
            self.assertEqual(scan_watched_directories()["errors"], [])
        entry = db.find_franchise_by_folder_path(str(root.resolve()))
        self.assertEqual(entry["anilist_id"], 100)
        seasons = db.get_seasons_for_franchise(entry["id"])
        self.assertEqual([(s["season_number"], s["anilist_id"]) for s in seasons],
                         [(1, 100), (2, 200), (4, None)])
        self.assertTrue(all(s["storage_state"] == "ON_DISK" for s in seasons))

    def test_organizer_keeps_empty_source_folders(self):
        from pathlib import Path
        from app.core.organizer import execute_organize_anime
        root = Path(self.temp.name) / 'anime'
        source = root / 'old' / 'episode.mkv'
        source.parent.mkdir(parents=True)
        source.write_bytes(b'video')
        target = root / 'Season 1' / source.name
        result = execute_organize_anime({'folder_path': str(root), 'moves': [{'source': str(source), 'target': str(target)}]})
        self.assertEqual(result['moved'], 1)
        self.assertTrue(source.parent.exists())
        self.assertEqual(target.read_bytes(), b'video')
