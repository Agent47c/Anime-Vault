"""Shared-theme selector and review for explicit physical season moves."""
from PyQt5.QtCore import Qt,pyqtSignal,QThread
from PyQt5.QtWidgets import QDialog,QListWidget,QListWidgetItem,QSpinBox,QPushButton,QButtonGroup,QInputDialog,QWidget,QCheckBox,QFileDialog
from app import db
from app.ui.components.workflow import chrome,text,field,button
from app.ui.io_task import start
from app.core import season_file_moves as moves


class SeasonFileMoves(QDialog):
    centered_workflow=True
    workflow_width=900
    saved=pyqtSignal(int)
    def __init__(self,fid,parent=None):
        super().__init__(parent);self.fid=fid;self.plan=None;self._pending=False;self.episode_numbers={};self.folder_override=None
        body,self.apply_button=chrome(self,'Move episodes into a season','Choose files, review their destination, then confirm. Filenames stay unchanged.','移動','Review move',self.review)
        self.setObjectName('season_numbers');self.setWindowTitle('Move episodes into a season')
        from app.ui.episode_selection_style import style
        self.setStyleSheet(style('season_numbers'))
        self.season=QSpinBox(self);self.season.setRange(1,999);self.season.setValue(1);self.season.hide()
        self.destination_label=text('');body.addWidget(self.destination_label)
        from app.ui.components.flow_layout import FlowLayout
        self.season_buttons=QButtonGroup(self);self.season_buttons.setExclusive(True)
        choices=QWidget();self.choices=FlowLayout(choices);body.addWidget(choices)
        numbers={s.get('season_number') for s in db.get_series_seasons(fid) if s.get('season_number')}
        for number in sorted(numbers or {1}):self.add_season_button(number)
        if numbers and 1 not in numbers:self.add_season_button(min(numbers))
        self.add_season_control=button('Add season…',self.add_season);self.choices.addWidget(self.add_season_control)
        self.list=QListWidget();self.list.setMinimumHeight(240);self.list.setAccessibleName('Episode files to move');body.addWidget(self.list)
        self.select_button=button('Select all files',self.select_all);body.addWidget(self.select_button,0,Qt.AlignLeft)
        self.number_button=button('Number selected episodes…',self.number_selected);body.addWidget(self.number_button,0,Qt.AlignLeft)
        self.labels_button=button('Edit release labels…',self.edit_labels);body.addWidget(self.labels_button,0,Qt.AlignLeft)
        self.folder_button=button('Choose destination season folder…',self.choose_folder);body.addWidget(self.folder_button,0,Qt.AlignLeft)
        self.remove_empty=QCheckBox('Remove old season folders after moving, only if empty');self.remove_empty.setChecked(True);self.remove_empty.toggled.connect(self.invalidate);body.addWidget(self.remove_empty)
        self.message=text('Loading indexed episode files…');body.addWidget(self.message)
        self.apply_button.setEnabled(False);self.season.valueChanged.connect(self.invalidate);self.season.valueChanged.connect(self.update_destination);self.season.valueChanged.connect(lambda _:setattr(self,'folder_override',None));self.list.itemChanged.connect(self.invalidate);self.update_destination()
        start(self,lambda:(moves.files(fid),moves.pending(fid)),self.loaded)
    def loaded(self,value):
        files,pending=value
        self._pending=bool(pending);self.list.blockSignals(True)
        for row in files:
            numbers=[int(n) for n in (row.get('numbers') or '').split(',') if n]
            self.episode_numbers[row['id']]=numbers
            item=QListWidgetItem(f'S{row["season_number"] or "?"} · Episodes {", ".join(map(str,numbers))} · '+row['path']);item.setData(Qt.UserRole,row['id']);item.setData(Qt.UserRole+1,row['path']);item.setCheckState(Qt.Unchecked);self.list.addItem(item)
            if not row.get('available',True):item.setText('Missing location — '+item.text());item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
        self.list.blockSignals(False)
        self.apply_button.setEnabled(bool(files) or bool(pending));self.message.setText('Select the episode files to place in one season folder.')
        if pending:self.show_plan(pending)
    def select_all(self):
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            if self.list.item(i).flags() & Qt.ItemIsEnabled:self.list.item(i).setCheckState(Qt.Checked)
        self.list.blockSignals(False);self.invalidate()
    def invalidate(self,*_):
        if self._pending:return
        self.plan=None;self.apply_button.setText('Review move')
    def number_selected(self):
        items=[self.list.item(i) for i in range(self.list.count()) if self.list.item(i).checkState()==Qt.Checked]
        if not items:self.message.setText('Check the files to number first.');return
        first,ok=QInputDialog.getInt(self,'Number selected episodes','First local episode number',1,1,9999)
        if not ok:return
        for item in items:
            numbers=self.episode_numbers[item.data(Qt.UserRole)];count=max(1,len(numbers))
            self.episode_numbers[item.data(Qt.UserRole)]=list(range(first,first+count));item.setText('Episodes '+', '.join(map(str,range(first,first+count)))+' · '+item.data(Qt.UserRole+1));first+=count
        self.invalidate()
    def edit_labels(self):
        from app.ui.dialogs.season_numbers import SeasonNumbers
        from app.ui.navigation import navigate
        dialog=SeasonNumbers(self.fid,self);dialog.saved.connect(self.saved);navigate(dialog)
    def choose_folder(self):
        series=db.get_series(self.fid) or {}
        folder=QFileDialog.getExistingDirectory(self,'Choose destination season folder',series.get('root_folder_path') or '')
        if not folder:return
        from pathlib import Path
        from app.core.consolidation import explicit_season
        number=explicit_season(Path(folder).name)
        if number:self.add_season_button(number);self.season.setValue(number)
        self.folder_override=folder;self.invalidate();self.message.setText('Destination folder: '+folder)
    def add_season_button(self,number):
        existing=self.season_buttons.button(number)
        if existing:existing.setChecked(True);self.season.setValue(number);return
        control=button(f'Season {number:02}',lambda checked=False,n=number:self.season.setValue(n));control.setCheckable(True)
        self.season_buttons.addButton(control,number);self.choices.addWidget(control);control.setChecked(number==self.season.value())
    def add_season(self):
        number,ok=QInputDialog.getInt(self,'Add season','Season number',1,1,999)
        if not ok:return
        exists=self.season_buttons.button(number) is not None
        self.add_season_button(number);self.season.setValue(number);self.update_destination()
        self.invalidate()
        self.message.setText(f'Season {number:02} already exists — selected it.' if exists else f'Season {number:02} selected. Its folder will be created only after reviewing and confirming the move.')
    def update_destination(self,*_):
        title=(db.get_series(self.fid) or {}).get('display_title','Anime')
        self.destination_label.setText(f'{title} / Season {self.season.value():02}')
    def review(self):
        if self.plan:
            from app.ui.components.message_boxes import AppMessageBox as QMessageBox
            if QMessageBox.question(self,'Move selected episode files?',self.message.text()+'\n\nThe database will assign these files to the selected season. Existing files will not be overwritten.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
            start(self,lambda:moves.apply(self.plan,QThread.currentThread().isInterruptionRequested),self.completed,major=True,operation_title='Moving episodes between seasons');return
        ids=[self.list.item(i).data(Qt.UserRole) for i in range(self.list.count()) if self.list.item(i).checkState()==Qt.Checked]
        start(self,lambda:moves.preview(self.fid,ids,self.season.value(),self.episode_numbers,self.remove_empty.isChecked(),self.folder_override),self.show_plan)
    def show_plan(self,plan):
        self.plan=plan;self.message.setText(f'{len(plan["rows"])} files → Season {plan["season"]:02}\n'+plan['destination']['folder']+'\n'+('The season folder will be created.' if plan['destination']['create'] else 'Use the existing season folder.'))
        self.apply_button.setText('Confirm move');self.apply_button.setEnabled(True)
        if plan.get('remove_empty'):self.message.setText(self.message.text()+'\nOld season directories will be removed only if empty. Release filenames stay unchanged.')
        if moves.pending(self.fid):
            self._pending=True;self.season.setEnabled(False);self.list.setEnabled(False);self.select_button.setEnabled(False);self.remove_empty.setEnabled(False)
            for control in [*self.season_buttons.buttons(),self.add_season_control,self.number_button,self.labels_button,self.folder_button]:control.setEnabled(False)
    def completed(self,message):self.message.setText(message);self.saved.emit(self.fid);self.accept()
    def reject(self):
        if getattr(self,'_apply_worker',None) and self._apply_worker.isRunning():return
        super().reject()
