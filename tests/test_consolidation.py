import unittest
from pathlib import Path
import test_ui_regressions as support
from app.core.consolidation import explicit_season, release_folder, make_plan, apply_plan


class ConsolidationTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def test_code_geass_filename_overrides_generated_folder(self):
        from app.core.parser import extract_episode_numbers
        self.assertEqual(extract_episode_numbers('Code Geass R2 2x25.mkv'), [25])
        self.assertEqual(explicit_season('Code Geass R2 2x01.mkv'), 2)
        self.assertEqual(release_folder(Path('Code Geass/Season 1/Code Geass R2 2x01.mkv'))[0], 'Season 02')

    def test_meaningful_outer_season_beats_nested_season_one(self):
        self.assertEqual(release_folder(Path('Show S04/Season 1/Show - 01.mkv'))[0], 'Season 04')

    def test_absolute_arc_and_conflicting_range(self):
        self.assertIn('063-077', release_folder(Path('Show/Season 02 EP063-077/Show - 063.mkv'), absolute=True)[0])
        self.assertTrue(release_folder(Path('Show/Season 16 EP579-587/Show - 628.mkv'), absolute=True)[1])

    def test_arc_metadata_is_preserved(self):
        release, reason = release_folder(Path('Show/Season 1/Show - 01.mkv'), 'Show Hashira Training Arc')
        self.assertIn('Hashira Training Arc', release)
        self.assertIsNone(reason)

    def test_cross_root_collisions_preserve_every_file(self):
        base = Path(self.temp.name)
        roots = [base / 'first', base / 'second']
        for index, root in enumerate(roots):
            folder = root / 'Alpha' / 'Season 1'
            folder.mkdir(parents=True)
            (folder / 'Alpha S01E01.mkv').write_bytes(bytes([index]))
        destination = base / 'combined'
        plan = make_plan(roots, destination)
        self.assertEqual(len(plan['moves']), 2)
        self.assertEqual(len({m['target'] for m in plan['moves']}), 2)
        self.assertFalse(destination.exists())
        result = apply_plan(plan, base / 'journal.jsonl')
        self.assertEqual(result['errors'], [])
        self.assertEqual(len(result['moved']), 2)
        self.assertEqual({p.read_bytes() for p in destination.rglob('*.mkv')}, {b'\x00', b'\x01'})
        self.assertTrue(all(root.exists() for root in roots))

    def test_modified_sources_abort_before_any_move(self):
        base = Path(self.temp.name)
        root = base / 'source'
        folder = root / 'Alpha' / 'Season 1'
        folder.mkdir(parents=True)
        source = folder / 'Alpha S01E01.mkv'
        source.write_bytes(b'original')
        plan = make_plan([root], base / 'combined')
        source.write_bytes(b'changed since preview')
        with self.assertRaises(ValueError):
            apply_plan(plan, base / 'journal.jsonl')
        self.assertTrue(source.exists())
        self.assertFalse((base / 'combined').exists())
