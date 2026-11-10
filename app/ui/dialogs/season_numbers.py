"""User-controlled numbering labels without touching paths or release IDs."""
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout,QSpinBox,QCheckBox
from app import db
from app.core.season_numbering import save_manual
from app.ui.dialogs.drawer import DrawerDialog
from app.ui.components.workflow import chrome,card,text
from app.ui.io_task import start


class SeasonNumbers(DrawerDialog):
    saved=pyqtSignal(int)
    def __init__(self,fid,parent=None):
        super().__init__(parent);self.fid=fid;self.controls={}
        body,self.save_button=chrome(self,'Edit season numbers','Choose which release is S1, S2, S3 and so on.','詳細','Save numbering',self.save)
        self.rows=[s for s in db.get_series_seasons(fid) if s.get('relation_type')=='SEASON']
        self.expected=[tuple(s[k] for k in ('id','franchise_id','anilist_id','title_display','season_number')) for s in sorted(self.rows,key=lambda s:s['id'])]
        for season in self.rows:
            frame,box=card();box.addWidget(text(season['title_display'],'workflow_row_title'))
            box.addWidget(text(season.get('season_folder_path') or 'Metadata only · No local files'))
            row=QHBoxLayout();row.addWidget(text('Season number'),1)
            number=QSpinBox();number.setRange(1,999);number.setValue(max(1,season.get('season_number') or 1))
            number.setMinimumHeight(44);number.setAccessibleName('Season number for '+season['title_display'])
            self.controls[season['id']]=number;row.addWidget(number);box.addLayout(row);body.addWidget(frame)
        body.addWidget(text('Only season labels change. Files, folder names, provider release links and episode history stay in place. Repeated numbers can be used for parts of the same season.'))
        self.reviewed=QCheckBox('I reviewed these season labels');body.addWidget(self.reviewed)
        self.save_button.setEnabled(False);self.reviewed.toggled.connect(self.save_button.setEnabled);body.addStretch()
    def save(self):
        if not self.reviewed.isChecked():return
        values={sid:control.value() for sid,control in self.controls.items()}
        start(self,lambda:save_manual(self.fid,values,self.expected),self.saved_result)
    def saved_result(self,_):self.saved.emit(self.fid);self.accept()
    def reject(self):
        if getattr(self,'_apply_worker',None) and self._apply_worker.isRunning():return
        super().reject()
