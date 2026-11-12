"""Connected setup/search/queue/settings regressions with isolated user data."""
import base64
import io
import json
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from datetime import datetime,timedelta
import test_ui_regressions as support
from app import db
from app.core import downloads,download_discovery as discovery,download_queue as queue,source_bridge,chrome_bridge

MAGNET='magnet:?xt=urn:btih:'+'a'*40+'&dn=Example'


class ExperienceTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def ordinary(self):
        fid=db.upsert_franchise(dict(anilist_id=9000,display_title='Dr Stone',title_romaji='Dr Stone'))
        for number in (1,2):
            folder=Path(self.temp.name)/f'Season {number}';folder.mkdir()
            name=f'Dr Stone S{number:02}E10.mkv';(folder/name).write_bytes(b'video')
            db.upsert_season(dict(franchise_id=fid,anilist_id=9000+number,title_display=f'Dr Stone Season {number}',season_number=number,season_folder_path=str(folder),video_files_json=json.dumps([name]),episodes_total=12,airing_status='FINISHED'))
        return fid

    def result(self,title,**values):return dict(title=title,magnet=MAGNET,identity='a',source='Fixture source',seeders=10,quality='1080p',group='ASW',size='1 GiB',**values)

    def test_season_identity_and_library_vs_source_availability(self):
        fid=self.ordinary();context=discovery.library_context(fid,2)
        self.assertIn('EPISODE:S2:10',context['local']);self.assertNotIn('EPISODE:S1:10',context['local'])
        owned=discovery.classify(self.result('[ASW] Dr Stone S02E10 [1080p]'),context)
        self.assertEqual(owned['status'],'In Library')
        available=discovery.classify(self.result('[ASW] Dr Stone S02E11 [1080p]'),context)
        self.assertEqual(available['status'],'Missing — Release Found')
        rows=discovery.availability_rows(context,[available])
        self.assertEqual(next(r['status'] for r in rows if r['episode']=='EPISODE:S2:12'),'Missing — No Release Found')
        wrong=discovery.classify(self.result('[ASW] Dr Stone S01E11 [1080p]'),context)
        self.assertEqual(wrong['status'],'Match Uncertain')
        different_release=discovery.classify(self.result('Dr Stone New World - 01'),discovery.library_context(fid,1))
        self.assertEqual(different_release['status'],'Match Uncertain')

    def test_batches_and_pending_do_not_accidentally_redownload_owned_episodes(self):
        fid=self.ordinary();context=discovery.library_context(fid,2)
        batch=discovery.classify(self.result('Dr Stone S02 [01-12] [1080p]'),context)
        self.assertEqual(len(batch['episode_keys']),12)
        self.assertEqual(discovery.missing_plan(context,[batch])[0],[])
        downloads._save_jobs([dict(id='queued',fid=fid,status='Downloading',destination=self.temp.name,episode_keys=['EPISODE:S2:11'])])
        context=discovery.library_context(fid,2)
        queued=discovery.classify(self.result('Dr Stone S02E11'),context)
        self.assertEqual(queued['status'],'Downloading or Queued')
        self.assertNotIn('EPISODE:S2:11',context['missing'])

    def test_continuing_series_aggregates_arcs_and_excludes_future_boundary(self):
        for index,numbers in enumerate((range(1,63),[63,65],[66,67])):
            folder=Path(self.temp.name)/f'Arc {index}';folder.mkdir()
            names=[f'One Piece - {n:04}.mkv' for n in numbers]
            for name in names:(folder/name).write_bytes(b'video')
            db.upsert_season(dict(franchise_id=self.fid,title_display=f'One Piece arc {index}',season_number=index+1,season_folder_path=str(folder),video_files_json=json.dumps(names),airing_status='RELEASING',next_airing_ep=68,next_airing_at=int((datetime.now()+timedelta(days=2)).timestamp())))
        context=discovery.library_context(self.fid)
        self.assertEqual(context['missing'],['EPISODE:ABS:64'])
        future=discovery.classify(self.result('One Piece - 0068 [1080p]'),context)
        self.assertEqual(future['status'],'Match Uncertain')

    def test_review_revalidates_duplicates_before_any_submission(self):
        fid=self.ordinary();context=discovery.library_context(fid,2)
        row=discovery.classify(self.result('Dr Stone S02E11'),context)
        with patch.object(downloads,'add_download') as add:
            with self.assertRaises(ValueError):discovery.submit(fid,[row,row])
            add.assert_not_called()
        downloads._save_jobs([dict(id='queued',fid=fid,status='Paused',destination=self.temp.name,episode_keys=row['episode_keys'])])
        with patch.object(downloads,'add_download') as add:
            with self.assertRaises(ValueError):discovery.submit(fid,[row])
            add.assert_not_called()

    def test_bridge_command_result_roundtrip_and_origin_rejection(self):
        source_bridge.heartbeat('https://nyaa.si',True)
        identifier=source_bridge.enqueue('https://nyaa.si/?q=Example','Nyaa')
        self.assertEqual(source_bridge.claim('https://nyaa.si')['id'],identifier)
        with self.assertRaises(ValueError):source_bridge.finish(identifier,'https://other.example',[self.result('Example - 01')])
        source_bridge.finish(identifier,'https://nyaa.si',[self.result('Example - 01')])
        rows=source_bridge.wait(identifier,timeout=.2)
        self.assertEqual(rows[0]['title'],'Example - 01');self.assertEqual(rows[0]['source'],'Nyaa')
        identifier=source_bridge.enqueue('https://nyaa.si/?q=Other')
        with self.assertRaises(InterruptedError):source_bridge.wait(identifier,cancelled=lambda:True)

    def test_streaming_native_host_delivers_search_without_launching_another_app(self):
        db.set_state('chrome.capture_extension','a'*32)
        source_bridge.heartbeat('https://nyaa.si',True)
        identifier=source_bridge.enqueue('https://nyaa.si/?q=Example','Nyaa')
        incoming=io.BytesIO();outgoing=io.BytesIO()
        chrome_bridge.write_message(incoming,dict(action='search_result',id=identifier,results=[self.result('Example - 01')]))
        incoming.seek(0)
        with patch.object(chrome_bridge,'launch_desktop') as launch:
            self.assertEqual(chrome_bridge.connected_loop(dict(action='connect',site='https://nyaa.si',enabled=True),'chrome-extension://'+'a'*32+'/',incoming,outgoing),0)
            launch.assert_not_called()
        outgoing.seek(0);self.assertEqual(chrome_bridge.read_message(outgoing)['action'],'connected')
        self.assertEqual(chrome_bridge.read_message(outgoing)['id'],identifier)
        self.assertEqual(source_bridge.wait(identifier,timeout=.2)[0]['title'],'Example - 01')

    def test_setup_reports_disconnected_extension_and_tests_actual_folder(self):
        from app.core.download_setup import checks
        destination=Path(self.temp.name)/'downloads'
        downloads.save_settings(dict(engine='builtin',destination=str(destination)))
        with patch.object(downloads,'test_connection',return_value='Built-in ready'):
            result=checks()
        self.assertTrue(result['folder'].startswith('Ready:'))
        self.assertTrue(result['extension'].startswith('Needs attention:'))
        self.assertEqual(list(destination.iterdir()),[])

    def test_queue_distinguishes_unfinished_from_missing_completed_files(self):
        file=Path(self.temp.name)/'episode.mkv';file.write_bytes(b'video')
        item=dict(id='one',fid=self.fid,title='One Piece',destination=self.temp.name,status='Complete',indexed=True,progress=1,verified_files=[dict(path=str(file),size=5)])
        downloads._save_jobs([item]);self.assertEqual(queue.status(queue.snapshot()[0]),'Completed')
        file.unlink();item['integrity_checked']=0;downloads._save_jobs([item])
        self.assertEqual(queue.status(queue.snapshot()[0]),'Incomplete or missing files')
        unfinished=dict(item,indexed=False,status='Downloading',progress=.2,integrity_missing=False)
        self.assertEqual(queue.status(unfinished),'Downloading')
        db.init_db();self.assertEqual(downloads.jobs()[0]['id'],'one')

    def test_removing_entry_keeps_files_and_qbit_delete_is_never_requested(self):
        file=Path(self.temp.name)/'keep.mkv';file.write_bytes(b'video')
        item=dict(id='one',fid=self.fid,title='One Piece',destination=self.temp.name,status='Paused',engine='builtin',desired='paused')
        downloads._save_jobs([item])
        queue.action('one','remove')
        self.assertEqual(downloads.jobs(),[]);self.assertEqual(file.read_bytes(),b'video')

    def test_legacy_remove_never_contacts_external_client_and_keeps_files(self):
        file=Path(self.temp.name)/'keep.mkv';file.write_bytes(b'video')
        item=dict(id='one',fid=self.fid,title='One Piece',destination=self.temp.name,status='Paused',engine='qbittorrent',tag='AnimeVault-one')
        downloads._save_jobs([item])
        with patch('requests.sessions.Session.request',side_effect=AssertionError('External API must not be called')):
            queue.action('one','remove')
        self.assertEqual(downloads.jobs(),[]);self.assertEqual(file.read_bytes(),b'video')

    def test_explicit_download_file_recycle_uses_journal_and_keeps_record(self):
        import shutil
        identifier='a'*32;root=Path(self.temp.name)/('Anime-'+identifier[:10]);target=root/'Episodes';target.mkdir(parents=True)
        file=target/'Episode 01.mkv';file.write_bytes(b'video')
        extra=target/'personal-notes.txt';extra.write_text('Keep this')
        item=dict(id=identifier,fid=self.fid,title='One Piece',root=str(root),destination=str(target),status='Paused',engine='builtin',desired='cancelled',download_files=[dict(name=file.name,size=5)])
        downloads._save_jobs([item])
        recycle=Path(self.temp.name)/'recycled';recycle.mkdir()
        with patch('app.core.recycle_bin.send2trash',side_effect=lambda path:shutil.move(path,str(recycle/Path(path).name))):
            queue.recycle_files(identifier)
        self.assertFalse(file.exists());self.assertEqual((recycle/file.name).read_bytes(),b'video')
        self.assertEqual(extra.read_text(),'Keep this')
        self.assertEqual(downloads.jobs()[0]['id'],identifier)
        connection=db.get_connection()
        try:self.assertEqual(connection.execute("SELECT status FROM file_operations WHERE kind='RECYCLE'").fetchone()[0],'COMPLETED')
        finally:connection.close()

    def test_player_language_preferences_reach_only_supported_player_arguments(self):
        from app import config
        video=Path(self.temp.name)/'Episode 01.mkv';video.write_bytes(b'video')
        config.set_media_player_type('mpv')
        for key,value in [('playback.slang','eng'),('playback.alang','jpn'),('playback.subtitles','0'),('playback.fullscreen','1')]:db.set_state(key,value)
        with patch.object(config,'set_last_episode_path'),patch.object(config,'detect_installed_players',return_value={'mpv':'mpv.exe'}),patch('subprocess.Popen') as launch:
            config.launch_video_file(str(video))
            arguments=launch.call_args.args[0]
            self.assertIn('--slang=eng',arguments);self.assertIn('--alang=jpn',arguments);self.assertIn('--sid=no',arguments);self.assertIn('--fullscreen',arguments)

    def test_partial_retry_files_are_not_marked_in_library_until_reindexed(self):
        fid=self.ordinary();seasons=db.get_seasons_for_franchise(fid)
        second=next(s for s in seasons if s['season_number']==2)
        downloads._save_jobs([dict(id='one',fid=fid,status='Downloading',destination=second['season_folder_path'],episode_keys=['EPISODE:S2:10'])])
        context=discovery.library_context(fid,2)
        self.assertNotIn('EPISODE:S2:10',context['local']);self.assertIn('EPISODE:S2:10',context['pending'])

    def test_folder_scans_do_not_import_unverified_download_payloads(self):
        from app.core.scanner import scan_watched_directories
        watched=Path(self.temp.name)/'watched';folder=watched/'Partial-aaaaaaaaaa';target=folder/'Episodes';target.mkdir(parents=True)
        (target/'Partial Anime - 01.mkv').write_bytes(b'partial')
        db.add_watched_directory(str(watched))
        downloads._save_jobs([dict(id='a'*32,fid=self.fid,title='One Piece',engine='builtin',root=str(folder),destination=str(target),status='Downloading')])
        result=scan_watched_directories(allow_network=False)
        self.assertEqual(result['new'],0);self.assertEqual(len(db.get_all_franchises()),1)
        queue.action('a'*32,'remove')
        result=scan_watched_directories(allow_network=False)
        self.assertEqual(result['new'],0)

    def test_mag_hash_is_canonical_between_base32_and_hex(self):
        from app.core.magnet_capture import validate
        content=bytes.fromhex('ab'*20)
        hex_link='magnet:?xt=urn:btih:'+content.hex()
        base32_link='magnet:?xt=urn:btih:'+base64.b32encode(content).decode()
        self.assertEqual(validate(hex_link)['identity'],validate(base32_link)['identity'])

    def test_settings_categories_and_download_preferences_persist(self):
        from app.ui.pages.settings_page import SettingsPage
        page=SettingsPage();self.assertEqual(page.tabs.count(),8)
        self.assertEqual(len(page._tab_layouts),8)
        page.download_config.engine.setCurrentIndex(page.download_config.engine.findData('builtin'))
        page.download_config.controls['destination'].setText(self.temp.name)
        downloads.save_settings(page.download_config._config())
        page.deleteLater();self.app.processEvents()
        other=SettingsPage();self.assertEqual(other.download_config.engine.currentData(),'builtin')
        self.assertEqual(other.download_config.controls['destination'].text(),self.temp.name)
        other.deleteLater()

    def test_wal_backup_includes_committed_rows_and_restore_keeps_safety_copy(self):
        backup_folder=Path(self.temp.name)/'backups';db.set_state('backup_directory',str(backup_folder))
        connection=db.get_connection()
        try:
            connection.execute('UPDATE franchises SET user_notes=? WHERE id=?',('Before',self.fid));connection.commit()
            path=db.backup_database()
            from contextlib import closing
            with closing(sqlite3.connect(path)) as backup:self.assertEqual(backup.execute('SELECT user_notes FROM franchises WHERE id=?',(self.fid,)).fetchone()[0],'Before')
            db.update_franchise_field(self.fid,'user_notes','After')
            db.restore_database(path)
            self.assertEqual(db.get_franchise(self.fid)['user_notes'],'Before')
            self.assertGreaterEqual(len(list(backup_folder.glob('*.db'))),2)
        finally:connection.close()

    def test_import_list_opt_in_and_change_detection_preserve_notes(self):
        from app.core import import_lists
        path=Path(self.temp.name)/'watched.txt';path.write_text('One Piece\nNew Unmatched Anime\n',encoding='utf-8')
        import_lists.save([dict(path=str(path),enabled=False,status='WATCHING')])
        self.assertEqual(import_lists.refresh(),0)
        db.update_franchise_field(self.fid,'user_notes','Personal note')
        import_lists.save([dict(path=str(path),enabled=True,status='WATCHING')])
        self.assertEqual(import_lists.refresh(),2)
        self.assertEqual(import_lists.refresh(),0)
        self.assertEqual(db.get_franchise(self.fid)['user_notes'],'Personal note')
        record=db.find_franchise_by_title('New Unmatched Anime')
        self.assertTrue(record['is_custom']);self.assertTrue(record['needs_review'])
        db.update_franchise_field(record['id'],'display_title','My corrected title')
        db.update_franchise_field(record['id'],'title_romaji','My corrected title')
        before=len(db.get_all_franchises())
        import_lists.refresh(force=True)
        self.assertEqual(len(db.get_all_franchises()),before)
        self.assertEqual(db.get_franchise(record['id'])['display_title'],'My corrected title')

    def test_source_extension_parser_and_browser_flow(self):
        import shutil,subprocess
        if not shutil.which('node'):self.skipTest('Node is needed for extension tests')
        result=subprocess.run(['node','--test','browser-extension/tests/search.test.js'],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_nested_review_drawer_returns_to_live_search_page(self):
        from PyQt5.QtWidgets import QWidget,QStackedWidget,QVBoxLayout
        from app.ui.pages.release_search_page import ReleaseSearchPage,ConfirmCoverage
        from app.ui.navigation import navigate
        host=QWidget();host.stacked_widget=QStackedWidget(host);QVBoxLayout(host).addWidget(host.stacked_widget)
        original=QWidget();host.stacked_widget.addWidget(original);host.resize(1280,800);host.show()
        fid=self.ordinary();search=ReleaseSearchPage(host,fid);navigate(search)
        search_page=host.stacked_widget.currentWidget()
        context=discovery.library_context(fid,2);entry=discovery.classify(self.result('Uncertain release'),context)
        confirm=ConfirmCoverage(search,entry,context,lambda _:None);navigate(confirm)
        self.assertFalse(search_page._nav_completed)
        confirm.reject();self.assertIs(host.stacked_widget.currentWidget(),search_page)
        search.reject();host.hide();host.deleteLater()

    def test_generated_source_result_to_real_native_library_import(self):
        import subprocess,sys
        result=subprocess.run([sys.executable,'scripts/check_download_workflow.py'],capture_output=True,text=True,timeout=35)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
