import json,unittest
from pathlib import Path
from unittest.mock import patch
import test_ui_regressions as support
from app import db
from app.core import downloads,download_library


class FolderRoutes(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def test_nested_watched_folders_do_not_hide_main_library_root(self):
        root=Path(self.temp.name)/'library';root.mkdir()
        db.add_watched_directory(str(root));db.add_watched_directory(str(root/'Black Clover'))
        db.add_watched_directory(str(root/'.animevault-downloads'))
        self.assertEqual(Path(downloads.library_root()),root)
        self.assertEqual(Path(download_library.preview()['root']),root)

    def test_destination_choice_is_saved_before_generating_merge_preview(self):
        from app.ui.pages.merge_page import MergePage
        page=MergePage();self.addCleanup(page.deleteLater)
        root=Path(self.temp.name)/'chosen';root.mkdir()
        with patch('app.ui.pages.merge_page.QFileDialog.getExistingDirectory',return_value=str(root)):page.choose_destination()
        self.assertEqual(Path(downloads.library_root()),root)
        self.assertEqual(db.get_state('library.main_root'),str(root))
        self.assertIsNone(page.plan)

    def test_separate_roots_require_a_choice_and_download_setting_stays_separate(self):
        root=Path(self.temp.name)
        for name in ('first','second'):db.add_watched_directory(str(root/name))
        self.assertIsNone(downloads.library_root())
        db.set_state('library.main_root',str(root/'first'))
        stage=root/'downloads';db.set_state('downloads.settings',json.dumps(dict(destination=str(stage))))
        self.assertEqual(Path(downloads.library_root()),root/'first')
        self.assertEqual(Path(downloads.settings()['destination']),stage)

    def test_global_download_folder_does_not_follow_selected_anime(self):
        from app.ui.pages.downloads_page import DownloadsPage
        stage=Path(self.temp.name)/'downloads';stage.mkdir();anime=stage/'Black Clover';anime.mkdir()
        db.set_state('downloads.settings',json.dumps(dict(destination=str(stage))))
        with patch.object(DownloadsPage,'refresh'):page=DownloadsPage()
        page.timer.stop();self.addCleanup(page.deleteLater)
        job=dict(id='example',root=str(anime),destination=str(anime))
        page.items=[job];opened=[]
        with patch.object(page,'selected',return_value=job),patch('app.ui.pages.downloads_page.QDesktopServices.openUrl',side_effect=lambda url:opened.append(url.toLocalFile()) or True):
            page.open_folder(global_folder=True);page.open_folder('example')
        self.assertEqual([Path(p).resolve() for p in opened],[stage.resolve(),anime.resolve()])
    def test_explicit_default_download_path_is_not_rewritten_by_main_root(self):
        db.set_state('downloads.settings',json.dumps(dict(destination=downloads.DEFAULTS['destination'])))
        db.set_state('library.main_root',str(Path(self.temp.name)/'main'))
        self.assertEqual(downloads.settings()['destination'],downloads.DEFAULTS['destination'])
