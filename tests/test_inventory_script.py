import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from inventory_anime_roots import scan_root, write_reports


class InventoryScriptTests(unittest.TestCase):
    def test_reports_preserve_inputs_and_list_all_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / 'anime'
            root.mkdir()
            video = root / '[Group] Show - 01 [1080p].mkv'
            video.write_bytes(b'unchanged')
            (root / 'notes.txt').write_text('notes', encoding='utf-8')
            before = video.stat().st_mtime_ns
            with contextlib.redirect_stdout(io.StringIO()):
                report = write_reports([root], base / 'reports')
            self.assertEqual(report['unique_video_paths'], 1)
            self.assertEqual(len(report['roots'][0]['files']), 2)
            self.assertEqual(video.read_bytes(), b'unchanged')
            self.assertEqual(video.stat().st_mtime_ns, before)
            self.assertEqual(len(list(root.iterdir())), 2)
            for filename in ('files.csv', 'inventory.json', 'summary.md'):
                self.assertTrue((base / 'reports' / filename).is_file())

    def test_missing_root_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = scan_root(Path(temporary) / 'missing')
            self.assertTrue(report['errors'])

    def test_reports_cannot_be_written_inside_anime_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(ValueError):
                write_reports([root], root / 'reports')
