"""Phase 2 acceptance: temporary inventories and mocked provider traffic only."""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import unittest
from unittest.mock import patch, Mock

import test_ui_regressions as support
from app import db
from app.core import scan_state as state, anilist_client as client
from app.core.scanner import scan_watched_directories, ScanProgress
from app.core.match_evidence import context, choose


class TrustworthyScanningTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def rows(self, query, args=()):
        with closing(db.get_connection()) as conn:
            return [dict(r) for r in conn.execute(query,args)]

    def library(self, count=2):
        root = Path(self.temp.name)/'library'
        show = root/'Exact Anime'/'Season 1'
        show.mkdir(parents=True)
        for n in range(1,count+1):
            (show/f'Exact Anime S01E{n:03}.mkv').write_bytes(b'media'+str(n).encode())
        db.add_watched_directory(str(root))
        return root,show

    def scan(self):
        return scan_watched_directories(allow_network=False)

    def test_unchanged_scan_does_not_parse_sync_or_request_api(self):
        self.library()
        self.scan()
        before = self.rows('SELECT * FROM physical_files')
        with patch('app.core.scanner._update_on_disk_info',side_effect=AssertionError('unchanged index')), \
             patch('app.core.matching.auto_match_indexed_folders',side_effect=AssertionError('unchanged API')), \
             patch('app.core.scanner.is_offline',side_effect=AssertionError('network probe')):
            result = scan_watched_directories()
        self.assertEqual(result['scanned'],0)
        self.assertEqual(result['changed_files'],0)
        self.assertEqual(before,self.rows('SELECT * FROM physical_files'))

    def test_changed_file_keeps_episode_history_and_unaffected_identity(self):
        root,show = self.library()
        self.scan()
        old = self.rows('SELECT * FROM physical_files')
        with closing(db.get_connection()) as conn,conn:
            eid = conn.execute('SELECT episode_id FROM file_episodes LIMIT 1').fetchone()[0]
            conn.execute("INSERT INTO episode_history(episode_id,played_at,event) VALUES (?,1,'PLAY')",(eid,))
        (show/'Exact Anime S01E003.mkv').write_bytes(b'new episode')
        result = self.scan()
        self.assertEqual(result['changed_files'],1)
        self.assertEqual(result['updated'],1)
        self.assertEqual(len(self.rows('SELECT * FROM physical_files')),3)
        self.assertTrue(all(r in self.rows('SELECT * FROM physical_files') for r in old))
        self.assertEqual(self.rows('SELECT episode_id FROM episode_history')[0]['episode_id'],eid)

    def test_offline_and_reconnect_preserve_manifest_and_history(self):
        root,show = self.library()
        self.scan()
        baseline = self.rows('SELECT * FROM scan_files')
        hidden = root.with_name('disconnected')
        root.rename(hidden)
        result = self.scan()
        self.assertEqual(list(result['root_states'].values()),['OFFLINE'])
        self.assertEqual({r['availability'] for r in self.rows('SELECT * FROM physical_files')},{'OFFLINE'})
        self.assertEqual(baseline,self.rows('SELECT * FROM scan_files'))
        hidden.rename(root)
        self.assertEqual(self.scan()['scanned'],0)
        self.assertEqual({r['availability'] for r in self.rows('SELECT * FROM physical_files')},{'AVAILABLE'})

    def test_unreadable_subtree_does_not_checkpoint_partial_inventory(self):
        root,show = self.library()
        self.scan()
        before = self.rows('SELECT * FROM scan_files')
        with patch('app.core.scan_state.inventory',side_effect=PermissionError('access denied')):
            result = self.scan()
        self.assertTrue(result['errors'])
        self.assertEqual(before,self.rows('SELECT * FROM scan_files'))
        self.assertEqual(db.get_watched_directories()[0]['availability'],'INACCESSIBLE')

    def test_deleted_file_below_readable_root_is_missing_not_offline(self):
        root,show = self.library()
        self.scan()
        victim = next(show.iterdir())
        victim.unlink()
        self.scan()
        self.assertEqual(sorted(r['availability'] for r in self.rows('SELECT * FROM physical_files')),['AVAILABLE','MISSING'])
        self.assertEqual(len(self.rows('SELECT * FROM episodes')),2)
        self.assertEqual(db.get_watched_directories()[0]['availability'],'ONLINE')
        hidden=root.with_name('offline-with-known-missing-file')
        root.rename(hidden)
        self.scan()
        hidden.rename(root)
        self.scan()
        self.assertEqual(sorted(r['availability'] for r in self.rows('SELECT * FROM physical_files')),['AVAILABLE','MISSING'])

    def test_cancellation_does_not_save_partial_inventory(self):
        root,show = self.library()
        token = ScanProgress()
        with self.assertRaises(InterruptedError):
            state.inventory(root,lambda: True)
        token.cancellation = lambda: True
        self.assertEqual(scan_watched_directories(scan_progress=token,allow_network=False)['scanned'],0)
        self.assertEqual(self.rows('SELECT * FROM scan_files'),[])

    def test_matching_uses_season_year_format_and_rejects_close_alternatives(self):
        evidence = context('[EMBER] Exact Anime S02E10 (2025).mkv','Season 2','Exact Anime',2)
        correct = {'id':30,'format':'TV','seasonYear':2025,'title':{'english':'Exact Anime Season 2'}}
        wrong = {'id':31,'format':'MOVIE','seasonYear':2020,'title':{'english':'Exact Anime'}}
        # Candidate aliases retain a base title; season remains separate evidence.
        selected,ranked = choose([wrong,correct],evidence)
        self.assertEqual(selected,correct)
        self.assertTrue(next(r for r in ranked if r['id']==31)['conflict'])
        twin = dict(correct,id=32)
        self.assertIsNone(choose([correct,twin],evidence)[0])
        self.assertEqual(choose([correct,correct],evidence)[0],correct)

    def test_conflicting_filename_never_inherits_broader_folder_match(self):
        evidence = context('Other Show - 10.mkv','Exact Anime','Exact Anime',1)
        candidate = {'id':3,'format':'TV','title':{'english':'Exact Anime'}}
        self.assertIsNone(choose([candidate],evidence)[0])

    def test_unresolved_match_is_persisted_for_review(self):
        self.library()
        with patch('app.core.scanner.is_offline',return_value=False), \
             patch('app.core.matching.client.search_anime',return_value=[
                 {'id':31,'format':'TV','title':{'english':'Exact Anime'}},
                 {'id':32,'format':'TV','title':{'english':'Exact Anime'}}]):
            result = scan_watched_directories()
        self.assertEqual(result['errors'],[])
        reviews = self.rows('SELECT * FROM matching_review')
        self.assertEqual(len(reviews),1)
        record = db.get_franchise(reviews[0]['local_id'])
        self.assertIsNone(record['anilist_id'])
        self.assertEqual(record['needs_review'],1)
        self.assertTrue(json.loads(reviews[0]['candidates_json']))

    def test_manual_and_legacy_matches_survive_restart_and_auto_attempt(self):
        with closing(db.get_connection()) as conn,conn:
            state.decision(conn,'series',self.fid,42)
        db.init_db()
        with closing(db.get_connection()) as conn,conn:
            self.assertFalse(state.decision(conn,'series',self.fid,99,'AUTO'))
        self.assertEqual(self.rows("SELECT provider_id FROM matching_decisions WHERE kind='series' AND local_id=?",(self.fid,))[0]['provider_id'],42)

    def test_unrelated_file_in_same_folder_requires_review(self):
        root,show=self.library()
        (show/'Completely Different Series S01E03.mkv').write_bytes(b'unrelated')
        candidate={'id':31,'format':'TV','title':{'english':'Exact Anime'}}
        with patch('app.core.scanner.is_offline',return_value=False),patch('app.core.matching.client.search_anime',return_value=[candidate]):
            scan_watched_directories()
        row=self.rows('SELECT context_json FROM matching_review')[0]
        evidence=json.loads(row['context_json'])
        self.assertEqual(len(evidence['files']),3)
        self.assertTrue(evidence.get('conflicting_file') or evidence['filename'])

    def test_artwork_deduplicates_provider_version_and_remembers_absence(self):
        covers = Path(self.temp.name)/'covers-cache'
        covers.mkdir()
        media = {'id':321,'bannerImage':'https://example.test/banner1.jpg'}
        requests_seen=[]
        def download(url,filename):
            from PyQt5.QtGui import QImage
            requests_seen.append(url)
            time.sleep(.03)
            image=QImage(2,2,QImage.Format_RGB32)
            image.fill(0)
            image.save(str(covers/filename),'JPEG')
            return filename
        with patch.object(client,'COVERS_DIR',covers),patch.object(client,'_download_artwork',side_effect=download):
            with ThreadPoolExecutor(max_workers=4) as pool:
                names = list(pool.map(lambda n:client.download_banner(media,n),range(4)))
            self.assertEqual(len(set(names)),1)
            self.assertEqual(len(requests_seen),1)
            media['bannerImage']=None
            self.assertIsNone(client.download_banner(media,1))
            self.assertIsNone(client.download_banner(media,2))
            self.assertEqual(len(requests_seen),1)
            media['bannerImage']='https://example.test/banner2.jpg'
            self.assertNotEqual(client.download_banner(media,1),names[0])
            self.assertEqual(len(requests_seen),2)

    def test_failed_artwork_has_persistent_retry_deadline(self):
        media = {'id':322,'bannerImage':'https://example.test/missing.jpg'}
        with patch.object(client,'_download_artwork',return_value=None) as download:
            client.download_banner(media,1)
            client.download_banner(media,2)
        self.assertEqual(download.call_count,1)

    def test_api_rate_limit_does_not_recurse_and_cancellation_prevents_request(self):
        response = Mock(status_code=429)
        with patch.object(client,'_rate_limit'),patch.object(client.requests,'post',return_value=response) as post:
            self.assertIsNone(client._graphql_request('query',{}))
            self.assertEqual(post.call_count,1)
        with patch.object(client.requests,'post') as post:
            with self.assertRaises(InterruptedError):
                with client.cancellable(lambda: True):
                    client.search_anime('stale')
            post.assert_not_called()

    def test_stale_search_results_cannot_replace_current_query(self):
        from PyQt5.QtCore import QThread,pyqtSignal
        from app.ui.dialogs.rematch_dialog import RematchDialog
        class Search(QThread):
            results_ready=pyqtSignal(list)
            error_occurred=pyqtSignal(str)
            def __init__(self,query):
                super().__init__()
                self.query=query
                self.running=False
                self.interrupted=False
            def start(self): self.running=True
            def isRunning(self): return self.running
            def requestInterruption(self): self.interrupted=True
        with patch('app.ui.dialogs.rematch_dialog.OFFLINE_MODE',False),patch('app.ui.dialogs.rematch_dialog.AniListSearchWorker',Search):
            dialog=RematchDialog(self.fid)
            first=dialog._search_worker
            dialog._start_search('new query')
            self.assertTrue(first.interrupted)
            with patch.object(dialog,'_on_results_ready') as ready:
                first.results_ready.emit([{'id':1}])
                ready.assert_not_called()
                first.running=False
                first.finished.emit()
                latest=dialog._search_worker
                self.assertEqual(latest.query,'new query')
                latest.results_ready.emit([{'id':2}])
                ready.assert_called_once_with([{'id':2}])
            dialog.reject()
            latest.running=False
            latest.finished.emit()
            dialog.deleteLater()

    def test_cards_fill_available_width_and_keep_loaded_posters_on_resize(self):
        from app.ui.pages.library_page import LibraryPage
        for n in range(18):
            db.upsert_franchise({'display_title':f'Example title {n}'})
        page=LibraryPage()
        page._set_view_mode('grid')
        page.resize(1450,900)
        page.show()
        self.app.processEvents()
        with patch('app.ui.components.poster_card.refresh_pixmap',side_effect=AssertionError('decode on resize')):
            page._reflow_grid()
            self.app.processEvents()
            cols=page._grid_columns
            first,last=page._cards[0],page._cards[cols-1]
            margins=page.page_scroll.widget().layout().contentsMargins()
            available=page.page_scroll.viewport().width()-margins.left()-margins.right()
            self.assertEqual(sum(c.width() for c in page._cards[:cols])+20*(cols-1),available)
            self.assertLessEqual(abs(last.geometry().right()-(page.grid_container.width()-1)),1)
            self.assertAlmostEqual(first.POSTER_HEIGHT/first.width(),1.5,places=2)
            page.resize(1180,900)
            self.app.processEvents()
            page._reflow_grid()
            self.assertLess(page._grid_columns,cols)
        page.close();page.deleteLater()

    def test_scan_worker_keeps_event_loop_within_100ms_budget(self):
        from PyQt5.QtCore import QThread,QTimer,QEventLoop
        self.library(500)
        gui_thread = threading.get_ident()
        real_inventory = state.inventory
        observed=[]
        def slow_inventory(*args,**kwargs):
            observed.append(threading.get_ident())
            time.sleep(.15)  # simulate a slow HDD without blocking the UI
            return real_inventory(*args,**kwargs)
        class Worker(QThread):
            failure=None
            def run(inner):
                try:
                    self.scan()
                except Exception as error:
                    inner.failure=error
        worker=Worker()
        loop=QEventLoop()
        ticks=[time.perf_counter()]
        timer=QTimer()
        timer.setInterval(5)
        timer.timeout.connect(lambda:ticks.append(time.perf_counter()))
        worker.finished.connect(loop.quit)
        with patch.object(state,'inventory',side_effect=slow_inventory):
            timer.start();worker.start();loop.exec_();worker.wait();timer.stop()
        self.assertIsNone(worker.failure)
        self.assertTrue(observed and all(t!=gui_thread for t in observed))
        self.assertGreater(len(ticks),10)
        maximum=max(b-a for a,b in zip(ticks,ticks[1:]))
        print(f'Phase 2 scanner heartbeat: max {maximum*1000:.1f} ms (500 files)')
        self.assertLess(maximum,.100)
