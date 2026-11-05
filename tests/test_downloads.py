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
                'root':str(root),'destination':str(target),'progress':0,'status':'Downloading','created':0},file

    def test_search_encodes_once_and_preserves_website_filters(self):
        query=service.make_query('Kizoku Tensei','10','[ASW]','1080p')
        values=parse_qs(urlsplit(service.search_url(service.DEFAULTS['source'],query)).query)
        self.assertEqual(values['q'],['[ASW] Kizoku Tensei 10 1080p'])
        self.assertEqual(values['f'],['0']);self.assertEqual(values['c'],['0_0'])
        with self.assertRaises(ValueError): service.search_url('javascript:alert(1)','test')
        with self.assertRaises(ValueError): service.search_url('https://{query}.example.test/?q=x','test')
        with self.assertRaises(ValueError): service.search_url('https://example.test/?q=old','test')

    def test_connection_requires_loopback_and_uses_session_login(self):
        with self.assertRaises(ValueError): service.validate_url('http://192.168.1.2:8080',True)
        with self.assertRaises(ValueError): service.validate_url('http://user:password@127.0.0.1:8080',True)
        session=Mock();session.headers={}
        session.request.return_value=Mock(status_code=200,text='Ok.')
        with patch.object(service.requests,'Session',return_value=session),patch.object(service,'password',return_value='secret'):
            client=service.Client(service.DEFAULTS);client.close()
        args,kwargs=session.request.call_args
        self.assertEqual(args[0],'POST')
        self.assertTrue(args[1].endswith('/api/v2/auth/login'))
        self.assertEqual(kwargs['data'],{'username':'admin','password':'secret'})
        self.assertFalse(kwargs['allow_redirects']);self.assertFalse(session.trust_env)

    def test_password_persistence_contains_encrypted_blob_only(self):
        with patch.object(service,'protect',return_value='encrypted-for-windows-user'):
            service.save_settings({'destination':self.temp.name},'secret-password')
        saved=db.get_state('downloads.settings')
        self.assertNotIn('secret-password',saved)
        self.assertEqual(json.loads(saved)['secret'],'encrypted-for-windows-user')

    def test_windows_secret_roundtrip(self):
        try:
            import win32crypt
        except ImportError:
            self.skipTest('Windows DPAPI is not available')
        encrypted=service.protect('temporary-test-password')
        self.assertNotIn('temporary-test-password',encrypted)
        self.assertEqual(service.password({'secret':encrypted}),'temporary-test-password')

    def test_add_sets_unique_tag_and_fresh_destination_without_touching_media(self):
        self.enable()
        client=Mock();client.call.return_value=Mock(text='Ok.')
        with patch.object(service,'Client',return_value=client):
            destination=service.add_download(self.fid,'magnet:?xt=urn:btih:'+'a'*40,2)
        row=service.jobs()[0]
        self.assertEqual(row['destination'],destination)
        self.assertFalse(Path(destination).exists())
        data=client.call.call_args.kwargs['data']
        self.assertEqual(data['savepath'],destination)
        self.assertEqual(data['tags'],row['tag']);self.assertEqual(data['autoTMM'],'false')
        self.assertEqual(data['paused'],'true');self.assertEqual(data['stopped'],'true')
        self.assertEqual(db.get_franchise(self.fid)['anilist_id'],21)

    def test_uncertain_submission_retains_job_for_reconciliation(self):
        self.enable()
        client=Mock();client.call.side_effect=TimeoutError('connection timed out')
        with patch.object(service,'Client',return_value=client),self.assertRaises(TimeoutError):
            service.add_download(self.fid,'magnet:?xt=urn:btih:'+'a'*40)
        self.assertIn('unconfirmed',service.jobs()[0]['status'])

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
        client=Mock()
        def response(route,**kwargs):
            if route=='torrents/info':
                self.assertEqual(kwargs['params'],{'tag':item['tag']})
                return Mock(json=lambda:[{'hash':'abc','progress':1,'state':'uploading','save_path':item['destination']}])
            return Mock(json=lambda:[{'name':file.name,'size':5,'progress':1,'priority':1}])
        client.call.side_effect=response
        with patch.object(service,'Client',return_value=client),patch('app.core.scanner._update_on_disk_info') as index:
            items,changed=service.poll()
            self.assertTrue(changed);self.assertEqual(items[0]['status'],'Indexed')
            self.assertEqual(index.call_count,1)
            service.poll();self.assertEqual(index.call_count,1)
        self.assertEqual(file.read_bytes(),b'video')

    def test_incomplete_or_hash_checking_torrents_are_never_indexed(self):
        self.enable();item,file=self.item()
        for progress,state in ((.9,'downloading'),(1,'checkingUP'),(1,'moving'),(1,'missingFiles')):
            service._save_jobs([item])
            client=Mock();client.call.return_value=Mock(json=lambda:[{'progress':progress,'state':state}])
            with patch.object(service,'Client',return_value=client),patch('app.core.scanner._update_on_disk_info') as index:
                self.assertFalse(service.poll()[1]);index.assert_not_called()

    def test_missing_file_remains_visible_and_retryable(self):
        self.enable();item,file=self.item();service._save_jobs([item]);file.unlink()
        client=Mock()
        client.call.side_effect=[Mock(json=lambda:[{'hash':'abc','progress':1,'state':'uploading','save_path':item['destination']}]),
                                 Mock(json=lambda:[{'name':file.name,'size':5,'progress':1,'priority':1}])]
        with patch.object(service,'Client',return_value=client),patch('app.core.scanner._update_on_disk_info') as index:
            items,changed=service.poll();index.assert_not_called()
        self.assertFalse(changed);self.assertIn('Needs review',items[0]['status'])

    def test_real_completed_index_preserves_existing_folder_and_notes(self):
        from app.core.scanner import _update_on_disk_info
        old=Path(self.temp.name)/'old-anime';old.mkdir()
        old_file=old/'One Piece - 001.mkv';old_file.write_bytes(b'old-video')
        _update_on_disk_info(self.fid,str(old))
        db.update_franchise_field(self.fid,'user_notes','Keep my notes')
        self.enable();item,file=self.item();service._save_jobs([item])
        client=Mock()
        client.call.side_effect=[Mock(json=lambda:[{'hash':'abc','progress':1,'state':'uploading','save_path':item['destination']}]),
                                 Mock(json=lambda:[{'name':file.name,'size':5,'progress':1,'priority':1}])]
        with patch.object(service,'Client',return_value=client):
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
        client=Mock()
        client.call.side_effect=[Mock(json=lambda:[{'hash':'abc','progress':1,'state':'uploading','save_path':item['destination']}]),
                                 Mock(json=lambda:[{'name':file.name,'size':5,'progress':1,'priority':1}])]
        with patch.object(service,'Client',return_value=client),patch('app.core.scanner._update_on_disk_info') as index:
            rows,changed=service.poll();index.assert_not_called()
        self.assertFalse(changed);self.assertIn('identity changed',rows[0]['status'])
