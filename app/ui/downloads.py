"""Themed download setup/handoff drawer and a bounded background monitor."""
from PyQt5.QtCore import QObject,QTimer,QUrl,pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QApplication,QLineEdit,QCheckBox,QFileDialog,QListWidget,QListWidgetItem,QSpinBox
from app import db
from app.core import downloads as service
from app.ui.dialogs.drawer import DrawerDialog
from app.ui.components.workflow import chrome,text,field,button
from app.ui.io_task import IOTask,track,start


class DownloadMonitor(QObject):
    changed=pyqtSignal()
    status=pyqtSignal(str)

    def __init__(self):
        super().__init__(QApplication.instance())
        self.worker=None
        self.timer=QTimer(self)
        self.timer.setInterval(15000)
        self.timer.timeout.connect(self.check)
        self.timer.start()

    def check(self):
        if self.worker or not service.settings()['enabled'] or not any(j['status']!='Indexed' for j in service.jobs()):
            return
        worker=IOTask(lambda:service.poll(worker.isInterruptionRequested))
        self.worker=worker
        track(self.worker)
        self.worker.succeeded.connect(self._ready)
        self.worker.failed.connect(self.status.emit)
        self.worker.finished.connect(self._finished)
        self.worker.start()

    def _ready(self,result):
        items,changed=result
        self.status.emit('Downloads checked')
        if changed: self.changed.emit()

    def _finished(self):
        worker,self.worker=self.worker,None
        worker.deleteLater()


_monitor=None


def monitor():
    global _monitor
    if _monitor is None:
        _monitor=DownloadMonitor()
    return _monitor


