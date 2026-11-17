import json,unittest
from pathlib import Path
from contextlib import closing
from app import db
from app.core.folder_cleanup import remove_stale_folder
import test_ui_regressions as support


class FolderCleanupTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def season(self,folder):
        return db.upsert_season(dict(franchise_id=self.fid,title_display='Season 01',season_number=1,season_folder_path=str(folder),video_files_json='[]',storage_state='NOT_DOWNLOADED',anilist_id=12345))
    def test_remove_missing_link_keeps_release_and_episode_history(self):
        folder=Path(self.temp.name)/'missing';sid=self.season(folder)
        from app.core import identity
        season=next(s for s in db.get_seasons_for_franchise(self.fid) if s['id']==sid)
        with closing(db.get_connection()) as conn,conn:
            rid=identity._release(conn,season)
            eid=conn.execute("INSERT INTO episodes(release_id,identity_key,original_number,numbering_scheme) VALUES (?,?,?,?)",(rid,'episode:1',1,'SEASON_RELATIVE')).lastrowid
            conn.execute('INSERT INTO episode_history(episode_id,played_at) VALUES (?,?)',(eid,123))
        from app.ui.organizer_cache import configuration,same_scan_state
        before=configuration({})
        remove_stale_folder(sid)
        self.assertFalse(same_scan_state(before,configuration({})))
        with closing(db.get_connection()) as conn:
            row=conn.execute('SELECT * FROM seasons WHERE id=?',(sid,)).fetchone()
            self.assertIsNone(row['season_folder_path']);self.assertEqual(row['anilist_id'],12345)
            self.assertIsNotNone(conn.execute('SELECT id FROM episodes WHERE id=?',(eid,)).fetchone())
            self.assertEqual(conn.execute('SELECT played_at FROM episode_history WHERE episode_id=?',(eid,)).fetchone()[0],123)
    def test_folder_deletion_is_optional_and_nonempty_directory_is_never_deleted(self):
        folder=Path(self.temp.name)/'season';folder.mkdir();sid=self.season(folder)
        remove_stale_folder(sid);self.assertTrue(folder.is_dir())
        db.update_season_field(sid,'season_folder_path',str(folder));(folder/'keep.ass').write_text('subtitle')
        with self.assertRaisesRegex(ValueError,'not empty'):remove_stale_folder(sid,True)
        self.assertTrue((folder/'keep.ass').exists())
        (folder/'keep.ass').unlink();remove_stale_folder(sid,True);self.assertFalse(folder.exists())
    def test_real_video_and_library_root_are_protected(self):
        folder=Path(self.temp.name)/'season';folder.mkdir();video=folder/'Episode 1.mkv';video.write_bytes(b'video');sid=self.season(folder)
        with self.assertRaisesRegex(ValueError,'contains videos'):remove_stale_folder(sid,True)
        self.assertEqual(video.read_bytes(),b'video');video.unlink();db.add_watched_directory(str(folder))
        with self.assertRaisesRegex(ValueError,'library root'):remove_stale_folder(sid,True)
    def test_missing_folder_row_has_red_bin_and_cancel_does_not_remove_it(self):
        from unittest.mock import patch
        from PyQt5.QtWidgets import QPushButton
        from app.ui.pages.detail_modal import DetailModal
        folder=Path(self.temp.name)/'missing';sid=self.season(folder)
        page=DetailModal(self.fid);self.addCleanup(page.deleteLater)
        if hasattr(page,'episode_panel'):self.addCleanup(page.episode_panel.stop)
        bins=[b for b in page.findChildren(QPushButton) if b.accessibleName()=='Remove leftover folder entry']
        self.assertTrue(bins);self.assertTrue(bins[0].property('danger'));self.assertFalse(bins[0].icon().isNull())
        season=next(s for s in db.get_seasons_for_franchise(self.fid) if s['id']==sid)
        with patch('app.ui.pages.detail_modal.QMessageBox.exec_',return_value=0),patch('app.core.folder_cleanup.remove_stale_folder') as remove:
            page._remove_stale_folder(season);remove.assert_not_called()
        self.assertEqual(next(s for s in db.get_seasons_for_franchise(self.fid) if s['id']==sid)['season_folder_path'],str(folder))
    def test_stale_row_cannot_discard_an_owned_video_at_its_new_location(self):
        from app.core import identity
        folder=Path(self.temp.name)/'missing';sid=self.season(folder)
        actual=Path(self.temp.name)/'moved.mkv';actual.write_bytes(b'video');size,mtime,device,inode=identity.signature(actual)
        with closing(db.get_connection()) as conn,conn:
            file_id=conn.execute("INSERT INTO physical_files(season_id,original_name,size_bytes,mtime_ns,device,inode,availability) VALUES (?,?,?,?,?,?,'AVAILABLE')",(sid,actual.name,size,mtime,device,inode)).lastrowid
            conn.execute('INSERT INTO file_locations VALUES (?,?,?)',(file_id,str(actual),identity.path_key(actual)))
        with self.assertRaisesRegex(ValueError,'another recorded location'):remove_stale_folder(sid,True)
        self.assertEqual(actual.read_bytes(),b'video')
