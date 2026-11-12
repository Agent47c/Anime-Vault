"""Home presentation, preserved actions and real-data adapters."""
import base64,json,threading,time,unittest,sys,uuid
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from PyQt5.QtCore import Qt,QEvent,QPoint,QTimer,QObject
from PyQt5.QtGui import QKeyEvent,QPalette,QContextMenuEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QMainWindow,QLineEdit,QCheckBox,QPushButton,QLabel
import test_ui_regressions as support
from app import db
from app.core import playback,identity
from app.core.home_facts import download_badges

class HomeTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def episode(self):
        folder=Path(self.temp.name)/'Season 1';folder.mkdir(exist_ok=True);path=folder/'Example S01E01.mkv';path.write_bytes(b'example video')
        sid=db.upsert_season(dict(franchise_id=self.fid,season_number=1,title_display='Example',season_folder_path=str(folder),storage_state='ON_DISK',video_files_json=json.dumps([path.name])))
        identity.sync_inventory(sid);identity.track_play(str(path));return path,playback.episode_ids(path)
    def wait(self):
        from app.ui.io_task import running
        end=time.monotonic()+5
        while running() and time.monotonic()<end:QTest.qWait(10)
    def test_home_header_preserves_routes_actions_and_omits_profile(self):
        from app.ui.components.home_header import HomeHeader
        host=QMainWindow();host.top_search_input=QLineEdit();host.coll_counts={};host._on_nav_clicked=Mock();host._on_collection_clicked=Mock();host._request_refresh=Mock();host._open_custom_entry_dialog=Mock();host._open_watched_import_dialog=Mock()
        header=HomeHeader(host);self.assertEqual(set(header.tabs),{0,1,2,3,4,5})
        header.tabs[5].click();host._on_nav_clicked.assert_called_once_with(5)
        header.search.setText('Example');self.assertEqual(host.top_search_input.text(),'Example')
        labels=[action.text() for action in header.options.menu().actions()]
        self.assertFalse(any('Select multiple' in label for label in labels));self.assertIn('Settings',labels)
        for label in ('Add anime','Import watched TXT list','Watched, removed','Refresh local library','Refresh and sync with internet'):self.assertIn(label,labels)
        self.assertFalse(any('profile' in w.accessibleName().lower() for w in header.findChildren(QPushButton)))
        header.resize(1280,76);header.show();self.app.processEvents()
        self.assertLessEqual(abs(header.capsule.geometry().center().x()-header.rect().center().x()),1)
        from app.ui.home_style import colors
        self.assertEqual(header.search.palette().color(QPalette.PlaceholderText).name(),colors()['muted'])
        host.library_page=SimpleNamespace(set_selection_mode=Mock(),_selection_mode=False)
        header.select_action.trigger();host.library_page.set_selection_mode.assert_called_once_with(True)
        header.deleteLater();host.deleteLater()

    def test_constructing_posters_never_shows_a_temporary_native_window(self):
        from app.ui.components.home_poster import HomePosterCard
        from PyQt5.QtWidgets import QWidget
        shown=[]
        class Watch(QObject):
            def eventFilter(self,widget,event):
                if event.type()==QEvent.Show and isinstance(widget,QWidget) and widget.isWindow():shown.append(widget.objectName())
                return False
        watcher=Watch();self.app.installEventFilter(watcher)
        try:
            cards=[HomePosterCard(db.get_franchise(self.fid)) for _ in range(8)]
            self.assertEqual(shown,[])
            for card in cards:card.deleteLater()
        finally:self.app.removeEventFilter(watcher)

    def test_right_click_select_enters_selection_mode_without_opening_details(self):
        from app.ui.pages.library_page import LibraryPage
        from PyQt5.QtWidgets import QApplication
        page=LibraryPage();page._set_view_mode('grid');page.resize(1280,900);page.show();self.app.processEvents()
        card=page._cards[0];chosen=[];page.card_clicked.connect(chosen.append)
        def select():
            menu=QApplication.activePopupWidget()
            next(action for action in menu.actions() if action.text()=='Select').trigger();menu.close()
        QTimer.singleShot(0,select)
        card.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Mouse,QPoint(10,10),card.mapToGlobal(QPoint(10,10))))
        self.assertTrue(page._selection_mode);self.assertTrue(card.selection_box.isVisible())
        self.assertIn(card.franchise_id,page.selected_fids);self.assertEqual(chosen,[])
        self.wait();page.hide();page.deleteLater()

    def test_schedule_counts_and_preview_alignment_and_navigation(self):
        from datetime import date
        from app.ui.components.home_day import HomeDay
        from PyQt5.QtWidgets import QLabel,QPushButton
        entries=[dict(title='A very long anime title for testing the release preview width and alignment',episode=19,time='20:26',fid=1),dict(title='Second anime',episode=2,time='21:00',fid=2)]
        day=HomeDay(date.today(),True,'',entries);day.resize(180,110);day.show();self.app.processEvents()
        self.assertEqual(day.release_button.findChild(QLabel,'airing_release_title').text(),'2 anime releases')
        self.assertEqual(day.release_button.findChild(QLabel,'airing_release_time').text(),'')
        selected=[];day.selected.connect(selected.append);day.release_button._show_preview();self.app.processEvents()
        popup=day.release_button.preview;rows=popup.findChildren(QPushButton,'airing_preview_item')
        self.assertEqual(len(rows),2)
        for row in rows:
            self.assertGreaterEqual(row.height(),72)
            for label in row.findChildren(QLabel):
                self.assertLessEqual(label.mapTo(row,QPoint(0,0)).x()+label.width(),row.width())
                self.assertLessEqual(label.mapTo(row,QPoint(0,0)).y()+label.height(),row.height())
        QTest.mouseClick(rows[1],Qt.LeftButton);self.assertEqual(selected,[entries[1]])
        day.hide();day.deleteLater()
        single=HomeDay(date.today(),False,'',entries[:1]);single.resize(180,110);single.show();self.app.processEvents()
        self.assertIn('A very long',single.release_button.findChild(QLabel,'airing_release_title').toolTip())
        single.hide();single.deleteLater()
    def test_poster_checkbox_selects_batch_without_opening_details(self):
        from app.ui.pages.library_page import LibraryPage
        page=LibraryPage();page.resize(1280,900);page.show();self.app.processEvents();chosen=[];page.card_clicked.connect(chosen.append)
        card=page._cards[0];self.assertFalse(card.selection_box.isVisible())
        page.set_selection_mode(True);self.assertTrue(card.selection_box.isVisible());QTest.mouseClick(card.selection_box,Qt.LeftButton)
        self.assertIn(card.franchise_id,page.selected_fids);self.assertEqual(chosen,[]);self.assertTrue(page.batch_bar.isVisible())
        page._clear_selection();self.assertFalse(card.selection_box.isChecked())
        self.assertFalse(card.selection_box.isVisible());self.assertFalse(page._selection_mode)
        self.assertEqual(page.airing_week.count(),7)
        self.assertEqual({page.airing_week.getItemPosition(i)[0] for i in range(7)},{0})
        # Keyboard selection uses the same path as right-click → Select.
        QTest.keyClick(card,Qt.Key_Space);self.assertTrue(page._selection_mode)
        self.assertIn(card.franchise_id,page.selected_fids)
        page._set_view_mode('compact');self.assertFalse(page.compact_table.isColumnHidden(0))
        page._clear_selection();self.assertTrue(page.compact_table.isColumnHidden(0))
        self.wait();page.hide();page.deleteLater()
    def test_download_badges_include_group_members_but_not_other_titles(self):
        groups=[dict(id=1,series_member_ids=[1,2]),dict(id=3,series_member_ids=[3])]
        badges=download_badges(groups,[dict(fid=2,progress=.82,desired='running',status='Downloading'),dict(fid=3,progress=1,indexed=True)])
        self.assertEqual(badges[1]['label'],'DL 82%');self.assertNotIn(3,badges)
    def test_space_ignores_search_and_controls_but_toggles_from_home(self):
        from app.ui.playback import HomePlaybackKeys
        window=QMainWindow();window.library_page=SimpleNamespace(isVisible=lambda:True);window.isActiveWindow=lambda:True
        player=Mock();keys=HomePlaybackKeys(window,player);event=QKeyEvent(QEvent.KeyPress,Qt.Key_Space,Qt.NoModifier)
        with patch('PyQt5.QtWidgets.QApplication.focusWidget',return_value=QLineEdit()):self.assertFalse(keys.eventFilter(window,event))
        with patch('PyQt5.QtWidgets.QApplication.focusWidget',return_value=None):self.assertTrue(keys.eventFilter(window,event))
        player.toggle.assert_called_once()
        window.library_page.isVisible=lambda:False
        with patch('PyQt5.QtWidgets.QApplication.focusWidget',return_value=None):self.assertTrue(keys.eventFilter(window,event))
        self.assertEqual(player.toggle.call_count,2);window.deleteLater()
    def test_saved_progress_remains_attached_to_episode_after_a_move(self):
        path,ids=self.episode();playback.save_progress(ids,300,1200)
        target=path.with_name('Renamed S01E01.mkv');path.rename(target)
        with closing(db.get_connection()) as conn,conn:identity.relocate(conn,str(path),str(target))
        self.assertEqual(playback.episode_ids(target),ids);saved=playback.last_progress()
        self.assertEqual(saved['position'],300);self.assertEqual(saved['duration'],1200);self.assertEqual(Path(saved['path']),target)
        with closing(db.get_connection()) as conn:self.assertEqual(conn.execute('SELECT position_seconds FROM episode_history WHERE episode_id=? AND event=?',(ids[0],'PROGRESS')).fetchone()[0],300)
    def test_resume_arguments_and_default_player_capability(self):
        path,ids=self.episode();playback.save_progress(ids,300,1200)
        vlc=playback.launch_session('vlc',path);mpv=playback.launch_session('mpv',path)
        self.assertTrue('--http-host=127.0.0.1' in vlc.arguments);self.assertEqual(float(next(a.split('=',1)[1] for a in vlc.arguments if a.startswith('--start-time='))),300)
        self.assertTrue(any(a.startswith('--input-ipc-server=') for a in mpv.arguments));self.assertEqual(float(next(a.split('=',1)[1] for a in mpv.arguments if a.startswith('--start='))),300)
        self.assertIsNone(playback.launch_session('default',path))
        self.assertFalse(any(a.startswith('--start=') for a in playback.Session('mpv',path,resume=False).arguments))
    def test_vlc_real_loopback_transport_reads_and_toggles_only_owned_session(self):
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        path,ids=self.episode();session=playback.Session('vlc',path);session.process=Mock();session.process.poll.return_value=None
        state={'paused':False,'id':1};auth='Basic '+base64.b64encode((':'+session.password).encode()).decode()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                if self.headers.get('Authorization')!=auth:self.send_error(401);return
                if 'pl_pause' in self.path:state['paused']=not state['paused']
                body=json.dumps(dict(time=120,length=1440,currentplid=state['id'],state='paused' if state['paused'] else 'playing')).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();session.port=server.server_port
        try:
            self.assertEqual(session.poll()['position'],120);session.toggle();self.assertTrue(session.poll()['paused'])
            self.assertEqual(playback.saved_progress(ids)['duration'],1440)
            state['id']=2
            with self.assertRaises(playback.MediaChanged):session.poll()
        finally:server.shutdown();server.server_close();thread.join()
    def test_mpv_verifies_media_before_recording_progress(self):
        path,ids=self.episode();session=playback.Session('mpv',path);session.process=Mock();session.process.poll.return_value=None
        with patch.object(playback,'_pipe_command',side_effect=[str(path),100,1200,False]):self.assertTrue(session.poll()['active'])
        with patch.object(playback,'_pipe_command',return_value=str(path.with_name('other.mkv'))):
            with self.assertRaises(playback.MediaChanged):session.poll()
    def test_invalid_progress_is_not_persisted(self):
        path,ids=self.episode();playback.save_progress(ids,float('nan'),1200);self.assertEqual(playback.saved_progress(ids),{})

    def test_switching_sessions_retires_only_the_verified_owned_player_in_worker(self):
        previous=Mock();previous.poll.return_value={'position':10,'duration':100};previous.ids=[];previous.process.poll.return_value=None
        with patch.object(playback,'_session',previous),patch.object(playback,'_retired',[]),patch.object(playback,'last_progress',return_value={}):
            playback.attach(None);previous.process.terminate.assert_not_called()
            playback.poll();previous.process.terminate.assert_called_once()
        previous.reset_mock();previous.poll.side_effect=playback.MediaChanged('Changed outside app')
        with patch.object(playback,'_session',previous),patch.object(playback,'_retired',[]),patch.object(playback,'last_progress',return_value={}):
            playback.attach(None);playback.poll();previous.process.terminate.assert_not_called()
    def test_idle_monitor_does_not_keep_reading_the_database(self):
        from app.ui.playback import PlaybackMonitor
        player=PlaybackMonitor();player.timer.stop();player._revision=playback.revision()
        with patch.object(playback,'active',return_value=False),patch('app.ui.playback.IOTask') as worker:player.check()
        worker.assert_not_called();player.close();player.deleteLater()

    def test_large_text_wraps_filters_and_batch_without_horizontal_clipping(self):
        from app.ui.pages.library_page import LibraryPage
        from app.ui.theme import apply_theme
        db.set_state('text_scale','1.3');apply_theme(self.app,'dark')
        page=LibraryPage();page._set_view_mode('grid');page.resize(1100,800);page.show();self.app.processEvents();page._on_item_checked(self.fid,True);QTest.qWait(120)
        self.assertLessEqual(page.page_scroll.widget().width(),page.page_scroll.viewport().width()+1)
        self.assertEqual(page.airing_week.count(),7)
        self.wait();page.hide();page.deleteLater();db.set_state('text_scale','1.0');apply_theme(self.app,'dark')

    def test_hidden_home_gets_light_theme_when_shown(self):
        from app.ui.pages.library_page import LibraryPage
        from app.ui.theme import apply_theme
        page=LibraryPage();page.setProperty('animevaultThemeScope',True);page.show();self.app.processEvents();page.hide()
        apply_theme(self.app,'light');page.show();self.app.processEvents()
        self.assertIn('#f7f3f6',page.styleSheet());self.wait();page.hide();page.deleteLater();apply_theme(self.app,'dark')

    @unittest.skipUnless(sys.platform=='win32','Windows named-pipe protocol')
    def test_mpv_named_pipe_transport_round_trip(self):
        import win32file,win32pipe
        endpoint=r'\\.\pipe\animevault-test-'+uuid.uuid4().hex
        handle=win32pipe.CreateNamedPipe(endpoint,win32pipe.PIPE_ACCESS_DUPLEX,win32pipe.PIPE_TYPE_BYTE|win32pipe.PIPE_READMODE_BYTE|win32pipe.PIPE_WAIT,1,65536,65536,2000,None)
        errors=[]
        def serve():
            try:
                try:win32pipe.ConnectNamedPipe(handle,None)
                except OSError as error:
                    if error.winerror!=535:raise
                request=json.loads(win32file.ReadFile(handle,65536)[1])
                win32file.WriteFile(handle,(json.dumps(dict(request_id=request['request_id'],data=123,error='success'))+'\n').encode())
                win32file.FlushFileBuffers(handle)
            except Exception as error:errors.append(type(error).__name__)
            finally:win32file.CloseHandle(handle)
        thread=threading.Thread(target=serve,daemon=True);thread.start()
        self.assertEqual(playback._pipe_command(endpoint,['get_property','time-pos']),123)
        thread.join(timeout=2);self.assertFalse(errors);self.assertFalse(thread.is_alive())
