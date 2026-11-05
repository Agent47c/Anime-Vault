"""On-demand file inventory presented as a virtualized episode grid."""
import json
import os
from pathlib import Path

from PyQt5.QtCore import Qt, QAbstractListModel, QModelIndex, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QListView, QStyledItemDelegate,
    QMessageBox, QShortcut, QAbstractItemView,
)

from app import db
from app.config import VIDEO_EXTENSIONS, launch_video_file, set_last_franchise_id, get_last_episode_path
from app.core.parser import clean_title, extract_episode_numbers
from app.core.consolidation import explicit_season
from app.core.library_health import release_availability_notice
from app.ui.theme import COLORS


class EpisodeWorker(QThread):
    ready = pyqtSignal(list, list)
    failed = pyqtSignal(str)

    def __init__(self, fid, season_ids=None):
        super().__init__(QApplication.instance())
        self.fid = fid
        self.season_ids = season_ids

    def run(self):
        try:
            rows, warnings, seen = [], [], set()
            series = db.get_series(self.fid)
            if not series:
                raise ValueError("This anime is no longer in your library.")
            continuous = db.uses_continuous_episodes(series) or series.get("anilist_id") == 21
            watched = {Path(row["folder_path"]).resolve() for row in db.get_watched_directories()}
            for season in db.get_series_seasons(self.fid):
                if self.season_ids is not None and season["id"] not in self.season_ids:
                    continue
                if self.isInterruptionRequested():
                    return
                folder = season.get("season_folder_path")
                if not folder or season.get("storage_state") != "ON_DISK":
                    continue
                root = Path(folder).resolve()
                if not root.is_dir():
                    warnings.append(str(root))
                    continue
                # A shared loose-file root contains several anime. Keep its
                # inventory restricted to the files assigned to this entry.
                shared = root in watched or (season.get("local_scan_key") or "").startswith("loose-root:")
                if shared:
                    sources = ((root / name, season) for name in json.loads(season.get("video_files_json") or "[]"))
                else:
                    def walk():
                        def unreadable(error):
                            warnings.append(str(error.filename))
                        for directory, folders, files in os.walk(root, onerror=unreadable, followlinks=False):
                            if self.isInterruptionRequested():
                                return
                            folders[:] = [name for name in folders if not (Path(directory) / name).is_symlink()]
                            for name in files:
                                yield Path(directory) / name, season
                    sources = walk()
                for path, owner in sources:
                    if self.isInterruptionRequested():
                        return
                    if path.suffix.lower() not in VIDEO_EXTENSIONS or path.is_symlink() or not path.is_file():
                        continue
                    key = os.path.normcase(os.path.abspath(path))
                    if key in seen:
                        continue
                    seen.add(key)
                    numbers = extract_episode_numbers(path.name)
                    kind = owner.get("relation_type", "SEASON")
                    number = min(numbers, default=10000)
                    category = "Movie" if kind == "MOVIE" else "Episode"
                    label = clean_title(path.stem) if category == "Movie" or not numbers else (
                        str(numbers[0]) if len(numbers) == 1 else f"{numbers[0]}\u2013{numbers[-1]}"
                    )
                    if numbers and category == "Episode":
                        label = "Episode " + label
                    season_number = explicit_season(path.stem)
                    if season_number is None:
                        season_number = next((explicit_season(parent.name) for parent in path.parents
                                              if (parent == root or root in parent.parents)
                                              and explicit_season(parent.name) is not None), None)
                    if season_number is None and owner.get("anilist_id"):
                        season_number = owner.get("season_number")
                    season_label = f"S{season_number}" if season_number else "Season unknown"
                    subtitle = category if category == "Movie" else f"{season_label} / Episode"
                    rows.append({
                        "title": label, "type": category, "subtitle": subtitle, "name": path.name, "path": str(path),
                        "folder": owner.get("title_display") or root.name,
                        "season_id": owner["id"], "release_id": owner.get("anilist_id"), "kind": kind,
                        "sort": (kind != "SEASON", 0 if continuous else owner.get("season_number") or 0, number, path.name.casefold()),
                    })
            rows.sort(key=lambda row: row["sort"])
            if not self.isInterruptionRequested():
                self.ready.emit(rows, warnings)
        except Exception as error:
            if not self.isInterruptionRequested():
                self.failed.emit(str(error))


class EpisodeModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []
        self.last_played = self._path_key(get_last_episode_path())

    @staticmethod
    def _path_key(path):
        return os.path.normcase(os.path.abspath(path)) if path else None

    def mark_played(self, path):
        previous = self.last_played
        self.last_played = self._path_key(path)
        for number, row in enumerate(self.rows):
            if self._path_key(row["path"]) in (previous, self.last_played):
                index = self.index(number)
                self.dataChanged.emit(index, index, [Qt.UserRole + 1, Qt.AccessibleDescriptionRole])

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self.rows[index.row()]
        if role in (Qt.DisplayRole, Qt.AccessibleTextRole):
            return f"{row['title']} / {row.get('subtitle', row['type'])}"
        if role == Qt.ToolTipRole:
            return f"{row['title']} / {row.get('subtitle', row['type'])}"
        if role == Qt.UserRole:
            return row
        if role == Qt.UserRole + 1:
            return self._path_key(row["path"]) == self.last_played
        if role == Qt.AccessibleDescriptionRole:
            return "Last played" if self._path_key(row["path"]) == self.last_played else ""

    def replace(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()


class EpisodeDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        from PyQt5.QtWidgets import QStyle
        row = index.data(Qt.UserRole)
        palette = COLORS.get(QApplication.instance().property("animevaultTheme"), COLORS["dark"])
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        rect = option.rect.adjusted(5, 5, -5, -5)
        last_played = index.data(Qt.UserRole + 1)
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)
        painter.setBrush(QColor(palette["accent"] if last_played else palette["bg_card_alt"] if hovered or selected else palette["bg_card"]))
        border = QColor(palette["accent_secondary"] if selected else palette["accent"] if last_played else palette["text_muted"])
        if not selected:
            border.setAlpha(72)
        painter.setPen(QPen(border, 2 if selected else 1))
        painter.drawRoundedRect(rect, 12, 12)
        text = rect.adjusted(12, 10, -12, -10)
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(palette["on_red"] if last_played else palette["text_primary"]))
        painter.drawText(text.x(), text.y() + 18, painter.fontMetrics().elidedText(row["title"], Qt.ElideRight, text.width()))
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor(palette["on_red"] if last_played else palette["text_secondary"]))
        painter.drawText(text.x(), text.y() + 44, row.get("subtitle", row["type"]))
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(210, 82)


