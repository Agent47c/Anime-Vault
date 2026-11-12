"""Built-in engine regressions use generated media and loopback peers only."""
import json
import time
from pathlib import Path
from unittest.mock import patch
import unittest
import test_ui_regressions as support
from app import db
from app.core import downloads as service, builtin_torrents as native


class BuiltinTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown

    @classmethod
    def setUpClass(cls): support.Regressions.setUpClass.__func__(cls)

    def config(self):
        config={**service.DEFAULTS,'engine':'builtin','enabled':True,'destination':str(Path(self.temp.name)/'downloads')}
        db.set_state('downloads.settings',json.dumps(config))
        return config

    def torrent(self):
        lt=native.library()
        root=Path(self.temp.name)/'source';folder=root/'Release';folder.mkdir(parents=True)
        (folder/'Episode 01.mkv').write_bytes(b'first-episode-'*65536)
        (folder/'Episode 02.mkv').write_bytes(b'second-episode-'*65536)
        import hashlib
        paths=sorted(folder.iterdir())
        content=b''.join(p.read_bytes() for p in paths)
        info={b'name':b'Release',b'piece length':16384,
              b'files':[{b'length':p.stat().st_size,b'path':[p.name.encode()]} for p in paths],
              b'pieces':b''.join(hashlib.sha1(content[i:i+16384]).digest() for i in range(0,len(content),16384))}
        path=Path(self.temp.name)/'release.torrent'
        path.write_bytes(lt.bencode({b'info':info}))
        return path,root

    def test_native_default_and_validate_limits(self):
        self.assertEqual(service.settings()['engine'],'builtin')
        service.save_settings({'engine':'builtin','url':'unused','destination':self.temp.name,'download_limit_kib':64})
        self.assertEqual(service.settings()['download_limit_kib'],64)
        self.assertIn('libtorrent',service.test_connection({'engine':'builtin'}))
        for change in ({'engine':'unknown'},{'upload_limit_kib':-1}):
            with self.assertRaises(ValueError): service.save_settings(change)

    def test_native_selection_resume_and_cancel_keep_files(self):
        config=self.config();path,source=self.torrent()
        adapter=native.EngineClient(config,network=False)
        with patch.object(native,'engine',return_value=adapter):
            try:
                destination=service.add_download(self.fid,str(path),2,origin='browser:test')
                job=service.jobs()[0]
                self.assertTrue(job['submission_confirmed'])
                self.assertEqual(job['engine'],'builtin')
                self.assertEqual(service.add_download(self.fid,str(path),2,origin='browser:test'),destination)
                entries=service.builtin_files(job['id'])
                self.assertEqual(len(entries),2)
                self.assertTrue(all(e['priority']==4 for e in entries))
                service.control_builtin(job['id'],'resume')
                with self.assertRaises(ValueError): service.control_builtin(job['id'],'files',[])
                service.control_builtin(job['id'],'files',[0])
                job=service.jobs()[0]
                self.assertEqual(job['selected_files'],[0]);self.assertTrue(job['selection_confirmed'])
                self.assertEqual([e['priority'] for e in service.builtin_files(job['id'])],[4,0])
                service.control_builtin(job['id'],'pause')
                adapter.close()
                self.assertTrue((adapter.folder/(job['id']+'.resume')).is_file())
                adapter=native.EngineClient(config,network=False)
                # Replace the adapter returned by the surrounding mock.
                native.engine.return_value=adapter
                restored=service.builtin_files(job['id'])
                self.assertEqual([e['priority'] for e in restored],[4,0])
                marker=Path(destination)/'keep.txt';marker.write_text('Keep me')
                service.control_builtin(job['id'],'cancel')
                self.assertEqual(marker.read_text(),'Keep me')
                self.assertIn('Cancelled',service.jobs()[0]['status'])
            finally:
                adapter.close()

    def test_duplicate_torrent_is_blocked_and_invalid_files_are_not_submitted(self):
        config=self.config();path,_=self.torrent()
        adapter=native.EngineClient(config,network=False)
        with patch.object(native,'engine',return_value=adapter):
            try:
                service.add_download(self.fid,str(path))
                with self.assertRaises(ValueError): service.add_download(self.fid,str(path))
                with self.assertRaises(ValueError): service.add_download(self.fid,'magnet:?xt=urn:btih:bad')
                self.assertEqual(len(service.jobs()),1)
            finally: adapter.close()

    def test_unsafe_metadata_and_windows_collisions_are_blocked(self):
        from unittest.mock import Mock
        info=Mock();files=Mock();info.files.return_value=files
        files.num_files.return_value=1;files.file_size.return_value=10;files.file_flags.return_value=0
        for name in ('../outside.mkv','C:/outside.mkv','folder/CON.mkv','folder/name.mkv:stream','folder/trailing./file'):
            files.file_path.return_value=name
            with self.assertRaises(ValueError,msg=name): native.safe_files(info)
        files.file_path.side_effect=['folder/A.mkv','folder/a.mkv'];files.num_files.return_value=2
        with self.assertRaises(ValueError): native.safe_files(info)

    def test_completion_only_indexes_verified_selected_files_once(self):
        from unittest.mock import Mock
        config=self.config();path,_=self.torrent()
        adapter=native.EngineClient(config,network=False)
        with patch.object(native,'engine',return_value=adapter):
            try:
                destination=service.add_download(self.fid,str(path))
                item=service.jobs()[0]
                target=Path(destination)/'Release'/'Episode 01.mkv';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'video')
                snapshot={'status':'Complete','progress':1,'complete':True,'files':[
                    {'name':'Release/Episode 01.mkv','size':5,'priority':4,'progress':1},
                    {'name':'Release/Episode 02.mkv','size':8,'priority':0,'progress':0}]}
                with patch.object(adapter,'snapshot',return_value=snapshot),patch('app.core.scanner._update_on_disk_info') as index:
                    self.assertTrue(service.poll()[1]);self.assertFalse(service.poll()[1])
                    self.assertEqual(index.call_count,1)
                    self.assertEqual(list(index.call_args.kwargs['inventory']),[str(target.resolve())])
                    target.unlink();items=service.jobs();items[0]['indexed']=False;service._save_jobs(items)
                    self.assertFalse(service.poll()[1]);self.assertIn('Needs review',service.jobs()[0]['status'])
            finally: adapter.close()

    def test_virtual_file_model_handles_large_selection_without_widgets(self):
        from app.ui.downloads import TorrentFileModel
        from PyQt5.QtCore import Qt
        model=TorrentFileModel([dict(name=f'EP {i}.mkv',size=1024,priority=0) for i in range(10000)])
        self.assertEqual(model.rowCount(),10000)
        model.select_all(False);self.assertEqual(model.selected,set())
        model.setData(model.index(9999),Qt.Checked,Qt.CheckStateRole)
        self.assertEqual(model.selected,{9999})

    def test_helper_failure_preserves_job_for_restart_recovery(self):
        config=self.config();path,_=self.torrent()
        adapter=native.EngineClient(config,network=False)
        with patch.object(native,'engine',return_value=adapter):
            try:
                service.add_download(self.fid,str(path))
                before=service.jobs()[0]
                adapter.process.kill();adapter.process.wait(timeout=5)
                with self.assertRaises(ValueError): service.builtin_files(before['id'])
                self.assertEqual(service.jobs()[0]['id'],before['id'])
                self.assertTrue((adapter.folder/(before['id']+'.torrent')).exists())
            finally: adapter.close()

    def test_drawer_is_native_only_and_has_no_external_credentials(self):
        from app.ui.downloads import DownloadsDrawer
        self.config()
        drawer=DownloadsDrawer(fid=self.fid)
        drawer.show();self.app.processEvents()
        self.assertEqual(drawer.engine.currentData(),'builtin')
        self.assertEqual(drawer.engine.count(),1)
        self.assertFalse(hasattr(drawer,'password_input'))
        self.assertNotIn('url',drawer.controls)
        self.assertNotIn('username',drawer.controls)
        self.assertTrue(drawer.seed.isVisible())
        drawer.timer.stop();drawer.hide();drawer.deleteLater()

    def test_native_loopback_transfer_hashes_and_excludes_unselected_episode(self):
        import subprocess,sys
        result=subprocess.run([sys.executable,'scripts/check_builtin_engine.py'],capture_output=True,text=True,timeout=35)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
