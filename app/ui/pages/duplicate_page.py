"""On-demand Organizer review for exact duplicate episode files."""
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTreeWidget,
    QTreeWidgetItem, QMessageBox, QHeaderView, QFrame,QMenu,
)
from app.core.duplicates import find_duplicates, delete_duplicate,save_review,load_review


class DuplicateWorker(QThread):
    ready = pyqtSignal(object)
    status = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, selected=None, parent=None,from_database=False):
        super().__init__(parent)
        self.selected = selected
        self.from_database=from_database

    def run(self):
        try:
            if self.selected is None:
                result = (load_review if self.from_database else find_duplicates)(self.isInterruptionRequested, self.status.emit)
                if self.isInterruptionRequested():raise InterruptedError('Stopped')
                if not self.from_database:save_review(result)
            else:
                deleted = 0
                for group, file in self.selected:
                    delete_duplicate(group, file, self.isInterruptionRequested)
                    deleted += 1
                result = deleted
            self.ready.emit(result)
        except InterruptedError:
            self.failed.emit("Stopped. Scan again to refresh the results.")
        except Exception as error:
            self.failed.emit(str(error))


class DuplicatePage(QDialog):
    data_changed = pyqtSignal()
    busy_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Duplicate episode files")
        self.organizer_owner=parent
        self.setObjectName('duplicate_page')
        self._worker = self._batch_worker = None
        layout = QVBoxLayout(self)
        title = QLabel("Duplicate files")
        title.setObjectName("duplicate_heading")
        layout.addWidget(title)
        note = QLabel("Only byte-identical files from the same anime, release and episode are offered for deletion. Different encodes and revised episodes remain separate.")
        note.setWordWrap(True)
        layout.addWidget(note)
        actions = QHBoxLayout()
        self.scan = QPushButton("Check duplicate files")
        self.scan.setProperty("accent", True)
        menu=QMenu(self.scan)
        menu.addAction('Check saved results from database',lambda:self._scan(True))
        menu.addAction('Check duplicate files on drive',lambda:self._scan(False))
        self.scan.setMenu(menu)
        actions.addWidget(self.scan)
        self.stop = QPushButton("Stop")
        self.stop.setEnabled(False)
        self.stop.clicked.connect(self._stop)
        actions.addWidget(self.stop)
        actions.addStretch()
        self.delete = QPushButton("Delete selected copies")
        self.delete.clicked.connect(self._delete)
        self.delete.setEnabled(False)
        actions.addWidget(self.delete)
        layout.addLayout(actions)
        self.status = QLabel("Expand an anime after scanning to review its files. Nothing is selected automatically.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Anime / episode / file", "Action"])
        self.tree.setColumnWidth(0, 760)
        self.tree.itemChanged.connect(self._selection_changed)
        layout.addWidget(self.tree, 1)
        layout.setContentsMargins(24,20,24,24);layout.setSpacing(18)
        layout.removeWidget(title);layout.removeWidget(note)
        from app.ui.components.design import MotifHeader
        header=MotifHeader('重複');header.setObjectName('merge_panel');head=QVBoxLayout(header);head.setContentsMargins(24,24,24,24);head.setSpacing(10)
        header.setAttribute(Qt.WA_StyledBackground,True)
        head.addWidget(title);head.addWidget(note);layout.insertWidget(0,header)
        safety=QLabel('One verified copy in each group is kept. Only additional identical copies can be selected for the Recycle Bin.');safety.setWordWrap(True);safety.setObjectName('merge_hint');layout.insertWidget(layout.indexOf(self.tree),safety)
        footer=QFrame();footer.setObjectName('merge_panel');foot=QVBoxLayout(footer);guarantee=QLabel('Safe deletion: reviewed copies go to the OS Recycle Bin. One verified copy is always protected.');guarantee.setWordWrap(True);foot.addWidget(guarantee);layout.addWidget(footer)
        layout.removeItem(actions)
        overview=QFrame();overview.setObjectName('merge_panel');overview_box=QVBoxLayout(overview);overview_box.setContentsMargins(16,16,16,16);overview_box.setSpacing(16)
        stats=QHBoxLayout();self.summary_labels=[]
        for caption in ('Affected series','Identical copies found','Potential reclaim'):
            tile=QFrame();tile.setObjectName('duplicate_stat');tile_box=QVBoxLayout(tile);label=QLabel(caption);label.setObjectName('merge_hint');tile_box.addWidget(label);value=QLabel('—');value.setObjectName('duplicate_value');tile_box.addWidget(value);self.summary_labels.append(value);stats.addWidget(tile)
        overview_box.addLayout(stats);overview_box.addLayout(actions);layout.insertWidget(1,overview)
        self.tree.setAlternatingRowColors(False);self.tree.setRootIsDecorated(True);self.tree.setIndentation(24)
        self.tree.header().setSectionResizeMode(0,QHeaderView.Stretch);self.tree.header().setSectionResizeMode(1,QHeaderView.ResizeToContents)
        self.tree.header().setStretchLastSection(False)
        self.tree.setUniformRowHeights(False);self.tree.setAccessibleName('Duplicate files grouped by anime and episode')
        self.delete.setText('Move selected copies to Recycle Bin');self.delete.setProperty('accent',True)
        for button in (self.scan,self.stop,self.delete):button.setCursor(Qt.PointingHandCursor);button.setAccessibleName(button.text());button.setMinimumHeight(44)
        self.refresh_home_style()

    def refresh_home_style(self):
        from app.ui.merge_duplicate_style import qss
        self.setProperty('animevaultOwnScaledStyle',True);self.setStyleSheet(qss('duplicate_page'))

    def _busy(self):
        return any(worker and worker.isRunning() for worker in (self._worker, self._batch_worker))

    def _start(self, worker, deleting=False):
        self.scan.setEnabled(False)
        self.delete.setEnabled(False)
        self.tree.setEnabled(False)
        self.stop.setEnabled(True)
        worker.status.connect(self.status.setText)
        worker.failed.connect(self._failed)
        worker.finished.connect(self._idle)
        if deleting:
            self._batch_worker = worker
            worker.ready.connect(self._deleted)
        else:
            self._worker = worker
            worker.ready.connect(self._results)
        self.busy_changed.emit(True)
        worker.start()

    def _failed(self, message):
        self.status.setText(message)
        if self._batch_worker is not None and self._batch_worker.selected is not None:
            self.tree.clear()
            self.data_changed.emit()

    def _idle(self):
        self.scan.setEnabled(True)
        self.tree.setEnabled(True)
        self.stop.setEnabled(False)
        self._selection_changed()
        self.busy_changed.emit(False)

    def _scan(self,from_database=False):
        if self._busy() or self._owner_busy():
            return
        self.tree.clear()
        self.status.setText("Verifying identical files. Large files can take time on an HDD.")
        self._start(DuplicateWorker(parent=self,from_database=from_database))

    def _results(self, result):
        groups, errors = result
        self.tree.clear()
        copies=sum(max(0,len(group['files'])-1) for group in groups)
        size=sum((file.get('signature') or [0])[0] for group in groups for file in group['files'][1:])
        from app.core.storage import format_bytes
        titles={group['files'][0]['title'] for group in groups if group['files']}
        for label,value in zip(self.summary_labels,(f'{len(titles)} anime',f'{copies} copies',format_bytes(size))):label.setText(value)
        parents = {}
        self.tree.blockSignals(True)
        for group in groups:
            title = group["files"][0]["title"]
            if title not in parents:
                parents[title] = QTreeWidgetItem(self.tree, [title])
            episodes = ", ".join(map(str, group["files"][0]["episodes"]))
            branch = QTreeWidgetItem(parents[title], ["Episode " + episodes, "Verified identical files"])
            for index, file in enumerate(group["files"]):
                size=(file.get('signature') or [0])[0]
                item = QTreeWidgetItem(branch, [file["path"]+'\n'+format_bytes(size), "Protected / Keep" if index == 0 else "Verified identical copy"])
                item.setToolTip(0, file["path"])
                if index==0:item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
                if index:
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.Unchecked)
                    item.setData(0, Qt.UserRole, (group, file))
        self.tree.blockSignals(False)
        self.status.setText(f"{len(groups)} exact duplicate groups. {len(errors)} files could not be checked.")
        self.status.setToolTip("\n".join(errors[:20]))
        for error in errors:
            warning=QTreeWidgetItem(self.tree,[error,'Review location / rescan drive']);warning.setToolTip(0,error)

    def _selected(self):
        items = []
        iterator = self.tree.invisibleRootItem()
        for anime in range(iterator.childCount()):
            parent = iterator.child(anime)
            for group in range(parent.childCount()):
                branch = parent.child(group)
                for file in range(branch.childCount()):
                    item = branch.child(file)
                    if item.checkState(0) == Qt.Checked and item.data(0, Qt.UserRole):
                        items.append(item.data(0, Qt.UserRole))
        return items

    def _selection_changed(self, *args):
        selected=self._selected()
        self.delete.setEnabled(not self._busy() and bool(selected))
        from app.core.storage import format_bytes
        size=sum((file.get('signature') or [0])[0] for _,file in selected)
        self.delete.setText(f'Move {len(selected)} selected copies to Recycle Bin · {format_bytes(size)}' if selected else 'Move selected copies to Recycle Bin')

    def _delete(self):
        selected = self._selected()
        if not selected or self._busy() or self._owner_busy():
            return
        response = QMessageBox.question(
            self, "Delete duplicate copies",
            f"Move {len(selected)} selected duplicate files to the Recycle Bin? The retained copy in each group will remain. Both files will be verified again. If recycling fails, the file is kept.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if response == QMessageBox.Yes:
            self._start(DuplicateWorker(selected, self), deleting=True)

    def _deleted(self, count):
        self.tree.clear()
        self.status.setText(f"Moved {count} verified duplicate copies to the Recycle Bin. Scan again to refresh the results.")
        self.data_changed.emit()

    def _stop(self):
        for worker in (self._worker, self._batch_worker):
            if worker and worker.isRunning():
                worker.requestInterruption()

    def _owner_busy(self):
        owner=self.organizer_owner
        if owner is None or not hasattr(owner,'merge_page'):return False
        busy=owner.merge_page.busy() or any(worker and worker.isRunning() for worker in (owner._worker,getattr(owner,'_batch_worker',None)))
        if busy:self.status.setText('Wait for the current organizer or merge operation to finish before checking duplicate files.')
        return busy

    def reject(self):
        if self._busy():
            self._stop()
            return
        super().reject()
