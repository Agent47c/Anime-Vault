"""Review completed downloads before moving them into the main library."""
from PyQt5 import sip
from PyQt5.QtCore import Qt,QAbstractTableModel,QModelIndex
from PyQt5.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableView,QHeaderView,QAbstractItemView
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
        self.setObjectName('downloads_page');self.refresh_home_style()
        title=QLabel('Move completed downloads to library');title.setStyleSheet('font-size:24px;font-weight:700;');box.addWidget(title)
        note=QLabel(f"{len(plan['rows'])} verified files → {plan['root']}\nExisting files are never overwritten. Active downloads and unknown files stay in place. Keep the app open until the current file finishes.");note.setWordWrap(True);box.addWidget(note)
        table=QTableView();table.setModel(MoveModel(plan['rows'],table));table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);table.setEditTriggers(QAbstractItemView.NoEditTriggers);table.setTextElideMode(Qt.ElideMiddle);box.addWidget(table,1)
        self.status=QLabel('\n'.join(plan['notes']));self.status.setWordWrap(True);box.addWidget(self.status)
        row=QHBoxLayout();back=QPushButton('Cancel');back.clicked.connect(self.reject);row.addWidget(back);row.addStretch()
        self.stop=QPushButton('Stop after current file');self.stop.setEnabled(False);self.stop.clicked.connect(self.interrupt);row.addWidget(self.stop)
        self.move_button=QPushButton(f"Move {len(plan['rows'])} files");self.move_button.setEnabled(bool(plan['rows']));self.move_button.clicked.connect(self.begin);row.addWidget(self.move_button);box.addLayout(row)
        for button in (back,self.stop,self.move_button):button.setMinimumHeight(44);button.setCursor(Qt.PointingHandCursor)
    def begin(self):
        self.move_button.setEnabled(False);self.stop.setEnabled(True)
        self.status.setText('Moving verified files… Keep the app open. Stop after current file leaves the remaining files in place.')
        worker=IOTask(lambda:download_library.move(self.plan,worker.isInterruptionRequested));self._worker=worker;self._apply_worker=worker;track(worker)
        def ready(message):
            if not sip.isdeleted(self):
                self.status.setText(message)
                self.move_button.setText('Retry remaining files');self._retry_ready='Review and retry:' in message or 'Stopped' in message
                from app.ui.downloads import monitor
                monitor().changed.emit()
        def done():
            if not sip.isdeleted(self):self.stop.setEnabled(False);self._worker=None;self._apply_worker=None;self.move_button.setEnabled(getattr(self,'_retry_ready',False))
            worker.deleteLater()
        worker.succeeded.connect(ready);worker.failed.connect(lambda message:ready('Review and retry: '+message));worker.finished.connect(done);worker.start()
    def refresh_home_style(self):
        from app.ui.transfer_style import qss
        self.setStyleSheet(qss('downloads_page'))
    def interrupt(self):
        if self._worker and not sip.isdeleted(self._worker):self._worker.requestInterruption()
    def done(self,result):
        self.interrupt();super().done(result)
