import json
import unittest
from pathlib import Path
from unittest.mock import patch
import test_ui_regressions as support
from app import db
from app.core.loose import inspect_loose_episodes
from app.core.organizer import inspect_all_library, execute_organize_anime
from app.core.scanner import scan_watched_directories


class LooseRootTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def prepare(self):
        root = Path(self.temp.name) / 'Library'
        root.mkdir()
        for name in ('[Group] Alpha S02 - 01 [1080p].mkv', '[Group] Alpha S02 - 02 [1080p].mkv', 'Beta - 01.mkv', '2026-06-19 13-13-55.mkv', 'Random movie.mp4'):
            (root / name).write_bytes(b'original bytes')
        (root / '[Group] Alpha S02 - 01 [1080p].en.ass').write_bytes(b'subtitles')
        db.add_watched_directory(str(root))
        return root

    def test_preview_groups_files_without_creating_folders(self):
        root = self.prepare()
        groups, unknown = inspect_loose_episodes(root)
        self.assertEqual(len(groups), 2)
        self.assertEqual(sum(item['video_count'] for item in groups), 3)
        self.assertEqual(len(unknown), 2)
        self.assertFalse(any(p.is_dir() for p in root.iterdir()))
        alpha = next(item for item in groups if item['anime_name'] == 'Alpha')
        self.assertEqual(alpha['season_number'], 2)
        self.assertEqual(len(alpha['moves']), 3)  # Two episodes and matching subtitle.

    def test_organizer_scan_indexes_anime_before_moves(self):
        root = self.prepare()
        result = inspect_all_library()
        self.assertEqual(len(result['unorganized']), 2)
        self.assertIsNotNone(db.find_franchise_by_title('Alpha'))
        self.assertIsNotNone(db.find_franchise_by_title('Beta'))
        alpha = db.find_franchise_by_title('Alpha')
        files = [name for s in db.get_seasons_for_franchise(alpha['id']) for name in json.loads(s['video_files_json'])]
        self.assertEqual(len(files), 2)
        self.assertTrue(all('Alpha' in name for name in files))
        self.assertFalse(any(p.is_dir() for p in root.iterdir()))

    def test_moves_preserve_bytes_and_do_not_double_count_library(self):
        root = self.prepare()
        result = inspect_all_library()
        alpha = next(item for item in result['unorganized'] if item['anime_name'] == 'Alpha')
        outcome = execute_organize_anime(alpha)
        self.assertEqual(outcome['errors'], [])
        self.assertEqual(outcome['moved'], 3)
        destination = root / 'Alpha' / 'Season 2'
        self.assertEqual(len(list(destination.glob('*.mkv'))), 2)
        for file in destination.glob('*.mkv'):
            self.assertEqual(file.read_bytes(), b'original bytes')
        self.assertTrue((root / 'Beta - 01.mkv').exists())
        self.assertTrue((root / 'Random movie.mp4').exists())
        entry = db.find_franchise_by_title('Alpha')
        self.assertEqual(entry['total_size_bytes'], 2 * len(b'original bytes'))
        self.assertEqual(sum(len(json.loads(s['video_files_json'])) for s in db.get_seasons_for_franchise(entry['id'])), 2)

    def test_library_scan_never_assigns_sibling_anime_to_same_entry(self):
        self.prepare()
        with patch('app.core.scanner.is_offline', return_value=True):
            scan_watched_directories()
            scan_watched_directories()
        alpha, beta = db.find_franchise_by_title('Alpha'), db.find_franchise_by_title('Beta')
        self.assertNotEqual(alpha['id'], beta['id'])
        self.assertEqual(sum(len(json.loads(s['video_files_json'])) for s in db.get_seasons_for_franchise(alpha['id'])), 2)
        self.assertEqual(sum(len(json.loads(s['video_files_json'])) for s in db.get_seasons_for_franchise(beta['id'])), 1)
