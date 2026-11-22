import time,unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtTest import QTest
from app import db
from app.ui.pages.settings_page import SettingsPage
from app.ui.components.message_boxes import AppMessageBox
import test_ui_regressions as support

class RestoreRestartDialogTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_real_restore_completion_opens_restart_action(self):
        backup=db.backup_database()
        host=QMainWindow();host._running_threads=lambda:[];host._restart_app=Mock(return_value=True)
        host._force_exit=Mock();page=SettingsPage();host.setCentralWidget(page);host.show()
        self.addCleanup(host.deleteLater);seen=[]
        def accept_restart():
            for dialog in host.findChildren(AppMessageBox):
                if dialog.isVisible() and 'restart required' in dialog.windowTitle():
                    seen.append(True)
                    next(button for button in dialog.buttons() if button.text()=='Restart Anime Vault').click()
        poll=QTimer();poll.timeout.connect(accept_restart);poll.start(10)
        with (patch('app.ui.pages.settings_page.QFileDialog.getOpenFileName',return_value=(backup,'')),
              patch.object(AppMessageBox,'question',return_value=AppMessageBox.Yes),
              patch('app.ui.io_task.running',return_value=[]),
              patch('app.core.downloads.jobs',return_value=[]),patch('app.core.builtin_torrents.active',return_value=False),
              patch('app.ui.user_edits.user_edits',return_value=SimpleNamespace(pending=False))):
            page._restore_db()
            deadline=time.monotonic()+8
            while not seen and time.monotonic()<deadline:QTest.qWait(20)
            worker=getattr(page,'_apply_worker',None)
            if worker is not None:worker.wait(3000)
            QTest.qWait(30)
        poll.stop();self.assertTrue(seen,'Successful restore must present an actual restart dialog')
        host._restart_app.assert_called_once();host._force_exit.assert_not_called()
