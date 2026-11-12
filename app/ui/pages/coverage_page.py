"""Native episode coverage report; keeps conservative existing inventory rules."""
import json,time
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QFrame,QScrollArea,QWidget,QPushButton,QFileDialog
from app import db
from app.core.library_health import episode_inventory,movie_inventory
from app.ui.io_task import start
from app.ui.five_screen_style import qss

def prepare_coverage(fid):
    record=db.get_series(fid)
    if not record:raise ValueError('This anime no longer exists.')
    seasons=db.get_series_seasons(fid,series=record)
    continuous=db.uses_continuous_episodes(record)
    coverage=episode_inventory(seasons,continuous=continuous)
    return dict(record=record,seasons=seasons,continuous=continuous,coverage=coverage,movies=movie_inventory(seasons,json.loads(record.get('metadata_json') or 'null')))

class CoveragePage(QDialog):
    full_page=True
    dispose_on_leave=True
    def __init__(self,fid,parent=None):
        super().__init__(parent);self.fid=fid;self.report=None;self.setObjectName('coverage_report');self.setWindowTitle('Episode coverage & franchise breakdown');self.resize(1200,850);self.setStyleSheet(qss('coverage_report'))
        root=QVBoxLayout(self);root.setContentsMargins(28,24,28,24);root.setSpacing(20)
        title=QLabel(self.windowTitle());title.setObjectName('transfer_heading');root.addWidget(title)
        self.status=QLabel('Reading indexed episode coverage…');self.status.setWordWrap(True);root.addWidget(self.status)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);content=QWidget();content.setObjectName('transfer_clear');self.body=QHBoxLayout(content);self.body.setContentsMargins(0,0,0,0);self.body.setSpacing(24);self.left=QVBoxLayout();self.right=QVBoxLayout();self.body.addLayout(self.left,2);self.body.addLayout(self.right,1);scroll.setWidget(content);root.addWidget(scroll,1)
        footer=QHBoxLayout();footer.addStretch();self.export=QPushButton('Export breakdown (.json)');self.export.setEnabled(False);self.export.clicked.connect(self.export_report);footer.addWidget(self.export);close=QPushButton('Close report');close.setProperty('accent',True);close.clicked.connect(self.reject);footer.addWidget(close);root.addLayout(footer)
        start(self,lambda:prepare_coverage(fid),self.render)
    def panel(self,layout,title,detail):
        frame=QFrame();frame.setObjectName('transfer_panel');box=QVBoxLayout(frame);box.setContentsMargins(20,16,20,16);box.setSpacing(10)
        name=QLabel(title);name.setTextFormat(Qt.PlainText);name.setWordWrap(True);name.setObjectName('update_title');box.addWidget(name)
        text=QLabel(detail);text.setTextFormat(Qt.PlainText);text.setWordWrap(True);box.addWidget(text);layout.addWidget(frame)
    def render(self,data):
        self.report=data;coverage=data['coverage'];movies=data['movies'];self.export.setEnabled(True)
        self.status.setText(f"{coverage['unique_episode_count']} distinct main-series episode numbers found. Movies, specials and alternate editions are separate.")
        self.panel(self.left,'Unverified franchise boundaries','Only gaps between detected episodes are checked unless boundaries are verified. Files elsewhere in this franchise can fill a gap in an arc.')
        if data['continuous'] and coverage['missing_episodes']:self.panel(self.left,'Gaps across all episode folders',', '.join(map(str,coverage['missing_episodes'])))
        for season in data['seasons']:
            result=coverage['seasons'].get(season['id'])
            if not result:continue
            detail=f"{result['found_count']} distinct episodes · {result['file_count']} files\n{result['range_note']}"
            if result['missing_episodes']:detail+='\nGaps in checked interval: '+', '.join(map(str,result['missing_episodes']))
            if result['duplicate_episodes']:detail+='\nRepeated numbers (may be alternate encodes): '+', '.join(map(str,result['duplicate_episodes']))
            if result['unrecognized_files']:detail+=f"\n{len(result['unrecognized_files'])} filenames need review."
            self.panel(self.left,season['title_display'],detail)
        self.panel(self.right,'Franchise metrics',f"{coverage['unique_episode_count']} distinct episode numbers\n{len(data['seasons'])} indexed releases\n{sum(s.get('size_bytes') or 0 for s in data['seasons'])/1024**3:.1f} GB indexed\nCompletion ratio: unverified boundaries are not assumed complete.")
        detail=(f"{movies['matched_count']} matched of {movies['released_count']} released movies. Provider catalog may be incomplete.\n" if movies['catalog_available'] else 'No provider movie catalog cached.\n')+f"{len(movies['upcoming'])} unreleased and {len(movies['unknown_release'])} unknown-status movies excluded from missing counts."
        if movies['not_matched']:detail+='\nReleased titles not matched locally (review filenames):\n'+'\n'.join(r['title'] for r in movies['not_matched'])
        if movies['unmatched_local_files']:detail+='\nLocal movie filenames needing a match:\n'+'\n'.join(movies['unmatched_local_files'])
        self.panel(self.right,'Released movies',detail);self.left.addStretch();self.right.addStretch()
    def export_report(self):
        if not self.report:return
        path,_=QFileDialog.getSaveFileName(self,'Export coverage',str(db.EXPORTS_DIR/f'coverage-{self.fid}-{int(time.time())}.json'),'JSON (*.json)')
        if not path:return
        from pathlib import Path
        report=self.report
        def write():
            destination=Path(path);destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=lambda value:sorted(value) if isinstance(value,set) else str(value)),encoding='utf-8')
        start(self,write,lambda _:self.status.setText('Coverage report exported.'))
    def reject(self):
        if getattr(self,'_apply_worker',None) and self._apply_worker.isRunning():return
        super().reject()
