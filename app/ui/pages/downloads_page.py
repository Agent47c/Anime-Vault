"""Queue-first Downloads destination; settings and source search stay separate."""
from pathlib import Path
from PyQt5.QtCore import Qt,QAbstractTableModel,QModelIndex,QTimer,QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QWidget,QFrame,QScrollArea,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QTableView,QHeaderView,QAbstractItemView,QMessageBox,QMenu,QInputDialog,QLineEdit,QSpinBox,QAbstractSpinBox,QGridLayout,QFileDialog
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
        if role==Qt.UserRole:return item
        if role not in (Qt.DisplayRole,Qt.ToolTipRole,Qt.AccessibleTextRole):return None
        episodes=item.get('episode_keys') or []
        from app.core.download_discovery import coverage_label
        label=coverage_label(episodes)
        size=(format_bytes(item['downloaded']) if item.get('downloaded') is not None else '—')+' / '+(format_bytes(item['total']) if item.get('total') is not None else '—')
        eta=item.get('eta');remaining=f'{eta//60}m {eta%60}s' if isinstance(eta,int) and 0<=eta<8640000 else '—'
        values=[item['title']+('\n'+item['release_title'] if item.get('release_title') else ''),label,f"{item.get('progress',0):.0%}",size,
                format_bytes(item.get('download_rate') or 0)+'/s',remaining,download_queue.status(item)]
        if role==Qt.ToolTipRole:return '\n'.join([str(v) for v in values]+[item['destination'],item.get('integrity_error') or '', 'Select this transfer to use the Pause, Resume, Stop, Retry, Choose files and More controls.'])
        return values[index.column()]


