import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from app.ui.pages.settings_page import SettingsPage,QMessageBox
from app.ui.main_window import MainWindow


class BackupProgressRestartTests(unittest.TestCase):
    def test_both_backup_types_use_major_themed_progress(self):
        for full in (False,True):
            page=SimpleNamespace(full_backup=Mock(),backup_caches=Mock(),backup_status=Mock())
            page.full_backup.isChecked.return_value=full;page.backup_caches.isChecked.return_value=False
            with patch('app.ui.io_task.start') as start,patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):
                SettingsPage._backup_db(page)
            self.assertTrue(start.call_args.kwargs['major'])
            self.assertIn('backup' if full else 'database',start.call_args.kwargs['operation_title'])

    def test_zip_restore_routes_correctly_with_progress_and_resumes_timers_on_failure(self):
        timer=Mock();timer.isActive.return_value=True;timer.interval.return_value=3000
        host=SimpleNamespace(_running_threads=lambda:[],setEnabled=Mock(),_download_monitor=SimpleNamespace(timer=timer))
        worker=SimpleNamespace(finished=Mock())
        page=SimpleNamespace(window=lambda:host,backup_status=Mock(),_database_restored=Mock(),_apply_worker=worker)
        with (patch('app.ui.pages.settings_page.QFileDialog.getOpenFileName',return_value=('backup.zip','')),
             patch.object(QMessageBox,'question',return_value=QMessageBox.Yes),
             patch('app.ui.io_task.running',return_value=[]),patch('app.ui.io_task.start') as start,
             patch('app.core.builtin_torrents.active',return_value=False),patch('app.core.downloads.jobs',return_value=[]),
             patch('app.ui.user_edits.user_edits',return_value=SimpleNamespace(pending=False)),
             patch('app.core.profile_backup.restore_backup') as restore):
            SettingsPage._restore_db(page)
            self.assertTrue(start.call_args.kwargs['major'])
            start.call_args.args[1]();restore.assert_called_once_with('backup.zip')
        timer.stop.assert_called_once()
        worker.finished.connect.call_args.args[0]()
        timer.start.assert_called_once_with(3000);host.setEnabled.assert_called_with(True)

    def test_success_requires_restart_without_refreshing_old_ui(self):
        central=Mock();host=SimpleNamespace(setEnabled=Mock(),centralWidget=lambda:central,_force_exit=Mock())
        page=SimpleNamespace(window=lambda:host,backup_status=Mock(),scan_completed=Mock())
        with patch('app.ui.pages.settings_page.QMessageBox') as notice:
            notice.return_value.clickedButton.return_value=None
            SettingsPage._database_restored(page,True)
        self.assertTrue(page._restore_succeeded);self.assertTrue(host._restore_restart_required)
        central.setEnabled.assert_called_once_with(False);host._force_exit.assert_called_once()
        page.scan_completed.emit.assert_not_called();self.assertIn('restart required',notice.call_args.args[1])

    def test_required_restart_bypasses_tray_preference(self):
        host=SimpleNamespace(_restore_restart_required=True,_force_exit=Mock());event=Mock()
        MainWindow.closeEvent(host,event)
        event.ignore.assert_called_once();host._force_exit.assert_called_once()

    def test_restored_window_settings_are_not_overwritten_on_exit(self):
        host=SimpleNamespace(_restore_restart_required=True,_save_geometry=Mock(),hide=Mock(),_cleanup_and_exit=Mock(return_value=False))
        with patch('app.ui.main_window.QTimer.singleShot'):MainWindow._force_exit(host)
        host._save_geometry.assert_not_called()

    def test_required_restart_close_does_not_reenter_shutdown(self):
        host=SimpleNamespace(_restore_restart_required=True,_force_exiting=True,_force_exit=Mock());event=Mock()
        MainWindow.closeEvent(host,event)
        event.ignore.assert_called_once();host._force_exit.assert_not_called()

    def test_blocked_restore_explains_why_restart_prompt_does_not_appear(self):
        host=SimpleNamespace(_running_threads=lambda:[object()])
        page=SimpleNamespace(window=lambda:host,backup_status=Mock())
        with (patch('app.ui.pages.settings_page.QFileDialog.getOpenFileName',return_value=('backup.zip','')),
              patch.object(QMessageBox,'question',return_value=QMessageBox.Yes),
              patch.object(QMessageBox,'warning') as warning,patch('app.ui.io_task.start') as start,
              patch('app.ui.io_task.running',return_value=[]),patch('app.ui.user_edits.user_edits',return_value=SimpleNamespace(pending=False))):
            SettingsPage._restore_db(page)
        start.assert_not_called();self.assertEqual(warning.call_args.args[1],'Restore not started')

    def test_success_restart_button_invokes_app_restart(self):
        host=SimpleNamespace(setEnabled=Mock(),_restart_app=Mock(return_value=True),_force_exit=Mock())
        page=SimpleNamespace(window=lambda:host,backup_status=Mock())
        button=object()
        with patch('app.ui.pages.settings_page.QMessageBox') as notice:
            notice.return_value.addButton.side_effect=[button,object()]
            notice.return_value.clickedButton.return_value=button
            SettingsPage._database_restored(page,True)
        host._restart_app.assert_called_once();host._force_exit.assert_not_called()