class EpisodePage(QDialog):
    dispose_on_leave = True

    def __init__(self, fid, parent=None, release=None):
        super().__init__(parent)
        self.fid = fid
        self.release = release
        self.setWindowTitle("Choose episode")
        self.setObjectName("series_details")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 24)
        heading = QLabel("Choose episode")
        heading.setObjectName("heading")
        layout.addWidget(heading)
        self.status = QLabel("Finding video files?")
        self.status.setObjectName("subheading")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.availability = QLabel()
        self.availability.setObjectName("episode_availability")
        self.availability.setWordWrap(True)
        self.availability.setTextFormat(Qt.PlainText)
        self.availability.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.availability.hide()
        layout.addWidget(self.availability)
        self.model = EpisodeModel(self)
        self.view = QListView()
        self.view.setObjectName("episode_grid")
        self.view.setAccessibleName("Episodes. Select a block to play. Use arrow keys and Enter with the keyboard.")
        self.view.setViewMode(QListView.IconMode)
        self.view.setResizeMode(QListView.Adjust)
        self.view.setMovement(QListView.Static)
        self.view.setLayoutMode(QListView.Batched)
        self.view.setBatchSize(100)
        self.view.setUniformItemSizes(True)
        self.view.setGridSize(QSize(210, 82))
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setMouseTracking(True)
        self.view.setModel(self.model)
        self.view.setItemDelegate(EpisodeDelegate(self.view))
        self.view.clicked.connect(self._play)
        layout.addWidget(self.view, 1)
        for key in ("Return", "Enter"):
            shortcut = QShortcut(key, self.view)
            shortcut.activated.connect(lambda: self._play(self.view.currentIndex()))
        self._worker = EpisodeWorker(fid)
        self._worker.ready.connect(self._loaded)
        self._worker.failed.connect(self.status.setText)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.finished.connect(self._worker_done)
        self.finished.connect(self._cancel)
        self._worker.start()

    def _loaded(self, rows, warnings):
        self.model.replace(rows)
        self._show_availability(rows, warnings)
        self.status.setText(f"{len(rows):,} video files across all local episode folders. Select a block to play."
                            + (f" {len(warnings)} folders could not be read." if warnings else "")
                            if rows else "No local video files found.")
        if rows:
            self.view.setCurrentIndex(self.model.index(0))

    def _show_availability(self, rows, warnings):
        series = db.get_series(self.fid) or {}
        seasons = db.get_series_seasons(self.fid)
        requests = {}
        for season in seasons:
            episode = season.get("next_airing_ep")
            if episode:
                key = (season.get("anilist_id") or season["id"], episode)
                requests[key] = {"episode": episode, "release_id": season.get("anilist_id"), "season_id": season["id"], "airing_at": season.get("next_airing_at")}
        record = db.get_franchise(self.fid) or {}
        metadata = json.loads(record.get("metadata_json") or "{}") or {}
        episode = (metadata.get("nextAiringEpisode") or {}).get("episode")
        if episode:
            key = (record.get("anilist_id") or self.fid, episode)
            requests.setdefault(key, {"episode": episode, "release_id": record.get("anilist_id"), "airing_at": (metadata.get("nextAiringEpisode") or {}).get("airingAt")})
        if self.release:
            requests = {0: self.release}
        messages = []
        root = series.get("root_folder_path") or "your anime library folder"
        for release in requests.values():
            episode = release["episode"]
            if db.uses_continuous_episodes(series) or series.get("anilist_id") == 21:
                scoped = [row for row in rows if row.get("kind") == "SEASON"]
            else:
                relevant = [season for season in seasons if
                            (release.get("release_id") is not None and season.get("anilist_id") == release["release_id"])
                            or (release.get("season_id") is not None and season["id"] == release["season_id"])]
                numbers = {season["season_number"] for season in relevant}
                ids = {season["id"] for season in relevant}
                ids.update(season["id"] for season in seasons if not season.get("anilist_id") and season["season_number"] in numbers)
                scoped = [row for row in rows if row["season_id"] in ids]
                if not ids:
                    messages.append(f"Episode {episode}: match its local season to verify availability.")
                    continue
            filenames = [Path(row["path"]).name for row in scoped if row.get("kind") == "SEASON"]
            messages.append(release_availability_notice(
                filenames, episode, root, release.get("airing_at"), bool(warnings)
            ))
        if messages:
            self.availability.setText("\n\n".join(messages))
            self.availability.show()

    def _worker_done(self):
        self._worker = None

    def _cancel(self, *args):
        if self._worker:
            self._worker.requestInterruption()

    def _play(self, index):
        if not index.isValid():
            return
        row = index.data(Qt.UserRole)
        try:
            launch_video_file(row["path"])
            self.model.mark_played(row["path"])
            set_last_franchise_id(self.fid)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Could not play episode", str(error))