class DownloadsPage(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self._queue_worker=None;self.items=[]
        self.setObjectName('downloads_page')
        self.setAttribute(Qt.WA_StyledBackground,True)
        from app.ui.home_style import load_fonts
        from app.ui.components.flow_layout import FlowLayout
        load_fonts();box=QVBoxLayout(self);box.setContentsMargins(20,20,20,24);box.setSpacing(20)
        header=FlowLayout();title=QLabel('Downloads & Transfers');title.setObjectName('transfer_heading');header.addWidget(title)
        controls=QWidget();controls.setObjectName('transfer_clear');controls.setProperty('homeAlignRight',True);actions=QHBoxLayout(controls);actions.setContentsMargins(0,0,0,0)
        for label,callback in [('Setup Guide',lambda:open_setup(self)),('Add download',self.add),('Pause all',lambda:self.bulk('pause')),('Clear completed',lambda:self.bulk('clear_completed'))]:
            button=QPushButton(label);button.setMinimumHeight(44);button.setCursor(Qt.PointingHandCursor);button.clicked.connect(callback);actions.addWidget(button)
            if label=='Add download':button.setProperty('accent',True)
        header.addWidget(controls);box.addLayout(header)
        self.summary=QLabel('Your download queue is saved across restarts.');self.summary.setObjectName('transfer_meta');self.summary.setWordWrap(True);box.addWidget(self.summary)
        filters=FlowLayout();self.filter=QComboBox(self);self.filter.addItems(['All','Active','Paused / stopped','Completed','Failed / missing files']);self.filter.hide()
        self.filter.currentIndexChanged.connect(self.render);self.filter_buttons=[]
        for number,label in enumerate(['All Transfers','Active','Paused / stopped','Completed','Incomplete or Missing']):
            button=QPushButton(label);button.setProperty('chip',True);button.setCheckable(True);button.clicked.connect(lambda checked=False,n=number:self.filter.setCurrentIndex(n));self.filter_buttons.append(button);filters.addWidget(button)
        box.addLayout(filters)
        columns=QHBoxLayout();columns.setSpacing(20);left=QWidget();left.setObjectName('transfer_clear');queue_box=QVBoxLayout(left);queue_box.setContentsMargins(0,0,0,0);queue_box.setSpacing(12);columns.addWidget(left,2)
        self.model=QueueModel(self);self.table=QTableView();self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setTextElideMode(Qt.ElideRight);self.table.setWordWrap(False);self.table.setShowGrid(False);self.table.verticalHeader().hide();self.table.verticalHeader().setDefaultSectionSize(64)
        self.table.horizontalHeader().hide()
        for i in range(1,7):self.table.setColumnHidden(i,True)
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        from app.ui.components.transfer_row import TransferDelegate
        delegate=TransferDelegate(self.table);delegate.action_requested.connect(self.row_action);self.table.setItemDelegateForColumn(0,delegate)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu);self.table.customContextMenuRequested.connect(self.row_menu)
        self.table.setAccessibleName('Saved downloads and transfer activity');queue_box.addWidget(self.table,1)
        self.empty=QLabel('No downloads yet. Start with Setup Guide, or open an anime and choose Find Download Files.');self.empty.setWordWrap(True);queue_box.addWidget(self.empty)
        self.guide=QFrame();self.guide.setObjectName('transfer_panel');self.guide.setMinimumWidth(280);self.guide.setMaximumWidth(400);guide=QVBoxLayout(self.guide);guide.setContentsMargins(20,20,20,20);guide.setSpacing(14)
        heading=QLabel('Guided Download Setup');heading.setStyleSheet('font-size:18px;font-weight:600;');guide.addWidget(heading)
        note=QLabel('Destination & transfer limits');note.setObjectName('transfer_meta');guide.addWidget(note)
        config=downloads.settings();guide.addWidget(QLabel('Default download folder'))
        self.destination=QLineEdit(config['destination']);self.destination.setAccessibleName('Default download folder');guide.addWidget(self.destination)
        self.destination.setToolTip(config['destination']);self.destination.setCursorPosition(0);self.destination.textChanged.connect(self.destination.setToolTip)
        browse=QPushButton('Browse…');browse.clicked.connect(self.choose_destination);guide.addWidget(browse,0,Qt.AlignRight)
        limits=QGridLayout();self.down_limit=QSpinBox();self.up_limit=QSpinBox()
        for col,(label,control,key) in enumerate([('Max down (KiB/s)',self.down_limit,'download_limit_kib'),('Max up (KiB/s)',self.up_limit,'upload_limit_kib')]):
            limits.addWidget(QLabel(label),0,col);control.setRange(0,1000000);control.setValue(config[key]);control.setSpecialValueText('Unlimited');control.setAccessibleName(label);limits.addWidget(control,1,col)
            control.setButtonSymbols(QAbstractSpinBox.NoButtons)
        guide.addLayout(limits)
        save=QPushButton('Save preferences');save.clicked.connect(self.save_preferences);guide.addWidget(save)
        setup=QPushButton('Continue setup guide');setup.clicked.connect(lambda:open_setup(self));guide.addWidget(setup)
        settings=QPushButton('All download settings');settings.clicked.connect(self.open_settings);guide.addWidget(settings);guide.addStretch()
        self.guide_scroll=QScrollArea();self.guide_scroll.setWidgetResizable(True);self.guide_scroll.setFrameShape(QFrame.NoFrame);self.guide_scroll.setMinimumWidth(280);self.guide_scroll.setMaximumWidth(400);self.guide_scroll.setWidget(self.guide)
        columns.addWidget(self.guide_scroll,1);box.addLayout(columns,1)
        controls=FlowLayout()
        for label,action in [('Pause','pause'),('Resume','resume'),('Stop','stop'),('Retry','retry'),('Choose files','files')]:
            button=QPushButton(label);button.setMinimumHeight(44);button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False,command=action:self.action(command));controls.addWidget(button)
        more=QPushButton('More');more.setMinimumHeight(44);menu=QMenu(more)
        menu.addAction('Open download folder',lambda checked=False:self.open_folder())
        menu.addAction('Remove queue entry — keep files',lambda:self.action('remove'))
        menu.addSeparator();menu.addAction('Move download files to Recycle Bin…',self.delete_files)
        more.setMenu(menu);controls.addWidget(more)
        refresh=QPushButton('Refresh');refresh.clicked.connect(lambda:monitor().check());controls.addWidget(refresh);box.addLayout(controls)
        move=QPushButton('Move completed to library');move.clicked.connect(self.move_completed);controls.addWidget(move)
        self.status=QLabel('');self.status.setWordWrap(True);box.addWidget(self.status)
        for control in self.findChildren(QPushButton):
            control.setCursor(Qt.PointingHandCursor)
            if not control.accessibleName():control.setAccessibleName(control.text())
        self.table.viewport().setCursor(Qt.PointingHandCursor)
        self.guide_scroll.setAccessibleName('Download setup preferences')
        self.timer=QTimer(self);self.timer.setInterval(2500);self.timer.timeout.connect(self.refresh)
        monitor().status.connect(self.updated);self.refresh_home_style();self.refresh()

    def refresh_home_style(self):
        from app.ui.transfer_style import qss
        from app.ui.home_style import px
        self.setProperty('animevaultOwnScaledStyle',True)
        style=qss('downloads_page')
        if self.styleSheet()!=style:self.setStyleSheet(style)
        self.table.verticalHeader().setDefaultSectionSize(px(100))
    def choose_destination(self):
        path=QFileDialog.getExistingDirectory(self,'Default download folder',self.destination.text())
        if path:self.destination.setText(path)
    def save_preferences(self):
        values=dict(destination=self.destination.text(),download_limit_kib=self.down_limit.value(),upload_limit_kib=self.up_limit.value())
        start(self,lambda:downloads.save_settings(values),lambda _ :self.status.setText('Download preferences saved. Existing files stay in place.'))
    def bulk(self,command):
        identifiers=[item['id'] for item in self.items if command=='pause' or download_queue.status(item)=='Completed']
        if command=='clear_completed' and QMessageBox.question(self,'Clear completed queue entries?',f'Remove {len(identifiers)} completed queue records? All downloaded files and library history will be kept.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        start(self,lambda:download_queue.bulk_action(command,identifiers,cancelled=lambda:bool(getattr(self,'_apply_worker',None) and self._apply_worker.isInterruptionRequested())),lambda message:(self.status.setText(message),self.refresh(),monitor().check()))
    def row_action(self,row,number,point):
        if not 0<=row<len(self.model.rows):return
        self.table.selectRow(row)
        if number==0:
            state=download_queue.status(self.model.rows[row])
            if state=='Completed':self.open_folder()
            else:self.action('resume' if state in ('Paused','Stopped') else 'retry' if state=='Failed' else 'pause')
        elif number==1:self.action('files')
        else:self.row_menu(point)
    def row_menu(self,point):
        index=self.table.indexAt(point)
        if index.isValid():self.table.selectRow(index.row())
        item=self.selected()
        if item is None:return
        identifier=item['id']
        menu=QMenu(self)
        for label,command in [('Pause','pause'),('Resume','resume'),('Stop','stop'),('Retry','retry'),('Choose files','files'),('Remove queue entry — keep files','remove')]:menu.addAction(label,lambda checked=False,c=command:self.action(c,identifier))
        menu.addAction('Open download folder',lambda:self.open_folder(identifier));menu.addAction('Move files to Recycle Bin…',lambda:self.delete_files(identifier));menu.exec_(self.table.viewport().mapToGlobal(point))
    def move_completed(self):
        from app.core import download_library
        from app.ui.dialogs.download_library_move import DownloadLibraryMove
        start(self,download_library.preview,lambda plan:navigate(DownloadLibraryMove(plan,self),lambda _:self.refresh()))

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
    def loaded(self,items):
        if getattr(self,'_queue_loaded',False) and self.items==items:return
        self._queue_loaded=True;self.items=items;self.render()
    def render(self,*_):
        selected=self.selected();identifier=selected['id'] if selected else None
        filter_index=self.filter.currentIndex()
        allowed=[None,{'Queued','Downloading'},{'Paused','Stopped'},{'Completed'},{'Failed','Incomplete or missing files'}][filter_index]
        rows=[i for i in self.items if allowed is None or download_queue.status(i) in allowed]
        if [i['id'] for i in rows]==[i['id'] for i in self.model.rows]:
            self.model.rows=rows
            if rows:self.model.dataChanged.emit(self.model.index(0,0),self.model.index(len(rows)-1,self.model.columnCount()-1))
        else:
            self.model.beginResetModel();self.model.rows=rows;self.model.endResetModel()
        for row,item in enumerate(self.model.rows):
            if item['id']==identifier:self.table.selectRow(row)
        self.empty.setVisible(not self.model.rows)
        counts=[len(self.items),sum(download_queue.status(i) in ('Queued','Downloading') for i in self.items),sum(download_queue.status(i) in ('Paused','Stopped') for i in self.items),sum(download_queue.status(i)=='Completed' for i in self.items),sum(download_queue.status(i) in ('Failed','Incomplete or missing files') for i in self.items)]
        for n,(button,label) in enumerate(zip(self.filter_buttons,['All Transfers','Active','Paused / stopped','Completed','Incomplete or Missing'])):
            button.setText(f'{label}  {counts[n]}');button.setChecked(n==filter_index)
        self.summary.setText(f"↓ {format_bytes(sum(i.get('download_rate') or 0 for i in self.items))}/s   ↑ {format_bytes(sum(i.get('upload_rate') or 0 for i in self.items))}/s   ·   {len(self.items)} saved transfers")
    def selected(self):
        rows=self.table.selectionModel().selectedRows()
        return self.model.rows[rows[0].row()] if rows else None
    def action(self,command,identifier=None):
        item=next((job for job in self.items if job['id']==identifier),None) if identifier else self.selected()
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
                'Retry this same queue entry using Anime Vault? It will start downloading. Previous external-client files stay untouched in their old folder. If this torrent is running in another application, stop it there first.',
                QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
            if response!=QMessageBox.Yes:return
        if command=='remove' and QMessageBox.question(self,'Remove queue entry?','Remove this transfer from the queue? Downloaded files and library history will be kept.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        start(self,lambda:download_queue.action(identifier,command),lambda message:(self.status.setText(message),self.refresh(),monitor().check()))
    def open_folder(self,identifier=None):
        if isinstance(identifier,bool):identifier=None
        item=next((job for job in self.items if job['id']==identifier),None) if identifier else self.selected()
        # The download root may differ from its staging destination after indexing.
        candidates=([item.get('library_destination'),item.get('root'),item.get('destination')]
                    if item else [downloads.settings().get('destination')])
        path=next((Path(value) for value in candidates if value and Path(value).is_dir()),None)
        if path is None:
            self.status.setText('The download folder is missing or the drive is unavailable.');return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):
            self.status.setText('Windows could not open the download folder: '+str(path))
    def delete_files(self,identifier=None):
        item=next((job for job in self.items if job['id']==identifier),None) if identifier else self.selected()
        if item is None:return
        if QMessageBox.question(self,'Move downloaded files to Recycle Bin?',f"Move files in {item['root']} to the Recycle Bin? Library history and the queue record are kept. This is separate from removing an entry. Space is reclaimed after emptying the Recycle Bin.",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        start(self,lambda:download_queue.recycle_files(item['id']),lambda message:(self.status.setText(message),self.refresh(),monitor().changed.emit()))
