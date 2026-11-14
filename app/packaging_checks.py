"""Explicit standalone-build checks, isolated from every real user profile."""
import json
import os
import sys
import tempfile
import time
import traceback
from pathlib import Path


def run(arguments):
    if len(arguments) != 1:
        return 2
    report_file = Path(arguments[0]).resolve()
    report = {'ok': False, 'frozen': bool(getattr(sys, 'frozen', False)), 'checks': []}
    try:
        with tempfile.TemporaryDirectory(prefix='AnimeVault-package-check-') as directory:
            root = Path(directory)
            os.environ['ANIMEVAULT_DATA_DIR'] = str(root / 'profile')
            os.environ['QT_QPA_PLATFORM'] = 'offscreen'
            os.environ['OFFLINE_MODE'] = 'true'
            os.environ['APP_PROFILE'] = '0'
            from app import db, config
            from app.paths import RESOURCE_DIR
            assert db.DATA_DIR == root / 'profile'
            assert config.DATA_DIR == db.DATA_DIR
            assert not db.DB_PATH.exists()
            db.init_db()
            report['checks'].append('Isolated first-run profile and identity schema')
            fid = db.upsert_franchise({'display_title': 'Installer check', 'is_custom': 1, 'user_notes': 'Preserved note', 'user_rating': 8})
            backup = db.backup_database(str(root / 'backup'))
            db.update_franchise_field(fid, 'user_notes', 'Changed fixture')
            db.restore_database(backup)
            assert db.get_franchise(fid)['user_notes'] == 'Preserved note'
            assert db.get_franchise(fid)['user_rating'] == 8
            report['checks'].append('SQLite backup/restore retains notes and ratings')
            conn = db.get_connection()
            assert conn.execute("SELECT name FROM sqlite_master WHERE name='physical_files'").fetchone()
            conn.close()
            required = ('assets/fonts/PlusJakartaSans.ttf', 'assets/fonts/JetBrainsMono.ttf',
                        'app/ui/assets/chevron-dark.svg', 'app/ui/assets/chevron-light.svg',
                        'browser-extension/manifest.json', 'third_party/libtorrent-LICENSE.txt',
                        'scripts/cache_player_icon.ps1')
            for relative in required:
                assert (RESOURCE_DIR / relative).is_file(), relative
            report['checks'].append('Fonts, SVG controls, extension and bundled notices')
            from app.core.builtin_torrents import EngineClient
            client = EngineClient({'enabled': False}, network=False)
            try:
                client.save()
            finally:
                client.close()
            report['checks'].append('Separate native libtorrent helper starts and stops; public network disabled')
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtTest import QTest
            from PyQt5.QtCore import QCoreApplication, QEvent
            from app.ui.theme import apply_theme
            from app.ui.main_window import MainWindow
            from app.ui.pages.detail_modal import DetailModal
            from app.ui.io_task import running
            app = QApplication.instance() or QApplication([])
            db.set_state('scan_schedule', 'manual')
            db.set_state('metadata_auto', '0')
            apply_theme(app, 'dark')
            window = MainWindow()
            window.show()
            for index in (0, 2, 5, 1, 3, 4, 0):
                window._on_nav_clicked(index)
                QTest.qWait(100)
            details = DetailModal(fid, window)
            assert details.franchise['display_title'] == 'Installer check'
            details.deleteLater()
            end = time.monotonic() + 15
            while not window._cleanup_and_exit() and time.monotonic() < end:
                QTest.qWait(100)
            if running():
                raise RuntimeError('Package fixture workers did not stop')
            window.hide()
            window.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            app.processEvents()
            report['checks'].append('All six navigation tabs, Details and orderly shutdown')
        report['ok'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return 0 if report['ok'] else 1
