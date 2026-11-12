import json,time,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from PyQt5.QtWidgets import QMainWindow,QLineEdit
from PyQt5.QtGui import QImage
import test_ui_regressions as support
from app import db

class DownloadSettingsPolishTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_metrics_refresh_preserves_download_count_and_unchanged_text_is_noop(self):
        from app.ui.components.home_header import HomeHeader
        from PyQt5.QtTest import QSignalSpy
        host=QMainWindow();host.top_search_input=QLineEdit();host.coll_counts={}
        for name in ('_on_nav_clicked','_on_collection_clicked','_request_refresh','_open_custom_entry_dialog','_open_watched_import_dialog'):setattr(host,name,Mock())
        header=HomeHeader(host);header.tabs[5].setText('Downloads  2');spy=QSignalSpy(header.tabs[5].size_changed)
        header.tabs[5].setText('Downloads  2');self.assertEqual(len(spy),0)
        header.metrics({'total':0},0);self.assertEqual(header.tabs[5].text(),'Downloads  2');header.deleteLater();host.deleteLater()
    def test_staging_is_not_an_anime_and_completed_jobs_use_linked_title(self):
        from app.core import downloads,organizer
        root=Path(self.temp.name)/'library';staging=root/'.animevault-downloads';folder=staging/'encoder-job'/'Season 01';folder.mkdir(parents=True);file=folder/'Encoder 06.mkv';file.write_bytes(b'video')
        db.add_watched_directory(str(root));db.set_state('downloads.settings',json.dumps({'destination':str(staging)}))
        downloads._save_jobs([dict(id='job',fid=self.fid,indexed=True,destination=str(folder),root=str(folder.parent),verified_files=[dict(path=str(file),size=5)])])
        with patch.object(organizer,'inspect_anime_folder',return_value={'video_count':0}) as inspect:
            results=organizer.inspect_all_library()
        self.assertFalse(any(Path(call.args[0]).is_relative_to(staging) for call in inspect.call_args_list))
        item=next(row for row in results['all'] if row.get('download_job_id')=='job');self.assertEqual(item['anime_name'],'One Piece');self.assertEqual(item['video_count'],1)
        with self.assertRaises(ValueError):organizer.execute_organize_anime(item)
    def test_cached_player_icon_does_not_download_again(self):
        from app.core import player_icons
        with patch.object(db,'DATA_DIR',Path(self.temp.name)):
            root=Path(self.temp.name)/'player-icons';root.mkdir();image=QImage(32,32,QImage.Format_ARGB32);image.fill(0xffaaaaaa);image.save(str(root/'vlc.png'))
            (root/'attempts.json').write_text(json.dumps({name:time.time() for name in player_icons.SOURCES}))
            with patch('app.config.detect_installed_players',return_value={}),patch('app.config.get_custom_player_path',return_value=''),patch('requests.get') as get:
                icons=player_icons.cached_icons();get.assert_not_called();self.assertIn('vlc',icons)
    def test_potplayer_detection_uses_real_executable(self):
        from app.config import detect_installed_players
        with patch('app.config.os.path.isfile',side_effect=lambda path:str(path).endswith('PotPlayerMini64.exe')):
            self.assertTrue(detect_installed_players()['potplayer'].endswith('PotPlayerMini64.exe'))
    def test_updates_actions_are_direct_equal_width_and_have_no_more_menu(self):
        from app.ui.pages.updates_page import UpdateCard
        from PyQt5.QtWidgets import QPushButton
        record=db.get_franchise(self.fid);record['update_summary']='Episode 7 airing soon'
        card=UpdateCard(record)
        buttons={b.text():b for b in card.findChildren(QPushButton)}
        self.assertNotIn('More',buttons)
        for label in ('Later','Dismiss','Not interested','Mute anime','Watched and ignore'):self.assertIn(label,buttons);self.assertFalse(buttons[label].isHidden())
        self.assertEqual(buttons['Later'].width(),buttons['Dismiss'].width());card.deleteLater()
    def test_release_popup_fits_last_item_and_uses_no_horizontal_scroll(self):
        from app.ui.components.airing_count import AiringCount
        from PyQt5.QtWidgets import QScrollArea
        from PyQt5.QtCore import Qt
        button=AiringCount([dict(title='Example anime',episode=n,time='19:30') for n in (6,7)]);button.show();button._show_preview();self.app.processEvents()
        scroll=button.preview.findChild(QScrollArea);self.assertEqual(scroll.horizontalScrollBarPolicy(),Qt.ScrollBarAlwaysOff);self.assertEqual(scroll.verticalScrollBar().maximum(),0)
        button._hide_preview();button.close();button.deleteLater()
    def test_settings_connect_actions_share_compact_row_and_potplayer_is_selectable(self):
        from app.ui.pages.settings_page import SettingsPage
        from PyQt5.QtWidgets import QPushButton
        page=SettingsPage();buttons={b.text():b for b in page.download_config.findChildren(QPushButton)}
        self.assertIs(buttons['Connect Chrome extension'].parentWidget(),buttons['Open Chrome extension folder'].parentWidget())
        self.assertGreaterEqual(page.player_combo.findData('potplayer'),0);page.deleteLater()
    def test_release_popup_shows_three_full_rows_then_scrolls(self):
        from app.ui.components.airing_count import AiringCount
        from PyQt5.QtWidgets import QScrollArea,QPushButton
        previous=self.app.property('animevaultScale')
        try:
            for scale in (1.0,1.3):
                self.app.setProperty('animevaultScale',scale)
                button=AiringCount([dict(title=f'Anime {n}',episode=n,time='19:30') for n in range(1,6)]);button.show();button._show_preview();self.app.processEvents()
                scroll=button.preview.findChild(QScrollArea);rows=scroll.widget().findChildren(QPushButton,'airing_preview_item')
                self.assertGreater(scroll.verticalScrollBar().maximum(),0)
                self.assertLessEqual(rows[2].geometry().bottom(),scroll.viewport().height())
                self.assertGreaterEqual(rows[3].geometry().top(),scroll.viewport().height())
                scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum());self.app.processEvents()
                point=rows[-1].mapTo(scroll.viewport(),rows[-1].rect().bottomLeft());self.assertLessEqual(point.y(),scroll.viewport().height())
                button._hide_preview();button.close();button.deleteLater()
        finally:self.app.setProperty('animevaultScale',previous)
