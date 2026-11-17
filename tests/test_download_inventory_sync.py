"""Temporary-file regressions for partial downloads, moves and stale previews."""
import json,threading,unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton
import test_ui_regressions as support
from app import db
from app.core import downloads,download_inventory,scan_state,scanner,organizer,download_library,file_operations,identity
from app.ui import organizer_cache


class InventorySyncTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def partial(self):
        root=Path(self.temp.name)/'anime';root.mkdir()
        video=root/'Demo - 177.mkv';video.write_bytes(bytes(4096))
        other=root/'Other - 01.mkv';other.write_bytes(b'complete video')
        job=dict(id='partial',fid=self.fid,root=str(root),destination=str(root),engine='builtin',status='Downloading',desired='running',indexed=False,total=4096)
        downloads._save_jobs([job]);return root,video,other,job
    def completed(self):
        from test_download_recovery_and_moves import DownloadRecoveryTests
        return DownloadRecoveryTests.fixture(self)

    def test_preallocated_video_is_not_ready_but_untracked_neighbour_is_scanned(self):
        root,video,other,job=self.partial()
        # A real job owns its isolated root; place an ordinary neighbour outside
        # that root to prove that the watched parent is not excluded wholesale.
        isolated=root/'torrent-job';isolated.mkdir();video.rename(isolated/video.name);video=isolated/video.name
        job.update(root=str(isolated),destination=str(isolated));downloads._save_jobs([job])
        _,inventory=scan_state.inventory(root)
        self.assertNotIn(str(video),inventory);self.assertIn(str(other),inventory)
        item=organizer.inspect_anime_folder(str(root))
        self.assertEqual([Path(m['source']) for m in item['moves']],[other])
        rows=download_inventory.organizer_rows();self.assertFalse(rows[0]['download_ready'])
        self.assertEqual(rows[0]['status_badge'],'Download not ready')

    def test_restore_checking_and_file_size_do_not_override_completion(self):
        root,video,other,job=self.partial()
        job.update(indexed=True,status='Checking files',verified_files=[dict(path=str(video),size=4096)])
        downloads._save_jobs([job]);self.assertFalse(download_inventory.Snapshot().can_index(video))
        self.assertFalse(download_library.preview(str(Path(self.temp.name)/'library'))['rows'])
        job['status']='Indexed';downloads._save_jobs([job])
        snapshot=download_inventory.Snapshot();self.assertTrue(snapshot.can_index(video));self.assertFalse(snapshot.can_organize(video))
        self.assertFalse(organizer.inspect_anime_folder(str(root))['moves'])
        plan=download_library.preview(str(Path(self.temp.name)/'library'))
        job['status']='Checking files';downloads._save_jobs([job])
        self.assertIn('no longer ready',download_library.move(plan));self.assertTrue(video.exists())

    def test_progress_ticks_do_not_invalidate_preview_but_completion_does(self):
        root,video,other,job=self.partial();before=db.get_state('downloads.inventory_revision')
        job.update(progress=.5,downloaded=2048,download_rate=5000);downloads._save_jobs([job])
        self.assertEqual(db.get_state('downloads.inventory_revision'),before)
        job.update(indexed=True,status='Indexed',verified_files=[dict(path=str(video),size=4096)]);downloads._save_jobs([job])
        self.assertNotEqual(db.get_state('downloads.inventory_revision'),before)

    def test_move_clears_old_scan_presence_and_organizer_row_immediately(self):
        file,root,job=self.completed();db.add_watched_directory(job['root'])
        watched=next(r for r in db.get_watched_directories() if Path(r['folder_path'])==Path(job['root']))
        # Seed a legacy scan snapshot that incorrectly included staging files.
        files={str(file):identity.signature(file)};scan_state.checkpoint(watched['id'],identity.path_key(job['root']),'legacy-snapshot',files,self.fid)
        from app.ui.pages.organizer_page import OrganizerPage
        page=OrganizerPage();self.addCleanup(page.deleteLater)
        self.assertTrue(any(r.get('download_job_id')==job['id'] for r in page._data['all']))
        stale_config=organizer_cache.configuration(page._rules);old_rows=json.loads(json.dumps(page._data))
        plan=download_library.preview(str(root));self.assertIn('1 files moved',download_library.move(plan))
        target=Path(plan['rows'][0]['target']);self.assertTrue(target.is_file());self.assertFalse(file.exists())
        page.apply_downloads([job])  # Even a delayed pre-move snapshot cannot restore it.
        self.assertFalse(any(r.get('download_job_id')==job['id'] for r in page._data['all']))
        with closing(db.get_connection()) as conn:
            self.assertEqual(conn.execute('SELECT present FROM scan_files WHERE path_key=?',(identity.path_key(file),)).fetchone()[0],0)
            self.assertIsNotNone(conn.execute('SELECT file_id FROM file_locations WHERE path_key=?',(identity.path_key(target),)).fetchone())
        page._on_scan_finished(dict(old_rows,_configuration=stale_config))
        self.assertFalse(any(r.get('download_job_id')==job['id'] for r in page._data['all']))
        self.assertFalse(organizer_cache.save_preview(dict(old_rows),stale_config))

    def test_review_disabled_until_verified_and_ready_after_completion(self):
        root,video,other,job=self.partial()
        from app.ui.pages.organizer_page import OrganizerPage
        page=OrganizerPage();self.addCleanup(page.deleteLater)
        self.assertFalse(page.table.cellWidget(0,3).findChild(QPushButton).isEnabled())
        page._on_select_all_toggled(Qt.Checked);self.assertFalse(page._selected_items)
        job.update(indexed=True,status='Indexed',verified_files=[dict(path=str(video),size=4096)]);downloads._save_jobs([job]);page.apply_downloads()
        self.assertTrue(page.table.cellWidget(0,3).findChild(QPushButton).isEnabled())
    def test_completed_job_is_not_imported_as_an_anime_named_after_its_folder(self):
        root,video,other,job=self.partial();isolated=root/'torrent-job';isolated.mkdir();video.rename(isolated/video.name);video=isolated/video.name
        job.update(root=str(isolated),destination=str(isolated),indexed=True,status='Indexed',verified_files=[dict(path=str(video),size=4096)])
        downloads._save_jobs([job]);db.add_watched_directory(str(root))
        scanner.scan_watched_directories(allow_network=False)
        titles={f['display_title'] for f in db.get_all_franchises()}
        self.assertNotIn('torrent-job',titles);self.assertIn('Other',titles)
        self.assertTrue(video.exists());self.assertTrue(other.exists())

    def test_move_in_progress_defers_inventory_without_marking_root_offline(self):
        file,root,job=self.completed();target=root/'One Piece'/'Season 02'/file.name
        job['library_move_intent']=[dict(source=str(file),target=str(target))];downloads._save_jobs([job])
        with self.assertRaises(download_inventory.InventoryDeferred):scan_state.inventory(root)
        self.assertTrue(file.exists());self.assertFalse(target.exists())
        job['library_move_error']='Destination already exists; review the remaining files.';downloads._save_jobs([job])
        row=download_inventory.organizer_rows()[0]
        self.assertEqual(row['status_badge'],'Move needs review');self.assertTrue(row['download_ready'])
        result=scanner.scan_watched_directories(allow_network=False)
        self.assertNotIn('INACCESSIBLE',result['root_states'].values())

    def test_scan_commit_and_move_do_not_interleave(self):
        root=Path(self.temp.name)/'library';anime=root/'Demo';anime.mkdir(parents=True)
        source=anime/'Demo - 01.mkv';source.write_bytes(b'video');target=anime/'Season 1'/source.name
        db.add_watched_directory(str(root));read=threading.Event();release=threading.Event();moved=threading.Event();errors=[]
        original=scan_state.inventory
        def inventory(folder,*args,**kwargs):
            result=original(folder,*args,**kwargs)
            if Path(folder)==anime.resolve():read.set();release.wait(5)
            return result
        def scan():
            try:scanner.scan_watched_directories(allow_network=False)
            except Exception as error:errors.append(error)
        def move():
            try:file_operations.move_file(source,target);moved.set()
            except Exception as error:errors.append(error)
        with patch.object(scan_state,'inventory',side_effect=inventory):
            worker=threading.Thread(target=scan);worker.start()
            try:
                self.assertTrue(read.wait(5));relocator=threading.Thread(target=move);relocator.start()
                self.assertFalse(moved.wait(.05))
            finally:release.set();worker.join(5)
            relocator.join(5)
        self.assertFalse(errors);self.assertTrue(moved.is_set());self.assertFalse(source.exists())
        with closing(db.get_connection()) as conn:
            self.assertEqual(conn.execute('SELECT present FROM scan_files WHERE path_key=?',(identity.path_key(source),)).fetchone()[0],0)
