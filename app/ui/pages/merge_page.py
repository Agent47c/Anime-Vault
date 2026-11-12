"""Selected-series consolidation with an in-app preview and background workers."""
import json
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QCheckBox, QProgressBar, QScrollArea, QFrame, QComboBox, QSizePolicy,
)
from app import db
from app.ui.components.design import MotifHeader, ElidedLabel
from app.core.consolidation import make_plan, save_plan, apply_plan, sync_moved_inventory, approve_release_group


class MergePlanWorker(QThread):
    ready = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, roots, destination):
        super().__init__()
        self.roots, self.destination = roots, destination

    def run(self):
        try:
            plan = make_plan(self.roots, self.destination)
            if self.isInterruptionRequested():
                return
            folder = report_directory('merge-preview')
            save_plan(plan, folder)
            self.ready.emit({'plan': plan, 'report': str(folder)})
        except Exception as error:
            self.failed.emit(str(error))


def report_directory(prefix):
    return db.DATA_DIR / 'exports' / (prefix + '-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))


def selected_plan(plan, titles):
    return {**plan, 'moves': [entry for entry in plan['moves'] if entry['series'] in titles]}


class MergeWorker(QThread):
    progress = pyqtSignal(int, int, str)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, plan):
        super().__init__()
        self.plan = plan

    def run(self):
        try:
            folder = report_directory('merge-run')
            folder.mkdir(parents=True, exist_ok=False)
            source = db.get_connection()
            backup = sqlite3.connect(str(folder / 'before-moves.db'))
            try:
                source.backup(backup)
            finally:
                source.close()
                backup.close()
            result = apply_plan(self.plan, folder / 'move-journal.jsonl',
                                progress=self.progress.emit, should_stop=self.isInterruptionRequested)
            try:
                sync_moved_inventory(result['moved'], self.plan['destination'])
            except Exception as error:
                result['errors'].append({'source': 'Library indexing', 'error': str(error)})
            result['report'] = str(folder)
            (folder / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            self.completed.emit(result)
        except Exception as error:
            self.failed.emit(str(error))


class MergePage(QWidget):
    data_changed = pyqtSignal()
    busy_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plan = None
        self._merge_worker = self._merge_plan_worker = None
        self._rows = []
        self._setup_ui()
        from app.ui.merge_duplicate_style import apply_merge
        apply_merge(self)
        self.load_roots()

    def refresh_home_style(self):
        from app.ui.merge_duplicate_style import qss
        self.setProperty('animevaultOwnScaledStyle',True);self.setStyleSheet(qss('merge_page'))

    @staticmethod
    def _label(value, role="merge_hint"):
        label = QLabel(value)
        label.setObjectName(role)
        label.setWordWrap(True)
        return label

    @staticmethod
    def _button(value, callback, primary=False):
        control = QPushButton(value)
        control.setProperty("accent", primary)
        control.setCursor(Qt.PointingHandCursor)
        control.setMinimumHeight(40)
        control.clicked.connect(callback)
        return control

    def _panel(self, title, hint=""):
        panel = QFrame()
        panel.setObjectName("merge_panel")
        box = QVBoxLayout(panel)
        box.setContentsMargins(20, 20, 20, 20)
        box.setSpacing(12)
        box.addWidget(self._label(title, "merge_panel_title"))
        if hint:
            box.addWidget(self._label(hint))
        return panel, box

    @staticmethod
    def _style_table(table, heights):
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.verticalHeader().hide()
        table.verticalHeader().setDefaultSectionSize(heights)
        table.horizontalHeader().setFixedHeight(40)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        table.horizontalHeader().setMinimumSectionSize(40)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.setTextElideMode(Qt.ElideRight)

    def _setup_ui(self):
        self.setObjectName("merge_page")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content.setObjectName("merge_content")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 12, 28, 28)
        layout.setSpacing(20)
        header = MotifHeader("\u7d71\u5408")
        head = QHBoxLayout(header)
        head.setContentsMargins(0, 0, 0, 0)
        titles = QVBoxLayout()
        titles.setSpacing(4)
        titles.addWidget(self._label("Season organizer", "merge_heading"))
        titles.addWidget(self._label("Choose source roots and one destination. Preview every move, then select one or several anime."))
        head.addLayout(titles, 1)
        self.preview_state = self._label("Preview required", "merge_state")
        head.addWidget(self.preview_state, 0, Qt.AlignTop)
        layout.addWidget(header)

        controls = QHBoxLayout()
        controls.setSpacing(20)
        sources, source_layout = self._panel("Source roots", "Folders to merge from.")
        self.roots = QListWidget()
        self.roots.setObjectName("merge_roots")
        self.roots.setFixedHeight(108)
        self.roots.itemChanged.connect(self.invalidate)
        source_layout.addWidget(self.roots)
        controls.addWidget(sources, 5)
        destination, dest_layout = self._panel("Destination library", "Every selected anime moves into this folder.")
        dest_row = QHBoxLayout()
        dest_row.setSpacing(8)
        self.destination = QLineEdit(db.get_state('merge_destination', r'E:\Anime Library'))
        self.destination.setAccessibleName("Destination library")
        self.destination.textChanged.connect(self.invalidate)
        dest_row.addWidget(self.destination, 1)
        self.browse = self._button("Browse...", self.choose_destination)
        dest_row.addWidget(self.browse)
        dest_layout.addLayout(dest_row)
        self.preview_button = self._button("Generate move preview", self.preview, True)
        dest_layout.addWidget(self.preview_button, 0, Qt.AlignLeft)
        dest_layout.addStretch()
        controls.addWidget(destination, 7)
        layout.addLayout(controls)

        preview, preview_layout = self._panel("Move preview", "Files needing review stay in their original locations.")
        self.table = QTableWidget(0, 6)
        self.table.setObjectName("merge_preview")
        self.table.setHorizontalHeaderLabels(["", "Anime", "Ready files", "Needs folder", "Total size", "Destination"])
        self._style_table(self.table, 80)
        self.table.setMinimumHeight(240)
        self.table.setMaximumHeight(340)
        for col in (0, 2, 3, 4):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        for col in (1, 5):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 48)
        self.table.itemSelectionChanged.connect(self.show_files)
        self.table.itemChanged.connect(self.update_selection)
        preview_layout.addWidget(self.table)
        layout.addWidget(preview)

        files, files_layout = self._panel("Files for highlighted anime", "Highlighted in the table above. Tick its checkbox there to include it.")
        self.files_heading = files_layout.itemAt(0).widget()
        self.files = QTableWidget(0, 3)
        self.files.setObjectName("merge_files")
        self.files.setHorizontalHeaderLabels(["Source", "Destination", "Status"])
        self._style_table(self.files, 48)
        self.files.setMinimumHeight(220)
        self.files.setMaximumHeight(320)
        self.files.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.files.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.files.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        files_layout.addWidget(self.files)
        layout.addWidget(files)

        review, review_layout = self._panel("Before you move")
        review_row = QHBoxLayout()
        review_row.setSpacing(12)
        labels = QVBoxLayout()
        labels.setSpacing(2)
        self.review_label = self._label("For files needing a folder", "merge_row_title")
        labels.addWidget(self.review_label)
        labels.addWidget(self._label("Applies to the highlighted anime"))
        review_row.addLayout(labels, 1)
        self.release_combo = QComboBox()
        self.release_combo.setEditable(True)
        self.release_combo.addItem("Unassigned episodes")
        self.release_combo.setMinimumWidth(180)
        self.release_input = self.release_combo.lineEdit()
        self.release_input.setPlaceholderText("Unassigned episodes, Season 21, or Arcs/Egghead")
        self.release_combo.setAccessibleName("Folder for files needing review")
        review_row.addWidget(self.release_combo)
        self.approve_button = self._button("Approve folder for highlighted anime", self.approve_folder)
        self.approve_button.setEnabled(False)
        review_row.addWidget(self.approve_button)
        review_layout.addLayout(review_row)
        divider = QFrame()
        divider.setObjectName("merge_divider")
        divider.setFixedHeight(1)
        review_layout.addWidget(divider)
        self.confirm = QCheckBox("I reviewed the selected files and destination")
        self.confirm.toggled.connect(self.update_selection)
        review_layout.addWidget(self.confirm)
        self.status = self._label("Generate a preview to begin. No files are selected automatically.")
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        review_layout.addWidget(self.status)
        self.selection_summary = self._label("")
        self.selection_summary.hide()
        review_layout.addWidget(self.selection_summary)
        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.move_button = self._button("Move selected anime", self.move_selected, True)
        self.move_button.setEnabled(False)
        actions.addWidget(self.move_button)
        self.stop_button = self._button("Stop after current file", self.stop)
        self.stop_button.setEnabled(False)
        actions.addWidget(self.stop_button)
        hint = self._label("Move unlocks after you tick the review box.")
        actions.addWidget(hint, 1)
        review_layout.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.hide()
        review_layout.addWidget(self.progress)
        layout.addWidget(review)
        layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll)

    @staticmethod
    def _pill(table, row, column, value, review=False):
        holder = QWidget()
        holder.setAttribute(Qt.WA_TransparentForMouseEvents)
        holder.setObjectName("merge_pill_cell")
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(12, 6, 12, 6)
        label = QLabel(value)
        label.setObjectName("merge_pill")
        label.setProperty("review", review)
        label.setToolTip(value)
        label.setFixedHeight(24)
        label.setMinimumWidth(label.fontMetrics().horizontalAdvance(value) + 20)
        layout.addWidget(label, 0, Qt.AlignVCenter)
        layout.addStretch()
        item = table.item(row, column)
        if item is not None:
            item.setForeground(QColor(Qt.transparent))
            item.setSizeHint(QSize(label.minimumWidth() + 24, table.rowHeight(row)))
        table.setCellWidget(row, column, holder)

    def load_roots(self):
        self.roots.blockSignals(True)
        self.roots.clear()
        for root in db.get_watched_directories():
            item = QListWidgetItem(root['folder_path'])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked if Path(root['folder_path']).resolve() == Path(self.destination.text()).resolve() else Qt.Checked)
            self.roots.addItem(item)
        self.roots.blockSignals(False)

    def invalidate(self, *_):
        self.plan = None
        self.confirm.setChecked(False)
        self.move_button.setEnabled(False)
        self.table.setRowCount(0)
        self.files.setRowCount(0)
        self.approve_button.setEnabled(False)
        self.preview_state.setText("Preview required")
        self.files_heading.setText("Files for highlighted anime")
        self.selection_summary.hide()

    def choose_destination(self):
        folder = QFileDialog.getExistingDirectory(self, 'Choose destination library')
        if folder:
            self.destination.setText(folder)

    def busy(self):
        return any(worker and worker.isRunning() for worker in (self._merge_worker, self._merge_plan_worker))

    def set_busy(self, busy, moving=False):
        for control in (self.roots, self.destination, self.browse, self.preview_button, self.table, self.confirm, self.release_input):
            control.setEnabled(not busy)
        self.move_button.setEnabled(False)
        self.approve_button.setEnabled(False)
        self.stop_button.setEnabled(busy and moving)
        self.progress.setVisible(busy)
        self.preview_state.setText("Moving files" if busy and moving else "Preparing preview" if busy else "Preview ready" if self.plan else "Preview required")
        self.busy_changed.emit(busy)

    def preview(self):
        if self.busy():
            return
        roots = [self.roots.item(i).text() for i in range(self.roots.count()) if self.roots.item(i).checkState() == Qt.Checked]
        if not roots or not self.destination.text().strip():
            self.status.setText('Choose at least one source and a destination.')
            return
        self.invalidate()
        self.set_busy(True)
        self.progress.setRange(0, 0)
        self.status.setText('Reading source folders and preparing the preview…')
        self._merge_plan_worker = MergePlanWorker(roots, self.destination.text().strip())
        self._merge_plan_worker.ready.connect(self.plan_ready)
        self._merge_plan_worker.failed.connect(self.failed)
        self._merge_plan_worker.start()

    def plan_ready(self, payload):
        self.plan = payload['plan']
        db.set_state('merge_destination', self.plan['destination'])
        self.set_busy(False)
        self.render()
        errors = self.plan['errors']
        self.status.setText(f"{len(self._rows)} anime folders · {len(self.plan['unassigned'])} unassigned files · {len(errors)} errors. Preview: {payload['report']}" + ('\n' + '\n'.join(errors[:3]) if errors else ''))

    def render(self):
        self.table.blockSignals(True)
        grouped = defaultdict(list)
        for entry in self.plan['moves']:
            grouped[entry['series']].append(entry)
        self._rows = sorted(grouped)
        self.table.setRowCount(len(self._rows))
        for row, title in enumerate(self._rows):
            entries = grouped[title]
            ready = [entry for entry in entries if not entry['review_reason']]
            item = QTableWidgetItem('')
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            item.setCheckState(Qt.Unchecked)
            self.table.setItem(row, 0, item)
            item.setToolTip("Include " + title)
            values = [title, str(len(ready)), str(len(entries) - len(ready)), f"{sum(e['bytes'] for e in entries)/1024**3:.2f} GiB", str(Path(self.plan['destination']) / title)]
            for column, value in enumerate(values, 1):
                cell = QTableWidgetItem(value)
                cell.setToolTip(value)
                self.table.setItem(row, column, cell)
            self._pill(self.table, row, 3, str(len(entries) - len(ready)), bool(len(entries) - len(ready)))
            title_cell = QWidget()
            title_cell.setObjectName("merge_title_cell")
            labels = QVBoxLayout(title_cell)
            labels.setContentsMargins(12, 8, 12, 8)
            labels.setSpacing(3)
            name = ElidedLabel(title)
            name.setObjectName("merge_title")
            labels.addWidget(name)
            source = str(Path(entries[0]["source"]).parent)
            from app.ui.components.folder_button import FolderButton
            path = FolderButton(source)
            path.setObjectName("merge_path")
            labels.addWidget(path)
            self.table.item(row, 1).setForeground(QColor(Qt.transparent))
            self.table.setCellWidget(row, 1, title_cell)
        self.table.blockSignals(False)
        self.confirm.setChecked(False)
        self.update_selection()

    def selected_titles(self):
        return {title for row, title in enumerate(self._rows) if self.table.item(row, 0) and self.table.item(row, 0).checkState() == Qt.Checked}

    def update_selection(self, *_):
        selected = self.selected_titles() if self.plan else set()
        ready = sum(entry['series'] in selected and not entry.get('review_reason') for entry in self.plan['moves']) if self.plan else 0
        self.move_button.setText(f'Move {len(selected)} selected anime')
        self.move_button.setEnabled(bool(ready and self.confirm.isChecked() and self.plan and not self.plan['errors'] and not self.busy()))
        if self.plan:
            entries = [entry for entry in self.plan["moves"] if entry["series"] in selected]
            size = sum(entry["bytes"] for entry in entries if not entry.get("review_reason"))
            needs_folder = sum(bool(entry.get("review_reason")) for entry in entries)
            from app.core.storage import format_bytes
            self.selection_summary.setText(f"{len(selected)} anime selected \u00b7 {ready:,} ready files \u00b7 {format_bytes(size)} will move to {self.plan['destination']}. {needs_folder} files need a folder and stay where they are until approved.")
            self.selection_summary.show()
        if selected and not ready and not self.busy():
            self.status.setText('Selected files need a folder. Highlight the anime, choose a folder below, then approve it. Unassigned episodes keeps their numbering without guessing an arc.')

    def show_files(self):
        self.approve_button.setEnabled(False)
        if not self.plan or self.table.currentRow() < 0 or self.table.currentRow() >= len(self._rows):
            return
        title = self._rows[self.table.currentRow()]
        entries = [entry for entry in self.plan['moves'] if entry['series'] == title]
        self.approve_button.setEnabled(any(entry.get('review_reason') for entry in entries) and not self.busy())
        self.review_label.setText('For files needing a folder')
        self.review_label.setToolTip('Folder for ' + title)
        self.files_heading.setText('Files for ' + title)
        self.files.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            state = 'Needs folder' if entry['review_reason'] else ('Ready · approved folder' if entry.get('review_approved') else 'Ready · retain both copies' if entry['collision_preserved'] else 'Ready')
            for column, value in enumerate((entry['source'], entry['target'], state)):
                cell = QTableWidgetItem(value)
                cell.setToolTip(value)
                if column == 2 and entry.get('review_reason'):
                    cell.setToolTip(entry['review_reason'])
                if column == 0:
                    cell.setText(Path(entry["source"]).name)
                elif column == 1:
                    try:
                        cell.setText(str(Path(entry["target"]).relative_to(self.plan["destination"])))
                    except ValueError:
                        pass
                self.files.setItem(row, column, cell)
            self._pill(self.files, row, 2, state, bool(entry.get("review_reason")))

    def approve_folder(self):
        row = self.table.currentRow()
        if not self.plan or row < 0 or row >= len(self._rows) or self.busy():
            return
        title = self._rows[row]
        selected = self.selected_titles() | {title}
        try:
            self.plan = approve_release_group(self.plan, title, self.release_input.text())
        except ValueError as error:
            self.status.setText(str(error))
            return
        self.render()
        for index, name in enumerate(self._rows):
            if name in selected:
                self.table.item(index, 0).setCheckState(Qt.Checked)
        self.table.selectRow(self._rows.index(title))
        self.show_files()
        self.status.setText(f'Approved {self.release_input.text()} for {title}. Review the updated destinations and check the confirmation before moving.')

    def move_selected(self):
        if not self.plan or not self.confirm.isChecked() or not self.selected_titles() or self.busy():
            return
        host = self.window()
        if hasattr(host, '_active_task_page') and host._active_task_page(protect_only=True) is not None:
            self.status.setText('Wait for the other file operation to finish before merging.')
            return
        subset = selected_plan(self.plan, self.selected_titles())
        self.set_busy(True, moving=True)
        self.progress.setRange(0, sum(not entry['review_reason'] for entry in subset['moves']))
        self.progress.setValue(0)
        self.status.setText('Backing up the database and validating selected files…')
        self._merge_worker = MergeWorker(subset)
        self._merge_worker.progress.connect(self.on_progress)
        self._merge_worker.completed.connect(self.completed)
        self._merge_worker.failed.connect(self.failed)
        self._merge_worker.start()

    def on_progress(self, current, total, title):
        self.progress.setRange(0, total)
        self.progress.setValue(current)
        self.status.setText(f'Moving {title} · {current}/{total} files. You can navigate; keep the app open.')

    def stop(self):
        if self._merge_worker:
            self._merge_worker.requestInterruption()
            self.stop_button.setEnabled(False)
            self.status.setText('Stopping after the current file, then updating the library…')

    def completed(self, result):
        moved = {entry['source'] for entry in result['moved']}
        self.plan['moves'] = [entry for entry in self.plan['moves'] if entry['source'] not in moved]
        self.set_busy(False)
        self.render()
        if result['errors']:
            self.plan = None  # Require a fresh preview after an uncertain outcome.
            self.move_button.setEnabled(False)
        self.status.setText(f"Moved {len(moved)} files · {len(result['errors'])} errors" + (' · Stopped safely' if result.get('cancelled') else '') + f"\nLog: {result['report']}" + ''.join('\n' + error['error'] for error in result['errors'][:3]))
        self.data_changed.emit()

    def failed(self, message):
        self.set_busy(False)
        self.invalidate()
        self.status.setText('No further moves will run. Generate a fresh preview.\n' + message)
