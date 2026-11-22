"""Drive discovery, remembered searches and truthful saved player progress."""
import ctypes
import json
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from PyQt5.QtCore import Qt
import test_ui_regressions as support
from app import db
from app.core import duplicates,download_discovery as discovery,download_queries,downloads,playback,potplayer
from app.core.storage import format_rate


class DownloadSearchProgressFixes(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def folder(self):
        folder=Path(self.temp.name)/'Season 02';folder.mkdir()
        db.upsert_season(dict(franchise_id=self.fid,season_number=2,season_folder_path=str(folder),
                             title_display='Season 02',video_files_json='[]',storage_state='MISSING'))
        return folder

    def test_drive_scan_discovers_files_with_empty_and_stale_inventory(self):
        folder=self.folder()
        for name in ('Show S02E08.mkv','Show S02E08 copy.mkv'):(folder/name).write_bytes(b'identical')
        messages=[];groups,errors=duplicates.find_duplicates(progress=messages.append)
        self.assertEqual(errors,[]);self.assertEqual(len(groups),1)
        self.assertTrue(messages[0].startswith('Scanning directory'))
        self.assertIn('2 files',messages[-1])

    def test_drive_scan_skips_incomplete_torrent_files(self):
        folder=self.folder()
        for name in ('Show S02E08.mkv','Show S02E08 copy.mkv'):(folder/name).write_bytes(b'partial')
        downloads._save_jobs([dict(id='pending',destination=str(folder),status='Downloading')])
        self.assertEqual(duplicates.find_duplicates(),([],[]))

    def test_missing_drive_folder_reports_reason(self):
        folder=self.folder();folder.rmdir()
        groups,errors=duplicates.find_duplicates()
        self.assertFalse(groups);self.assertIn('Missing directory',errors[0])

    def test_edited_query_reopens_as_selected_custom_choice(self):
        from app.ui.pages.release_search_page import ReleaseSearchPage
        page=ReleaseSearchPage(None,self.fid);self.addCleanup(page.deleteLater)
        text='[Judas] Black Clover season 02 episode 08'
        page.query.setText(text);page.reject()
        other=ReleaseSearchPage(None,self.fid);self.addCleanup(other.deleteLater)
        self.assertEqual(other.query.text(),text)
        self.assertTrue(other.title_choice.currentData(Qt.UserRole+1))
        self.assertEqual(other.title_choice.currentData(),text)
        self.assertIn('Custom search',other.title_choice.currentText());other.reject()

    def test_remembered_alias_accepts_spaced_episode_and_full_word_labels(self):
        discovery.remember_confirmed_alias(self.fid,dict(title='[Judas] Encoder Name S02 E07',
            season=2,continuous=False,episodes=[7],source_episodes=[7]))
        for title in ('[Judas] Encoder Name S02E08','[Judas] Encoder Name S02 E08',
                      '[Judas] Encoder Name Season 02 Episode 08'):
            with self.subTest(title=title):
                result=discovery.classify(dict(title=title),discovery.library_context(self.fid))
                self.assertEqual(result['episode_keys'],['EPISODE:S2:8'])
                self.assertNotEqual(result['status'],'Match Uncertain')
        wrong=discovery.classify(dict(title='[Judas] Encoder Name S03 E08'),discovery.library_context(self.fid))
        self.assertEqual(wrong['status'],'Match Uncertain')

    def test_spaced_release_uses_existing_local_episode_coverage(self):
        db.update_franchise_field(self.fid,'title_en','Black Clover')
        db.set_continuous_episodes(self.fid,False)
        folder=self.folder();name='Black Clover S02E08.mkv';(folder/name).write_bytes(b'video')
        season=db.get_seasons_for_franchise(self.fid)[0]
        db.upsert_season({**season,'video_files_json':json.dumps([name]),'storage_state':'ON_DISK'})
        result=discovery.classify(dict(title='Black Clover Season 02 Episode 08'),discovery.library_context(self.fid,2))
        self.assertEqual(result['status'],'In Library')

    def test_home_refresh_reloads_saved_position_instead_of_empty_progress(self):
        from app.ui.components.home_hero import HomeHero
        from app.ui.pages.library_page import HeroResumeCard
        hero=HomeHero();self.addCleanup(hero.deleteLater)
        hero._resume_episode=str(Path(self.temp.name)/'Example.mkv');hero.current_fid=self.fid
        with patch.object(HeroResumeCard,'refresh'),patch.object(playback,'episode_ids',return_value=[123]),\
             patch.object(playback,'saved_progress',return_value=dict(position=312,duration=1200)):
            hero.refresh()
        self.assertEqual(hero._live_playback['position'],312)
        self.assertIn('14:48 left',hero.playback_text.text())

    def session(self):
        with patch.object(playback,'episode_ids',return_value=[]):session=playback.Session('potplayer','Example.mkv')
        session.ids=[123];session.process=Mock();session.process.poll.return_value=None
        return session

    def test_zero_time_reply_never_erases_last_valid_progress(self):
        session=self.session()
        with patch.object(potplayer,'poll',return_value=(312,1200,False)),patch.object(playback,'save_progress'):
            session.poll()
        with patch.object(potplayer,'poll',return_value=(0,0,True)):
            with self.assertRaises(TimeoutError):session.poll()
        self.assertEqual(session.state['position'],312)
        session.process.poll.return_value=0
        self.assertEqual(session.poll()['duration'],1200)

    def test_transient_error_after_long_playback_keeps_session_and_position(self):
        session=self.session();session.started-=1000
        session.state=dict(position=312,duration=1200,path=session.path)
        with patch.object(playback,'_session',session),patch.object(playback,'_retired',[]),\
             patch.object(potplayer,'poll',side_effect=TimeoutError('busy')):
            state=playback.poll()
            self.assertIs(playback._session,session)
            self.assertEqual(state['position'],312);self.assertEqual(state['duration'],1200)

    def test_potplayer_uses_pointer_sized_message_result(self):
        send=Mock()
        def response(*args):args[-1]._obj.value=1200000;return 1
        send.side_effect=response
        with patch('ctypes.WinDLL',return_value=Mock(SendMessageTimeoutW=send)):
            self.assertEqual(potplayer.send(0x123456789,1024,20482),1200000)
        self.assertIs(send.argtypes[-1]._type_,ctypes.c_size_t)

    def test_rate_switches_units_at_one_mebibyte(self):
        for rate,expected in ((0,'0.00 KB/s'),(524288,'512.00 KB/s'),(1048575,'1,024.00 KB/s'),
                              (1048576,'1.00 MB/s'),(3145728,'3.00 MB/s')):
            self.assertEqual(format_rate(rate),expected)
