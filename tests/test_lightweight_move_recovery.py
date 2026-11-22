"""Temporary move proofs and common source notation, with isolated files only."""
import json
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
import test_ui_regressions as support
from app import db
from app.core import file_operations as operations,download_queue,downloads,download_library
from app.core import download_discovery as discovery,download_assignment
from app.core.parser import extract_episode_numbers,explicit_season_number,season_episode_match


class LightweightRecoveryTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def paths(self):return Path(self.temp.name)/'source.mkv',Path(self.temp.name)/'target.mkv'

    def job(self,source,target):
        return dict(id='proof',indexed=True,verified_files=[dict(path=str(source),size=5)],
                    library_move_intent=[dict(job_id='proof',source=str(source),target=str(target))])

    def test_same_size_without_completed_record_is_not_recovery_proof(self):
        source,target=self.paths();target.write_bytes(b'wrong');job=self.job(source,target)
        download_queue.check_completed_files(job)
        self.assertTrue(job['integrity_missing']);self.assertEqual(job['verified_files'][0]['path'],str(source))

    def test_same_volume_recovery_uses_metadata_without_hashing(self):
        source,target=self.paths();source.write_bytes(b'video');operations.move_file(source,target)
        job=self.job(source,target)
        with patch.object(operations,'_digest',side_effect=AssertionError('No video reads on polling')):
            download_queue.check_completed_files(job)
        self.assertFalse(job['integrity_missing']);self.assertEqual(job['verified_files'][0]['path'],str(target))

    def test_cross_volume_proof_records_target_identity_and_poll_does_not_rehash(self):
        source,target=self.paths();source.write_bytes(b'video');operations.copy_move_file(source,target)
        job=self.job(source,target)
        with patch.object(operations,'_digest',side_effect=AssertionError('No video reads on polling')):
            download_queue.check_completed_files(job)
            self.assertTrue(download_library._finished(source,target))
        self.assertFalse(job['integrity_missing'])

    def test_changed_target_is_not_adopted(self):
        source,target=self.paths();source.write_bytes(b'video');operations.move_file(source,target)
        target.write_bytes(b'changed-size');job=self.job(source,target)
        download_queue.check_completed_files(job);self.assertTrue(job['integrity_missing'])

    def test_acknowledgement_cleans_only_settled_move_records(self):
        source,target=self.paths();source.write_bytes(b'video');operations.move_file(source,target)
        rows=self.job(source,target)['library_move_intent']
        downloads._save_jobs([dict(id='proof',indexed=True,library_moved=False,library_move_intent=rows)],completed_moves=rows)
        self.assertTrue(operations.completed_move(source,target))
        downloads._save_jobs([dict(id='proof',indexed=True,library_moved=True,verified_files=[dict(path=str(target),size=5)])],completed_moves=rows)
        with closing(db.get_connection()) as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM file_operations').fetchone()[0],0)
        self.assertTrue(target.is_file());self.assertTrue(downloads.jobs()[0]['library_moved'])

    def test_interrupted_move_keeps_proof_until_it_is_consumed(self):
        source,target=self.paths();source.write_bytes(b'video')
        with patch.object(operations,'_complete',side_effect=RuntimeError('interrupted')):
            with self.assertRaises(RuntimeError):operations.move_file(source,target)
        self.assertFalse(operations.completed_move(source,target))
        self.assertEqual(operations.recover_operations()['recovered'],1)
        self.assertTrue(operations.completed_move(source,target))

    def test_failed_cleanup_rolls_back_queue_acknowledgement(self):
        source,target=self.paths();source.write_bytes(b'video');operations.move_file(source,target)
        job=self.job(source,target);downloads._save_jobs([job]);rows=job['library_move_intent']
        with closing(db.get_connection()) as conn,conn:
            conn.execute("CREATE TRIGGER block_cleanup BEFORE DELETE ON file_operations BEGIN SELECT RAISE(ABORT,'simulated interruption'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            downloads._save_jobs([dict(id='proof',library_moved=True)],completed_moves=rows)
        self.assertTrue(downloads.jobs()[0]['library_move_intent'])
        self.assertFalse(downloads.jobs()[0].get('library_moved',False))
        self.assertTrue(operations.completed_move(source,target))

    def test_another_active_consumer_keeps_shared_move_proof(self):
        source,target=self.paths();source.write_bytes(b'video');operations.move_file(source,target)
        rows=self.job(source,target)['library_move_intent']
        downloads._save_jobs([dict(id='proof',library_moved=True),dict(id='other',library_move_intent=rows)],completed_moves=rows)
        self.assertTrue(operations.completed_move(source,target))

    def test_common_season_spellings_share_title_and_episode_evidence(self):
        for token in ('S02E08','S2 E8','S 02 E 08','S-02 E-08','S_02_E_08','Season 2 Episode 08'):
            title='[Judas] Black Clover '+token
            with self.subTest(title=title):
                self.assertEqual(explicit_season_number(title),2)
                self.assertEqual(extract_episode_numbers(title),[8])
                self.assertEqual(discovery.download_title_key(title),'blackclover')
                self.assertEqual(int(season_episode_match(title)[1]),2)
        self.assertIsNone(explicit_season_number('Black Clover 1080p'))
        self.assertIsNone(explicit_season_number('Black Clover S200'))

    def test_remembered_mapping_and_next_search_use_same_spaced_token(self):
        title='[Judas] Alternate Name S 02 E 07'
        discovery.remember_confirmed_alias(self.fid,dict(title=title,season=2,continuous=False,episodes=[7],source_episodes=[7]))
        row=discovery.classify(dict(title='[Judas] Alternate Name S2 E08'),discovery.library_context(self.fid))
        self.assertEqual(row['episode_keys'],['EPISODE:S2:8']);self.assertNotEqual(row['status'],'Match Uncertain')
        download_assignment.remember(dict(id='confirmed',fid=self.fid,created=1,assignment_version=1,
            season=2,continuous=False,episode_keys=['EPISODE:S2:7'],source_episodes=[7],release_title=title))
        self.assertEqual(download_assignment.next_search(self.fid)['query'],'[Judas] Alternate Name S02E08')
