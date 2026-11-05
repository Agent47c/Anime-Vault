import tempfile
import unittest
from pathlib import Path
from standardize_one_piece import identify, build_plan, execute
from app.core.parser import extract_episode_numbers


class OnePieceNamesTests(unittest.TestCase):
    def test_episode_title_removed_and_number_and_quality_preserved(self):
        info = identify('[Anime Time] One Piece - 0747 - The Silver Fortress! [1080p].mkv')
        self.assertEqual(info['title'], 'One Piece - Episode 0747 [1080p]')
        self.assertEqual(identify('[Kayoanime] - 1018.mkv')['episode'], 1018)
        self.assertIsNone(identify('One Piece - 1001.mkv')['quality'])

    def test_reedit_is_not_renumbered_as_original_series(self):
        info = identify('[ASW] One Piece Log - Fish-Man Island Saga - 01 [1080p].mkv')
        self.assertTrue(info['reedit'])
        self.assertEqual(info['title'], 'One Piece - Re-edit Episode 0001 [1080p]')

    def test_existing_version_tag_is_preserved(self):
        self.assertEqual(identify('One Piece - Episode 0579 [720p] [v2].mp4')['title'], 'One Piece - Episode 0579 [720p] [v2]')

    def test_other_series_movies_and_true_specials_are_untouched(self):
        for name in ('Solo Leveling - 23.mkv', 'One Piece Movie 01.mkv', 'One Piece - 1023SP.mp4', 'One Piece Egghead SP6.mkv'):
            self.assertIsNone(identify(name), name)

    def test_special_word_in_episode_title_does_not_hide_normal_episode(self):
        name = "[Anime Time] One Piece - 0918 - It's On! The Special Operation.mkv"
        self.assertEqual(identify(name)['episode'], 918)
        self.assertEqual(extract_episode_numbers(name), [918])

    def test_renames_preserve_duplicate_copies_and_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'One Piece'
            season = root / 'Season 1'
            season.mkdir(parents=True)
            for name, content in (('[A] One Piece - 001 [1080p].mkv', b'encode one'), ('[B] One Piece - 001 [1080p].mkv', b'encode two')):
                (season / name).write_bytes(content)
            plan = build_plan(root)
            self.assertEqual(len({entry['target'] for entry in plan['moves']}), 2)
            execute(plan, Path(temporary) / 'journal.jsonl')
            self.assertEqual({p.read_bytes() for p in season.iterdir()}, {b'encode one', b'encode two'})
            self.assertEqual(build_plan(root)['moves'], [])
