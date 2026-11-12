"""Themed download setup/handoff drawer and a bounded background monitor."""
from PyQt5.QtCore import QObject,QTimer,QUrl,pyqtSignal,Qt,QAbstractListModel,QModelIndex
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QApplication,QLineEdit,QCheckBox,QFileDialog,QListWidget,QListWidgetItem,QSpinBox,QComboBox,QListView,QWidget,QHBoxLayout,QMessageBox,QSizePolicy
from app import db
from app.core import downloads as service
from app.ui.dialogs.drawer import DrawerDialog
from app.ui.components.workflow import chrome,text,field,button
from app.ui.magnet_capture import review_text as text
from app.ui.io_task import IOTask,track,start


class DownloadMonitor(QObject):
    changed=pyqtSignal()
    snapshot_ready=pyqtSignal(object)
    status=pyqtSignal(str)

    def __init__(self):
        super().__init__(QApplication.instance())
        self.worker=None
        self.closing=False
        self.timer=QTimer(self)
        self.timer.setInterval(15000)
        self.timer.timeout.connect(self.check)
        self.timer.start()

    def check(self):
        config=service.settings()
        items=service.jobs()
        if not self.closing:self.snapshot_ready.emit(items)
        self.timer.setInterval(3000 if any(j.get('engine')=='builtin' and j.get('desired')!='cancelled' for j in items) else 15000)
        if self.closing or self.worker or not config['enabled'] or not any(j['status']!='Indexed' or (j.get('engine')=='builtin' and j.get('desired')!='cancelled') for j in items):
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
        self.snapshot_ready.emit(items)
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
    def __init__(self,parent=None,fid=None,settings_only=False):
        super().__init__(parent)
        self.configuration_only=settings_only
        self.fid=fid
        config=service.settings()
        series=db.get_franchise(fid) if fid else {}
        body,self.save_button=chrome(self,'Downloads','Choose a download engine, find a torrent and track its progress.','取込','Save settings',self._save)
        self.engine=QComboBox()
        self.engine.addItem('Built-in downloader','builtin')
        self.engine.setCurrentIndex(0);self.engine.setEnabled(False)
        field(body,'Download engine',self.engine)
        self.notice=text('Anime Vault downloads directly using its built-in torrent engine. No external client, Web UI or login is needed.')
        body.addWidget(self.notice)
        from app.ui.magnet_capture import enable_browser_capture
        self.capture_status=text('Optional Chrome extension: save your source website below first, then connect the extension. It catches clicks only on that site; your normal magnet handler stays unchanged.')
        body.addWidget(self.capture_status)
        self.extension_id=QLineEdit(db.get_state('chrome.capture_extension',''))
        self.extension_id.setPlaceholderText('Extension ID from chrome://extensions')
        field(body,'Chrome extension ID',self.extension_id)
        body.addWidget(button('Connect Chrome extension',lambda:enable_browser_capture(self,self.capture_status,self.extension_id.text().strip())))
        from pathlib import Path
        body.addWidget(button('Open Chrome extension folder',lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[2]/'browser-extension')))))
        self.enabled=QCheckBox('Enable downloads')
        self.enabled.setChecked(config['enabled']);body.addWidget(self.enabled)
        body.addWidget(text('Confirmed downloads start automatically. Choose files remains available as an optional queue action.'))
        self.controls={}
        for name,label in [('destination','Download destination'),('source','Website search URL — use {query}'),('group','Release group (optional)'),('quality','Quality (optional)')]:
            control=QLineEdit(str(config[name]));control.setAccessibleName(label)
            self.controls[name]=control;field(body,label,control)
            if name=='destination':
                body.addWidget(button('Choose destination…',self._browse_destination))
        self.test_button=button('Test connection',self._test)
        body.addWidget(self.test_button)
        self.download_limit=QSpinBox();self.upload_limit=QSpinBox()
        for control,key,label in ((self.download_limit,'download_limit_kib','Built-in download limit (KiB/s)'),(self.upload_limit,'upload_limit_kib','Built-in upload limit (KiB/s)')):
            control.setRange(0,1000000);control.setSpecialValueText('Unlimited')
            control.setValue(config[key]);field(body,label,control)
        self.seed=QCheckBox('Keep seeding completed downloads')
        self.seed.setChecked(config['seed_completed']);body.addWidget(self.seed)
        body.addWidget(text('Built-in downloads continue in the tray. Exiting completely saves progress and stops transfers. Cancel keeps downloaded files.'))
        self.status=text('Not connected');body.addWidget(self.status)
        if settings_only:
            self.engine.currentIndexChanged.connect(self._engine_changed)
            self._engine_changed()
            self.cancel_button.hide()
            self.setFocusProxy(self.engine)
            # Settings owns the scrolling surface. Reuse the real controls
            # without nesting a drawer header or a second scroll area inside it.
            from PyQt5.QtWidgets import QScrollArea
            root=self.layout();root.itemAt(0).widget().hide()
            scroll=self.findChild(QScrollArea)
            content=scroll.takeWidget();root.removeWidget(scroll);scroll.hide()
            content.setParent(self);root.insertWidget(1,content)
            return
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
        hint=text('Each download uses a new isolated subfolder under your destination. Completed video files are verified and added to this anime; existing files are never moved or renamed. Keep Anime Vault open or minimized to the tray while downloading.')
        body.addWidget(hint)
        self.add_button=add=button('Add selected torrent',self._add,True)
        add.setEnabled(bool(fid));body.addWidget(add)
        if not fid:
            body.addWidget(text('Open Find / download from an anime to associate a torrent with that library entry.'))
        body.addWidget(text('Tracked downloads','workflow_field_label'))
        self.list=QListWidget();self.list.setMinimumHeight(180);body.addWidget(self.list)
        self.list.setWordWrap(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        actions=QWidget();row=QHBoxLayout(actions);row.setContentsMargins(0,0,0,0);row.setSpacing(8)
        self.job_buttons=[]
        for label,action in [('Files','files'),('Pause','pause'),('Resume','resume'),('Cancel','cancel')]:
            control=button(label,lambda checked=False,command=action:self._job_action(command))
            control.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed)
            control.setAccessibleName(label+' selected built-in download')
            row.addWidget(control);self.job_buttons.append(control)
        body.addWidget(actions)
        self.list.currentItemChanged.connect(self._selection_changed)
        self.engine.currentIndexChanged.connect(self._engine_changed)
        self._engine_changed()
        self.timer=QTimer(self);self.timer.setInterval(2000);self.timer.timeout.connect(self._render);self.timer.start()
        self._render()
        monitor().status.connect(self.status.setText)

    def _config(self):
        return {**{name:control.text().strip() for name,control in self.controls.items()},'enabled':self.enabled.isChecked(),'start_paused':False,
                'engine':self.engine.currentData(),'download_limit_kib':self.download_limit.value(),'upload_limit_kib':self.upload_limit.value(),'seed_completed':self.seed.isChecked()}

    def reload_settings(self):
        config=service.settings()
        self.engine.setCurrentIndex(0);self.engine.setEnabled(False)
        for key,control in self.controls.items():control.setText(str(config[key]))
        self.enabled.setChecked(config['enabled'])
        self.seed.setChecked(config['seed_completed']);self.download_limit.setValue(config['download_limit_kib']);self.upload_limit.setValue(config['upload_limit_kib'])
        self.extension_id.setText(db.get_state('chrome.capture_extension',''))
        self._engine_changed()

    def _engine_changed(self,*_):
        self.test_button.setText('Check Anime Vault engine')
        if hasattr(self,'add_button'):self.add_button.setText('Add download')

    def _secret(self):
        return None

    def _save(self):
        config,secret=self._config(),self._secret()
        start(self,lambda:service.save_settings(config,secret),self._saved)

    def _saved(self,_):
        self.status.setText('Settings saved. Downloads are tracked while Anime Vault is open.')
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
            QMessageBox.information(self,'Enable downloads','Enable downloads and save settings first.');return
        if not source:
            QMessageBox.information(self,'Choose a torrent','Copy a magnet link from your chosen result, or choose its .torrent file.');return
        def submit():
            service.save_settings(config,secret)
            return service.add_download(fid,source,season)
        start(self,submit,self._added)

    def _added(self,path):
        self.source.clear()
        message='Download started. '
        self.status.setText(message+'Destination: '+path)
        self._render();monitor().check()

    def _browse_destination(self):
        path=QFileDialog.getExistingDirectory(self,'Choose download destination',self.controls['destination'].text())
        if path: self.controls['destination'].setText(path)

    def _browse_torrent(self):
        path,_=QFileDialog.getOpenFileName(self,'Choose torrent','','Torrent files (*.torrent)')
        if path: self.source.setText(path)

    def _render(self):
        selected=self.list.currentItem().data(Qt.UserRole) if self.list.currentItem() else None
        items=service.jobs()
        signature=str(items)
        if signature==getattr(self,'_jobs_signature',None): return
        self._jobs_signature=signature
        self.list.clear()
        for job in items:
            extra=''
            if job.get('engine')=='builtin':
                eta=job.get('eta');eta_text=f'{eta//60}m {eta%60}s' if eta is not None else '—'
                extra=f"\n↓ {job.get('download_rate',0)/1024:.0f} KiB/s · ↑ {job.get('upload_rate',0)/1024:.0f} KiB/s · Remaining {eta_text}"
            label=QListWidgetItem(f"{job['title']} · {job['progress']:.0%}\n{job['status']}"+extra)
            label.setData(Qt.UserRole,job['id'])
            label.setToolTip(job['destination']);self.list.addItem(label)
            if job['id']==selected: self.list.setCurrentItem(label)
        self._selection_changed()

    def _selection_changed(self,*_):
        current=self.list.currentItem()
        job=next((j for j in service.jobs() if current and j['id']==current.data(Qt.UserRole)),None)
        for control in self.job_buttons:
            control.setEnabled(bool(service.settings()['enabled'] and job and job.get('engine')=='builtin' and job.get('desired')!='cancelled'))

    def _job_action(self,action):
        current=self.list.currentItem()
        if current is None: return
        identifier=current.data(Qt.UserRole)
        if action=='files':
            def show(entries):
                if not entries:
                    self.status.setText('Metadata is still loading. Try Files again shortly.');return
                from app.ui.navigation import navigate
                navigate(TorrentFilesDrawer(self,identifier,entries),lambda _:self._render())
            start(self,lambda:service.builtin_files(identifier),show)
            return
        if action=='cancel' and QMessageBox.question(self,'Cancel download?','Stop this transfer? Downloaded files will be kept.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:
            return
        def done(message):
            self.status.setText(message);self._render();monitor().check()
        start(self,lambda:service.control_builtin(identifier,action),done)

    def reject(self):
        if self.configuration_only:return
        worker=getattr(self,'_apply_worker',None)
        if worker and worker.isRunning(): return
        if hasattr(self,'timer'): self.timer.stop()
        super().reject()


class TorrentFileModel(QAbstractListModel):
    """Virtual list: do not create thousands of checkbox widgets."""
    def __init__(self,entries,parent=None):
        super().__init__(parent)
        self.entries=entries
        self.selected={i for i,e in enumerate(entries) if e.get('priority',0)>0}
        if not self.selected: self.selected=set(range(len(entries)))

    def rowCount(self,parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.entries)

    def data(self,index,role=Qt.DisplayRole):
        if not index.isValid() or not 0<=index.row()<len(self.entries): return None
        item=self.entries[index.row()]
        if role==Qt.DisplayRole: return f"{item['name']} · {item['size']/1024/1024:.1f} MiB"
        if role==Qt.ToolTipRole: return item['name']
        if role==Qt.CheckStateRole: return Qt.Checked if index.row() in self.selected else Qt.Unchecked

    def flags(self,index):
        return Qt.ItemIsEnabled|Qt.ItemIsSelectable|Qt.ItemIsUserCheckable if index.isValid() else Qt.NoItemFlags

    def setData(self,index,value,role=Qt.EditRole):
        if role!=Qt.CheckStateRole or not index.isValid(): return False
        if value==Qt.Checked: self.selected.add(index.row())
        else: self.selected.discard(index.row())
        self.dataChanged.emit(index,index,[Qt.CheckStateRole]);return True

    def select_all(self,checked):
        self.selected=set(range(len(self.entries))) if checked else set()
        if self.entries: self.dataChanged.emit(self.index(0),self.index(len(self.entries)-1),[Qt.CheckStateRole])


class TorrentFilesDrawer(DrawerDialog):
    def __init__(self,parent,identifier,entries):
        super().__init__(parent)
        self.identifier=identifier
        body,self.apply_button=chrome(self,'Choose download files','Select the files to download. Existing library files stay in place.','取込','Start selected files',self._apply)
        self.model=TorrentFileModel(entries,self)
        choices=QWidget();row=QHBoxLayout(choices);row.setContentsMargins(0,0,0,0)
        row.addWidget(button('Select all',lambda:self.model.select_all(True)))
        row.addWidget(button('Clear selection',lambda:self.model.select_all(False)))
        body.addWidget(choices)
        self.files=QListView();self.files.setModel(self.model)
        self.files.setObjectName('torrent_files')
        self.files.setUniformItemSizes(True);self.files.setMinimumHeight(300)
        self.files.setTextElideMode(Qt.ElideMiddle)
        self.files.setAccessibleName('Torrent files to download')
        body.addWidget(self.files,1)
        body.addWidget(text('Cancelling this screen leaves the current download selection unchanged.'))

    def _apply(self):
        selected=sorted(self.model.selected)
        start(self,lambda:service.control_builtin(self.identifier,'files',selected),lambda _:self._applied())

    def _applied(self):
        monitor().check();self.accept()


def open_downloads(parent,fid=None):
    from app.ui.navigation import navigate
    navigate(DownloadsDrawer(parent,fid))
