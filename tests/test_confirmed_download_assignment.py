import json
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
import test_ui_regressions as support
from app import db
from app.core import downloads, download_assignment as assignment, download_discovery as discovery, identity, download_library


class ConfirmedDownloads(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def job(self, number=177, logical=7):
        root=Path(self.temp.name)/'staging';root.mkdir(exist_ok=True)
        file=root/f'Black Clover - {number}.mkv';file.write_bytes(b'new video')
        with closing(db.get_connection()) as conn,conn:
            conn.execute('INSERT OR IGNORE INTO library_series(franchise_id) VALUES (?)',(self.fid,))
            series=conn.execute('SELECT id FROM library_series WHERE franchise_id=?',(self.fid,)).fetchone()[0]
        job=dict(id='confirmed',fid=self.fid,series_id=series,title='One Piece',destination=str(root),root=str(root),assignment_version=1,
            season=2,continuous=False,episode_keys=[f'EPISODE:S2:{logical}'],source_episodes=[number],release_title=f'[Judas] Black Clover - {number}',group='Judas',created=1,desired='running')
        return file,job

    def test_filename_177_is_database_season_two_episode_seven_without_old_data_changes(self):
        old=Path(self.temp.name)/'old';old.mkdir();(old/'Episode 1.mkv').write_bytes(b'old')
        db.upsert_season(dict(franchise_id=self.fid,season_number=1,title_display='Season 1',relation_type='SEASON',season_folder_path=str(old),video_files_json='["Episode 1.mkv"]',storage_state='ON_DISK'))
        with closing(db.get_connection()) as conn:before=[tuple(r) for r in conn.execute('SELECT * FROM episodes')]
        file,job=self.job();downloads._index_completed(job,[file])
        with closing(db.get_connection()) as conn:
            row=conn.execute('SELECT e.*,f.original_name FROM episodes e JOIN file_episodes fe ON fe.episode_id=e.id JOIN physical_files f ON f.id=fe.file_id JOIN file_locations l ON l.file_id=f.id WHERE l.path_key=?',(identity.path_key(file),)).fetchone()
            self.assertEqual([tuple(r) for r in conn.execute('SELECT * FROM episodes WHERE id<=?',(len(before),))],before)
        self.assertEqual((row['original_number'],row['release_number'],row['mapping_source']),(177,7,'MANUAL'))
        self.assertEqual(row['original_name'],'Black Clover - 177.mkv');self.assertTrue(file.exists())
        context=discovery.library_context(self.fid,2,continuous=False)
        self.assertIn('EPISODE:S2:7',context['local']);self.assertNotIn('EPISODE:S2:177',context['local'])
        downloads._index_completed(job,[file])
        with closing(db.get_connection()) as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM physical_files').fetchone()[0],2)
        self.assertTrue(db.uses_continuous_episodes(db.get_series(self.fid)))

    def test_completion_refuses_to_guess_multi_file_offsets(self):
        file,job=self.job();second=file.with_name('Black Clover - 178.mkv');second.write_bytes(b'two')
        with self.assertRaisesRegex(ValueError,'assignment'):downloads._index_completed(job,[file,second])
        self.assertTrue(file.exists());self.assertTrue(second.exists())
        with closing(db.get_connection()) as conn:self.assertFalse(conn.execute('SELECT 1 FROM physical_files').fetchone())

    def test_next_search_uses_confirmed_source_and_logical_numbers(self):
        _,job=self.job();downloads._save_jobs([job])
        next=assignment.next_search(self.fid)
        self.assertEqual((next['target_episode'],next['source_episode'],next['season']),(8,178,2))
        self.assertEqual(next['query'],'[Judas] Black Clover 178')
        from app.core.release_actions import auto_grab
        with patch.object(discovery,'search',return_value={'context':{},'results':[]}),patch.object(discovery,'submit') as submit:
            result=auto_grab(self.fid,None,999)
        submit.assert_not_called();self.assertEqual(result['assignment_context']['target_episode'],8)

    def test_learned_mapping_survives_clearing_completed_queue(self):
        _,job=self.job();assignment.remember(job);downloads._save_jobs([])
        self.assertEqual(assignment.next_search(self.fid)['source_episode'],178)

    def test_magnet_without_display_name_learns_actual_completed_source_title(self):
        file,job=self.job();job.update(source_episodes=[],release_title='Magnet download',group=None)
        downloads._index_completed(job,[file]);downloads._save_jobs([])
        result=assignment.next_search(self.fid)
        self.assertEqual(result['query'],'Black Clover 178');self.assertEqual(result['target_episode'],8)

    def test_pack_uses_only_exact_confirmed_source_numbers(self):
        file,job=self.job();second=file.with_name('Black Clover - 178.mkv');second.write_bytes(b'two')
        job.update(episode_keys=['EPISODE:S2:7','EPISODE:S2:8'],source_episodes=[177,178])
        downloads._index_completed(job,[file,second])
        context=discovery.library_context(self.fid,2,continuous=False)
        self.assertEqual(set(context['local']),{'EPISODE:S2:7','EPISODE:S2:8'})

    def test_separate_future_downloads_share_one_season_through_partial_moves(self):
        from app.core.library_health import episode_inventory
        from app.ui.pages.episode_page import EpisodeWorker
        file,one=self.job();downloads._index_completed(one,[file]);one.update(engine='builtin',desired='cancelled',status='Indexed')
        staging=Path(self.temp.name)/'second download';staging.mkdir();second=staging/'Black Clover - 178.mkv';second.write_bytes(b'second')
        two={**one,'id':'two','root':str(staging),'destination':str(staging),'episode_keys':['EPISODE:S2:8'],'source_episodes':[178]}
        downloads._index_completed(two,[second]);downloads._save_jobs([one,two])
        self.assertEqual(len(db.get_series_seasons(self.fid)),1)
        self.assertEqual(episode_inventory(db.get_series_seasons(self.fid))['unique_episode_count'],2)
        root=Path(self.temp.name)/'library';root.mkdir();db.add_watched_directory(str(root))
        plan=download_library.preview();plan['rows']=[r for r in plan['rows'] if r['job_id']==one['id']]
        self.assertIn('1 files moved',download_library.move(plan));self.assertTrue(second.exists())
        rows=[];worker=EpisodeWorker(self.fid);worker.ready.connect(lambda values,warnings:rows.extend(values))
        with patch('app.ui.pages.episode_page.os.walk') as walk,patch('app.ui.pages.episode_page.os.path.relpath',side_effect=ValueError('different drives')):worker.run()
        self.assertEqual(len(rows),2);walk.assert_not_called();worker.deleteLater()
        self.assertIn('1 files moved',download_library.move(download_library.preview()))
        self.assertEqual(len(db.get_series_seasons(self.fid)),1)
        self.assertEqual(set(discovery.library_context(self.fid,2,continuous=False)['local']),{'EPISODE:S2:7','EPISODE:S2:8'})

    def test_auto_move_waits_for_verified_completion_and_uses_approved_folder(self):
        from unittest.mock import Mock
        file,job=self.job();root=Path(self.temp.name)/'library';root.mkdir();db.add_watched_directory(str(root))
        job.update(engine='builtin',move_when_completed=True,approved_destination=assignment.destination(self.fid,2))
        config={**downloads.DEFAULTS,'enabled':True};db.set_state('downloads.settings',json.dumps(config));downloads._save_jobs([job])
        adapter=Mock();adapter.snapshot.return_value=dict(status='Downloading',complete=False,files=[])
        with patch('app.core.builtin_torrents.engine',return_value=adapter):downloads.poll()
        self.assertTrue(file.exists());self.assertFalse(Path(job['approved_destination']['folder']).exists())
        adapter.snapshot.return_value=dict(status='Completed',complete=True,files=[dict(name=file.name,size=file.stat().st_size,priority=1,progress=1)])
        with patch('app.core.builtin_torrents.engine',return_value=adapter):downloads.poll()
        self.assertFalse(file.exists(),downloads.jobs());self.assertTrue((Path(job['approved_destination']['folder'])/file.name).exists())
        self.assertTrue(downloads.jobs()[0]['library_moved'])

    def test_same_torrent_can_be_redownloaded_only_after_completion(self):
        from unittest.mock import Mock
        from app.core.magnet_capture import validate
        from app.core.download_queue import status
        file,job=self.job();downloads._index_completed(job,[file])
        magnet='magnet:?xt=urn:btih:'+'a'*40
        job.update(engine='builtin',torrent_identity='testhash',source_identity=validate(magnet)['identity'],status='Completed')
        downloads._save_jobs([job]);db.set_state('downloads.settings',json.dumps({**downloads.DEFAULTS,'enabled':True,'destination':str(Path(self.temp.name)/'incoming')}))
        adapter=Mock();adapter.snapshot.return_value={'status':'Completed'}
        def prepare(item,source):item['torrent_identity']='testhash';return None
        adapter.prepare.side_effect=prepare
        with patch('app.core.builtin_torrents.engine',return_value=adapter):
            with self.assertRaisesRegex(ValueError,'already tracked'):downloads.add_download(self.fid,magnet,2)
            target=downloads.add_download(self.fid,magnet,2,context=dict(duplicate_action='redownload',season=2,episode_keys=job['episode_keys']))
        rows=downloads.jobs();self.assertEqual(len(rows),2);self.assertNotEqual(target,job['destination'])
        self.assertEqual(status(rows[0]),'Completed');self.assertTrue(rows[0]['retired_for_redownload']);self.assertTrue(file.exists())

    def test_optional_file_selection_retains_confirmed_source_to_logical_mapping(self):
        from unittest.mock import Mock
        file,job=self.job();job.update(engine='builtin',episode_keys=['EPISODE:S2:7','EPISODE:S2:8'],source_episodes=[177,178])
        downloads._save_jobs([job]);db.set_state('downloads.settings',json.dumps({**downloads.DEFAULTS,'enabled':True}))
        adapter=Mock();adapter.snapshot.return_value=dict(status='Downloading',files=[dict(name=file.name),dict(name='Black Clover - 178.mkv')])
        with patch('app.core.builtin_torrents.engine',return_value=adapter):downloads.control_builtin(job['id'],'files',[0])
        current=downloads.jobs()[0];self.assertEqual(current['episode_keys'],['EPISODE:S2:7']);self.assertEqual(current['source_episodes'],[177])
        downloads._index_completed(current,[file])
        self.assertEqual(set(discovery.library_context(self.fid,2,continuous=False)['local']),{'EPISODE:S2:7'})

    def test_confirmation_does_not_change_series_numbering_and_move_defaults_off(self):
        from app.ui.pages.release_search_page import ConfirmCoverage
        values=[];context=discovery.library_context(self.fid,2,continuous=False)
        page=ConfirmCoverage(None,dict(title='Black Clover - 177',episodes=[177],season=2,continuous=False),context,values.append)
        self.addCleanup(page.deleteLater);page.episode_inputs[0].setText('7');page.apply()
        self.assertEqual(values[0]['source_episodes'],[177]);self.assertEqual(values[0]['episode_keys'],['EPISODE:S2:7'])
        self.assertFalse(values[0]['move_when_completed']);self.assertTrue(db.uses_continuous_episodes(db.get_series(self.fid)))

    def test_manual_confirmation_can_chain_workers_before_finished_signal(self):
        from PyQt5.QtCore import QObject,pyqtSignal
        from PyQt5.QtWidgets import QDialog
        from app.ui import io_task
        class ImmediateTask(QObject):
            succeeded=pyqtSignal(object);failed=pyqtSignal(str);finished=pyqtSignal()
            def __init__(self,operation):super().__init__();self.operation=operation
            def isRunning(self):return True
            def start(self):self.succeeded.emit(self.operation());self.finished.emit()
        page=QDialog();self.addCleanup(page.deleteLater);values=[]
        with patch.object(io_task,'IOTask',ImmediateTask):
            io_task.start(page,lambda:'prepared',lambda first:io_task.start(page,lambda:first+' and submitted',values.append))
        self.assertEqual(values,['prepared and submitted']);self.assertTrue(page.isEnabled())

    def test_duplicate_choice_skip_replace_or_redownload(self):
        from app.ui.pages.release_search_page import ConfirmCoverage
        from app.ui.components.message_boxes import AppMessageBox
        file,job=self.job();downloads._index_completed(job,[file])
        for label,action in [('Skip this download',None),('Replace old copy','replace'),('Download another copy','redownload')]:
            values=[];context=discovery.library_context(self.fid,2,continuous=False)
            page=ConfirmCoverage(None,dict(title='Alternative - 07',episodes=[7],season=2,continuous=False),context,values.append)
            self.addCleanup(page.deleteLater)
            def choose(box):box._clicked=next(b for b in box._roles if b.text()==label)
            with patch.object(AppMessageBox,'exec_',choose):page.apply()
            self.assertEqual(bool(values),action is not None)
            if action:self.assertEqual(values[0]['duplicate_action'],action)
            if action=='replace':self.assertEqual(identity.path_key(values[0]['replacement_files'][0]['path']),identity.path_key(file))
            self.assertTrue(file.exists())

    def test_editing_assignment_clears_old_replacement_permission(self):
        from app.ui.pages.release_search_page import ConfirmCoverage
        file,job=self.job();downloads._index_completed(job,[file]);values=[]
        entry=dict(title='Another release - 07',episodes=[7],season=2,continuous=False,duplicate_action='replace',replacement_files=[dict(path=str(file),signature=list(identity.signature(file)))])
        page=ConfirmCoverage(None,entry,discovery.library_context(self.fid,2,continuous=False),values.append);self.addCleanup(page.deleteLater)
        page.episode_inputs[0].setText('8');page.apply()
        self.assertNotIn('duplicate_action',values[0]);self.assertNotIn('replacement_files',values[0]);self.assertTrue(file.exists())

    def test_first_download_uses_selected_empty_metadata_season(self):
        sid=db.upsert_season(dict(franchise_id=self.fid,season_number=2,anilist_id=123,title_display='Season 2',relation_type='SEASON'))
        file,job=self.job();job['local_season_id']=sid;downloads._index_completed(job,[file])
        seasons=db.get_series_seasons(self.fid);self.assertEqual(len(seasons),1);self.assertEqual(seasons[0]['id'],sid)
        self.assertEqual(set(discovery.library_context(self.fid,2,continuous=False)['local']),{'EPISODE:S2:7'})

    def test_approved_move_preserves_name_and_recycles_only_after_new_copy_arrives(self):
        file,job=self.job();downloads._index_completed(job,[file]);job.update(engine='builtin',desired='cancelled',status='Indexed')
        root=Path(self.temp.name)/'library';root.mkdir();db.add_watched_directory(str(root));downloads._save_jobs([job])
        season=root/'One Piece'/'Season 2';season.mkdir(parents=True)
        old=season/file.name;old.write_bytes(b'old copy')
        job.update(move_when_completed=True,approved_destination=assignment.destination(self.fid,2),duplicate_action='replace',replacement_files=[dict(path=str(old),signature=list(identity.signature(old)))])
        downloads._save_jobs([job]);plan=download_library.preview();self.assertEqual(len(plan['rows']),1)
        target=Path(plan['rows'][0]['target']);self.assertEqual(target.name,file.name)
        def recycle(path):
            self.assertTrue(target.is_file());self.assertEqual(target.read_bytes(),b'new video');Path(path).unlink()
        with patch('app.core.file_operations.send2trash',recycle):result=download_library.move(plan)
        self.assertIn('1 files moved',result);self.assertFalse(old.exists());self.assertTrue(target.exists())
        self.assertTrue(downloads.jobs()[0]['replacement_completed'])

    def test_locked_old_copy_keeps_new_copy_and_retry_intent(self):
        file,job=self.job();downloads._index_completed(job,[file]);job.update(engine='builtin',desired='cancelled',status='Indexed')
        root=Path(self.temp.name)/'library';root.mkdir();db.add_watched_directory(str(root))
        old=root/'old encoding.mkv';old.write_bytes(b'old')
        job.update(duplicate_action='replace',replacement_files=[dict(path=str(old),signature=list(identity.signature(old)))])
        downloads._save_jobs([job]);plan=download_library.preview();target=Path(plan['rows'][0]['target'])
        with patch('app.core.file_operations.send2trash',side_effect=OSError('Old copy is locked')):message=download_library.move(plan)
        self.assertIn('locked',message);self.assertTrue(target.exists());self.assertTrue(old.exists())
        saved=downloads.jobs()[0];self.assertFalse(saved.get('library_moved'));self.assertTrue(saved.get('library_move_intent'))
        retry=download_library.preview();self.assertTrue(retry['rows'])
        with patch('app.core.file_operations.send2trash',lambda p:Path(p).unlink()):download_library.move(retry)
        self.assertFalse(old.exists());self.assertTrue(target.exists());self.assertTrue(downloads.jobs()[0]['library_moved'])
