"""Queue-first Downloads destination; settings and source search stay separate."""
from pathlib import Path
from PyQt5.QtCore import Qt,QAbstractTableModel,QModelIndex,QTimer,QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QTableView,QHeaderView,QAbstractItemView,QMessageBox,QMenu,QInputDialog
from app import db
from app.core import downloads,download_queue
from app.core.storage import format_bytes
from app.ui.io_task import IOTask,track,start
from app.ui.downloads import monitor,TorrentFilesDrawer,open_downloads
from app.ui.download_setup import open_setup
from app.ui.navigation import navigate


class QueueModel(QAbstractTableModel):
    headers=['Anime / release','Episodes','Progress','Downloaded / total','Speed','Remaining','Status']
    def __init__(self,parent=None): super().__init__(parent);self.rows=[]
    def rowCount(self,parent=QModelIndex()): return 0 if parent.isValid() else len(self.rows)
    def columnCount(self,parent=QModelIndex()): return len(self.headers)
    def headerData(self,section,orientation,role=Qt.DisplayRole):
        if role==Qt.DisplayRole and orientation==Qt.Horizontal:return self.headers[section]
    def data(self,index,role=Qt.DisplayRole):
        if not index.isValid():return None
        item=self.rows[index.row()]
        if role==Qt.ToolTipRole:return '\n'.join(str(v) for v in (item['title'],item.get('release_title',''),item.get('status',''),item.get('integrity_error',''),item['destination']) if v)
        if role!=Qt.DisplayRole:return None
        episodes=item.get('episode_keys') or []
        from app.core.download_discovery import coverage_label
        label=coverage_label(episodes)
        size=(format_bytes(item['downloaded']) if item.get('downloaded') is not None else '—')+' / '+(format_bytes(item['total']) if item.get('total') is not None else '—')
        eta=item.get('eta');remaining=f'{eta//60}m {eta%60}s' if isinstance(eta,int) and 0<=eta<8640000 else '—'
        values=[item['title']+('\n'+item['release_title'] if item.get('release_title') else ''),label,f"{item.get('progress',0):.0%}",size,
                format_bytes(item.get('download_rate') or 0)+'/s',remaining,download_queue.status(item)]
        return values[index.column()]


