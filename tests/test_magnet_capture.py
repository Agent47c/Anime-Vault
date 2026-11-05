"""Selected-site capture: no real registry edits, browser changes or downloads."""
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import unittest
from unittest.mock import Mock,patch
import test_ui_regressions as support
from app import db
from app.core import magnet_capture as inbox,chrome_bridge as bridge,downloads

MAGNET='magnet:?xt=urn:btih:'+'a'*40+'&dn=One+Piece+-+1170'
EXTENSION='a'*32


class MagnetCaptureTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown

    @classmethod
    def setUpClass(cls): support.Regressions.setUpClass.__func__(cls)

    def connect(self): db.set_state('chrome.capture_extension',EXTENSION)

    def test_valid_links_and_unsafe_payloads(self):
        self.assertEqual(inbox.validate(MAGNET)['name'],'One Piece - 1170')
        inbox.validate(MAGNET.replace('magnet:','MAGNET:'))
        inbox.validate('magnet:?xt=urn:btmh:1220'+'b'*64)
        for value in ['http://example.org',MAGNET+'\r\n',MAGNET+'" -c anything','magnet:?xt=urn:btih:bad','x'*17000,None]:
            with self.assertRaises(ValueError): inbox.validate(value)

    def test_queue_deduplicates_same_torrent_and_claims_one_at_a_time(self):
        identifier=inbox.enqueue(MAGNET)
        self.assertEqual(inbox.enqueue(MAGNET.replace('1170','1171')),identifier)
        item=inbox.next_link();self.assertEqual(item['id'],identifier)
        self.assertIsNone(inbox.next_link())
        self.assertEqual(inbox.next_link(reset_open=True)['id'],identifier)
        inbox.mark(identifier,'DISMISSED');self.assertIsNone(inbox.next_link())

    def test_queue_is_bounded(self):
        for n in range(32): inbox.enqueue(f'magnet:?xt=urn:btih:{n:040x}')
        with self.assertRaises(ValueError): inbox.enqueue('magnet:?xt=urn:btih:'+'f'*40)

    def test_submitting_without_a_job_is_recovered_but_existing_submission_is_not_resent(self):
        identifier=inbox.enqueue(MAGNET);inbox.next_link();inbox.mark(identifier,'SUBMITTING')
        self.assertEqual(inbox.next_link(reset_open=True)['id'],identifier)
        inbox.mark(identifier,'SUBMITTING')
        downloads._save_jobs([{'origin':'browser:'+identifier}])
        self.assertIsNone(inbox.next_link(reset_open=True))

    def test_only_connected_extension_and_selected_site_can_enqueue(self):
        self.connect()
        with self.assertRaises(ValueError): bridge.origin('https://*')
        good={'action':'capture','site':'https://nyaa.si','magnet':MAGNET}
        caller='chrome-extension://'+EXTENSION+'/'
        for message,origin in [(good,'chrome-extension://'+'b'*32+'/'),
            ({**good,'site':'https://other.example'},caller),
            ({**good,'site':'https://nyaa.si.evil.example'},caller),
            ({**good,'action':'execute'},caller)]:
            with self.assertRaises(ValueError): bridge.accept_message(message,origin)
        self.assertIsNone(inbox.next_link())
        identifier=bridge.accept_message(good,caller)
        self.assertEqual(inbox.next_link()['id'],identifier)

    def test_native_frames_are_bounded_and_unicode_roundtrips(self):
        output=io.BytesIO();value={'text':'日本語 ✓'}
        bridge.write_message(output,value)
        self.assertEqual(bridge.read_message(io.BytesIO(output.getvalue())),value)
        for payload in [b'',struct.pack('<I',70000),struct.pack('<I',5)+b'{}']:
            with self.assertRaises(ValueError): bridge.read_message(io.BytesIO(payload))

    def test_native_host_returns_only_framed_json_and_queues_before_launch(self):
        self.connect()
        message={'action':'capture','site':'https://nyaa.si','magnet':MAGNET}
        source=io.BytesIO();bridge.write_message(source,message);source.seek(0)
        output=io.BytesIO()
        def launch(): self.assertIsNotNone(inbox.next_link())
        with patch.object(bridge,'launch_desktop',side_effect=launch):
            result=bridge.run(['chrome-extension://'+EXTENSION+'/'],source,output)
        self.assertEqual(result,0)
        response=bridge.read_message(io.BytesIO(output.getvalue()))
        self.assertTrue(response['ok']);self.assertNotIn(MAGNET,output.getvalue().decode('utf-8',errors='ignore'))

    def test_invalid_native_payload_is_not_echoed_and_cannot_launch_app(self):
        output=io.BytesIO()
        with patch.object(bridge,'launch_desktop') as launch:
            result=bridge.run(['invalid'],io.BytesIO(struct.pack('<I',2)+b'{}'),output)
        self.assertEqual(result,1);launch.assert_not_called()
        self.assertFalse(bridge.read_message(io.BytesIO(output.getvalue()))['ok'])

    def test_registration_only_writes_chrome_native_host_key(self):
        registry=Mock()
        registry.HKEY_CURRENT_USER='HKCU';registry.KEY_SET_VALUE=2;registry.REG_SZ=1
        key=Mock();key.__enter__=Mock(return_value=key);key.__exit__=Mock(return_value=False)
        registry.CreateKeyEx.return_value=key
        with patch.dict('sys.modules',{'winreg':registry}),patch.object(bridge.sys,'platform','win32'):
            bridge.register(EXTENSION)
        self.assertEqual(registry.CreateKeyEx.call_count,1)
        self.assertEqual(registry.CreateKeyEx.call_args.args[:2],('HKCU',r'Software\Google\Chrome\NativeMessagingHosts\com.animevault.capture'))
        manifest=json.loads((db.DATA_DIR/'chrome-bridge'/'host.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['allowed_origins'],['chrome-extension://'+EXTENSION+'/'])
        command=(db.DATA_DIR/'chrome-bridge'/'host.cmd').read_text(encoding='utf-8')
        self.assertNotIn('magnet:',command)
        self.assertIn('chrome_magnet_host.py',command)
        self.assertEqual(db.get_state('chrome.capture_extension'),EXTENSION)

    def test_bad_extension_id_does_not_register(self):
        with self.assertRaises(ValueError): bridge.register('not-an-extension-id')

    def test_existing_desktop_is_not_launched_twice(self):
        with patch('PyQt5.QtCore.QLockFile') as lock,patch.object(bridge.subprocess,'Popen') as launch:
            lock.return_value.tryLock.return_value=False
            bridge.launch_desktop();launch.assert_not_called()

    def test_closed_desktop_launches_with_fixed_arguments_only(self):
        with patch('PyQt5.QtCore.QLockFile') as lock,patch.object(bridge.subprocess,'Popen') as launch:
            lock.return_value.tryLock.return_value=True
            bridge.launch_desktop()
        arguments=launch.call_args.args[0]
        self.assertEqual(arguments[-1],'--from-browser')
        self.assertFalse(any('magnet:' in arg for arg in arguments))

    def test_suggestion_requires_unique_exact_title(self):
        self.assertEqual(inbox.suggestion('[ASW] One Piece - 1170 [1080p].mkv',[{'id':1,'display_title':'One Piece'}]),1)
        self.assertIsNone(inbox.suggestion('Something else',[{'id':1,'display_title':'One Piece'}]))
        self.assertIsNone(inbox.suggestion('One Piece',[{'id':1,'display_title':'One Piece'},{'id':2,'display_title':'One Piece'}]))

    def test_browser_retry_reuses_existing_job_without_second_api_add(self):
        config={**downloads.DEFAULTS,'enabled':True,'destination':self.temp.name}
        db.set_state('downloads.settings',json.dumps(config))
        item_id=inbox.enqueue(MAGNET);item=inbox.next_link()
        client=Mock();client.call.return_value=Mock(text='Ok.')
        with patch.object(downloads,'Client',return_value=client):
            first=inbox.submit(item,self.fid,0)
            second=inbox.submit(item,self.fid,0)
        self.assertEqual(first,second);self.assertEqual(client.call.call_count,1)
        self.assertEqual(len(downloads.jobs()),1)

    def test_uncertain_browser_submission_cannot_be_blindly_duplicated(self):
        config={**downloads.DEFAULTS,'enabled':True,'destination':self.temp.name}
        db.set_state('downloads.settings',json.dumps(config))
        inbox.enqueue(MAGNET);item=inbox.next_link()
        client=Mock();client.call.side_effect=TimeoutError('uncertain')
        with patch.object(downloads,'Client',return_value=client):
            with self.assertRaises(TimeoutError): inbox.submit(item,self.fid,0)
            with self.assertRaises(ValueError): inbox.submit(item,self.fid,0)
        self.assertEqual(client.call.call_count,1)

    def test_captured_link_is_prefilled_but_never_downloaded_without_confirmation(self):
        from app.ui.magnet_capture import MagnetReview
        from PyQt5.QtTest import QTest
        import time
        inbox.enqueue(MAGNET);item=inbox.next_link()
        with patch.object(downloads,'add_download') as download:
            dialog=MagnetReview(item)
            self.assertEqual(dialog.item['uri'],MAGNET)
            self.assertEqual(dialog.anime.currentData(),self.fid)
            download.assert_not_called()
            dialog.reject()
            end=time.monotonic()+5
            while getattr(dialog,'_apply_worker',None) is not None and time.monotonic()<end: QTest.qWait(5)
            download.assert_not_called()
        self.assertIsNone(inbox.next_link())
        dialog.deleteLater()

    @unittest.skipUnless(shutil.which('node'),'Node.js is required for extension behavior tests')
    def test_chrome_extension_behaviors(self):
        root=Path(__file__).resolve().parents[1]
        result=subprocess.run(['node','--test','browser-extension/tests/capture.test.js'],cwd=root,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
