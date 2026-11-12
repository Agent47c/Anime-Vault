import json,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from contextlib import closing
import test_ui_regressions as support
from app import db
from app.core import downloads,download_queue,download_library,identity,file_operations


class DownloadRecoveryTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def fixture(self):
        root=Path(self.temp.name)/'staging';root.mkdir();file=root/'Example S02E10.mkv';file.write_bytes(b'video')
        sid=db.upsert_season(dict(franchise_id=self.fid,title_display='Season 2',season_number=2,season_folder_path=str(root),video_files_json=json.dumps([file.name]),storage_state='ON_DISK'))
        identity.sync_inventory(sid);identity.track_play(str(file));db.set_state('last_episode_path',str(file))
        job=dict(id='one',fid=self.fid,title='One Piece',engine='builtin',desired='cancelled',status='Indexed',indexed=True,season=2,destination=str(root),root=str(root),verified_files=[dict(path=str(file),size=5)])
        downloads._save_jobs([job]);target=Path(self.temp.name)/'library';target.mkdir();db.add_watched_directory(str(target))
        return file,target,job
    def test_completed_move_preserves_identity_history_and_last_played(self):
        file,root,job=self.fixture()
        with closing(db.get_connection()) as conn:before=[tuple(r) for r in conn.execute('SELECT id,episode_id FROM episode_history')]
        plan=download_library.preview();self.assertEqual(len(plan['rows']),1)
        result=download_library.move(plan);target=Path(plan['rows'][0]['target'])
        self.assertFalse(file.exists());self.assertEqual(target.read_bytes(),b'video');self.assertIn('1 files moved',result)
        self.assertEqual(db.get_state('last_episode_path'),str(target))
        self.assertEqual(db.get_franchise(self.fid)['root_folder_path'],plan['rows'][0]['library_folder'])
        with closing(db.get_connection()) as conn:self.assertEqual([tuple(r) for r in conn.execute('SELECT id,episode_id FROM episode_history')],before)
        moved=downloads.jobs()[0];self.assertEqual(moved['id'],'one');self.assertEqual(moved['verified_files'][0]['path'],str(target));self.assertEqual(download_queue.status(moved),'Completed')
        self.assertFalse(download_library.preview()['rows'])
    def test_collision_never_overwrites_and_changed_source_aborts(self):
        file,root,job=self.fixture();plan=download_library.preview();target=Path(plan['rows'][0]['target']);target.parent.mkdir(parents=True);target.write_bytes(b'keep')
        self.assertFalse(download_library.preview()['rows']);download_library.move(plan)
        self.assertEqual(target.read_bytes(),b'keep');self.assertEqual(file.read_bytes(),b'video')
    def test_copy_move_recovery_proves_target_without_losing_history(self):
        file,root,job=self.fixture();target=root/'copy.mkv'
        original=file_operations._complete
        with patch.object(file_operations,'_complete',side_effect=RuntimeError('power interrupted')):
            with self.assertRaises(RuntimeError):file_operations.copy_move_file(file,target)
        self.assertFalse(file.exists());self.assertEqual(target.read_bytes(),b'video')
        report=file_operations.recover_operations();self.assertEqual(report['recovered'],1);self.assertEqual(db.get_state('last_episode_path'),str(target))
    def test_retry_uses_existing_id_destination_and_selection(self):
        file,root,job=self.fixture();job.update(indexed=False,desired='running',status='Error: disk',selection_confirmed=True,selected_files=[0]);downloads._save_jobs([job])
        config={**downloads.DEFAULTS,'enabled':True};db.set_state('downloads.settings',json.dumps(config))
        adapter=Mock();adapter.snapshot.return_value={'status':'Downloading','progress':.2}
        with patch('app.core.builtin_torrents.engine',return_value=adapter),patch.object(downloads,'add_download') as add:
            download_queue.action('one','retry');download_queue.action('one','retry')
        add.assert_not_called();rows=downloads.jobs();self.assertEqual(len(rows),1);self.assertEqual(rows[0]['id'],'one');self.assertEqual(rows[0]['destination'],str(file.parent));self.assertEqual(rows[0]['selected_files'],[0]);self.assertEqual(file.read_bytes(),b'video')
    def test_resume_old_choose_files_job_starts_same_entry(self):
        file,root,job=self.fixture();job.update(indexed=False,desired='paused',status='Choose files to start',selection_confirmed=False,selected_files=None)
        downloads._save_jobs([job]);db.set_state('downloads.settings',json.dumps({**downloads.DEFAULTS,'enabled':True,'start_paused':True}))
        adapter=Mock();adapter.snapshot.return_value={'status':'Downloading'}
        with patch('app.core.builtin_torrents.engine',return_value=adapter):download_queue.action('one','resume')
        current=downloads.jobs();self.assertEqual(len(current),1);self.assertEqual(current[0]['id'],'one');self.assertEqual(current[0]['destination'],str(file.parent));self.assertTrue(current[0]['selection_confirmed']);self.assertEqual(current[0]['desired'],'running');self.assertIsNone(current[0]['selected_files'])
        self.assertFalse(downloads.settings()['start_paused'])
    def test_default_staging_is_under_main_root_and_custom_choice_is_kept(self):
        root=Path(self.temp.name)/'library';db.add_watched_directory(str(root));self.assertEqual(Path(downloads.settings()['destination']),root/'.animevault-downloads')
        db.set_state('downloads.settings',json.dumps({'destination':self.temp.name}));self.assertEqual(downloads.settings()['destination'],self.temp.name)
    def test_native_recheck_clears_error_before_hash_check(self):
        from app.core.builtin_torrents import Engine
        engine=Engine.__new__(Engine);handle=Mock();engine.attach=Mock(return_value=handle);engine.configured={}
        engine.recheck({'id':'one'});self.assertEqual([call[0] for call in handle.method_calls],['clear_error','force_recheck','resume'])
    def test_partial_cross_drive_relocation_keeps_both_paths_reachable(self):
        source=Path('C:/__animevault_fixture__/Season 01');target=Path('E:/__animevault_fixture__/Season 01')
        sid=db.upsert_season(dict(franchise_id=self.fid,season_folder_path=str(source),video_files_json=json.dumps(['a.mkv','b.mkv'])))
        with closing(db.get_connection()) as conn,conn:
            identity.relocate(conn,source/'a.mkv',target/'a.mkv')
            season=dict(conn.execute('SELECT * FROM seasons WHERE id=?',(sid,)).fetchone())
            paths=[Path(season['season_folder_path'])/name for name in json.loads(season['video_files_json'])]
            self.assertEqual({identity.path_key(p) for p in paths},{identity.path_key(target/'a.mkv'),identity.path_key(source/'b.mkv')})
    def test_remove_uses_cancel_and_removes_row_without_touching_files(self):
        file,root,job=self.fixture();job.update(desired='running');downloads._save_jobs([job]);config={**downloads.DEFAULTS,'enabled':True};db.set_state('downloads.settings',json.dumps(config))
        adapter=Mock();adapter.snapshot.return_value={'status':'Cancelled — files kept','files':[]}
        with patch('app.core.builtin_torrents.engine',return_value=adapter):download_queue.action('one','remove')
        self.assertEqual(downloads.jobs(),[]);self.assertEqual(file.read_bytes(),b'video')
        self.assertEqual(adapter.snapshot.call_args[0][0]['desired'],'cancelled')
    def test_partial_library_move_can_resume_without_moving_first_file_twice(self):
        file,root,job=self.fixture();second=file.parent/'Example S02E11.mkv';second.write_bytes(b'video2')
        sid=db.get_seasons_for_franchise(self.fid)[0]['id'];db.update_season_field(sid,'video_files_json',json.dumps([file.name,second.name]));identity.sync_inventory(sid)
        job['verified_files'].append(dict(path=str(second),size=6));downloads._save_jobs([job]);plan=download_library.preview()
        stopped=[];original=file_operations.move_file
        def first(*args,**kwargs):
            result=original(*args,**kwargs);stopped.append(True);return result
        with patch.object(file_operations,'move_file',side_effect=first):download_library.move(plan,cancelled=lambda:bool(stopped))
        self.assertTrue(second.exists());self.assertFalse(file.exists());self.assertTrue(downloads.jobs()[0].get('library_move_intent'))
        result=download_library.move(download_library.preview())
        self.assertIn('1 previously moved files reconciled',result);self.assertFalse(second.exists());self.assertTrue(downloads.jobs()[0]['library_moved'])
    def test_row_menu_keeps_original_target_when_selection_changes(self):
        from app.ui.pages.downloads_page import DownloadsPage
        from PyQt5.QtCore import QPoint
        with patch.object(DownloadsPage,'refresh'):
            page=DownloadsPage();page.items=[dict(id='one',title='First',destination=self.temp.name,status='Paused'),dict(id='two',title='Second',destination=self.temp.name,status='Paused')];page.render();page.table.selectRow(0)
            callbacks={}
            class Menu:
                def __init__(self,*args):pass
                def addAction(self,label,callback):callbacks[label]=callback
                def exec_(self,*args):
                    page.table.selectRow(1);callbacks['Remove queue entry — keep files']()
            with patch('app.ui.pages.downloads_page.QMenu',Menu),patch.object(page,'action') as action:
                page.row_menu(QPoint(1,1));action.assert_called_once_with('remove','one')
            page.timer.stop();page.deleteLater()
    def test_unselected_files_stay_in_staging_and_preview_does_not_move(self):
        file,root,job=self.fixture();extra=file.parent/'not-selected.txt';extra.write_bytes(b'keep')
        job['download_files']=[dict(name=file.name,size=5,priority=1),dict(name=extra.name,size=4,priority=0)]
        downloads._save_jobs([job]);plan=download_library.preview()
        self.assertEqual(len(plan['rows']),1);self.assertTrue(file.exists())
        from app.ui.dialogs.download_library_move import DownloadLibraryMove
        page=DownloadLibraryMove(plan);page.resize(1100,720);page.show();self.app.processEvents()
        self.assertIsNone(page._worker);self.assertTrue(page.move_button.isEnabled());self.assertTrue(file.exists())
        page.close();page.deleteLater()
        download_library.move(plan);self.assertTrue(extra.exists());self.assertFalse(file.exists())