class DownloadsPage(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self._queue_worker=None;self.items=[]
        self.setObjectName('downloads_page')
        box=QVBoxLayout(self);box.setContentsMargins(28,20,28,24);box.setSpacing(16)
        header=QHBoxLayout();title=QLabel('Downloads');title.setObjectName('download_heading');header.addWidget(title);header.addStretch()
        for label,callback in [('Setup',lambda:open_setup(self)),('Settings',self.open_settings),('Add download',self.add),('Refresh',lambda:monitor().check())]:
            button=QPushButton(label);button.setMinimumHeight(44);button.setCursor(Qt.PointingHandCursor);button.clicked.connect(callback);header.addWidget(button)
        box.addLayout(header)
        self.summary=QLabel('Your download queue is saved across restarts.');self.summary.setWordWrap(True);box.addWidget(self.summary)
        filters=QHBoxLayout();self.filter=QComboBox();self.filter.addItems(['All','Active','Paused / stopped','Completed','Failed / missing files'])
        self.filter.currentIndexChanged.connect(self.render);filters.addWidget(self.filter);filters.addStretch();box.addLayout(filters)
        self.model=QueueModel(self);self.table=QTableView();self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setTextElideMode(Qt.ElideRight);self.table.setWordWrap(False);self.table.setShowGrid(False);self.table.verticalHeader().hide();self.table.verticalHeader().setDefaultSectionSize(64)
        self.table.horizontalHeader().setMinimumSectionSize(90)
        for i in range(1,7):self.table.horizontalHeader().setSectionResizeMode(i,QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        self.table.setAccessibleName('Saved downloads and transfer activity');box.addWidget(self.table,1)
        self.empty=QLabel('No downloads yet. Start with Setup, or open an anime and choose Find Download Files.');self.empty.setWordWrap(True);box.addWidget(self.empty)
        controls=QHBoxLayout()
        for label,action in [('Pause','pause'),('Resume','resume'),('Stop','stop'),('Retry','retry'),('Choose files','files')]:
            button=QPushButton(label);button.setMinimumHeight(44);button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False,command=action:self.action(command));controls.addWidget(button)
        more=QPushButton('More');more.setMinimumHeight(44);menu=QMenu(more)
        menu.addAction('Open download folder',self.open_folder)
        menu.addAction('Remove queue entry — keep files',lambda:self.action('remove'))
        menu.addSeparator();menu.addAction('Move download files to Recycle Bin…',self.delete_files)
        more.setMenu(menu);controls.addWidget(more);controls.addStretch();box.addLayout(controls)
        self.status=QLabel('');self.status.setWordWrap(True);box.addWidget(self.status)
        self.timer=QTimer(self);self.timer.setInterval(2500);self.timer.timeout.connect(self.refresh)
        monitor().status.connect(self.updated);self.refresh()

    def showEvent(self,event): super().showEvent(event);self.timer.start();self.refresh()
    def hideEvent(self,event): self.timer.stop();super().hideEvent(event)
    def open_settings(self):
        host=self.window()
        if hasattr(host,'settings_page'):
            host.settings_page.tabs.setCurrentIndex(4);host._on_nav_clicked(4)
    def add(self):
        records=db.get_all_franchises();titles=[r['display_title'] for r in records]
        if not records:self.status.setText('Add an anime to the library first.');return
        title,ok=QInputDialog.getItem(self,'Add download','Anime',titles,0,False)
        if ok:open_downloads(self,records[titles.index(title)]['id'])
    def updated(self,message): self.status.setText(message);self.refresh()
    def refresh(self):
        if self._queue_worker:return
        worker=IOTask(download_queue.snapshot);self._queue_worker=worker;track(worker)
        worker.succeeded.connect(self.loaded);worker.failed.connect(self.status.setText);worker.finished.connect(self.finished);worker.start()
    def finished(self): self._queue_worker.deleteLater();self._queue_worker=None
    def loaded(self,items): self.items=items;self.render()
    def render(self,*_):
        selected=self.selected();identifier=selected['id'] if selected else None
        filter_index=self.filter.currentIndex()
        allowed=[None,{'Queued','Downloading'},{'Paused','Stopped'},{'Completed'},{'Failed','Incomplete or missing files'}][filter_index]
        self.model.beginResetModel();self.model.rows=[i for i in self.items if allowed is None or download_queue.status(i) in allowed];self.model.endResetModel()
        for row,item in enumerate(self.model.rows):
            if item['id']==identifier:self.table.selectRow(row)
        self.empty.setVisible(not self.model.rows)
        self.summary.setText(f"{len(self.items)} saved transfers · {sum(download_queue.status(i) in ('Queued','Downloading') for i in self.items)} active · {sum(download_queue.status(i)=='Completed' for i in self.items)} completed")
    def selected(self):
        rows=self.table.selectionModel().selectedRows()
        return self.model.rows[rows[0].row()] if rows else None
    def action(self,command):
        item=self.selected()
        if item is None:self.status.setText('Select a download first.');return
        identifier=item['id']
        if command=='files':
            if item.get('engine')!='builtin':self.status.setText('External client removed. Use Retry to add this torrent to Anime Vault, then choose its files.');return
            def show(entries):
                if entries:navigate(TorrentFilesDrawer(self,identifier,entries),lambda _:self.refresh())
                else:self.status.setText('Metadata is still loading. Retry Choose files shortly.')
            start(self,lambda:downloads.builtin_files(identifier),show);return
        if command=='retry' and item.get('engine')!='builtin':
            response=QMessageBox.question(self,'Retry with Anime Vault?',
                'Create a built-in download in a new folder? Existing files will stay untouched. If this torrent is running in another application, stop it there first to avoid two transfers. Choose files in the new entry when metadata is ready.',
                QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
            if response!=QMessageBox.Yes:return
        if command=='remove' and QMessageBox.question(self,'Remove queue entry?','Remove this transfer from the queue? Downloaded files and library history will be kept.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        start(self,lambda:download_queue.action(identifier,command),lambda message:(self.status.setText(message),self.refresh(),monitor().check()))
    def open_folder(self):
        item=self.selected()
        if item is None:return
        path=Path(item['destination'])
        if not path.is_dir():self.status.setText('The download folder is missing or the drive is unavailable.');return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    def delete_files(self):
        item=self.selected()
        if item is None:return
        if QMessageBox.question(self,'Move downloaded files to Recycle Bin?',f"Move files in {item['root']} to the Recycle Bin? Library history and the queue record are kept. This is separate from removing an entry. Space is reclaimed after emptying the Recycle Bin.",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        start(self,lambda:download_queue.recycle_files(item['id']),lambda message:(self.status.setText(message),self.refresh(),monitor().changed.emit()))
