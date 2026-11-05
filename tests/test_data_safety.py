"""Phase 1 acceptance tests use temporary media, never the user's library."""
import json
import os
from pathlib import Path
from contextlib import closing
import sqlite3
import unittest
from unittest.mock import patch

import test_ui_regressions as support
from app import db
from app.core import identity, file_operations as operations
from app.core.scanner import _update_on_disk_info


class DataSafetyTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def rows(self, sql, args=()):
        with closing(db.get_connection()) as conn:
            return [dict(row) for row in conn.execute(sql, args)]

    def indexed(self, number=1, names=('Show S01E10.mkv',)):
        root = Path(self.temp.name) / 'original' / 'Show'
        folder = root / f'Season {number}'
        folder.mkdir(parents=True, exist_ok=True)
        for name in names:
            (folder / name).write_bytes(b'media bytes:' + name.encode())
        db.set_continuous_episodes(self.fid, False)
        db.update_franchise_field(self.fid, 'root_folder_path', str(root))
        sid = db.upsert_season({'franchise_id': self.fid, 'title_display': f'Season {number}',
                                'season_number': number, 'season_folder_path': str(folder),
                                'video_files_json': json.dumps(list(names)), 'storage_state': 'ON_DISK',
                                'size_bytes': sum((folder / n).stat().st_size for n in names)})
        return sid, folder / names[0]

    def test_move_preserves_history_notes_release_artwork_and_all_path_consumers(self):
        from app.config import set_last_episode_path, get_last_episode_path
        sid, source = self.indexed()
        before = self.rows('SELECT * FROM episodes')[0]
        identity.save_episode_notes(before['id'], 'Keep this episode note')
        db.update_franchise_field(self.fid, 'cover_filename', 'keep-cover.jpg')
        set_last_episode_path(str(source))
        target = Path(self.temp.name) / 'merged' / 'Show' / 'Season 1' / source.name
        operations.move_file(source, target)
        after = self.rows('SELECT * FROM episodes')[0]
        self.assertEqual((after['id'], after['release_id'], after['notes']),
                         (before['id'], before['release_id'], 'Keep this episode note'))
        self.assertEqual(self.rows('SELECT episode_id FROM episode_history')[0]['episode_id'], before['id'])
        self.assertEqual(get_last_episode_path(), str(target))
        season = db.get_season(sid)
        self.assertEqual((Path(season['season_folder_path']) / json.loads(season['video_files_json'])[0]).resolve(), target.resolve())
        self.assertEqual(Path(db.get_franchise(self.fid)['root_folder_path']).resolve(), target.parent.parent.resolve())
        self.assertEqual(db.get_franchise(self.fid)['cover_filename'], 'keep-cover.jpg')
        self.assertEqual(self.rows('SELECT status FROM file_operations')[0]['status'], 'COMPLETED')

    def test_crash_between_rename_and_database_commit_is_reconciled_once(self):
        sid, source = self.indexed()
        target = source.parent / 'renamed.mkv'
        operation_id, _ = operations.prepare_move(source, target)
        os.rename(source, target)  # Equivalent to process death before _complete.
        self.assertEqual(self.rows('SELECT path FROM file_locations')[0]['path'], str(source))
        self.assertEqual(operations.recover_operations()['recovered'], 1)
        self.assertEqual(operations.recover_operations()['recovered'], 0)
        self.assertEqual(self.rows('SELECT status FROM file_operations WHERE id=?', (operation_id,))[0]['status'], 'COMPLETED')
        self.assertEqual(json.loads(db.get_season(sid)['video_files_json']), ['renamed.mkv'])
        self.assertTrue(target.is_file())

    def test_database_failure_after_rename_retains_recoverable_intent(self):
        _, source = self.indexed()
        target = source.parent / 'renamed.mkv'
        with patch.object(operations, '_complete', side_effect=sqlite3.OperationalError('disk busy')):
            with self.assertRaises(sqlite3.OperationalError):
                operations.move_file(source, target)
        self.assertEqual(self.rows('SELECT status FROM file_operations')[0]['status'], 'REVIEW')
        self.assertTrue(target.is_file())
        self.assertEqual(operations.recover_operations()['recovered'], 1)

    def test_permission_failure_is_visible_and_retryable(self):
        _, source = self.indexed()
        target = source.parent / 'renamed.mkv'
        with patch.object(operations, '_rename_noreplace', side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):
                operations.move_file(source, target)
        failed = self.rows('SELECT * FROM file_operations')[0]
        self.assertEqual(failed['status'], 'FAILED')
        self.assertIn('denied', failed['error'])
        self.assertTrue(source.is_file())
        operations.move_file(source, target)
        self.assertEqual(operations.recover_operations()['errors'], [])

    def test_recovery_does_not_accept_replacement_or_disconnected_destination(self):
        _, source = self.indexed()
        target = source.parent / 'renamed.mkv'
        operations.prepare_move(source, target)
        saved = source.with_suffix('.saved')
        os.rename(source, saved)
        target.write_bytes(b'other content')
        result = operations.recover_operations()
        self.assertEqual(result['recovered'], 0)
        self.assertTrue(result['errors'])
        self.assertEqual(self.rows('SELECT path FROM file_locations')[0]['path'], str(source))
        self.assertTrue(saved.is_file())

    def test_occupied_target_is_never_overwritten(self):
        _, source = self.indexed()
        target = source.parent / 'occupied.mkv'
        target.write_bytes(b'keep')
        with self.assertRaises(ValueError):
            operations.move_file(source, target)
        self.assertEqual(target.read_bytes(), b'keep')
        self.assertTrue(source.exists())

    def test_manual_move_is_reviewed_and_keeps_episode_history(self):
        from app.config import set_last_episode_path, get_last_episode_path
        _, source = self.indexed()
        set_last_episode_path(str(source))
        target = Path(self.temp.name) / 'new-root' / 'Show' / source.name
        target.parent.mkdir(parents=True)
        os.rename(source, target)
        db.add_watched_directory(str(target.parent.parent))
        result = identity.find_repair_candidates()
        self.assertEqual(result['recovered'], 0)
        self.assertEqual(get_last_episode_path(), str(source))
        candidate = result['candidates'][0]
        self.assertEqual(candidate['evidence'], 'SAME_FILE_SIGNATURE')
        identity.approve_repair(candidate['id'])
        self.assertEqual(get_last_episode_path(), str(target))
        self.assertEqual(len(self.rows('SELECT * FROM episode_history')), 1)

    def test_rescan_of_external_move_creates_candidate_without_relink(self):
        _, source = self.indexed()
        eid = self.rows('SELECT id FROM episodes')[0]['id']
        target_root = Path(self.temp.name) / 'moved-show'
        target_root.mkdir()
        target = target_root / source.name
        os.rename(source, target)
        _update_on_disk_info(self.fid, str(target_root))
        self.assertEqual(len(self.rows('SELECT * FROM physical_files')), 1)
        self.assertEqual(self.rows('SELECT path FROM file_locations')[0]['path'], str(source))
        self.assertEqual(self.rows('SELECT id FROM episodes')[0]['id'], eid)
        self.assertTrue(self.rows("SELECT * FROM repair_candidates WHERE status='REVIEW'"))

    def test_season_one_and_two_episode_ten_have_distinct_identities(self):
        self.indexed(1, ('Show S01E10.mkv',))
        self.indexed(2, ('Show S02E10.mkv',))
        episodes = self.rows('SELECT * FROM episodes ORDER BY id')
        self.assertEqual([e['original_number'] for e in episodes], [10, 10])
        self.assertNotEqual(episodes[0]['release_id'], episodes[1]['release_id'])
        self.assertNotEqual(episodes[0]['id'], episodes[1]['id'])

    def test_combined_file_maps_to_two_episode_ids_without_duplicate_file_rows(self):
        self.indexed(1, ('Show - 01-02.mkv',))
        identity.sync_inventory()
        self.assertEqual(len(self.rows('SELECT * FROM physical_files')), 1)
        self.assertEqual([e['original_number'] for e in self.rows('SELECT * FROM episodes ORDER BY original_number')], [1, 2])
        self.assertEqual(len(self.rows('SELECT * FROM file_episodes')), 2)

    def test_migration_backs_up_and_preserves_legacy_last_played(self):
        base = Path(self.temp.name) / 'legacy'
        base.mkdir()
        legacy = base / 'legacy.db'
        with closing(sqlite3.connect(legacy)) as conn:
            conn.executescript(db._SCHEMA_SQL)
            conn.execute("INSERT INTO franchises(id,display_title) VALUES (1,'Legacy')")
            conn.execute("INSERT INTO seasons(id,franchise_id,title_display,season_folder_path,video_files_json) VALUES (1,1,'Season 1',?,?)", (str(base), '["Show S01E10.mkv"]'))
            conn.execute("INSERT INTO app_state VALUES ('last_episode_path',?)", (str(base / 'Show S01E10.mkv'),))
            conn.commit()
        with patch.object(db, 'DB_PATH', legacy):
            db.init_db()
            before = self.rows('SELECT * FROM episodes')
            db.init_db()
            self.assertEqual(before, self.rows('SELECT * FROM episodes'))
            self.assertEqual(len(self.rows('SELECT * FROM episode_history')), 1)
        self.assertTrue(list((db.EXPORTS_DIR / 'migration-backups').glob('*.db')))

    def test_recycle_failure_never_falls_back_to_permanent_delete(self):
        _, source = self.indexed()
        with patch.object(operations, 'send2trash', side_effect=OSError('Recycle Bin unavailable')):
            with self.assertRaises(OSError):
                operations.recycle_file(source)
        self.assertTrue(source.is_file())
        self.assertEqual(self.rows('SELECT status FROM file_operations')[0]['status'], 'FAILED')
        self.assertEqual(len(self.rows('SELECT * FROM episodes')), 1)

    def test_release_states_do_not_treat_future_or_unknown_as_aired(self):
        self.indexed()
        eid = self.rows('SELECT id FROM episodes')[0]['id']
        identity.set_episode_release(eid, 10, aired_at=200)
        row = self.rows('SELECT * FROM episodes')[0]
        self.assertEqual(identity.episode_state(row, now=100), 'UPCOMING')
        self.assertEqual(identity.episode_state(row, now=300), 'AIRED')
        self.assertEqual(identity.episode_state({'release_state': 'UNKNOWN'}, now=100), 'UNKNOWN')

    def test_ambiguous_titles_do_not_pick_first_database_row(self):
        db.upsert_franchise({'display_title': 'Same title'})
        db.upsert_franchise({'display_title': 'Same title'})
        self.assertIsNone(db.find_franchise_by_title('Same title'))

    def test_continuing_series_split_arcs_root_files_and_future_boundary(self):
        from app.core.library_health import episode_inventory, season_health
        root = Path(self.temp.name) / 'One Piece'
        for relative in ('Season 01 EP001-062/One Piece - 001.mkv',
                         'Season 01 EP001-062/One Piece - 002.mkv',
                         'Season 02 EP063-077/One Piece - 063.mkv',
                         'Season 02 EP063-077/One Piece - 065.mkv',
                         'One Piece - 064.mkv'):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'video')
        _update_on_disk_info(self.fid, str(root))
        episodes = self.rows('SELECT * FROM episodes')
        self.assertEqual(len({e['release_id'] for e in episodes}), 1)
        self.assertTrue(all(e['numbering_scheme'] == 'ABSOLUTE' for e in episodes))
        seasons = db.get_seasons_for_franchise(self.fid)
        coverage = episode_inventory(seasons, continuous=True)
        self.assertNotIn(64, coverage['missing_episodes'])
        active = {'id': 99, 'relation_type': 'SEASON', 'storage_state': 'ON_DISK',
                  'airing_status': 'RELEASING', 'episodes_total': 1181,
                  'next_airing_ep': 66, 'next_airing_at': 9999999999,
                  'episode_start': 63, 'episode_end': 1181,
                  'video_files_json': '["One Piece - 063.mkv", "One Piece - 065.mkv"]'}
        self.assertEqual(season_health(active)['missing_episodes'], [64])
        active['airing_status'] = 'NOT_YET_RELEASED'
        self.assertEqual(season_health(active)['missing_episodes'], [])

    def test_replacing_encoding_changes_file_id_but_preserves_episode_notes(self):
        _, source = self.indexed()
        episode = self.rows('SELECT * FROM episodes')[0]
        identity.save_episode_notes(episode['id'], 'Retain')
        source.write_bytes(b'new encode of the same episode')
        identity.sync_inventory()
        self.assertEqual(len(self.rows('SELECT * FROM physical_files')), 2)
        self.assertEqual(len(self.rows('SELECT * FROM episodes')), 1)
        self.assertEqual(self.rows('SELECT notes FROM episodes')[0]['notes'], 'Retain')

    def test_interrupted_merge_updates_each_completed_file_immediately(self):
        from app.core.consolidation import make_plan, apply_plan
        sid, first = self.indexed(names=('Show S01E10.mkv', 'Show S01E11.mkv'))
        source_root = first.parents[2]
        destination = Path(self.temp.name) / 'merged'
        plan = make_plan([source_root], destination)
        completed = []
        def progress(count, total, title):
            completed.append(count)
            locations = self.rows('SELECT path FROM file_locations')
            self.assertEqual(sum(destination.resolve() in Path(row['path']).resolve().parents for row in locations), count)
        result = apply_plan(plan, Path(self.temp.name) / 'moves.jsonl', progress=progress,
                            should_stop=lambda: bool(completed))
        self.assertTrue(result['cancelled'])
        self.assertEqual(len(result['moved']), 1)
        self.assertEqual(operations.recover_operations()['recovered'], 0)
        self.assertEqual(len(list(source_root.rglob('*.mkv'))) + len(list(destination.rglob('*.mkv'))), 2)
        self.assertEqual(len(self.rows('SELECT * FROM episodes')), 2)

    def test_changed_preview_aborts_before_first_organizer_move(self):
        from app.core.organizer import inspect_anime_folder, execute_organize_anime
        root = Path(self.temp.name) / 'flat'
        root.mkdir()
        first, second = root / 'Show S01E01.mkv', root / 'Show S01E02.mkv'
        first.write_bytes(b'first')
        second.write_bytes(b'second')
        item = inspect_anime_folder(str(root))
        second.write_bytes(b'changed after preview')
        result = execute_organize_anime(item)
        self.assertEqual(result['moved'], 0)
        self.assertTrue(result['errors'])
        self.assertTrue(first.exists())

    def test_release_filter_reuses_loaded_rows_without_scanning_again(self):
        from app.ui.pages.episode_page import EpisodePage, EpisodeWorker
        with patch.object(EpisodeWorker, 'start'):
            page = EpisodePage(self.fid)
        rows = [{'title': 'Episode 1', 'release_state': state} for state in ('AIRED','UPCOMING','UNKNOWN')]
        page._all_rows = rows
        page.release_filter.setCurrentIndex(2)
        self.assertEqual(page.model.rows, [rows[1]])
        page.release_filter.setCurrentIndex(3)
        self.assertEqual(page.model.rows, [rows[2]])
        page.deleteLater()

    def test_explicit_season_numbers_override_misplaced_parent_folder(self):
        root = Path(self.temp.name) / 'mixed'
        folder = root / 'Season 1'
        folder.mkdir(parents=True)
        for name in ('Show S01E10.mkv', 'Show S02E10.mkv'):
            (folder / name).write_bytes(b'video')
        db.set_continuous_episodes(self.fid, False)
        _update_on_disk_info(self.fid, str(root))
        episodes = self.rows('SELECT * FROM episodes')
        self.assertEqual(len(episodes), 2)
        self.assertEqual(len({ep['release_id'] for ep in episodes}), 2)

    def test_explicit_season_tokens_are_not_collapsed_in_a_continuing_series(self):
        root = Path(self.temp.name) / 'mixed'
        root.mkdir()
        for name in ('Show S01E10.mkv', 'Show S02E10.mkv'):
            (root / name).write_bytes(b'video')
        _update_on_disk_info(self.fid, str(root))
        episodes = self.rows('SELECT * FROM episodes')
        self.assertEqual(len(episodes), 2)
        self.assertEqual(len({ep['identity_key'] for ep in episodes}), 2)
        self.assertTrue(all(ep['numbering_scheme'] == 'SEASON' for ep in episodes))

    def test_release_filter_states_use_airing_timestamp_not_local_file_presence(self):
        folder = Path(self.temp.name) / 'release'
        folder.mkdir()
        for number in (1, 3, 99):
            (folder / f'Show S01E{number:02}.mkv').write_bytes(b'media')
        db.set_continuous_episodes(self.fid, False)
        db.upsert_season({'franchise_id': self.fid, 'anilist_id': 200, 'title_display': 'Release',
                         'season_number': 1, 'season_folder_path': str(folder),
                         'video_files_json': json.dumps([p.name for p in folder.iterdir()]),
                         'airing_status': 'RELEASING', 'next_airing_ep': 3, 'next_airing_at': 9999999999})
        states = {ep['original_number']: identity.episode_state(ep) for ep in self.rows('SELECT * FROM episodes')}
        self.assertEqual(states, {1: 'AIRED', 3: 'UPCOMING', 99: 'UNKNOWN'})

    def test_explicit_manual_mapping_is_not_overwritten_by_folder_scan(self):
        self.indexed()
        eid = self.rows('SELECT id FROM episodes')[0]['id']
        identity.set_episode_release(eid, 99, state='UNKNOWN')
        identity.sync_inventory()
        episode = self.rows('SELECT * FROM episodes')[0]
        self.assertEqual((episode['release_number'], episode['mapping_source']), (99, 'MANUAL'))

    def test_verified_part_relative_mapping_drives_health_without_renaming(self):
        from app.core.library_health import season_health
        sid, source = self.indexed(2, ('Show - 13.mkv', 'Show - 14.mkv'))
        episodes = self.rows('SELECT * FROM episodes ORDER BY original_number')
        for episode, number in zip(episodes, (1, 2)):
            identity.set_episode_release(episode['id'], number, state='AIRED')
        db.update_season_field(sid, 'episodes_total', 3)
        db.update_season_field(sid, 'numbering_source', 'metadata')
        health = season_health(db.get_season(sid))
        self.assertEqual(health['missing_episodes'], [3])
        self.assertTrue(source.is_file())
        self.assertEqual([e['original_number'] for e in self.rows('SELECT * FROM episodes ORDER BY original_number')], [13, 14])

    def test_windows_recycling_does_not_use_legacy_fallback(self):
        import builtins
        from app.core import recycle_bin
        original_import = builtins.__import__
        def deny_modern(name, *args, **kwargs):
            if name == 'send2trash.win.modern':
                raise ImportError('pywin32 missing')
            return original_import(name, *args, **kwargs)
        with patch.object(recycle_bin.sys, 'platform', 'win32'), patch('builtins.__import__', side_effect=deny_modern):
            with self.assertRaises(OSError):
                recycle_bin.send2trash('never touched.mkv')

    def test_lazy_discovery_records_history_against_episode_not_just_path(self):
        _, first = self.indexed()
        new_file = first.parent / 'Show S01E11.mkv'
        new_file.write_bytes(b'new episode')
        identity.track_play(str(new_file))
        histories = self.rows('SELECT h.episode_id,e.original_number FROM episode_history h JOIN episodes e ON e.id=h.episode_id')
        self.assertEqual([row['original_number'] for row in histories], [11])
