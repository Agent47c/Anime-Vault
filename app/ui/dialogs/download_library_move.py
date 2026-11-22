"""Review completed downloads before moving them into the main library."""
from PyQt5 import sip
from PyQt5.QtCore import Qt,QAbstractTableModel,QModelIndex
from PyQt5.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableView,QHeaderView,QAbstractItemView,QComboBox,QFileDialog,QWidget
from app.ui.io_task import IOTask,track
from app.core import download_library


class MoveModel(QAbstractTableModel):
    def __init__(self,rows,parent):super().__init__(parent);self.rows=rows
    def rowCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.rows)
    def columnCount(self,parent=QModelIndex()):return 3
    def headerData(self,n,orientation,role=Qt.DisplayRole):
        if orientation==Qt.Horizontal and role==Qt.DisplayRole:return ['Anime','Source','Library destination'][n]
    def data(self,index,role=Qt.DisplayRole):
        if index.isValid() and role in (Qt.DisplayRole,Qt.ToolTipRole):return self.rows[index.row()][['anime','source','target'][index.column()]]


class DownloadLibraryMove(QDialog):
    dispose_on_leave=True
    def __init__(self,plan,parent=None):
        super().__init__(parent);self.plan=plan;self._worker=None;self.setWindowTitle('Move completed downloads to library');box=QVBoxLayout(self)
        self.setObjectName('downloads_page')
        title=QLabel('Move completed downloads to library')
        self.move_heading=title
        box.addWidget(title)
        note=QLabel(f"{len(plan['rows'])} verified files → {plan['root']}\nExisting files are never overwritten. Active downloads and unknown files stay in place. Keep the app open until the current file finishes.");self.note=note;note.setWordWrap(True);box.addWidget(note)
        self.folder_overrides={};self.only_job_id=plan.get('only_job_id');self.destination_choice=QComboBox()
        for destination in plan.get('destinations',[]):self.destination_choice.addItem(destination['title']+f' / Season {destination["season"]}',destination)
        existing={d.get('fid') for d in plan.get('destinations',[])}
        for anime in plan.get('indexed_staging',[]):
            if anime['fid'] not in existing:self.destination_choice.addItem(anime['title']+' / Indexed files in Downloads',anime)
        choose=QPushButton('Choose destination season folder…');self.choose_button=choose;choose.clicked.connect(self.choose_folder)
        other=QPushButton('Select this anime’s episode files to move…');self.other_button=other;other.clicked.connect(self.open_episode_mover)
        refresh=QPushButton('Refresh completed files');refresh.clicked.connect(self.refresh_plan)
        from app.ui.components.flow_layout import FlowLayout
        controls=QWidget();controls.setObjectName('transfer_clear');flow=FlowLayout(controls)
        self.destination_choice.setMinimumWidth(250);self.destination_choice.setMaximumWidth(420)
        for control in (self.destination_choice,choose,other,refresh):flow.addWidget(control)
        box.addWidget(controls)
        for control in (choose,other,refresh):control.setMinimumHeight(44);control.setCursor(Qt.PointingHandCursor)
        self.destination_choice.currentIndexChanged.connect(self.choice_changed);self.choice_changed()
        table=QTableView();table.setObjectName('completed_move_table');self.table=table;self.move_model=MoveModel(plan['rows'],table);table.setModel(self.move_model);table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);table.setEditTriggers(QAbstractItemView.NoEditTriggers);table.setTextElideMode(Qt.ElideMiddle);box.addWidget(table,1)
        self.status=QLabel('\n'.join(plan['notes']));self.status.setWordWrap(True);box.addWidget(self.status)
        row=QHBoxLayout();back=QPushButton('Cancel');back.clicked.connect(self.reject);row.addWidget(back);row.addStretch()
        self.stop=QPushButton('Stop after current file');self.stop.setEnabled(False);self.stop.clicked.connect(self.interrupt);row.addWidget(self.stop)
        self.move_button=QPushButton(f"Move {len(plan['rows'])} files");self.move_button.setEnabled(bool(plan['rows']));self.move_button.clicked.connect(self.begin);row.addWidget(self.move_button);box.addLayout(row)
        for button in (back,self.stop,self.move_button):button.setMinimumHeight(44);button.setCursor(Qt.PointingHandCursor)
        self.refresh_home_style()
    def choice_changed(self,*_):
        choice=self.destination_choice.currentData() or {}
        self.choose_button.setEnabled(bool(choice.get('id')) and not self._worker)
        self.other_button.setEnabled(bool(choice.get('fid')) and not self._worker)
    def choose_folder(self):
        if self._worker:return
        destination=self.destination_choice.currentData()
        if not destination or not destination.get('id'):return
        folder=QFileDialog.getExistingDirectory(self,'Choose the destination season folder',destination['anime_root'])
        if not folder:return
        self.folder_overrides[destination['id']]=folder
        for d in self.plan.get('destinations',[]):
            if d.get('fid')==destination.get('fid') and d.get('season')==destination.get('season'):self.folder_overrides[d['id']]=folder
        self.refresh_plan()
    def refresh_plan(self):
        if self._worker:return
        from app.ui.io_task import start
        def ready(plan):
            if self.only_job_id:plan['rows']=[r for r in plan['rows'] if r['job_id']==self.only_job_id]
            self.destination_choice.clear();seen=set()
            for d in plan.get('destinations',[]):
                if self.only_job_id and d['id']!=self.only_job_id:continue
                scope=(d.get('fid'),d['season'])
                if scope not in seen:self.destination_choice.addItem(d['title']+f' / Season {d["season"]}',d);seen.add(scope)
            for d in plan.get('indexed_staging',[]):
                if d['fid'] not in {scope[0] for scope in seen}:self.destination_choice.addItem(d['title']+' / Indexed files in Downloads',d)
            choice=self.destination_choice.currentData() or {};self.choose_button.setEnabled(bool(choice.get('id')));self.other_button.setEnabled(bool(choice.get('fid')))
            self.plan=plan;self.move_model.beginResetModel();self.move_model.rows=plan['rows'];self.move_model.endResetModel();self.note.setText(f'{len(plan["rows"])} verified files → {plan["root"]}');self.move_button.setText(f'Move {len(plan["rows"])} files');self.move_button.setEnabled(bool(plan['rows']));self.status.setText('\n'.join(plan['notes']) or 'Destination selected. Review the files, then choose Move.')
        start(self,lambda:download_library.preview(self.plan['root'],self.folder_overrides),ready)
    def open_episode_mover(self):
        if self._worker:return
        choice=self.destination_choice.currentData() or {}
        if not choice.get('fid'):return
        from app.ui.dialogs.season_file_moves import SeasonFileMoves
        from app.ui.navigation import navigate
        dialog=SeasonFileMoves(choice['fid'],self)
        def moved(_):
            from app.ui.downloads import monitor
            monitor().changed.emit();self.accept()
        dialog.saved.connect(moved);navigate(dialog)
    def begin(self):
        self.move_button.setEnabled(False);self.stop.setEnabled(True)
        self.status.setText('Moving verified files… Keep the app open. Stop after current file leaves the remaining files in place.')
        worker=IOTask(lambda:download_library.move(self.plan,worker.isInterruptionRequested));self._worker=worker;self._apply_worker=worker;track(worker)
        from app.ui.components.operation_progress import watch
        watch(self, worker, 'Moving completed downloads to the library', major=True)
        self.choice_changed()
        def ready(message):
            if not sip.isdeleted(self):
                self.status.setText(message)
                self.move_button.setText('Retry remaining files');self._retry_ready='Review and retry:' in message or 'Stopped' in message
                from app.ui.downloads import monitor
                monitor().changed.emit()
        def done():
            if not sip.isdeleted(self):self.stop.setEnabled(False);self._worker=None;self._apply_worker=None;self.move_button.setEnabled(getattr(self,'_retry_ready',False));self.choice_changed()
            worker.deleteLater()
        worker.succeeded.connect(ready);worker.failed.connect(lambda message:ready('Review and retry: '+message));worker.finished.connect(done);worker.start()
    def refresh_home_style(self):
        from app.ui.transfer_style import qss
        from app.ui.theme_catalog import is_manga_dark
        style=qss('downloads_page')
        if is_manga_dark():
            from app.ui.manga_style import manga_colors
            colors=manga_colors()
            style+=f'''
                QTableView#completed_move_table {{background:{colors['panel']};
                    color:{colors['text']};border:1px solid {colors['line']};border-radius:12px;}}
                QTableView#completed_move_table QHeaderView::section {{background:{colors['raised']};
                    color:{colors['muted']};font-family:"JetBrains Mono";padding:10px;}}
            '''
        self.setStyleSheet(style)
        if hasattr(self,'move_heading'):
            from app.ui.home_style import px
            font=f'font:800 {px(28)}px "Noto Serif";' if is_manga_dark() else 'font-size:24px;font-weight:700;'
            self.move_heading.setStyleSheet(font)
        if hasattr(self,'move_button'):
            self.move_button.setProperty('accent',True if is_manga_dark() else None)
    def interrupt(self):
        if self._worker and not sip.isdeleted(self._worker):self._worker.requestInterruption()
    def done(self,result):
        self.interrupt();super().done(result)
