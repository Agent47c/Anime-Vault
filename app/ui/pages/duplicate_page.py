"""On-demand Organizer review for exact duplicate episode files."""
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTreeWidget,
    QTreeWidgetItem, QMessageBox,
)
from app.core.duplicates import find_duplicates, delete_duplicate


class DuplicateWorker(QThread):
    ready = pyqtSignal(object)
    status = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, selected=None, parent=None):
        super().__init__(parent)
        self.selected = selected

    def run(self):
        try:
            if self.selected is None:
                result = find_duplicates(self.isInterruptionRequested, self.status.emit)
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
        self._worker = self._batch_worker = None
        layout = QVBoxLayout(self)
        title = QLabel("Duplicate episode files")
        title.setObjectName("heading")
        layout.addWidget(title)
        note = QLabel("Only byte-identical files from the same anime, release and episode are offered for deletion. Different encodes and revised episodes remain separate.")
        note.setWordWrap(True)
        layout.addWidget(note)
        actions = QHBoxLayout()
        self.scan = QPushButton("Check duplicate files")
        self.scan.setProperty("accent", True)
        self.scan.clicked.connect(self._scan)
        actions.addWidget(self.scan)
        self.stop = QPushButton("Stop")
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

    def _scan(self):
        if self._busy():
            return
        self.tree.clear()
        self.status.setText("Checking sizes, then SHA-256 hashes. Large files can take time on an HDD.")
        self._start(DuplicateWorker(parent=self))

    def _results(self, result):
        groups, errors = result
        parents = {}
        self.tree.blockSignals(True)
        for group in groups:
            title = group["files"][0]["title"]
            if title not in parents:
                parents[title] = QTreeWidgetItem(self.tree, [title])
            episodes = ", ".join(map(str, group["files"][0]["episodes"]))
            branch = QTreeWidgetItem(parents[title], ["Episode " + episodes, "Identical SHA-256"])
            for index, file in enumerate(group["files"]):
                item = QTreeWidgetItem(branch, [file["path"], "Keep" if index == 0 else "Verified identical copy"])
                item.setToolTip(0, file["path"])
                if index:
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.Unchecked)
                    item.setData(0, Qt.UserRole, (group, file))
        self.tree.blockSignals(False)
        self.status.setText(f"{len(groups)} exact duplicate groups. {len(errors)} files could not be checked.")
        self.status.setToolTip("\n".join(errors[:20]))

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
        self.delete.setEnabled(not self._busy() and bool(self._selected()))

    def _delete(self):
        selected = self._selected()
        if not selected or self._busy():
            return
        response = QMessageBox.question(
            self, "Delete duplicate copies",
            f"Move {len(selected)} selected duplicate files to the Recycle Bin? The retained copy in each group will remain. Both hashes will be checked again. If recycling fails, the file is kept.",
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

    def reject(self):
        if self._busy():
            self._stop()
            return
        super().reject()
