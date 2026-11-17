import json
import unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import patch,Mock
from PyQt5.QtCore import Qt
from app import db
from app.core import download_discovery as discovery,download_queries,downloads,download_queue,identity,season_file_moves
import test_ui_regressions as support


class SearchMemoryAndMoves(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def test_draft_restores_exact_search_and_keeps_languages_offline(self):
        from app.ui.pages.release_search_page import ReleaseSearchPage
        db.cache_media(self.fid,dict(id=21,title=dict(english='English name',romaji='Romaji name',native='日本語')))
        page=ReleaseSearchPage(None,self.fid);self.addCleanup(page.deleteLater)
        page.query.setText('[Judas] 自分の検索 S02E07 1080p');page.reject()
        other=ReleaseSearchPage(None,self.fid);self.addCleanup(other.deleteLater)
        self.assertEqual(other.query.text(),'[Judas] 自分の検索 S02E07 1080p')
        titles=[other.title_choice.itemData(i) for i in range(other.title_choice.count())]
        self.assertTrue({'English name','Romaji name','日本語'}<=set(titles));other.reject()
        db.update_franchise_field(self.fid,'metadata_json','{}')
        self.assertTrue({'English name','Romaji name','日本語'}<={v for _,v in download_queries.title_options(self.fid)})

    def test_memories_are_separate_for_each_anime(self):
        another=db.upsert_franchise(dict(display_title='Other anime'))
        download_queries.save_search_memory(self.fid,'Custom Black Clover',2)
        self.assertEqual(download_queries.search_memory(another),{})
        self.assertEqual(download_queries.search_memory(self.fid)['query'],'Custom Black Clover')

    def test_remembered_scope_and_offset_survive_fresh_search(self):
        discovery.remember_confirmed_alias(self.fid,dict(title='[Judas] Alternate Name - 177 [1080p]',season=2,continuous=False,episodes=[7],source_episodes=[177]))
        context=discovery.library_context(self.fid)
        self.assertTrue(context['continuous']) # Existing series preference stays unchanged.
        entry=discovery.classify(dict(title='[Judas] Alternate Name - 178 [1080p]'),context)
        self.assertEqual(entry['episode_keys'],['EPISODE:S2:8']);self.assertEqual(entry['source_episodes'],[178])
        wrong=discovery.classify(dict(title='[Judas] Alternate Name S03E08'),context)
        self.assertEqual(wrong['status'],'Match Uncertain')

    def test_remembered_title_does_not_override_explicit_other_season(self):
        discovery.remember_confirmed_alias(self.fid,dict(title='Alternate Name - 5',season=2,continuous=False,episodes=[5],source_episodes=[5]))
        entry=discovery.classify(dict(title='Alternate Name - 6'),discovery.library_context(self.fid,3,continuous=False))
        self.assertEqual(entry['status'],'Match Uncertain')

    def test_existing_title_only_alias_is_found_without_selecting_its_season(self):
        discovery.remember_download_alias(self.fid,2,'Legacy alternate')
        entry=discovery.classify(dict(title='Legacy alternate - 08'),discovery.library_context(self.fid))
        self.assertEqual(entry['episode_keys'],['EPISODE:S2:8'])

    def test_remembered_encoder_season_can_differ_from_library_season(self):
        discovery.remember_confirmed_alias(self.fid,dict(title='[Judas] Alternate S02E07',group='Judas',season=1,continuous=False,episodes=[7],source_episodes=[7]))
        result=discovery.classify(dict(title='[Judas] Alternate S02E08'),discovery.library_context(self.fid))
        self.assertEqual(result['episode_keys'],['EPISODE:S1:8'])
        from app.core.download_assignment import next_search
        downloads._save_jobs([dict(id='mapped',fid=self.fid,assignment_version=1,episode_keys=['EPISODE:S1:7'],source_episodes=[7],season=1,continuous=False,release_title='[Judas] Alternate S02E07',group='Judas',title='Alternate',desired='running')])
        self.assertEqual(next_search(self.fid)['query'],'[Judas] Alternate S02E08')

    def test_interruption_after_first_file_resumes_without_duplicate_history(self):
        a,b,rows=self.fixture();plan=season_file_moves.preview(self.fid,[r['id'] for r in rows],1)
        with self.assertRaises(InterruptedError):season_file_moves.apply(plan,Mock(side_effect=[False,True]))
        self.assertFalse(Path(plan['rows'][0]['source']).exists());self.assertTrue(Path(plan['rows'][1]['source']).exists())
        season_file_moves.apply(season_file_moves.pending(self.fid))
        with closing(db.get_connection()) as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM episode_history').fetchone()[0],2)

    def test_encoder_offsets_do_not_cross_to_another_numbering_pattern(self):
        discovery.remember_confirmed_alias(self.fid,dict(title='[Judas] Alternate - 177',group='Judas',season=2,continuous=False,episodes=[7],source_episodes=[177]))
        context=discovery.library_context(self.fid,2,continuous=False)
        self.assertEqual(discovery.classify(dict(title='[ASW] Alternate S02E08'),context)['status'],'Match Uncertain')
        discovery.remember_confirmed_alias(self.fid,dict(title='[ASW] Alternate S02E08',group='ASW',season=2,continuous=False,episodes=[8],source_episodes=[8]))
        context=discovery.library_context(self.fid,2,continuous=False)
        self.assertEqual(discovery.classify(dict(title='[Judas] Alternate - 178'),context)['episode_keys'],['EPISODE:S2:8'])
        self.assertEqual(discovery.classify(dict(title='[ASW] Alternate S02E09'),context)['episode_keys'],['EPISODE:S2:9'])

    def test_unified_confirmation_defaults_off_and_review_does_not_reconfirm(self):
        from app.ui.pages.release_search_page import ReleaseSearchPage,ConfirmCoverage,DownloadReview
        page=ReleaseSearchPage(None,self.fid);self.addCleanup(page.deleteLater)
        self.assertIn('Confirm season / episodes',page.action_buttons)
        self.assertNotIn('Confirm highlighted match',page.action_buttons)
        context=discovery.library_context(self.fid,2,continuous=False)
        entry=dict(title='Release - 7',identity='one',source='Test',episodes=[7],episode_keys=['EPISODE:S2:7'],season=2,continuous=True,match_confirmed=True,status='Missing — Release Found')
        dialog=ConfirmCoverage(None,entry,context,lambda _:None);self.addCleanup(dialog.deleteLater)
        self.assertFalse(dialog.continuous.isChecked())
        page.context=context;page.results=[entry];page.model.selected={'one'}
        with patch('app.ui.pages.release_search_page.navigate') as navigate:page.review()
        review=navigate.call_args.args[0];self.assertIsInstance(review,DownloadReview);review.deleteLater();page.reject()

    def test_remembering_title_updates_unselected_matching_results_immediately(self):
        from app.ui.pages.release_search_page import ReleaseSearchPage
        page=ReleaseSearchPage(None,self.fid);self.addCleanup(page.deleteLater)
        page.context=discovery.library_context(self.fid,2,continuous=False)
        page.results=[discovery.classify(dict(title=f'[ASW] Encoder Alternate - {n}',identity=str(n),source='Test'),page.context) for n in (7,8)]
        page.model.selected={'7'}
        with patch('app.ui.pages.release_search_page.navigate') as navigate:page.confirm_match()
        dialog=navigate.call_args.args[0];self.addCleanup(dialog.deleteLater);dialog.remember.setChecked(True);dialog.apply()
        second=next(r for r in page.results if r['identity']=='8')
        self.assertNotEqual(second['status'],'Match Uncertain');self.assertEqual(second['episode_keys'],['EPISODE:S2:8']);page.reject()

    def test_completed_stop_is_idempotent_and_never_restarts_engine(self):
        job=dict(id='done',fid=self.fid,engine='builtin',indexed=True,desired='cancelled',status='Completed',progress=1)
        downloads._save_jobs([job])
        with patch('app.core.builtin_torrents.engine') as engine:
            download_queue.action('done','stop');download_queue.action('done','stop')
        engine.assert_not_called();self.assertEqual(download_queue.status(downloads.jobs()[0]),'Completed')

    def test_completed_stop_detaches_active_engine_and_keeps_files(self):
        job=dict(id='done',fid=self.fid,engine='builtin',indexed=True,desired='running',status='Complete',progress=1)
        downloads._save_jobs([job]);db.set_state('downloads.settings',json.dumps({**downloads.DEFAULTS,'enabled':True,'seed_completed':False}))
        adapter=Mock();adapter.snapshot.return_value={'status':'Cancelled — files kept'}
        with patch('app.core.builtin_torrents.active',return_value=True),patch('app.core.builtin_torrents.engine',return_value=adapter):download_queue.action('done','stop')
        self.assertEqual(download_queue.status(downloads.jobs()[0]),'Completed');self.assertEqual(adapter.snapshot.call_count,1)

    def fixture(self):
        db.set_continuous_episodes(self.fid,False)
        root=Path(self.temp.name)/'library';root.mkdir();db.add_watched_directory(str(root))
        anime=root/'One Piece';one=anime/'Season 2';two=anime/'Other folder';one.mkdir(parents=True);two.mkdir()
        a=one/'Anime - 07.mkv';b=two/'Anime - 08.mkv';a.write_bytes(b'a');b.write_bytes(b'bb')
        for folder,file in [(one,a),(two,b)]:db.upsert_season(dict(franchise_id=self.fid,season_number=2,relation_type='SEASON',title_display=folder.name,season_folder_path=str(folder),video_files_json=json.dumps([file.name]),storage_state='ON_DISK'))
        db.update_franchise_field(self.fid,'root_folder_path',str(anime));identity.track_play(str(a))
        rows=season_file_moves.files(self.fid)
        return a,b,rows

    def test_files_from_two_folders_move_into_one_season_and_keep_history(self):
        a,b,rows=self.fixture();plan=season_file_moves.preview(self.fid,[r['id'] for r in rows],1)
        self.assertTrue(a.exists());self.assertTrue(b.exists())
        result=season_file_moves.apply(plan);self.assertIn('2 episode files',result)
        self.assertFalse(a.exists());self.assertFalse(b.exists())
        folder=Path(plan['destination']['folder']);self.assertTrue((folder/a.name).exists());self.assertTrue((folder/b.name).exists())
        context=discovery.library_context(self.fid,1,continuous=False)
        self.assertEqual(set(context['local']),{'EPISODE:S1:7','EPISODE:S1:8'})
        with closing(db.get_connection()) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM episode_history').fetchone()[0],2)
            self.assertEqual({r[0] for r in conn.execute('SELECT s.season_number FROM physical_files f JOIN seasons s ON s.id=f.season_id')},{1})
        self.assertIsNone(season_file_moves.pending(self.fid))

    def test_collision_aborts_before_moving_any_file(self):
        a,b,rows=self.fixture();dest=Path(downloads.library_root())/'One Piece'/'Season 01';dest.mkdir();(dest/b.name).write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError,'already contains'):season_file_moves.preview(self.fid,[r['id'] for r in rows],1)
        self.assertTrue(a.exists());self.assertTrue(b.exists());self.assertEqual((dest/b.name).read_bytes(),b'keep')

    def test_stopped_move_keeps_saved_plan_for_retry(self):
        a,b,rows=self.fixture();plan=season_file_moves.preview(self.fid,[r['id'] for r in rows],1)
        with self.assertRaises(InterruptedError):season_file_moves.apply(plan,lambda:True)
        self.assertIsNotNone(season_file_moves.pending(self.fid));self.assertTrue(a.exists());self.assertTrue(b.exists())
        season_file_moves.apply(season_file_moves.pending(self.fid));self.assertIsNone(season_file_moves.pending(self.fid))

    def test_move_only_selected_file_and_leave_other_episode_in_place(self):
        a,b,rows=self.fixture();chosen=next(r for r in rows if identity.path_key(r['path'])==identity.path_key(a))
        season_file_moves.apply(season_file_moves.preview(self.fid,[chosen['id']],1))
        self.assertFalse(a.exists());self.assertTrue(b.exists())
        with closing(db.get_connection()) as conn:
            b_season=conn.execute('SELECT s.season_number FROM physical_files f JOIN seasons s ON s.id=f.season_id JOIN file_locations l ON l.file_id=f.id WHERE l.path_key=?',(identity.path_key(b),)).fetchone()[0]
        self.assertEqual(b_season,2)

    def test_changed_file_aborts_before_any_move(self):
        a,b,rows=self.fixture();plan=season_file_moves.preview(self.fid,[r['id'] for r in rows],1)
        b.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'changed'):season_file_moves.apply(plan)
        self.assertTrue(a.exists());self.assertTrue(b.exists())

    def test_partial_download_cannot_be_moved(self):
        a,b,rows=self.fixture();downloads._save_jobs([dict(id='active',fid=self.fid,root=str(a.parent),destination=str(a.parent),indexed=False,status='Downloading',desired='running')])
        chosen=next(r for r in rows if identity.path_key(r['path'])==identity.path_key(a))
        with self.assertRaisesRegex(ValueError,'completion'):season_file_moves.preview(self.fid,[chosen['id']],1)
        self.assertTrue(a.exists())

    def test_partial_pack_move_keeps_remaining_download_reviewable(self):
        from app.core import download_library,download_inventory
        db.set_continuous_episodes(self.fid,False)
        root=Path(self.temp.name)/'library';root.mkdir();db.add_watched_directory(str(root))
        staging=Path(self.temp.name)/'download'/'Episodes';staging.mkdir(parents=True)
        a=staging/'Anime - 177.mkv';b=staging/'Anime - 178.mkv';a.write_bytes(b'a');b.write_bytes(b'bb')
        sid=db.upsert_season(dict(franchise_id=self.fid,season_number=2,relation_type='SEASON',title_display='Season 2',season_folder_path=str(staging),video_files_json=json.dumps([a.name,b.name]),storage_state='ON_DISK'))
        with closing(db.get_connection()) as conn:
            linked=conn.execute('SELECT e.id,e.original_number FROM episodes e JOIN file_episodes fe ON fe.episode_id=e.id JOIN physical_files f ON f.id=fe.file_id WHERE f.season_id=?',(sid,)).fetchall()
        for episode in linked:identity.set_episode_release(episode['id'],episode['original_number']-170)
        job=dict(id='pack',fid=self.fid,engine='builtin',root=str(staging.parent),destination=str(staging),season=2,continuous=False,indexed=True,status='Indexed',desired='cancelled',assignment_version=1,
            episode_keys=['EPISODE:S2:7','EPISODE:S2:8'],source_episodes=[177,178],verified_files=[dict(path=str(a),size=1),dict(path=str(b),size=2)],download_files=[dict(name=a.name,size=1),dict(name=b.name,size=2)])
        downloads._save_jobs([job]);chosen=next(r for r in season_file_moves.files(self.fid) if identity.path_key(r['path'])==identity.path_key(a))
        plan=season_file_moves.preview(self.fid,[chosen['id']],1);season_file_moves.apply(plan)
        current=downloads.jobs()[0];self.assertEqual(current['episode_keys'],['EPISODE:S1:7','EPISODE:S2:8'])
        self.assertTrue(download_inventory.Snapshot().can_scan_library(plan['rows'][0]['target']))
        remaining=download_library.preview();self.assertEqual(len(remaining['rows']),1);self.assertEqual(Path(remaining['rows'][0]['source']).name,b.name)

    def test_completed_after_stop_is_recorded_as_completed(self):
        a,b,rows=self.fixture()
        with closing(db.get_connection()) as conn:series=conn.execute('SELECT id FROM library_series WHERE franchise_id=?',(self.fid,)).fetchone()[0]
        job=dict(fid=self.fid,series_id=series,root=str(a.parent),desired='stopped')
        with patch('app.core.scanner._update_on_disk_info'):downloads._index_completed(job,[a])
        self.assertTrue(job['transfer_stopped']);self.assertEqual(job['desired'],'cancelled');self.assertEqual(download_queue.status(job),'Completed')

    def test_episode_display_uses_assigned_season_instead_of_original_filename(self):
        from app.ui.pages.episode_page import EpisodeWorker
        db.set_continuous_episodes(self.fid,False)
        root=Path(self.temp.name)/'library';root.mkdir();db.add_watched_directory(str(root))
        source=root/'One Piece'/'Season 2';source.mkdir(parents=True)
        file=source/'Anime S02E07.mkv';file.write_bytes(b'video')
        db.upsert_season(dict(franchise_id=self.fid,season_number=2,relation_type='SEASON',title_display='Season 2',season_folder_path=str(source),video_files_json=json.dumps([file.name]),storage_state='ON_DISK'))
        row=season_file_moves.files(self.fid)[0];season_file_moves.apply(season_file_moves.preview(self.fid,[row['id']],1))
        rows=[];worker=EpisodeWorker(self.fid);worker.ready.connect(lambda values,warnings:rows.extend(values));worker.run();worker.deleteLater()
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['name'],'Anime S02E07.mkv');self.assertEqual(rows[0]['subtitle'],'S1 / Episode')

    def test_edit_season_button_opens_reviewed_physical_move_flow(self):
        from app.ui.dialogs.season_numbers import SeasonNumbers
        from app.ui.components.message_boxes import AppMessageBox
        a,b,_=self.fixture();parent=SeasonNumbers(self.fid);self.addCleanup(parent.deleteLater)
        with patch('app.ui.navigation.navigate') as navigate:parent.move_files()
        dialog=navigate.call_args.args[0];self.addCleanup(dialog.deleteLater)
        worker=dialog._apply_worker
        if worker:worker.wait(5000)
        self.app.processEvents();self.assertEqual(dialog.list.count(),2)
        dialog.add_season_button(1);dialog.season.setValue(1);dialog.select_all();dialog.review();worker=dialog._apply_worker
        if worker:worker.wait(5000)
        self.app.processEvents();self.assertIsNotNone(dialog.plan);self.assertTrue(a.exists())
        with patch.object(AppMessageBox,'question',return_value=AppMessageBox.Yes):dialog.review()
        worker=dialog._apply_worker
        if worker:worker.wait(5000)
        self.app.processEvents();self.assertFalse(a.exists());self.assertFalse(b.exists())