class DownloadsDrawer(DrawerDialog):
    def __init__(self,parent=None,fid=None):
        super().__init__(parent)
        self.fid=fid
        config=service.settings()
        series=db.get_franchise(fid) if fid else {}
        body,self.save_button=chrome(self,'Downloads','Search your source, then send the selected torrent to qBittorrent.','取込','Save settings',self._save)
        self.notice=text('qBittorrent uses its Web UI username/password and a login session, not an Anime Vault API key. Enable Web UI in qBittorrent > Tools > Options > Web UI. Keep it bound to localhost.')
        body.addWidget(self.notice)
        self.enabled=QCheckBox('Enable qBittorrent connection and completion monitoring')
        self.enabled.setChecked(config['enabled']);body.addWidget(self.enabled)
        self.paused=QCheckBox('Start paused so I can choose files in qBittorrent')
        self.paused.setChecked(config['start_paused']);body.addWidget(self.paused)
        self.controls={}
        for name,label in [('url','qBittorrent Web UI URL'),('username','Web UI username'),('destination','Download destination'),('source','Website search URL — use {query}'),('group','Release group (optional)'),('quality','Quality (optional)')]:
            control=QLineEdit(str(config[name]));control.setAccessibleName(label)
            self.controls[name]=control;field(body,label,control)
            if name=='destination':
                body.addWidget(button('Choose destination…',self._browse_destination))
        self.password_input=QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText('Leave blank to keep the saved password')
        field(body,'Web UI password — encrypted for your Windows account',self.password_input)
        body.addWidget(button('Test connection',self._test))
        self.status=text('Not connected');body.addWidget(self.status)
        self.query_title=QLineEdit((series or {}).get('title_romaji') or (series or {}).get('display_title') or '')
        field(body,'Search title — editable',self.query_title)
        self.episode=QLineEdit();self.episode.setPlaceholderText('Optional, e.g. 1170. Use absolute numbers for continuing series.')
        field(body,'Episode',self.episode)
        body.addWidget(button('Search website',self._search,True))
        self.season=QSpinBox();self.season.setRange(0,100);self.season.setSpecialValueText('Continuing / season unknown')
        field(body,'Local season folder (0 = continuing / unknown)',self.season)
        self.source=QLineEdit();self.source.setPlaceholderText('Paste magnet:?xt=… or choose a .torrent file')
        field(body,'Selected torrent',self.source)
        body.addWidget(button('Choose .torrent file…',self._browse_torrent))
        hint=text('Each download uses a new isolated subfolder under your destination. Completed video files are verified and added to this anime; existing files are never moved or renamed. Keep qBittorrent open for downloading/seeding.')
        body.addWidget(hint)
        add=button('Send selected torrent to qBittorrent',self._add,True)
        add.setEnabled(bool(fid));body.addWidget(add)
        if not fid:
            body.addWidget(text('Open Find / download from an anime to associate a torrent with that library entry.'))
        body.addWidget(text('Tracked downloads','workflow_field_label'))
        self.list=QListWidget();self.list.setMinimumHeight(180);body.addWidget(self.list)
        self.timer=QTimer(self);self.timer.setInterval(2000);self.timer.timeout.connect(self._render);self.timer.start()
        self._render()
        monitor().status.connect(self.status.setText)

    def _config(self):
        return {**{name:control.text().strip() for name,control in self.controls.items()},'enabled':self.enabled.isChecked(),'start_paused':self.paused.isChecked()}

    def _secret(self):
        return self.password_input.text() or None

    def _save(self):
        config,secret=self._config(),self._secret()
        start(self,lambda:service.save_settings(config,secret),self._saved)

    def _saved(self,_):
        self.password_input.clear();self.status.setText('Settings saved. Completion checks run every 15 seconds while Anime Vault is open.')
        monitor().check()

    def _test(self):
        config,secret=self._config(),self._secret()
        start(self,lambda:service.test_connection(config,secret),self.status.setText)

    def _search(self):
        from PyQt5.QtWidgets import QMessageBox
        try:
            if not self.query_title.text().strip():
                raise ValueError('Enter the anime search title.')
            query=service.make_query(self.query_title.text(),self.episode.text(),self.controls['group'].text(),self.controls['quality'].text())
            url=service.search_url(self.controls['source'].text().strip(),query)
            if not QDesktopServices.openUrl(QUrl(url)):
                raise ValueError('The browser could not open the search URL.')
        except ValueError as error:
            QMessageBox.warning(self,'Search website',str(error))

    def _add(self):
        from PyQt5.QtWidgets import QMessageBox
        config,secret=self._config(),self._secret()
        source=self.source.text().strip();season=self.season.value();fid=self.fid
        if not config['enabled']:
            QMessageBox.information(self,'Enable connection','Enable the qBittorrent connection first.');return
        if not source:
            QMessageBox.information(self,'Choose a torrent','Copy a magnet link from your chosen result, or choose its .torrent file.');return
        def submit():
            service.save_settings(config,secret)
            return service.add_download(fid,source,season)
        start(self,submit,self._added)

    def _added(self,path):
        self.password_input.clear();self.source.clear()
        message='Sent paused. Choose files and start in qBittorrent. ' if self.paused.isChecked() else 'Sent to qBittorrent. '
        self.status.setText(message+'Destination: '+path)
        self._render();monitor().check()

    def _browse_destination(self):
        path=QFileDialog.getExistingDirectory(self,'Choose download destination',self.controls['destination'].text())
        if path: self.controls['destination'].setText(path)

    def _browse_torrent(self):
        path,_=QFileDialog.getOpenFileName(self,'Choose torrent','','Torrent files (*.torrent)')
        if path: self.source.setText(path)

    def _render(self):
        self.list.clear()
        for job in service.jobs():
            label=QListWidgetItem(f"{job['title']} · {job['progress']:.0%}\n{job['status']}")
            label.setToolTip(job['destination']);self.list.addItem(label)

    def reject(self):
        worker=getattr(self,'_apply_worker',None)
        if worker and worker.isRunning(): return
        self.timer.stop()
        super().reject()


def open_downloads(parent,fid=None):
    from app.ui.navigation import navigate
    navigate(DownloadsDrawer(parent,fid))
