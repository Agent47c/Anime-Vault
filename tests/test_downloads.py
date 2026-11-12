"""Download integration tests never contact a website/client or start a torrent."""
import json
from pathlib import Path
import unittest
from unittest.mock import Mock,patch
from urllib.parse import urlsplit,parse_qs
import test_ui_regressions as support
from app import db
from app.core import downloads as service


class DownloadTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown

    @classmethod
    def setUpClass(cls): support.Regressions.setUpClass.__func__(cls)

    def enable(self):
        config={**service.DEFAULTS,'enabled':True,'destination':str(Path(self.temp.name)/'downloads')}
        db.set_state('downloads.settings',json.dumps(config))

    def item(self):
        from contextlib import closing
        with closing(db.get_connection()) as conn,conn:
            conn.execute('INSERT OR IGNORE INTO library_series(franchise_id) VALUES (?)',(self.fid,))
            series_id=conn.execute('SELECT id FROM library_series WHERE franchise_id=?',(self.fid,)).fetchone()[0]
        root=Path(self.temp.name)/'finished'
        target=root/'Season 02';target.mkdir(parents=True)
        file=target/'Example Anime S02E10.mkv';file.write_bytes(b'video')
        return {'id':'abc','tag':'AnimeVault-abc','fid':self.fid,'series_id':series_id,'title':'One Piece',
                'root':str(root),'destination':str(target),'progress':0,'status':'Downloading','created':0,'engine':'builtin','desired':'running'},file

    def test_search_encodes_once_and_preserves_website_filters(self):
        query=service.make_query('Kizoku Tensei','10','[ASW]','1080p')
        values=parse_qs(urlsplit(service.search_url(service.DEFAULTS['source'],query)).query)
        self.assertEqual(values['q'],['[ASW] Kizoku Tensei 10 1080p'])
        self.assertEqual(values['f'],['0']);self.assertEqual(values['c'],['0_0'])
        with self.assertRaises(ValueError): service.search_url('javascript:alert(1)','test')
        with self.assertRaises(ValueError): service.search_url('https://{query}.example.test/?q=x','test')
        with self.assertRaises(ValueError): service.search_url('https://example.test/?q=old','test')

    def test_connection_checks_native_helper_without_external_login(self):
        probe=Mock();probe.call.return_value='test-version'
        with patch('app.core.builtin_torrents.EngineClient',return_value=probe):
            self.assertIn('test-version',service.test_connection({'engine':'qbittorrent'}))
        probe.call.assert_called_once_with('version');probe.close.assert_called_once()

    def test_legacy_settings_migrate_without_credentials(self):
        db.set_state('downloads.settings',json.dumps(dict(engine='qbittorrent',enabled=True,destination=self.temp.name,secret='old-secret',url='http://localhost:8080',username='admin')))
        self.assertEqual(service.settings()['engine'],'builtin')
        service.save_settings({},'do-not-save-password')
        saved=json.loads(db.get_state('downloads.settings'))
        self.assertEqual(saved['engine'],'builtin')
        for key in ('url','username','secret'):self.assertNotIn(key,saved)
        self.assertNotIn('do-not-save-password',json.dumps(saved))

    def adapter(self):
        adapter=Mock()
        adapter.snapshot.return_value={'status':'Downloading','files':[]}
        def prepare(item,source):item['torrent_identity']='a'*40;return object()
        adapter.prepare.side_effect=prepare
        return adapter

    def test_add_uses_native_and_fresh_destination_without_touching_media(self):
        self.enable();adapter=self.adapter()
        with patch('app.core.builtin_torrents.engine',return_value=adapter):
            destination=service.add_download(self.fid,'magnet:?xt=urn:btih:'+'a'*40,2)
        row=service.jobs()[0]
        self.assertEqual(row['destination'],destination)
        self.assertEqual(row['engine'],'builtin')
        self.assertFalse(Path(destination).exists())
        self.assertTrue(row['selection_confirmed'])
        self.assertEqual(row['desired'],'running')
        self.assertTrue(row['source_ref'].startswith('magnet:'))
        adapter.attach.assert_called_once()
        self.assertEqual(db.get_franchise(self.fid)['anilist_id'],21)

    def test_failed_native_attachment_retains_source_and_episode_identity_for_retry(self):
        self.enable();adapter=self.adapter();adapter.attach.side_effect=TimeoutError('engine timed out')
        with patch('app.core.builtin_torrents.engine',return_value=adapter),self.assertRaises(TimeoutError):
            service.add_download(self.fid,'magnet:?xt=urn:btih:'+'a'*40,2,context={'episode_keys':['EPISODE:S2:10'],'season':2})
        job=service.jobs()[0]
        self.assertIn('Needs review',job['status'])
        self.assertTrue(job['source_ref']);self.assertEqual(job['episode_keys'],['EPISODE:S2:10'])
        from app.core.magnet_capture import validate
        self.assertEqual(job['source_identity'],validate(job['source_ref'])['identity'])

    def test_legacy_retry_creates_native_job_without_touching_existing_files(self):
        from app.core import download_queue
        self.enable();old,file=self.item();old.update(engine='qbittorrent',source_ref='magnet:?xt=urn:btih:'+'a'*40,season=2,episode_keys=['EPISODE:S2:10'])
        service._save_jobs([old]);adapter=self.adapter()
        with patch('app.core.builtin_torrents.engine',return_value=adapter),patch('requests.sessions.Session.request',side_effect=AssertionError('No external client')):
            message=download_queue.action(old['id'],'retry')
            download_queue.action(old['id'],'retry')
        self.assertIn('Anime Vault',message)
        rows=service.jobs();self.assertEqual(len(rows),1)
        native=next(row for row in rows if row['engine']=='builtin')
        self.assertNotEqual(native['destination'],old['destination'])
        self.assertEqual(native['id'],old['id'])
        self.assertEqual(native['episode_keys'],old['episode_keys'])
        self.assertEqual(file.read_bytes(),b'video')

    def test_external_history_is_not_polled_and_missing_source_remains_reviewable(self):
        from app.core import download_queue
        self.enable();old,file=self.item();old['engine']='qbittorrent';service._save_jobs([old])
        with patch('requests.sessions.Session.request',side_effect=AssertionError('No external client')):
            rows,changed=service.poll()
            self.assertFalse(changed);self.assertIn('external client removed',rows[0]['status'])
            with self.assertRaisesRegex(ValueError,'link was not saved'):download_queue.action(old['id'],'retry')
        self.assertEqual(file.read_bytes(),b'video')

    def test_failed_legacy_retry_before_native_submission_keeps_retryable_history(self):
        from app.core import download_queue
        self.enable();old,file=self.item();old.update(engine='qbittorrent',source_ref='magnet:?xt=urn:btih:'+'a'*40)
        service._save_jobs([old]);adapter=self.adapter();adapter.prepare.side_effect=ValueError('Cannot start engine')
        with patch('app.core.builtin_torrents.engine',return_value=adapter),self.assertRaisesRegex(ValueError,'Cannot start engine'):
            download_queue.action(old['id'],'retry')
        rows=service.jobs();self.assertEqual(len(rows),1)
        self.assertIn('Native retry failed',rows[0]['status']);self.assertEqual(rows[0]['desired'],'running')
        self.assertEqual(file.read_bytes(),b'video')

    def completed_snapshot(self,item,file):
        return dict(complete=True,status='Complete',progress=1,files=[dict(name=file.name,size=5,progress=1,priority=1)])

    def test_completed_file_validation_blocks_escape_partial_and_wrong_path(self):
        item,file=self.item()
        entry={'name':file.name,'size':5,'progress':1,'priority':1}
        info={'save_path':item['destination']}
        self.assertEqual(service._completed_files(item,info,[entry]),[file.resolve()])
        for changed in ({**entry,'name':'../../outside.mkv'},{**entry,'progress':.5},{**entry,'size':9}):
            with self.assertRaises(ValueError): service._completed_files(item,info,[changed])
        with self.assertRaises(ValueError): service._completed_files(item,{'save_path':self.temp.name},[entry])

    def test_monitor_indexes_only_completed_tracked_torrent_once(self):
        self.enable();item,file=self.item();service._save_jobs([item])
        adapter=self.adapter();adapter.snapshot.return_value=self.completed_snapshot(item,file)
        with patch('app.core.builtin_torrents.engine',return_value=adapter),patch('app.core.scanner._update_on_disk_info') as index:
            items,changed=service.poll()
            self.assertTrue(changed);self.assertTrue(items[0]['indexed'])
            self.assertEqual(index.call_count,1)
            service.poll();self.assertEqual(index.call_count,1)
        self.assertEqual(file.read_bytes(),b'video')

    def test_incomplete_or_hash_checking_torrents_are_never_indexed(self):
        self.enable();item,file=self.item()
        for progress,state in ((.9,'downloading'),(1,'checkingUP'),(1,'moving'),(1,'missingFiles')):
            service._save_jobs([item])
            adapter=self.adapter();adapter.snapshot.return_value=dict(status=state,complete=False,progress=progress,files=[])
            with patch('app.core.builtin_torrents.engine',return_value=adapter),patch('app.core.scanner._update_on_disk_info') as index:
                self.assertFalse(service.poll()[1]);index.assert_not_called()

    def test_missing_file_remains_visible_and_retryable(self):
        self.enable();item,file=self.item();service._save_jobs([item]);file.unlink()
        adapter=self.adapter();adapter.snapshot.return_value=self.completed_snapshot(item,file)
        with patch('app.core.builtin_torrents.engine',return_value=adapter),patch('app.core.scanner._update_on_disk_info') as index:
            items,changed=service.poll();index.assert_not_called()
        self.assertFalse(changed);self.assertIn('Needs review',items[0]['status'])

    def test_real_completed_index_preserves_existing_folder_and_notes(self):
        from app.core.scanner import _update_on_disk_info
        old=Path(self.temp.name)/'old-anime';old.mkdir()
        old_file=old/'One Piece - 001.mkv';old_file.write_bytes(b'old-video')
        _update_on_disk_info(self.fid,str(old))
        db.update_franchise_field(self.fid,'user_notes','Keep my notes')
        self.enable();item,file=self.item();service._save_jobs([item])
        adapter=self.adapter();adapter.snapshot.return_value=self.completed_snapshot(item,file)
        with patch('app.core.builtin_torrents.engine',return_value=adapter):
            items,changed=service.poll()
        self.assertTrue(changed)
        record=db.get_franchise(self.fid)
        self.assertEqual(Path(record['root_folder_path']).resolve(),old.resolve())
        self.assertEqual(record['user_notes'],'Keep my notes')
        indexed=[name for season in db.get_seasons_for_franchise(self.fid) for name in json.loads(season['video_files_json'] or '[]')]
        self.assertEqual(len(indexed),2)
        self.assertEqual(old_file.read_bytes(),b'old-video')
        self.assertEqual(file.read_bytes(),b'video')

    def test_deleted_and_reused_franchise_id_cannot_capture_old_download(self):
        from contextlib import closing
        self.enable();item,file=self.item();service._save_jobs([item])
        with closing(db.get_connection()) as conn,conn:
            conn.execute('DELETE FROM franchises WHERE id=?',(self.fid,))
            conn.execute('INSERT INTO franchises(id,display_title) VALUES (?,?)',(self.fid,'Unrelated new anime'))
        adapter=self.adapter();adapter.snapshot.return_value=self.completed_snapshot(item,file)
        with patch('app.core.builtin_torrents.engine',return_value=adapter),patch('app.core.scanner._update_on_disk_info') as index:
            rows,changed=service.poll();index.assert_not_called()
        self.assertFalse(changed);self.assertIn('identity changed',rows[0]['status'])
