import unittest
from pathlib import Path
from unittest.mock import patch
import test_ui_regressions as support
from app.core.organizer import execute_organize_anime, organization_summary


class PermissionTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def test_permission_denial_is_a_failure(self):
        root = Path(self.temp.name)
        source = root / 'episode.mkv'
        source.write_bytes(b'video')
        target = root / 'Season 1' / source.name
        with patch('app.core.file_operations._rename_noreplace', side_effect=PermissionError('Access denied')):
            result = execute_organize_anime({'folder_path': str(root), 'moves': [{'source': str(source), 'target': str(target)}]})
        self.assertEqual(result['errors'][0]['kind'], 'permission')
        self.assertIn('No files were moved', organization_summary(result))
        self.assertIn('administrator', organization_summary(result))
        self.assertTrue(source.exists())

    def test_equal_size_collision_preserves_both_files(self):
        root = Path(self.temp.name)
        source = root / 'episode.mkv'
        source.write_bytes(b'aaaa')
        target = root / 'Season 1' / source.name
        target.parent.mkdir()
        target.write_bytes(b'bbbb')
        result = execute_organize_anime({'folder_path': str(root), 'moves': [{'source': str(source), 'target': str(target)}]})
        self.assertEqual(result['moved'], 1)
        self.assertEqual(target.read_bytes(), b'bbbb')
        self.assertEqual((target.parent / 'episode_1.mkv').read_bytes(), b'aaaa')
