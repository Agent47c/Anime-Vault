"""User-controlled numbering labels without touching paths or release IDs."""
import json
from PyQt5.QtCore import pyqtSignal,Qt,QSize
from PyQt5.QtGui import QIcon,QTransform
from PyQt5.QtWidgets import QDialog,QHBoxLayout,QVBoxLayout,QSpinBox,QCheckBox,QLineEdit,QWidget,QToolButton,QAbstractSpinBox
from app import db
from app.core.season_numbering import save_manual
from app.ui.components.workflow import chrome,card,text
from app.ui.io_task import start


class SeasonNumbers(QDialog):
    centered_workflow=True
    workflow_width=740
    dispose_on_leave=True
    saved=pyqtSignal(int)
    def __init__(self,fid,parent=None):
        super().__init__(parent);self.fid=fid;self.controls={}
        body,self.save_button=chrome(self,'Edit season numbers','Choose which release is S1, S2, S3 and so on.','詳細','Save numbering',self.save)
        self.setObjectName('season_numbers');self.setWindowTitle('Edit season numbers')
        self.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint);self.resize(740,850)
        self.refresh_home_style()
        self.rows=[s for s in db.get_series_seasons(fid) if s.get('relation_type')=='SEASON']
        self.expected=[tuple(s[k] for k in ('id','franchise_id','anilist_id','title_display','season_number')) for s in sorted(self.rows,key=lambda s:s['id'])]
        for season in self.rows:
            frame,box=card();box.setContentsMargins(20,20,20,20);box.setSpacing(12)
            badge_row=QHBoxLayout();local=season.get('storage_state')=='ON_DISK'
            badge=text('ON DISK' if local else 'METADATA ONLY','season_badge');badge.setProperty('metadata',not local);badge_row.addWidget(badge)
            count=len(json.loads(season.get('video_files_json') or '[]'));badge_row.addWidget(text(f'{count} files' if local else 'No local files'),1);box.addLayout(badge_row)
            box.addWidget(text(season['title_display'],'workflow_row_title'))
            path=QLineEdit(season.get('season_folder_path') or 'Metadata only · No local files');path.setReadOnly(True);path.setCursorPosition(0);path.setToolTip(path.text());path.setAccessibleName('Season folder');path.setMinimumHeight(36);box.addWidget(path)
            row=QHBoxLayout();row.addWidget(text('Season number','season_label'),1)
            number=QSpinBox();number.setRange(1,999);number.setValue(max(1,season.get('season_number') or 1))
            number.setMinimumHeight(48);number.setFixedWidth(76);number.setAlignment(Qt.AlignCenter);number.setButtonSymbols(QAbstractSpinBox.NoButtons);number.setAccessibleName('Season number for '+season['title_display'])
            stepper=QWidget();stepper.setObjectName('stepper');step=QHBoxLayout(stepper);step.setContentsMargins(0,0,0,0);step.setSpacing(0);step.addWidget(number);arrows=QVBoxLayout();arrows.setSpacing(0)
            from app.ui.icons import icon
            from app.ui.review_reference_style import reference_colors
            down=icon('chevron-down',reference_colors()['muted'])
            for label,callback,graphic in [('Increase season number',number.stepUp,QIcon(down.pixmap(22,22).transformed(QTransform().rotate(180)))),('Decrease season number',number.stepDown,down)]:
                arrow=QToolButton();arrow.setIcon(graphic);arrow.setIconSize(QSize(14,14));arrow.setFixedSize(32,24);arrow.setAccessibleName(label);arrow.setToolTip(label);arrow.setCursor(Qt.PointingHandCursor);arrow.clicked.connect(callback);arrows.addWidget(arrow)
            step.addLayout(arrows)
            self.controls[season['id']]=number;row.addWidget(stepper);box.addLayout(row);body.addWidget(frame)
        body.addWidget(text('Only season labels change. Files, folder names, provider release links and episode history stay in place. Repeated numbers can be used for parts of the same season.','season_notice'))
        self.reviewed=QCheckBox('I reviewed these season labels');body.addWidget(self.reviewed)
        self.reviewed.setCursor(Qt.PointingHandCursor)
        self.save_button.setEnabled(False);self.reviewed.toggled.connect(self.save_button.setEnabled);body.addStretch()
    def refresh_home_style(self):
        from app.ui.episode_selection_style import style
        self.setProperty('animevaultOwnScaledStyle',True);self.setStyleSheet(style('season_numbers'))
    def save(self):
        if not self.reviewed.isChecked():return
        values={sid:control.value() for sid,control in self.controls.items()}
        start(self,lambda:save_manual(self.fid,values,self.expected),self.saved_result)
    def saved_result(self,_):self.saved.emit(self.fid);self.accept()
    def reject(self):
        if getattr(self,'_apply_worker',None) and self._apply_worker.isRunning():return
        super().reject()
