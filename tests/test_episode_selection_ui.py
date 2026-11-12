"""New reference layouts retain numbering safety and virtualized playback."""
import json
import unittest
from unittest.mock import patch
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget,QToolButton,QLabel,QStackedWidget,QVBoxLayout
from PyQt5.QtTest import QTest
import test_ui_regressions as support
from app import db
from app.ui.dialogs.season_numbers import SeasonNumbers
from app.ui.pages.episode_page import EpisodePage,EpisodeWorker


class EpisodeSelectionUI(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def rows(self,count=19):
        return [dict(title=f'Episode {n}',type='Episode',subtitle='S1 / Episode',
            name=f'episode-{n}.mkv',path=f'/local/episode-{n}.mkv',kind='SEASON',
            season_id=1,release_id=None,release_state='AIRED') for n in range(1,count+1)]

    def episode_page(self,count=19):
        with patch.object(EpisodeWorker,'start'):page=EpisodePage(self.fid)
        page._loaded(self.rows(count),[])
        return page

    def test_footer_selection_and_play_use_existing_player_without_auto_launch(self):
        page=self.episode_page();page.show();self.app.processEvents()
        try:
            with patch('app.ui.pages.episode_page.launch_video_file') as launch:
                page.view.setCurrentIndex(page.model.index(6))
                self.assertIn('Episode 7',page.ready_title.text());self.assertTrue(page.footer_play.isEnabled())
                self.assertEqual(page.ready_path.text(),'/local/episode-7.mkv');launch.assert_not_called()
                page.footer_play.click();launch.assert_called_once_with('/local/episode-7.mkv')
                self.assertTrue(page.model.index(6).data(Qt.UserRole+1))
            page.release_filter.setCurrentIndex(2)
            self.assertEqual(page.model.rowCount(),0);self.assertFalse(page.footer_play.isEnabled());self.assertEqual(page.ready_path.text(),'')
            self.assertEqual(page.release_filter.count(),4)
        finally:page.reject();page.deleteLater()

    def test_thousands_of_blocks_remain_virtualized_and_fit_large_text(self):
        page=self.episode_page(2000)
        try:
            for scale in (1.0,1.3):
                self.app.setProperty('animevaultScale',scale);page.refresh_home_style()
                page.resize(1100,720);page.show();QTest.qWait(30)
                self.assertEqual(page.model.rowCount(),2000)
                self.assertLess(len(page.findChildren(QWidget)),100)
                self.assertLessEqual(page.view.horizontalScrollBar().maximum(),0)
                self.assertGreater(page.view.height(),150)
                self.assertLessEqual(page.playback_footer.geometry().bottom(),page.height())
        finally:
            self.app.setProperty('animevaultScale',1.0);page.reject();page.deleteLater()

    def test_centered_editor_keeps_review_gate_stepper_and_save_payload(self):
        sid=db.upsert_season(dict(franchise_id=self.fid,season_number=1,title_display='A long release name Season 2',
            season_folder_path=self.temp.name,video_files_json=json.dumps(['S01E01.mkv']),storage_state='ON_DISK'))
        host=QWidget();host.stacked_widget=QStackedWidget();QVBoxLayout(host).addWidget(host.stacked_widget)
        host.stacked_widget.addWidget(QWidget());host.resize(1280,850);host.show()
        from app.ui.navigation import navigate
        editor=SeasonNumbers(self.fid,host);navigate(editor);QTest.qWait(20)
        try:
            self.assertTrue(editor.centered_workflow);self.assertLessEqual(editor.width(),740)
            self.assertFalse(editor.save_button.isEnabled())
            next(b for b in editor.findChildren(QToolButton) if b.accessibleName()=='Increase season number').click()
            self.assertEqual(editor.controls[sid].value(),2)
            with patch('app.ui.dialogs.season_numbers.start',side_effect=lambda owner,operation,ready:operation()):
                editor.save();self.assertEqual(db.get_season(sid)['season_number'],1)
                editor.reviewed.setChecked(True);editor.save()
            self.assertEqual(db.get_season(sid)['season_number'],2)
            self.assertEqual(db.get_season(sid)['season_folder_path'],self.temp.name)
        finally:editor.reject();host.deleteLater()
