import json,unittest
from pathlib import Path
from app import db
from app.core import downloads,download_library,folder_cleanup
import test_ui_regressions as support
import test_download_recovery_and_moves as recovery


class LeftoversAndTargets(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    fixture=recovery.DownloadRecoveryTests.fixture
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_empty_reference_can_be_removed_without_touching_shared_live_folder(self):
        folder=Path(self.temp.name)/'Season 02';folder.mkdir();video=folder/'Episode 1.mkv';video.write_bytes(b'video')
        live=db.upsert_season(dict(franchise_id=self.fid,season_number=2,title_display='Live',season_folder_path=str(folder),video_files_json=json.dumps([video.name]),storage_state='ON_DISK'))
        empty=db.upsert_season(dict(franchise_id=self.fid,season_number=2,title_display='Empty',season_folder_path=str(folder),video_files_json='[]'))
        folder_cleanup.remove_stale_folder(empty)
        self.assertTrue(video.exists());self.assertEqual(db.get_season(live)['season_folder_path'],str(folder));self.assertIn(empty,folder_cleanup.hidden_folder_ids())
    def test_no_folder_metadata_entry_can_be_hidden_without_deleting_metadata(self):
        sid=db.upsert_season(dict(franchise_id=self.fid,anilist_id=123,title_display='Metadata',season_number=1))
        folder_cleanup.remove_stale_folder(sid);self.assertIsNotNone(db.get_season(sid));self.assertIn(sid,folder_cleanup.hidden_folder_ids())
    def test_ambiguous_real_folders_can_be_chosen_explicitly(self):
        file,root,job=self.fixture();anime=root/'One Piece';a=anime/'Season 02';b=anime/'Season 2';a.mkdir(parents=True);b.mkdir()
        db.update_franchise_field(self.fid,'root_folder_path',str(anime))
        blocked=download_library.preview();self.assertFalse(blocked['rows']);self.assertTrue(blocked['destinations'])
        plan=download_library.preview(folder_overrides={job['id']:str(a)})
        self.assertEqual(len(plan['rows']),1);self.assertEqual(Path(plan['rows'][0]['target']).parent,a)
        self.assertTrue(file.exists())
    def test_indexed_files_in_staging_remain_discoverable_after_queue_clear(self):
        file,root,job=self.fixture();downloads._save_jobs([])
        db.set_state('downloads.settings',json.dumps({**downloads.DEFAULTS,'destination':str(file.parent)}))
        plan=download_library.preview();self.assertFalse(plan['rows']);self.assertEqual(plan['indexed_staging'][0]['fid'],self.fid)
    def test_partial_download_explains_why_it_cannot_move(self):
        file,root,job=self.fixture();job.update(indexed=False,status='Downloading',desired='running');downloads._save_jobs([job])
        plan=download_library.preview();self.assertFalse(plan['rows']);self.assertIn('not ready',' '.join(plan['notes']))
    def test_stale_unpadded_database_path_cannot_override_new_padded_destination(self):
        file,root,job=self.fixture();anime=root/'One Piece'
        db.upsert_season(dict(franchise_id=self.fid,title_display='Old path',season_number=2,season_folder_path=str(anime/'Season 2'),video_files_json='[]'))
        plan=download_library.preview()
        self.assertEqual(Path(plan['rows'][0]['target']).parent,anime/'Season 02')
        self.assertFalse((anime/'Season 2').exists());self.assertTrue(file.exists())
