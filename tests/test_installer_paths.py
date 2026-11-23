"""Installed-data isolation without touching real AppData or development data."""
import tempfile
import unittest
import io
import json
import struct
from unittest.mock import patch
from pathlib import Path
from app.paths import data_directory, native_torrent_executable


class InstallerPathTests(unittest.TestCase):
    def test_payload_allows_public_ca_bundle_but_rejects_private_data(self):
        from build_exe import verify_payload
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cert = root / 'engine' / '_internal' / 'certifi' / 'cacert.pem'
            cert.parent.mkdir(parents=True)
            cert.write_bytes(b'Public certificate fixture')
            verify_payload(root)
            cert.write_bytes(b'PRIVATE KEY fixture')
            with self.assertRaises(RuntimeError):
                verify_payload(root)
            cert.write_bytes(b'Public certificate fixture')
            (root / 'library.db').write_bytes(b'fixture')
            with self.assertRaises(RuntimeError):
                verify_payload(root)

    def test_native_engine_uses_separate_bundle_and_missing_files_fail_clearly(self):
        with tempfile.TemporaryDirectory() as temporary:
            gui = Path(temporary) / 'AnimeVault.exe'
            with self.assertRaisesRegex(ValueError, 'download engine is missing'):
                native_torrent_executable(gui)
            host = gui.parent / 'engine' / 'AnimeVaultTorrentHost.exe'
            host.parent.mkdir()
            host.write_bytes(b'fixture')
            self.assertEqual(native_torrent_executable(gui), host)
    def test_windowed_chrome_host_uses_native_pipes_without_console_streams(self):
        from app.core import chrome_bridge
        class Pipe(io.BytesIO):
            def fileno(self):
                return 0
        payload = json.dumps({'action': 'fixture'}).encode()
        incoming = Pipe(struct.pack('<I', len(payload)) + payload)
        outgoing = Pipe()
        with patch('builtin_torrent_host.binary_stream', side_effect=[incoming, outgoing]) as streams, \
                patch('msvcrt.setmode'), patch('sys.stdin', None), patch('sys.stdout', None), \
                patch.object(chrome_bridge, 'accept_message', side_effect=ValueError('Fixture rejection')):
            result = chrome_bridge.run(['chrome-extension://' + 'a' * 32 + '/'])
        self.assertEqual(result, 1)
        self.assertEqual(streams.call_count, 2)
        self.assertFalse(json.loads(outgoing.getvalue()[4:])['ok'])

    def test_source_default_stays_in_checkout(self):
        root = Path(tempfile.gettempdir()) / 'Source Fixture'
        self.assertEqual(data_directory(frozen=False, environ={}, source_root=root), root / 'data')

    def test_installed_profile_never_uses_program_or_source_folder(self):
        local = Path(tempfile.gettempdir()) / 'AppData Fixture' / 'Local'
        source = local / 'Programs' / 'Anime Vault' / '_internal'
        self.assertEqual(data_directory(frozen=True, environ={'LOCALAPPDATA': str(local)}, source_root=source), local / 'AnimeVault')

    def test_installed_fallback_is_per_user(self):
        home = Path(tempfile.gettempdir()) / 'Account Fixture'
        self.assertEqual(data_directory(frozen=True, environ={}, home=home), home / 'AppData' / 'Local' / 'AnimeVault')

    def test_explicit_test_override_requires_absolute_location(self):
        with self.assertRaises(ValueError):
            data_directory(frozen=True, environ={'ANIMEVAULT_DATA_DIR': 'relative-data'})
        target = Path(tempfile.gettempdir()) / 'Isolated Fixture'
        self.assertEqual(data_directory(frozen=True, environ={'ANIMEVAULT_DATA_DIR': str(target)}), target)

    def test_setup_does_not_delete_or_bundle_user_data(self):
        root = Path(__file__).resolve().parents[1]
        setup = (root / 'installer' / 'AnimeVault.iss').read_text(encoding='utf-8')
        self.assertNotIn('[UninstallDelete]', setup)
        self.assertIn('AnimeVault.Installed.Desktop', setup)
        self.assertIn('DefaultDirName=C:\\Program Files\\Anime Vault', setup)
        self.assertNotIn('library.db', setup)

    def test_setup_allows_a_destination_and_avoids_reboot_replacements(self):
        setup = (Path(__file__).resolve().parents[1] / 'installer' / 'AnimeVault.iss').read_text(encoding='utf-8')
        self.assertIn('DisableDirPage=no', setup)
        self.assertIn('UsePreviousAppDir=yes', setup)
        self.assertIn('AlwaysRestart=no', setup)
        self.assertNotIn('restartreplace', setup.lower())
        self.assertNotIn('taskkill', setup.lower())
