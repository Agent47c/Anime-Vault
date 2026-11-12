"""Read-only audit of production code using temporary databases and mocked IO."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import sys, json, time, tempfile
import faulthandler
faulthandler.dump_traceback_later(15)
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt5.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from app import db
from app.ui.main_window import MainWindow
results = {}
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    from contextlib import ExitStack
    with ExitStack() as stack:
        for name, value in [('DATA_DIR',root),('DB_PATH',root/'library.db'),('COVERS_DIR',root/'covers'),('EXPORTS_DIR',root/'exports')]:
            stack.enter_context(patch.object(db,name,value))
        db.init_db()
        first = db.upsert_franchise({'display_title':'Audit Series','watch_status':'WATCHING','storage_state':'ON_DISK'})
        second = db.upsert_franchise({'display_title':'Audit Series Season 2','watch_status':'WATCHING','storage_state':'ON_DISK'})
        db.set_state('series_overrides',json.dumps({str(second):first}))
        results['grouped_counts']={'library_cards':len(db.get_series_library()),'storage_titles':db.get_library_stats()['on_disk'],'watching_count':sum(f['watch_status']=='WATCHING' for f in db.get_all_franchises())}
        print('Counts checked',flush=True)
        db.set_state('series_relation_cache','[]')
        try: db.get_series_library()
        except Exception as error: results['invalid_cache_shape']=type(error).__name__+': '+str(error)
        db.set_state('series_relation_cache','{}')
        from app.core import exporter
        with patch.object(exporter,'EXPORTS_DIR',root/'exports'),patch.object(exporter.time,'strftime',return_value='AUDIT_SAME_SECOND'):
            path1=exporter.export_json()
            old=Path(path1).read_text(encoding='utf-8')
            db.update_franchise_field(first,'user_notes','second export')
            path2=exporter.export_json()
            results['export_collision']={'same_path':path1==path2,'old_contents_overwritten':old!=Path(path1).read_text(encoding='utf-8')}
        from fastapi.testclient import TestClient
        print('Export checked; testing API boundary',flush=True)
        from app.api import server
        with patch.object(server,'API_ACCESS_TOKEN',''),patch.object(server,'LOCAL_API_HOST','127.0.0.1'):
            with TestClient(server.api,base_url='http://untrusted.example:8765') as client:
                response=client.get('/api/library',headers={'Origin':'http://untrusted.example:8765'})
                results['unexpected_host_origin']={'status':response.status_code}
        print('API checked',flush=True)
        host=SimpleNamespace(_refresh_busy=True,_shutdown_pending=False,_dirty_pages=set(),library_page=1,storage_page=2,updates_page=3,_start_refresh=Mock())
        MainWindow._start_refresh(host,scan_library=True,sync_internet=True)
        pending=[]
        host.refresh_button=Mock()
        host._on_data_updated=lambda:MainWindow._on_data_updated(host)
        with patch('app.ui.main_window.QTimer.singleShot',side_effect=lambda delay,callback:pending.append(callback)):
            MainWindow._finish_refresh(host)
        pending[0]()
        results['queued_refresh']={'requested':{'scan_library':True,'sync_internet':True},'next_call_args':str(host._start_refresh.call_args)}
        from app.ui.user_edits import UserEdits
        edits=UserEdits()
        edits.pending={first:{'user_notes':'unsaved audit fixture'}}
        with patch.object(db,'get_connection',side_effect=OSError('Audit simulated disk failure')):
            edits.flush()
            until=time.monotonic()+3
            while edits.worker is not None and time.monotonic()<until:
                app.processEvents();time.sleep(.005)
        host=SimpleNamespace(_running_threads=lambda:[],_shutdown_timer=Mock())
        with patch('app.ui.artwork.artwork_loader',return_value=SimpleNamespace(pool=SimpleNamespace(activeThreadCount=lambda:0))),patch('app.ui.main_window.server.stop_server'),patch('app.ui.main_window.QApplication.quit') as quit_app:
            MainWindow._finish_pending_exit(host)
            results['failed_edit_exit']={'pending_edits':bool(edits.pending),'quit_called':quit_app.called}
        from app.core import downloads
        media=root/'Audit Series'/'Season 02'/'Audit Series S01E07.mkv'
        media.parent.mkdir(parents=True);media.write_bytes(b'audit fixture, not real media')
        conn=db.get_connection()
        conn.execute('INSERT OR IGNORE INTO library_series(franchise_id) VALUES (?)',(first,));conn.commit()
        sid=conn.execute('SELECT id FROM library_series WHERE franchise_id=?',(first,)).fetchone()[0];conn.close()
        item={'fid':first,'series_id':sid,'root':str(root/'Audit Series'),'season':2,'episode_keys':['EPISODE:S2:10']}
        downloads._index_completed(item,[media])
        conn=db.get_connection()
        episodes=[dict(row) for row in conn.execute('SELECT identity_key,original_number,numbering_scheme,release_number FROM episodes')]
        conn.close()
        results['confirmed_download_mapping']={'confirmed':item['episode_keys'],'indexed':item['indexed'],'seasons':[{k:s.get(k) for k in ('season_number','title_display')} for s in db.get_seasons_for_franchise(first)],'episodes':episodes}
        host=SimpleNamespace(_shutdown_pending=False,status_pill=Mock(),_refresh_metrics=Mock())
        started=time.monotonic()
        with patch('app.ui.main_window.check_online',side_effect=lambda:(time.sleep(.15) or False)):
            MainWindow._initial_online_check(host)
        results['gui_connectivity_check']={'synchronous_delay_ms':round((time.monotonic()-started)*1000)}
        from app.ui.pages.storage_page import SegmentedCapacityBar,StoragePage
        from PyQt5.QtWidgets import QLabel
        capacity=SegmentedCapacityBar()
        host=SimpleNamespace(capacity_bar=capacity,capacity_sub_label=QLabel(),capacity_free_label=QLabel(),drive_title=QLabel(),legend_anime=QLabel(),legend_other=QLabel(),legend_free=QLabel())
        capacity.set_values(1500,800,1000)
        results['offline_capacity_arithmetic']={'stored_anime_bytes':1500,'online_used_bytes':800,'online_capacity_bytes':1000,'free_bytes':200,'legend_total_bytes':1500+max(0,800-1500)+200,'bar_anime_fraction':capacity.anime_pct}
        from app.ui.pages.settings_page import SettingsPage
        refresh=SimpleNamespace(isRunning=lambda:True)
        window=SimpleNamespace(_refresh_worker=refresh,setEnabled=Mock())
        settings=SimpleNamespace(backup_status=Mock(),window=lambda:window,_apply_worker=Mock())
        with patch('app.ui.pages.settings_page.QFileDialog.getOpenFileName',return_value=('audit-backup.db','')),patch('app.ui.pages.settings_page.QMessageBox.question',return_value=16384),patch('app.ui.io_task.running',return_value=[]),patch('app.core.builtin_torrents.active',return_value=False),patch('app.core.downloads.jobs',return_value=[]),patch('app.ui.io_task.start') as restore_start:
            SettingsPage._restore_db(settings)
            results['restore_during_refresh']={'refresh_running':refresh.isRunning(),'restore_started':restore_start.called}
faulthandler.cancel_dump_traceback_later()
print(json.dumps(results,indent=2))
