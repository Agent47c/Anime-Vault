"""Saved update details with a scoped, asynchronous Refresh data action."""
from PyQt5 import sip
from PyQt5.QtCore import Qt,QTimer,pyqtSignal
from PyQt5.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QScrollArea,QWidget,QFrame,QProgressBar,QComboBox
from app.ui.io_task import IOTask,track


class UpdateReviewPage(QDialog):
    dispose_on_leave=True
    refreshed=pyqtSignal()

    def __init__(self,parent,title,changes,identifiers,franchise_id=None):
        super().__init__(parent)
        self.identifiers=tuple(identifiers);self._worker=None;self._closed=False
        self._ignored_entries=set()
        self.franchise_id=franchise_id if franchise_id is not None else next(iter(self.identifiers),None)
        self.setObjectName('update_changes');self.setProperty('animevaultOwnScaledStyle',True)
        self.setWindowTitle('View changes');self.setProperty('navigationTitle',title+' / View changes')
        self.resize(900,650);self.refresh_home_style()
        outer=QVBoxLayout(self);header=QHBoxLayout()
        heading=QLabel(title);heading.setTextFormat(Qt.PlainText);heading.setWordWrap(True);heading.setObjectName('transfer_heading');header.addWidget(heading,1)
        self.details_button=QPushButton('Open details');self.details_button.setCursor(Qt.PointingHandCursor)
        self.details_button.setEnabled(self.franchise_id is not None);self.details_button.clicked.connect(self.open_details);header.addWidget(self.details_button)
        self.refresh_button=QPushButton('Refresh data');self.refresh_button.setProperty('accent',True);self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.clicked.connect(lambda:self.load(True));header.addWidget(self.refresh_button);outer.addLayout(header)
        self.progress=QProgressBar();self.progress.setRange(0,0);self.progress.setTextVisible(False);self.progress.setFixedHeight(4);self.progress.hide();outer.addWidget(self.progress)
        self.status=QLabel('Saved updates');self.status.setTextFormat(Qt.PlainText);self.status.setWordWrap(True);outer.addWidget(self.status)
        tools=QHBoxLayout();section=QLabel('Detected Releases & Updates');section.setObjectName('workflow_row_title');tools.addWidget(section,1)
        self.change_sort=QComboBox();self.change_sort.addItems(['Saved order','Release date: newest first','Release date: earliest first']);self.change_sort.setAccessibleName('Sort detected changes');self.change_sort.currentIndexChanged.connect(lambda:self.render(getattr(self,'_changes',[])));tools.addWidget(self.change_sort);outer.addLayout(tools)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content=QWidget();content.setObjectName('transfer_clear');self.rows=QVBoxLayout(content);self.rows.setSpacing(16);scroll.setWidget(content);outer.addWidget(scroll,1)
        self.render(changes)
        close=QPushButton('Close');close.setCursor(Qt.PointingHandCursor);close.clicked.connect(self.accept);outer.addWidget(close,0,Qt.AlignRight)
        if self.identifiers:QTimer.singleShot(0,lambda:self.load(False))
        else:self.refresh_button.setEnabled(False)

    def refresh_home_style(self):
        from app.ui.transfer_style import qss
        self.setStyleSheet(qss('update_changes'))

    def open_details(self):
        if self._closed or self.franchise_id is None:return
        from app.ui.pages.detail_modal import DetailModal
        from app.ui.navigation import navigate
        dialog=DetailModal(self.franchise_id,self,async_load=True)
        dialog.data_changed.connect(self.refreshed.emit)
        navigate(dialog)

    def render(self,changes):
        self._changes=list(changes)
        while self.rows.count():
            item=self.rows.takeAt(0)
            if item.widget():item.widget().deleteLater()
        if not changes:
            label=QLabel('No saved changes are available yet. Select Refresh data to check this anime for updates.')
            label.setWordWrap(True);self.rows.addWidget(label)
        entries=[e for e in getattr(self,'_entries',[]) if (e['fid'],e['raw']) not in self._ignored_entries]
        ordered=sorted(entries,key=lambda e:tuple(e.get('date') or (0,0,0)),reverse=self.change_sort.currentIndex()==1) if self.change_sort.currentIndex() else entries
        displayed=[(entry['text'],entry) for entry in ordered] if hasattr(self,'_entries') else [(change,None) for change in changes]
        for change,entry in displayed:
            name,separator,status=change.partition(' — ')
            from app.ui.components.paper_card import PaperCard
            box=PaperCard();box.setObjectName('change_card');box.setStyleSheet('background:transparent;border:none;');row=QVBoxLayout(box);row.setContentsMargins(24,22,24,22)
            from app.ui.manga_pages import active
            if not active():box.setObjectName('transfer_panel');box.setStyleSheet('');row.setContentsMargins(9,9,9,9)
            for value in (name,status) if separator else (name,):
                label=QLabel(value);label.setTextFormat(Qt.PlainText);label.setWordWrap(True);row.addWidget(label)
            self.rows.addWidget(box)
            if entry:
                actions=QHBoxLayout();actions.addStretch()
                find=QPushButton('Find release');
                from app.ui.icons import icon
                find.setIcon(icon('search','#596175')); find.clicked.connect(lambda checked=False,e=entry:self.find_release(e));actions.addWidget(find)
                ignore=QPushButton('Ignore');ignore.clicked.connect(lambda checked=False,e=entry:self.ignore_release(e));actions.addWidget(ignore);row.addLayout(actions)
        self.rows.addStretch()
        from app.ui.manga_workflows import finish
        finish(self)

    def find_release(self,entry):
        from app.ui.pages.release_search_page import ReleaseSearchPage
        from app.ui.navigation import navigate
        page=ReleaseSearchPage(self,entry['fid'],entry.get('assignment_context'))
        if entry.get('title'):page.query.setText(entry['title'])
        navigate(page)

    def ignore_release(self,entry):
        from app.core.update_review import ignore_entry
        key=(entry['fid'],entry['raw']);self._ignored_entries.add(key)
        worker=IOTask(lambda:ignore_entry(entry['fid'],entry['raw']));track(worker)
        def done(_):
            if sip.isdeleted(self) or self._closed:return
            self._entries=[e for e in self._entries if (e['fid'],e['raw'])!=(entry['fid'],entry['raw'])]
            self.render([e['text'] for e in self._entries]);self.refreshed.emit()
        def failed(message):
            self._ignored_entries.discard(key)
            if not sip.isdeleted(self) and not self._closed:self.status.setText('Could not ignore this release: '+message)
        worker.succeeded.connect(done);worker.failed.connect(failed);worker.finished.connect(worker.deleteLater);worker.start()

    def load(self,refresh):
        if self._closed or self._worker is not None:return
        from app.core.update_review import read_changes
        worker=IOTask(lambda:read_changes(self.identifiers,refresh,worker.isInterruptionRequested))
        self._worker=worker;track(worker)
        self.refresh_button.setEnabled(False);self.progress.show()
        self.status.setText('Checking AniList…' if refresh else 'Loading saved updates…')
        owner=self.parentWidget()
        while owner is not None and not hasattr(owner,'refresh_progress'):owner=owner.parentWidget()
        global_progress=getattr(owner,'refresh_progress',None) if refresh else None
        progress_key=f'update-review:{id(self)}'
        if global_progress is not None:global_progress.begin(progress_key,'Checking anime updates…')
        def ready(result):
            if sip.isdeleted(self) or self._closed:return
            self._entries=result.get('entries',[])
            self.render(result['changes'])
            self.status.setText(' · '.join(result['warnings']) or ('Update check complete.' if refresh else 'Saved updates loaded.'))
            if result['refreshed']:self.refreshed.emit()
        def failed(message):
            if not sip.isdeleted(self) and not self._closed:self.status.setText('Could not refresh. Saved changes are kept. '+message)
        def finished():
            if global_progress is not None and not sip.isdeleted(global_progress):global_progress.finish(progress_key)
            if not sip.isdeleted(self):
                self._worker=None
                if not self._closed:self.refresh_button.setEnabled(True);self.progress.hide()
            worker.deleteLater()
        worker.succeeded.connect(ready);worker.failed.connect(failed);worker.finished.connect(finished);worker.start()

    def done(self,result):
        self._closed=True
        if self._worker is not None:self._worker.requestInterruption()
        super().done(result)
