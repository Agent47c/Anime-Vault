"""Removal retains stable history and excludes kept files from rediscovery."""
import unittest
from pathlib import Path
from unittest.mock import patch
import test_ui_regressions as support
from app import db
from app.core.library_removal import remove_entry
from app.core.download_queue import scan_exclusions

class LibraryRemovalTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def test_keep_files_hides_entry_preserves_history_and_excludes_folder(self):
        folder=Path(self.temp.name)/'Anime';folder.mkdir();video=folder/'Episode 1.mkv';video.write_bytes(b'unchanged')
        db.update_franchise_field(self.fid,'root_folder_path',str(folder))
        db.update_franchise_field(self.fid,'user_notes','Keep my notes')
        with patch('app.core.downloads.jobs',return_value=[]):remove_entry(self.fid)
        self.assertEqual(video.read_bytes(),b'unchanged');self.assertEqual(db.get_all_franchises(),[])
        self.assertEqual(db.get_franchise(self.fid)['user_notes'],'Keep my notes')
        db.init_db();self.assertEqual(db.get_all_franchises(),[])
        self.assertEqual(db.get_library_stats()['total_franchises'],0)
        self.assertIn(str(folder.resolve()),[str(p) for p in scan_exclusions()])

    def test_active_download_blocks_removal_without_hiding_record(self):
        with patch('app.core.downloads.jobs',return_value=[{'fid':self.fid,'status':'Downloading','desired':'running'}]):
            with self.assertRaisesRegex(ValueError,'Stop'):remove_entry(self.fid)
        self.assertEqual(len(db.get_all_franchises()),1)

    def test_group_removal_includes_seasons_but_keeps_unrelated_anime(self):
        arc=db.upsert_franchise({'display_title':'Training arc'});other=db.upsert_franchise({'display_title':'Unrelated'})
        db.group_with_series(arc,self.fid)
        with patch('app.core.downloads.jobs',return_value=[]):remove_entry(self.fid)
        self.assertEqual([r['id'] for r in db.get_all_franchises()],[other])
        self.assertIsNotNone(db.get_franchise(arc))

    def test_failed_file_removal_keeps_entry_visible(self):
        db.upsert_season({'franchise_id':self.fid,'title_display':'Season 1','storage_state':'ON_DISK','video_files_json':'["Episode 1.mkv"]'})
        with patch('app.core.downloads.jobs',return_value=[]):
            with self.assertRaisesRegex(ValueError,'could not be removed'):remove_entry(self.fid,True)
        self.assertEqual(len(db.get_all_franchises()),1)
