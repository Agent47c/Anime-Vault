"""Compact browser-magnet review and same-instance inbox delivery."""
from PyQt5.QtCore import QObject,QTimer,Qt
from PyQt5.QtWidgets import QComboBox,QCompleter,QMessageBox,QSizePolicy
from app import db
from app.core import magnet_capture as inbox
from app.core import downloads
from app.ui.components.workflow import chrome,text,field,button
from app.ui.dialogs.drawer import DrawerDialog
from app.ui.io_task import IOTask,track,start


def review_text(value,role='workflow_hint'):
    """Wrap inside the drawer even for filenames and paths without spaces."""
    import re
    wrapped=re.sub(r'\S{28}',lambda match:match.group()+'\u200b',value)
    label=text(wrapped,role)
    label.setMinimumWidth(0)
    label.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
    label.setToolTip(value)
    return label


class MagnetReview(DrawerDialog):
    def __init__(self,item,parent=None):
        super().__init__(parent)
        self.item=item
        self.sent=False
        config=downloads.settings()
        body,self.send_button=chrome(self,'Browser magnet received','Choose the library anime, then confirm this download.','取込','Add download',self._send)
        body.addWidget(review_text(item['name'],'workflow_row_title'))
        body.addWidget(review_text('The magnet link has been filled in automatically. No download starts until you confirm.'))
        records=db.get_all_franchises()
        self.anime=QComboBox()
        self.anime.setEditable(True)
        self.anime.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.anime.setMinimumContentsLength(16)
        self.anime.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed)
        self.anime.view().setTextElideMode(Qt.ElideRight)
        self.anime.setInsertPolicy(QComboBox.NoInsert)
        self.anime.addItem('Choose anime…',None)
        for row in sorted(records,key=lambda r:r['display_title'].casefold()):
            self.anime.addItem(row['display_title'],row['id'])
        self.anime.completer().setFilterMode(Qt.MatchContains)
        self.anime.completer().setCompletionMode(QCompleter.PopupCompletion)
        suggestion=inbox.suggestion(item['name'],records)
        self.anime.setCurrentIndex(max(0,self.anime.findData(suggestion)))
        field(body,'Anime — type to find a title',self.anime)
        self.season=QComboBox()
        self.season.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.season.setMinimumContentsLength(16)
        self.season.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed)
        self.season.addItem('Continuing / season unknown',0)
        for number in range(1,101): self.season.addItem(f'Season {number}',number)
        from app.core.consolidation import explicit_season
        number=explicit_season(item['name']) or 0
        self.season.setCurrentIndex(max(0,self.season.findData(number)))
        field(body,'Season folder',self.season)
        config=downloads.settings()
        body.addWidget(review_text('Destination: '+config['destination']))
        body.addWidget(review_text('Starts downloading immediately after you confirm.'))
        body.addWidget(review_text('After completion, verified videos are indexed under this anime. Existing library files stay in place.'))
        self.status=review_text('Confirm the anime and season before sending.')
        body.addWidget(self.status)
        from app.ui.downloads import open_downloads
        configure=button('Configure downloads',lambda:open_downloads(self))
        configure.setAccessibleName('Configure download engine and destination')
        configure.setToolTip('Configure download engine and destination')
        body.addWidget(configure)
        body.addStretch()

    def _send(self):
        index=self.anime.currentIndex()
        fid=self.anime.itemData(index) if index>=0 and self.anime.currentText()==self.anime.itemText(index) else None
        if fid is None:
            QMessageBox.information(self,'Choose anime','Choose the correct anime from the library list first.')
            return
        if not downloads.settings()['enabled']:
            QMessageBox.information(self,'Configure downloads','Enable and save your download engine in Configure downloads, then return here.')
            return
        season=self.season.currentData()
        start(self,lambda:inbox.submit(self.item,fid,season),self._sent)

    def _sent(self,path):
        self.sent=True
        from app.ui.downloads import monitor
        monitor().check()
        host=self.window()
        if hasattr(host,'statusBar'):
            host.statusBar().showMessage('Download started. Open Downloads to track progress.',10000)
        self.accept()

    def reject(self):
        if getattr(self,'_apply_worker',None) and self._apply_worker.isRunning(): return
        start(self,lambda:inbox.mark(self.item['id'],'DISMISSED'),self._dismissed)

    def _dismissed(self,_):
        super().reject()


class MagnetInboxPump(QObject):
    """Never starts a second app/API server or reads the inbox on the GUI thread."""
    def __init__(self,window):
        super().__init__(window)
        self.window=window
        self.worker=None
        self.active=None
        self.first=True
        self.enabled=bool(db.get_state('chrome.capture_extension',''))
        self.timer=QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.check)
        if self.enabled: self.enable()

    def enable(self):
        self.enabled=True
        self.timer.start()
        QTimer.singleShot(0,self.check)

    def check(self):
        if not self.enabled or self.worker or self.active is not None or getattr(self.window,'_shutdown_pending',False): return
        reset=self.first
        worker=IOTask(lambda:inbox.next_link(reset))
        self.worker=worker;track(worker)
        worker.succeeded.connect(self._received)
        worker.failed.connect(self._error)
        worker.finished.connect(self._finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _error(self,message):
        self.window.statusBar().showMessage('Browser magnet inbox: '+message,10000)

    def _received(self,item):
        self.first=False
        if not item: return
        from app.ui.navigation import navigate
        dialog=MagnetReview(item,self.window)
        self.active=dialog
        dialog.finished.connect(self._closed)
        if self.window.isMinimized(): self.window.showNormal()
        self.window.show();self.window.raise_();self.window.activateWindow()
        navigate(dialog)

    def _closed(self,_):
        self.active=None

    def _finished(self):
        self.worker=None


def enable_browser_capture(dialog,status,extension_id):
    from app.core.chrome_bridge import register
    def connected(message):
        status.setText(message)
        host=dialog.window()
        if hasattr(host,'_magnet_inbox'): host._magnet_inbox.enable()
    start(dialog,lambda:register(extension_id),connected)
