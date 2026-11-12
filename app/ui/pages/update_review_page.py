"""Saved update details with a scoped, asynchronous Refresh data action."""
from PyQt5 import sip
from PyQt5.QtCore import Qt,QTimer,pyqtSignal
from PyQt5.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QScrollArea,QWidget,QFrame,QProgressBar
from app.ui.io_task import IOTask,track


class UpdateReviewPage(QDialog):
    dispose_on_leave=True
    refreshed=pyqtSignal()

    def __init__(self,parent,title,changes,identifiers,franchise_id=None):
        super().__init__(parent)
        self.identifiers=tuple(identifiers);self._worker=None;self._closed=False
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
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content=QWidget();content.setObjectName('transfer_clear');self.rows=QVBoxLayout(content);scroll.setWidget(content);outer.addWidget(scroll,1)
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
        while self.rows.count():
            item=self.rows.takeAt(0)
            if item.widget():item.widget().deleteLater()
        if not changes:
            label=QLabel('No saved changes are available yet. Select Refresh data to check this anime for updates.')
            label.setWordWrap(True);self.rows.addWidget(label)
        for change in changes:
            name,separator,status=change.partition(' — ')
            box=QFrame();box.setObjectName('transfer_panel');row=QVBoxLayout(box)
            for value in (name,status) if separator else (name,):
                label=QLabel(value);label.setTextFormat(Qt.PlainText);label.setWordWrap(True);row.addWidget(label)
            self.rows.addWidget(box)
        self.rows.addStretch()

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
