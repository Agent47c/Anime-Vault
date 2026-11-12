"""Details presentation and approved episode previews, without real downloads."""
import json,time,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from PyQt5.QtCore import Qt,QPoint
from PyQt5.QtWidgets import QApplication,QWidget
from PyQt5.QtTest import QTest
import test_ui_regressions as support
from app import db
from app.core import identity,episode_preview


class DetailScreenTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_episode_dates_use_stable_history_and_seasons_stay_separate(self):
        rows=[]
        for number in (1,2):
            folder=Path(self.temp.name)/f'Season {number}';folder.mkdir()
            path=folder/f'S{number:02}E01.mkv';path.write_bytes(b'video')
            sid=db.upsert_season(dict(franchise_id=self.fid,season_number=number,title_display=f'Season {number}',season_folder_path=str(folder),video_files_json=json.dumps([path.name]),storage_state='ON_DISK'))
            identity.sync_inventory(sid)
            rows.append(dict(path=str(path),title='Episode 1',release_id=21,season_id=sid))
        identity.track_play(rows[0]['path'])
        episode_preview.enrich_rows(rows)
        self.assertGreater(rows[0]['last_played'],0);self.assertEqual(rows[1]['last_played'],0)
        self.assertNotEqual(rows[0]['episode_ids'],rows[1]['episode_ids'])
    def test_unverified_mapping_never_requests_wrong_episode_description(self):
        with patch('requests.get') as request,patch('app.config.is_offline',return_value=False):
            result=episode_preview.load_preview(dict(path='missing.mkv',mal_id=21,provider_number=None))
        request.assert_not_called();self.assertIn('verified',result['description'])
    def test_episode_description_cache_and_failure_backoff(self):
        row=dict(path='missing.mkv',mal_id=21,provider_number=2)
        reply=Mock();reply.json.return_value={'data':{'title':'Episode title','synopsis':'A real <b>description</b>.'}}
        with patch('app.config.is_offline',return_value=False),patch('requests.get',return_value=reply) as request:
            first=episode_preview.load_preview(row);second=episode_preview.load_preview(row)
        self.assertEqual(first,second);self.assertEqual(first['description'],'A real description.');self.assertEqual(request.call_count,1)
        import requests
        with patch('app.config.is_offline',return_value=False),patch('requests.get',side_effect=requests.ConnectionError('offline')) as request:
            episode_preview.load_preview({**row,'provider_number':3});episode_preview.load_preview({**row,'provider_number':3})
        self.assertEqual(request.call_count,1)
    def test_no_ffmpeg_retry_loop_and_cancellation_stops_new_work(self):
        path=Path(self.temp.name)/'Episode 1.mkv';path.write_bytes(b'video')
        row=dict(path=str(path))
        with patch('shutil.which',return_value=None) as executable:
            episode_preview.load_preview(row);episode_preview.load_preview(row)
        self.assertEqual(executable.call_count,1)
        with patch('subprocess.run') as process,patch('requests.get') as request:
            episode_preview.load_preview({**row,'mal_id':21,'provider_number':4},cancelled=lambda:True)
        process.assert_not_called();request.assert_not_called()
    def test_local_frame_is_generated_once_and_loaded_from_cache(self):
        from PyQt5.QtGui import QImage,QColor
        path=Path(self.temp.name)/'Episode 1.mkv';path.write_bytes(b'video')
        def frame(command,**kwargs):
            image=QImage(320,180,QImage.Format_RGB32);image.fill(QColor('#ff6584'));image.save(command[-1]);return Mock(returncode=0)
        with patch('shutil.which',return_value='ffmpeg'),patch('subprocess.run',side_effect=frame) as process:
            first=episode_preview.load_preview(dict(path=str(path),file_id=42));second=episode_preview.load_preview(dict(path=str(path),file_id=42))
        self.assertEqual(process.call_count,1);self.assertFalse(first['image'].isNull());self.assertFalse(second['image'].isNull())
    def test_episode_list_is_virtualized_and_reopens_from_child_navigation(self):
        from app.ui.components.detail_episodes import DetailEpisodes
        panel=DetailEpisodes(self.fid,[]);panel._indexed=True
        panel._rows=[dict(path=f'file-{n}.mkv',title=f'Episode {n}',name=f'file-{n}.mkv',type='Episode',subtitle='S1 / Episode',season_id=1,last_played=0) for n in range(2000)]
        panel._requested={r['path'] for r in panel._rows};panel.filter_rows();panel.resize(1000,760)
        panel.show();self.app.processEvents()
        self.assertEqual(panel.model.rowCount(),2000)
        self.assertLess(len(panel.findChildren(QWidget)),100)
        self.assertIn('No watch date',panel.model.index(0).data(Qt.ToolTipRole))
        panel.hide();self.assertTrue(panel._stopped)
        panel.show();self.assertFalse(panel._stopped);self.assertTrue(panel._indexed)
        panel.hide();panel.deleteLater()
    def test_layout_keeps_all_existing_detail_actions_and_excludes_unapproved(self):
        from app.ui.pages.detail_modal import DetailModal
        from PyQt5.QtWidgets import QPushButton
        dialog=DetailModal(self.fid);dialog.resize(1200,900);dialog.show();self.app.processEvents()
        labels={b.text() for b in dialog.findChildren(QPushButton)}
        for label in ('Open folder','Edit title','Rematch','Find Download Files','View API JSON','Group with another series','Episode and movie check','Delete files...'):self.assertIn(label,labels)
        self.assertFalse(any('RSS' in s or 'Physical' in s or 'Profile' in s for s in labels))
        self.assertEqual(len(dialog.rating_buttons),10)
        self.assertGreaterEqual(dialog.rating_buttons[0].width(),24)
        dialog.reject();dialog.deleteLater()

    def test_large_text_layout_grows_without_horizontal_page_overflow(self):
        from app.ui.pages.detail_modal import DetailModal
        from app.ui.theme import apply_theme
        db.set_state('text_scale','1.3');apply_theme(self.app,'dark')
        dialog=DetailModal(self.fid);dialog.resize(1100,900);dialog.show();self.app.processEvents()
        try:
            self.assertLessEqual(dialog.right_scroll.widget().width(),dialog.right_scroll.viewport().width())
            self.assertGreaterEqual(dialog.rating_buttons[0].width(),31)
        finally:
            dialog.reject();dialog.deleteLater();db.set_state('text_scale','1.0');apply_theme(self.app,'dark')
