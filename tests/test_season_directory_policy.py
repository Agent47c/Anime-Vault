import tempfile
import unittest
from pathlib import Path
from app.core.organizer import inspect_anime_folder
from app.core.loose import inspect_loose_episodes
from app.core.season_paths import season_folder_name, existing_or_new_season_folder


class SeasonDirectoryPolicyTests(unittest.TestCase):
    def test_new_season_names_are_padded_without_truncating_large_numbers(self):
        self.assertEqual([season_folder_name(n) for n in (1,2,9,10,100)],
                         ['Season 01','Season 02','Season 09','Season 10','Season 100'])

    def test_organizer_root_and_release_subfolders_use_padded_targets(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'Demo S01E01.mkv').write_bytes(b'video')
            release=root/'[Group] Season 2 1080p';release.mkdir()
            (release/'Demo S02E01.mkv').write_bytes(b'video')
            # No database is needed for an untracked, ordinary library folder.
            from unittest.mock import patch
            with patch('app.core.download_inventory.Snapshot', autospec=True) as snapshot:
                snapshot.return_value.can_organize.return_value=True
                plan=inspect_anime_folder(str(root))
            targets={Path(row['target']).parent.name for row in plan['moves']}
            self.assertEqual(targets,{'Season 01','Season 02'})
            self.assertFalse((root/'Season 01').exists())

    def test_legacy_directory_is_not_reused_as_the_default_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);legacy=root/'Season 1';legacy.mkdir()
            self.assertEqual(existing_or_new_season_folder(root,1),root/'Season 01')
            self.assertFalse((root/'Season 01').exists())
            canonical=root/'Season 01';canonical.mkdir()
            self.assertEqual(existing_or_new_season_folder(root,1),canonical)

    def test_loose_episode_import_uses_same_padded_name(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'Demo S02E01.mkv').write_bytes(b'video')
            with patch('app.core.download_inventory.Snapshot', autospec=True) as snapshot:
                snapshot.return_value.can_organize.return_value=True
                groups,_=inspect_loose_episodes(root)
            self.assertEqual(Path(groups[0]['moves'][0]['target']).parent.name,'Season 02')

