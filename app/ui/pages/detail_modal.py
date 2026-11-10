from app.ui.navigation import navigate
"""
Detail Modal — Faithful reproduction of the Anime Details reference mockup.
Includes:
- Left Column: Poster with status badge, 'Play on streaming site' gradient button,
  'Edit title' and 'Open folder' buttons, 'Delete files...' button, and disclaimer.
- Right Column: Title, Romaji/Native subtitles, genre pills, synopsis,
  1-10 rating pill buttons, notes field, and structured Seasons, Movies & OVAs list.
"""

import os
import re
import json
import webbrowser
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QTextEdit, QFileDialog, QMessageBox,
    QSizePolicy, QPlainTextEdit, QComboBox, QMenu, QGridLayout, QButtonGroup,
)
from PyQt5.QtGui import QPixmap, QFont, QColor, QPainter, QPainterPath
from PyQt5.QtCore import Qt, pyqtSignal, QRectF,QTimer

from app.ui.artwork import artwork_loader
from app.ui.components.close_button import CloseButton
from app.ui.components.smooth_scroll import SmoothScrollArea
from app import db
from app.config import (
    COVERS_DIR,
    set_last_franchise_id, set_last_streaming_url,
    launch_video_file, VIDEO_EXTENSIONS, get_last_episode_path, get_media_player_type,
)
from app.core.parser import analyze_season_health, extract_episode_numbers
from app.core.library_health import season_health, episode_inventory, movie_inventory, release_availability_notice
from app.ui.dialogs.delete_confirm import DeleteConfirmDialog
from app.ui.dialogs.custom_entry import CustomEntryDialog
from app.ui.dialogs.rematch_dialog import RematchDialog



def format_synopsis(text):
    """Keep paragraph breaks while collapsing repeated empty lines for display."""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n[ \t]*", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() or "No synopsis available."


class SynopsisLabel(QLabel):
    """Size the scroll content to wrapped text plus one trailing line."""

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_text()

    def setText(self, text):
        super().setText(text)
        self._fit_text()

    def _fit_text(self):
        if self.width() <= 0:
            return
        self.setContentsMargins(0, 0, 0, self.fontMetrics().lineSpacing())
        height = self.heightForWidth(self.width())
        if height > 0 and self.height() != height:
            self.setFixedHeight(height)


class DetailModal(QDialog):
    """Anime detail modal replicating the Anime Details Modal reference mockup."""

    data_changed = pyqtSignal()
    loaded = pyqtSignal()
    dispose_on_leave = True

    def __init__(self, franchise_id: int, parent=None, async_load=False):
        super().__init__(parent)
        self._detail_generation=0;self._detail_closed=False
        self.franchise_id = franchise_id
        self.setObjectName("series_details")
        self.setWindowTitle("Anime Details")
        self.resize(1040, 760)
        self.setMinimumSize(940, 660)
        self.setSizeGripEnabled(True)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #15161d;
                border: 1px solid #303139;
                border-radius: 18px;
            }
        """)

        artwork_loader().changed.connect(self._metadata_changed)
        if async_load:
            layout=QVBoxLayout(self);self._loading_label=QLabel('Loading anime details…');layout.addWidget(self._loading_label);layout.addStretch()
            QTimer.singleShot(0,self._reload_async)
            return
        if not self._load_data():
            layout=QVBoxLayout(self)
            message=QLabel('This library entry changed or was removed. Go back to the Library to select its current card.')
            message.setWordWrap(True);layout.addWidget(message);layout.addStretch()
            return
        self._setup_ui()
        artwork_loader().request(self.franchise)

    def _reload_async(self,notify=False):
        if self._detail_closed:return
        from app.ui.io_task import IOTask,track
        from app.ui.detail_data import prepare_details
        from PyQt5 import sip
        self._detail_generation+=1;generation=self._detail_generation
        if hasattr(self,'_loading_label') and not sip.isdeleted(self._loading_label):self._loading_label.setText('Loading anime details…')
        fid=self.franchise_id
        worker=IOTask(lambda:prepare_details(fid));track(worker)
        def ready(data):
            if sip.isdeleted(self) or self._detail_closed or generation!=self._detail_generation:
                if data:data['snapshot']['connection'].close()
                return
            if data is None:
                self.data_changed.emit();self.reject();return
            self.franchise=data['franchise'];self.franchise_id=self.franchise['id'];self.seasons=data['seasons']
            self.continuous_episodes=data['continuous'];self.episode_coverage=data['coverage']
            self._poster_source=data['poster'];self._prepared_resume=data['resume']
            self._building_detail=True;self.setUpdatesEnabled(False)
            old=self.layout()
            if old is not None:
                def clear(layout):
                    while layout.count():
                        item=layout.takeAt(0)
                        if item.widget():item.widget().hide();item.widget().deleteLater()
                        elif item.layout():clear(item.layout())
                clear(old);sip.delete(old)
            builder=self._build_ui_steps()
            def build_next():
                if sip.isdeleted(self) or self._detail_closed or generation!=self._detail_generation:
                    builder.close();data['snapshot']['connection'].close();return
                try:
                    with db.refresh_view(data['snapshot']):next(builder)
                except StopIteration:
                    data['snapshot']['connection'].close()
                    self._building_detail=False;self.setUpdatesEnabled(True)
                    artwork_loader().request(self.franchise);self.loaded.emit()
                    if notify:self.data_changed.emit()
                except Exception as error:
                    data['snapshot']['connection'].close()
                    self._building_detail=False;self.setUpdatesEnabled(True);failed(str(error))
                else:QTimer.singleShot(0,build_next)
            build_next()
        def failed(message):
            if sip.isdeleted(self) or self._detail_closed or generation!=self._detail_generation:return
            QMessageBox.warning(self,'Could not load anime details',message)
        worker.succeeded.connect(ready);worker.failed.connect(failed)
        worker.finished.connect(worker.deleteLater);worker.start()

    def done(self,result):
        self._detail_closed=True;self._detail_generation+=1
        worker=getattr(self,'_worker',None)
        if worker and worker.isRunning():worker.requestInterruption()
        super().done(result)

    def _load_data(self):
        self._poster_source=None
        self.franchise = db.get_series(self.franchise_id)
        if not self.franchise:
            self.seasons=[];self.continuous_episodes=False
            self.episode_coverage=episode_inventory([],continuous=False)
            return False
        self.franchise_id=self.franchise['id']
        self.seasons = db.get_series_seasons(self.franchise_id,series=self.franchise)
        self.continuous_episodes = db.uses_continuous_episodes(self.franchise)
        self.episode_coverage = episode_inventory(self.seasons, continuous=self.continuous_episodes)
        return True

    def _setup_ui(self):
        for _ in self._build_ui_steps():pass

    def _build_ui_steps(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 24, 40, 28)
        scroll = SmoothScrollArea()
        self.right_scroll = scroll
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(20)
        breadcrumb = QLabel("Library / " + self.franchise.get("display_title", "Series details"))
        breadcrumb.setObjectName("subheading")
        content_layout.addWidget(breadcrumb)
        hero = QHBoxLayout()
        hero.setSpacing(38)
        content_layout.addLayout(hero)

        # Poster Container
        self.poster_label = QLabel()
        self.poster_label.setFixedSize(220, 310)
        self.poster_label.setPixmap(self._create_modal_poster())
        hero.addWidget(self.poster_label, 0, Qt.AlignTop)

        resume_path, resume_season = self._resume_candidate()
        numbers = extract_episode_numbers(resume_path.name) if resume_path else []
        label = f"Play episode {numbers[0]}" if numbers else "Play episode"
        self.play_button = QPushButton("\u25b6  " + label)
        self.play_button.setObjectName("detail_play_main")
        self.play_button.setCursor(Qt.PointingHandCursor)
        self.play_button.setFixedHeight(36)
        self.play_button.clicked.connect(self._resume_or_play)
        split = QFrame()
        split.setObjectName("detail_play_split")
        split_layout = QHBoxLayout(split)
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(0)
        split_layout.addWidget(self.play_button)
        choose_btn = QPushButton()
        choose_btn.setObjectName("detail_play_arrow")
        choose_btn.setAccessibleName("Playback options")
        choose_btn.setCursor(Qt.PointingHandCursor)
        choose_btn.setFixedSize(36, 36)
        self.play_menu = QMenu(choose_btn)
        self.play_menu.setObjectName("detail_play_menu")
        resume_text = f"Resume episode {numbers[0]}" if numbers else "Resume last episode"
        if resume_season and not self.continuous_episodes:
            resume_text += f"\tSeason {resume_season['season_number']}"
        resume = self.play_menu.addAction(resume_text, self._resume_or_play)
        resume.setEnabled(resume_path is not None)
        self.play_menu.addAction("Play from episode 1", self._on_play_episode)
        self.play_menu.addAction("Choose episode...", self._choose_episode)
        self.play_menu.addSeparator()
        player = {
            "default": "Windows default", "vlc": "VLC", "mpv": "MPV",
            "mpc-hc": "MPC-HC", "custom": "Custom player",
        }.get(get_media_player_type(), "Windows default")
        self.play_menu.addAction(f"Player: {player}\tChange in Settings", self._open_player_settings)
        choose_btn.setMenu(self.play_menu)
        split_layout.addWidget(choose_btn)
        playback = QHBoxLayout()
        playback.setSpacing(12)
        playback.addWidget(split)
        playback.addStretch()

        # Row 1: Edit Title | Rematch Anime

        edit_btn = QPushButton("Edit title")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setFixedHeight(34)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #1d1f29;
                color: #f3f4f6;
                border: 1px solid #383a44;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #303139;
            }
        """)
        edit_btn.clicked.connect(self._edit_entry)

        rematch_btn = QPushButton("Rematch")
        rematch_btn.setCursor(Qt.PointingHandCursor)
        rematch_btn.setFixedHeight(34)
        rematch_btn.setStyleSheet("""
            QPushButton {
                background-color: #1d1f29;
                color: #8c6cff;
                border: 1px solid #3b3558;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #242240;
                border-color: #8c6cff;
            }
        """)
        rematch_btn.clicked.connect(self._on_rematch)

        # Row 2: Open Folder | Delete files...

        folder_btn = QPushButton("Open folder")
        folder_btn.setCursor(Qt.PointingHandCursor)
        folder_btn.setFixedHeight(34)
        folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #1d1f29;
                color: #f3f4f6;
                border: 1px solid #383a44;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #303139;
            }
        """)
        folder_btn.clicked.connect(self._open_folder)

        delete_btn = QPushButton("Delete files...")
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setFixedHeight(34)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ef4444;
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.15);
                border-color: #ef4444;
            }
        """)
        delete_btn.clicked.connect(self._delete_all_files)

        # Disclaimer Notice
        notice = QLabel("Deleting keeps this entry, poster, rating and a Watched, removed status.")
        notice.setStyleSheet("font-size: 11px; color: #898d9f; line-height: 1.4;")
        notice.setWordWrap(True)
        right_layout = QVBoxLayout()
        yield  # Let navigation/input run between independent layout sections.
        right_layout.setSpacing(20)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_column = QWidget()
        right_column.setObjectName("detail_content")
        right_column.setLayout(right_layout)
        hero.addWidget(right_column, 1)

        # Top Bar: Title & Circular Close Button
        header_row = QHBoxLayout()
        header_left = QVBoxLayout()
        header_left.setSpacing(12)

        # Main English Title
        title_lbl = QLabel(self.franchise.get("display_title", "Unknown Anime"))
        title_lbl.setStyleSheet("font-size: 44px; font-weight: 800; color: #f3f4f6;")
        title_lbl.setWordWrap(True)
        header_left.addWidget(title_lbl)

        # Subtitle: Romaji · Japanese
        subtitles = []
        if self.franchise.get("title_romaji"):
            subtitles.append(self.franchise["title_romaji"])
        if self.franchise.get("title_native"):
            subtitles.append(self.franchise["title_native"])
        sub_lbl = QLabel(" · ".join(subtitles) if subtitles else "Anime details")
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("font-size: 12px; color: #b0b3c2;")
        header_left.addWidget(sub_lbl)
        header_row.addLayout(header_left, 1)

        close_btn = CloseButton()
        close_btn.clicked.connect(self.accept)
        header_row.addWidget(close_btn, 0, Qt.AlignTop)
        right_layout.addLayout(header_row)

        badges_row = QHBoxLayout()
        badges_row.setSpacing(10)
        metadata = json.loads(self.franchise.get("metadata_json") or "{}") or {}
        badges = [(metadata.get("format") or "Anime", False)]
        if metadata.get("season") and metadata.get("seasonYear"):
            badges.append((f"{metadata['season'].title()} {metadata['seasonYear']}", False))
        numbered = [season for season in self.seasons if season.get("relation_type") == "SEASON"]
        if numbered and not self.continuous_episodes:
            badges.append((f"{len(numbered)} seasons", False))
        elif self.continuous_episodes:
            badges.append(("Continuing series", False))
        for season in numbered:
            if season.get("airing_status") == "RELEASING":
                text = "Currently airing" if self.continuous_episodes else f"Season {season['season_number']} airing"
                badges.append((text, True))
                break
        genres = self.franchise.get("genres") or "[]"
        if isinstance(genres, str):
            genres = json.loads(genres)
        if genres:
            badges.append((" \u00b7 ".join(genres[:2]), False))
        for text, airing in badges:
            pill = QLabel(text)
            pill.setObjectName("detail_badge")
            pill.setProperty("airing", airing)
            badges_row.addWidget(pill)
        badges_row.addStretch()
        right_layout.addLayout(badges_row)
        actions = playback
        actions.takeAt(actions.count() - 1)
        actions.addWidget(folder_btn)
        actions.addWidget(edit_btn)
        actions.addWidget(rematch_btn)
        from app.ui.downloads import open_downloads
        download_btn = QPushButton('Find Download Files')
        download_btn.setCursor(Qt.PointingHandCursor)
        from app.ui.pages.release_search_page import open_release_search
        download_btn.clicked.connect(lambda:open_release_search(self,self.franchise_id))
        actions.addStretch()
        right_layout.addLayout(actions)
        right_layout.addWidget(download_btn,0,Qt.AlignLeft)
        release_notice = QFrame()
        release_notice.setObjectName("final_panel")
        notice_layout = QHBoxLayout(release_notice)
        notice_layout.setContentsMargins(12, 10, 12, 10)
        self._release_status = QLabel()
        self._release_status.setWordWrap(True)
        notice_layout.addWidget(self._release_status, 1)
        self._release_play = QPushButton("Play this episode")
        self._release_play.setProperty("accent", True)
        self._release_play.clicked.connect(self._play_release_episode)
        notice_layout.addWidget(self._release_play)
        self._release_notice = release_notice
        release_notice.hide()
        right_layout.addWidget(release_notice)

        # Synopsis
        synopsis_text = format_synopsis(self.franchise.get("synopsis"))
        synopsis_lbl = SynopsisLabel(synopsis_text)
        self.synopsis_label = synopsis_lbl
        synopsis_lbl.setTextFormat(Qt.PlainText)
        synopsis_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        synopsis_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        synopsis_lbl.setWordWrap(True)
        synopsis_lbl.setStyleSheet("font-size: 16px; color: #B4B9CA;")
        synopsis_lbl.setMinimumWidth(0)
        synopsis_scroll = QScrollArea()
        synopsis_scroll.setWidgetResizable(True)
        synopsis_scroll.setFrameShape(QFrame.NoFrame)
        synopsis_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        synopsis_scroll.setMaximumHeight(100)
        synopsis_scroll.setMinimumHeight(88)
        synopsis_lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        synopsis_scroll.setWidget(synopsis_lbl)
        right_layout.addWidget(synopsis_scroll)
        api_btn = QPushButton("View API JSON")
        api_btn.setToolTip("Inspect the complete local API record and cached AniList response")
        api_btn.clicked.connect(self._show_api_json)
        tools_row = QHBoxLayout()
        tools_row.setSpacing(12)
        tools_row.addWidget(api_btn)
        group_btn = QPushButton("Group with another series")
        group_btn.clicked.connect(self._group_with_series)
        tools_row.addWidget(group_btn)
        tools_row.addStretch()
        right_layout.addLayout(tools_row)

        watch_label = QLabel("WATCH STATUS")
        watch_label.setObjectName("subheading")
        right_layout.addWidget(watch_label)
        status_track = QFrame()
        status_track.setObjectName("watch_status_track")
        statuses = QHBoxLayout(status_track)
        statuses.setContentsMargins(0, 0, 0, 0)
        statuses.setSpacing(12)
        self.watch_status_buttons = QButtonGroup(self)
        for text, value in (
            ("Watched", "WATCHED"), ("Watching", "WATCHING"),
            ("Plan to watch", "PLAN_TO_WATCH"), ("Dropped", "DROPPED"),
        ):
            button = QPushButton(text)
            button.setObjectName("watch_status_option")
            button.setMinimumSize(116, 42)
            button.setCheckable(True)
            button.setChecked(self.franchise.get("watch_status") == value)
            self.watch_status_buttons.addButton(button)
            button.clicked.connect(lambda checked=False, status=value: self._change_watch_status(status))
            statuses.addWidget(button)
        right_layout.addWidget(status_track, 0, Qt.AlignLeft)

        # ===================================================================
        # Section: YOUR RATING (1 to 10 Buttons)
        # ===================================================================
        rating_box = QVBoxLayout()
        rating_box.setSpacing(12)

        self.rating_title = QLabel("YOUR RATING")
        rating_box.addWidget(self.rating_title)

        rating_buttons_row = QHBoxLayout()
        rating_buttons_row.setSpacing(10)
        self.rating_buttons = []
        current_rating = self.franchise.get("user_rating") or 0
        self._update_rating_title_text(current_rating)

        for num in range(1, 11):
            btn = QPushButton(str(num))
            btn.setFixedSize(36, 32)
            btn.setCursor(Qt.PointingHandCursor)
            is_active = (num == current_rating)

            if is_active:
                btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #d92468, stop:1 #8e2de2);
                        color: #ffffff;
                        border: none;
                        border-radius: 7px;
                        font-weight: 700;
                        font-size: 13px;
                        padding: 0;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1d1f29;
                        color: #94a3b8;
                        border: 1px solid #383a44;
                        border-radius: 7px;
                        font-weight: 600;
                        font-size: 13px;
                        padding: 0;
                    }
                    QPushButton:hover {
                        background-color: #272d3d;
                        color: #ffffff;
                        border-color: #3b4256;
                    }
                """)
            btn.clicked.connect(lambda checked=False, n=num: self._set_rating(n))
            rating_buttons_row.addWidget(btn)
            self.rating_buttons.append(btn)

        rating_buttons_row.addStretch()
        rating_box.addLayout(rating_buttons_row)
        right_layout.addLayout(rating_box)


        # ===================================================================
        # Section: NOTES
        # ===================================================================
        yield
        notes_box = QVBoxLayout()
        notes_box.setSpacing(12)

        notes_title = QLabel("NOTES")
        notes_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #b0b3c2; letter-spacing: 0.5px;")
        notes_box.addWidget(notes_title)

        self.notes_edit = QTextEdit()
        self.notes_edit.setFixedHeight(40)
        self.notes_edit.setPlaceholderText("Add personal notes...")
        self.notes_edit.setText(self.franchise.get("user_notes", ""))
        self.notes_edit.setStyleSheet("""
            QTextEdit {
                background-color: #14151c;
                color: #f3f4f6;
                border: 1px solid #303139;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QTextEdit:focus {
                border-color: #df2545;
            }
        """)
        self.notes_edit.textChanged.connect(self._save_notes)
        notes_box.addWidget(self.notes_edit)
        right_layout.addLayout(notes_box)

        # ===================================================================
        # Section: SEASONS, ARCS, MOVIES & SPECIALS
        # ===================================================================
        seasons_box = QVBoxLayout()
        seasons_box.setSpacing(12)

        seasons_title = QLabel("EPISODES, MOVIES AND SPECIALS" if self.continuous_episodes else "SEASONS ON DISK")
        seasons_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #b0b3c2; letter-spacing: 0.5px;")
        seasons_box.addWidget(seasons_title)
        if not self.continuous_episodes and any(s.get('relation_type')=='SEASON' for s in self.seasons):
            numbering=QPushButton('Edit season numbers')
            numbering.clicked.connect(self._edit_season_numbers)
            seasons_box.addWidget(numbering,0,Qt.AlignLeft)
        coverage_btn = QPushButton("Episode and movie check")
        coverage_btn.clicked.connect(self._show_coverage)
        tools_row.insertWidget(tools_row.count() - 1, coverage_btn)
        if any(season.get("relation_type") == "SEASON" for season in self.seasons):
            mode_btn = QPushButton("Use separate seasons" if self.continuous_episodes else "Combine episode folders")
            mode_btn.setToolTip("Change how episodes are grouped and counted. Files stay in their folders.")
            mode_btn.clicked.connect(self._toggle_continuous_episodes)
            right_layout.addWidget(mode_btn, 0, Qt.AlignLeft)
            mode_btn.setMinimumWidth(210)
        if self.continuous_episodes:
            total = self.episode_coverage["unique_episode_count"]
            missing = len(self.episode_coverage["missing_episodes"])
            seasons_box.addWidget(QLabel(f"{total} distinct episodes across all folders · {missing} gaps within the detected range"))


        if not self.seasons:
            no_seasons = QLabel("No season or movie records found.")
            no_seasons.setStyleSheet("color: #898d9f; font-size: 12px;")
            seasons_box.addWidget(no_seasons)
        else:
            ordered = self.seasons
            if self.continuous_episodes:
                ranges = self.episode_coverage["folder_ranges"]
                ordered = sorted(ordered, key=lambda row: (
                    row["relation_type"] != "SEASON", ranges.get(row["id"], (10000,))[0]
                ))
            seasons_box.addWidget(self._create_season_table(ordered))

        lower = QWidget()
        lower_layout = QVBoxLayout(lower)
        lower_layout.setContentsMargins(258, 0, 0, 0)
        lower_layout.setSpacing(20)
        lower_layout.addLayout(seasons_box)
        content_layout.addWidget(lower)
        delete_panel = QFrame()
        delete_panel.setObjectName("detail_delete_panel")
        delete_row = QHBoxLayout(delete_panel)
        delete_row.setContentsMargins(20, 16, 20, 16)
        delete_row.addWidget(notice, 1)
        delete_row.addWidget(delete_btn)
        lower_layout.addWidget(delete_panel)
        content_layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)

    def check_release_episode(self, release):
        if not self.franchise:return
        from app.ui.pages.episode_page import EpisodeWorker
        self._release_request = dict(release)
        self._available_release_path = None
        self._release_notice.show()
        self._release_play.hide()
        self._release_status.setText(f"Checking episode {release['episode']} in your library...")
        owned = [s for s in self.seasons if s.get("relation_type") == "SEASON"]
        matched = [s for s in owned if (
            release.get("release_id") is not None and s.get("anilist_id") == release["release_id"]
        ) or (release.get("season_id") is not None and s["id"] == release["season_id"])]
        if not self._release_request.get("airing_at"):
            stamp = next((season.get("next_airing_at") for season in matched if season.get("next_airing_at")), None)
            metadata = json.loads(self.franchise.get("metadata_json") or "{}") or {}
            upcoming = metadata.get("nextAiringEpisode") or {}
            if not stamp and upcoming.get("episode") == release["episode"]:
                stamp = upcoming.get("airingAt")
            self._release_request["airing_at"] = stamp
        if self.continuous_episodes or self.franchise.get("anilist_id") == 21:
            matched = owned
        elif not any(s.get("season_folder_path") for s in matched):
            numbers = {s["season_number"] for s in matched}
            local = [s for s in owned if s.get("season_folder_path") and s.get("storage_state") == "ON_DISK"]
            candidates = [s for s in local if not s.get("anilist_id") and s["season_number"] in numbers]
            if len(candidates) == 1:
                matched = candidates
            elif not matched and len(local) == 1 and not local[0].get("anilist_id"):
                matched = local
        ids = {season["id"] for season in matched}
        if not ids:
            self._release_status.setText(
                "The local season for this release is not matched yet. Match its season to check episode availability."
            )
            return
        self._worker = EpisodeWorker(self.franchise_id, season_ids=ids)
        self._worker.ready.connect(self._release_checked)
        self._worker.failed.connect(self._release_status.setText)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.finished.connect(self._release_worker_done)
        self.finished.connect(self._cancel_release_check)
        self._worker.start()

    def _cancel_release_check(self, *args):
        worker = getattr(self, "_worker", None)
        if worker:
            worker.requestInterruption()

    def _release_worker_done(self):
        self._worker = None

    def _release_checked(self, rows, warnings):
        episode = self._release_request.get("episode")
        matching = [row for row in rows if episode in extract_episode_numbers(Path(row["path"]).name)]
        root = self.franchise.get("root_folder_path") or "your configured anime library folder"
        self._release_status.setText(release_availability_notice(
            [Path(row["path"]).name for row in rows if row.get("kind") == "SEASON"],
            episode, root, self._release_request.get("airing_at"), bool(warnings),
        ))
        if matching:
            self._available_release_path = matching[0]["path"]
            self._release_play.show()

    def _play_release_episode(self):
        path = getattr(self, "_available_release_path", None)
        if path:
            try:
                launch_video_file(path)
                set_last_franchise_id(self.franchise_id)
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, "Could not play episode", str(error))

    def _resume_candidate(self):
        if getattr(self,'_building_detail',False):return self._prepared_resume
        saved = get_last_episode_path()
        if not saved:
            return None, None
        path = Path(saved)
        if not path.is_file():
            return None, None
        key = os.path.normcase(os.path.abspath(path))
        for season in self.seasons:
            folder = season.get("season_folder_path")
            if not folder or season.get("storage_state") != "ON_DISK":
                continue
            if any(os.path.normcase(os.path.abspath(Path(folder) / name)) == key
                   for name in json.loads(season.get("video_files_json") or "[]")):
                return path, season
        return None, None

    def _resume_or_play(self):
        path, _ = self._resume_candidate()
        if path:
            launch_video_file(str(path))
        else:
            self._on_play_episode()

    def _open_player_settings(self):
        host = self.parentWidget()
        while host and not hasattr(host, "_on_nav_clicked"):
            host = host.parentWidget()
        if host:
            host._on_nav_clicked(4)

    def _change_watch_status(self, status):
        db.update_franchise_field(self.franchise_id, "watch_status", status)
        self.franchise["watch_status"] = status
        self.data_changed.emit()

    def _create_season_table(self, seasons):
        table = QFrame()
        table.setObjectName("detail_table")
        grid = QGridLayout(table)
        grid.setContentsMargins(12, 8, 12, 8)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(0)
        grid.setAlignment(Qt.AlignTop)
        for column, (title, width, stretch) in enumerate((
            ("Season", 140, 3), ("Episodes", 62, 1), ("Status", 92, 2),
            ("Quality", 70, 1), ("Size", 56, 1), ("Actions", 164, 2),
        )):
            grid.setColumnMinimumWidth(column, width)
            grid.setColumnStretch(column, stretch)
            label = QLabel(title)
            label.setObjectName("subheading")
            label.setFixedHeight(32)
            grid.addWidget(label, 0, column)
        for row, season in enumerate(seasons, 1):
            kind = season.get("relation_type")
            title = season.get("title_display") or "Episode folder"
            if self.continuous_episodes and kind == "SEASON":
                interval = self.episode_coverage["folder_ranges"].get(season["id"])
                title = f"Episodes {interval[0]}\u2013{interval[1]}" if interval else "Episode folder"
            else:
                badge = f"S{season['season_number'] or '?'}" if kind == "SEASON" else {"MOVIE": "MOV", "COLLECTION": "ALT"}.get(kind, "SP")
                title = f"{badge} \u00b7 {title}"
            grid.setRowMinimumHeight(row, 76)
            info = QWidget()
            info_layout = QVBoxLayout(info)
            info_layout.setContentsMargins(0, 8, 0, 8)
            heading = QLabel(title)
            heading.setTextFormat(Qt.PlainText)
            heading.setWordWrap(True)
            heading.setStyleSheet("font-weight: 700;")
            info_layout.addWidget(heading)
            announced=season.get("airing_status")=="NOT_YET_RELEASED"
            path = QLabel(season.get("season_folder_path") or ("Announced · Not released" if announced else "Not downloaded"))
            path.setTextFormat(Qt.PlainText)
            path.setWordWrap(True)
            path.setObjectName("subheading")
            info_layout.addWidget(path)
            grid.addWidget(info, row, 0)
            files = json.loads(season.get("video_files_json") or "[]")
            health = self.episode_coverage["seasons"].get(season["id"]) or season_health(season)
            count = health["found_count"] if kind == "SEASON" else len(files)
            expected = None if self.continuous_episodes else season.get("episodes_total")
            grid.addWidget(QLabel('Not released' if announced and not files else f"{count} / {expected}" if expected else str(count)), row, 1)
            state = season.get("storage_state")
            from app.core.series_grouping import release_status
            note=release_status(season.get("airing_status"))
            if state != "ON_DISK" and not announced:
                note = "Watched, removed" if state == "WATCHED_REMOVED" else "Missing from disk"
            gaps = health["missing_episodes"]
            if gaps and not self.continuous_episodes and not announced:
                note += f" / {len(gaps)} gaps"
            status = QLabel(note)
            status.setWordWrap(True)
            status.setToolTip(health["range_note"])
            grid.addWidget(status, row, 2)
            import re
            qualities = sorted({match for name in files for match in re.findall(r"\b(?:2160|1080|720|480)p\b", name, re.I)}, reverse=True)
            quality = QLabel(", ".join(qualities) or "Unknown")
            quality.setWordWrap(True)
            if health["duplicate_episodes"]:
                quality.setToolTip("Multiple files for episodes " + ", ".join(map(str, health["duplicate_episodes"])))
            grid.addWidget(quality, row, 3)
            size = season.get("size_bytes") or 0
            grid.addWidget(QLabel(f"{size / 1024 ** 3:.1f} GB" if size else "\u2014"), row, 4)
            actions = QWidget()
            buttons = QHBoxLayout(actions)
            buttons.setContentsMargins(0, 4, 0, 4)
            buttons.setSpacing(6)
            if state == "ON_DISK":
                play = QPushButton("Play")
                play.clicked.connect(lambda checked=False, item=season: self._on_play_season(item))
                buttons.addWidget(play)
                delete = QPushButton("Delete...")
                delete.setProperty("danger", True)
                delete.clicked.connect(lambda checked=False, item=season: self._delete_season(item))
                buttons.addWidget(delete)
                if kind == "SEASON" and not self.continuous_episodes:
                    options = QMenu(play)
                    options.addAction("Play episode", lambda item=season: self._on_play_season(item))
                    options.addAction("Match season", lambda sid=season["id"]: self._match_season(sid))
                    play.setMenu(options)
            elif announced:
                label=QLabel("Not released");label.setObjectName("subheading");buttons.addWidget(label)
            else:
                locate = QPushButton("Locate")
                locate.clicked.connect(lambda checked=False, sid=season["id"]: self._locate_season(sid))
                buttons.addWidget(locate)
            grid.addWidget(actions, row, 5)
        scroller = QScrollArea()
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QFrame.NoFrame)
        scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroller.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroller.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        scroller.setWidget(table)
        table.ensurePolished()
        scroller.setFixedHeight(table.sizeHint().height() + 8)
        return scroller

    def _choose_episode(self):
        from app.ui.pages.episode_page import EpisodePage
        navigate(EpisodePage(self.franchise_id, self, release=getattr(self, "_release_request", None)))

    def _toggle_continuous_episodes(self):
        db.set_continuous_episodes(self.franchise["id"], not self.continuous_episodes)
        self._on_rematched(self.franchise_id)

    def _group_with_series(self):
        from app.ui.pages.group_series_page import GroupSeriesPage
        page=GroupSeriesPage(self.franchise_id,self)
        page.grouped.connect(self._on_rematched)
        navigate(page)

    def _edit_season_numbers(self):
        from app.ui.dialogs.season_numbers import SeasonNumbers
        dialog=SeasonNumbers(self.franchise_id,self)
        dialog.saved.connect(self._on_rematched)
        navigate(dialog)

    def _show_coverage(self):
        from html import escape
        from PyQt5.QtWidgets import QTextBrowser
        current = db.get_franchise(self.franchise_id) or self.franchise
        seasons = db.get_series_seasons(self.franchise_id)
        coverage = episode_inventory(seasons, continuous=self.continuous_episodes)
        media = json.loads(current.get("metadata_json") or "null")
        movies = movie_inventory(seasons, media)
        html = ["<h2>Episode coverage</h2>", f"<p>{coverage['unique_episode_count']} distinct main-series episode numbers found. Movies, specials and alternate editions are separate.</p>"]
        html.append("<p>Unverified boundaries: only gaps between detected episodes are checked. Files elsewhere in this franchise can fill a gap in an arc.</p>")
        if self.continuous_episodes and coverage["missing_episodes"]:
            html.append("<p>Gaps across all episode folders: " + ", ".join(map(str, coverage["missing_episodes"])) + "</p>")
        for season in (() if self.continuous_episodes else seasons):
            result = coverage["seasons"].get(season["id"])
            if not result:
                continue
            missing = result["missing_episodes"]
            html.append("<h3>" + escape(season["title_display"]) + "</h3>")
            html.append(f"<p>{result['found_count']} distinct episodes · {result['file_count']} files<br>" + escape(result["range_note"]) + "</p>")
            if missing:
                html.append("<p style='color:#f2b94b'>Gaps in checked interval: " + escape(", ".join(map(str, missing))) + "</p>")
            if result["duplicate_episodes"]:
                html.append("<p>Multiple files for episode numbers: " + escape(", ".join(map(str, result["duplicate_episodes"]))) + ". These may be alternate encodes.</p>")
            if result["unrecognized_files"]:
                html.append(f"<p>{len(result['unrecognized_files'])} filenames need review; they are not silently counted as numbered episodes.</p>")
        html.append("<h2>Released movies</h2>")
        if movies["catalog_available"]:
            html.append(f"<p>{movies['matched_count']} matched out of {movies['released_count']} released movies in the cached provider catalog. This catalog may be incomplete.</p>")
            if movies["not_matched"]:
                html.append("<h3>Released titles not matched locally</h3><p>Review filenames before treating these as missing.</p><ul>")
                html.extend("<li>" + escape(entry["title"]) + "</li>" for entry in movies["not_matched"])
                html.append("</ul>")
            html.append(f"<p>{len(movies['upcoming'])} unreleased movies excluded from missing counts. {len(movies['unknown_release'])} movies with unknown release status also excluded.</p>")
        else:
            html.append("<p>No provider movie catalog cached yet. Missing movie totals cannot be verified.</p>")
        if movies["unmatched_local_files"]:
            html.append("<h3>Local movie filenames needing a match</h3><ul>")
            html.extend("<li>" + escape(filename) + "</li>" for filename in movies["unmatched_local_files"])
            html.append("</ul>")
        dialog = QDialog(self)
        dialog.setWindowTitle("Episode & movie check")
        dialog.resize(760, 650)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser()
        browser.setHtml("".join(html))
        layout.addWidget(browser)
        close = QPushButton("Close")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        navigate(dialog)

    def _metadata_changed(self, fid):
        if fid != self.franchise_id:
            return
        self._reload_async()

    def _show_api_json(self):
        from app.api.server import franchise_payload
        dialog = QDialog(self)
        dialog.setWindowTitle("API JSON · " + self.franchise.get("display_title", "Anime"))
        dialog.resize(800, 650)
        layout = QVBoxLayout(dialog)
        source = QComboBox()
        source.addItem("Local library API · /api/franchise/" + str(self.franchise_id))
        source.addItem("AniList · cached provider response")
        layout.addWidget(source)
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        editor.setStyleSheet("font-family: Consolas; font-size: 12px; padding: 10px;")
        layout.addWidget(editor)
        def show_source():
            current = db.get_franchise(self.franchise_id) or {}
            payload = franchise_payload(self.franchise_id) if source.currentIndex() == 0 else json.loads(current.get("metadata_json") or "null")
            editor.setPlainText(json.dumps(payload, indent=2, ensure_ascii=False) if payload is not None else "Provider metadata has not been fetched yet. Close and reopen this viewer after artwork finishes loading.")
        source.currentIndexChanged.connect(show_source)
        show_source()
        close = QPushButton("Close")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close, 0, Qt.AlignRight)
        navigate(dialog)

    def _create_modal_poster(self) -> QPixmap:
        """Create left poster with top-left status pill."""
        pixmap = QPixmap(220, 310)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, 220, 310, 14, 14)
        painter.setClipPath(path)

        # Load image or draw gradient fallback
        cover = self.franchise.get("cover_filename")
        cover_path = COVERS_DIR / cover if cover else None
        loaded = False
        source=getattr(self,'_poster_source',None)
        if source is not None or cover_path and cover_path.is_file():
            img = QPixmap.fromImage(source) if source is not None else QPixmap(str(cover_path))
            if not img.isNull():
                scaled = img.scaled(220, 310, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                painter.drawPixmap((220 - scaled.width()) // 2, (310 - scaled.height()) // 2, scaled)
                loaded = True

        if not loaded:
            painter.fillRect(0, 0, 220, 310, QColor("#1e293b"))
            painter.setPen(QColor(255, 255, 255, 40))
            painter.setFont(QFont("Yu Gothic", 80, QFont.Bold))
            painter.drawText(QRectF(0, 100, 220, 120), Qt.AlignCenter, "葬")

        # Top-left badge
        storage_state = self.franchise.get("storage_state", "ON_DISK")
        dot_color = QColor("#22c55e") if storage_state == "ON_DISK" else QColor("#f59e0b")
        text = "On disk" if storage_state == "ON_DISK" else "Partial"

        painter.setClipping(False)
        painter.setBrush(QColor(14, 16, 24, 210))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(12, 12, 74, 22), 11, 11)

        painter.setBrush(dot_color)
        painter.drawEllipse(QRectF(20, 19, 7, 7))

        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
        painter.drawText(QRectF(32, 12, 50, 22), Qt.AlignVCenter, text)

        painter.end()
        return pixmap

    def _create_season_row(self, s: dict) -> QFrame:
        """Create a season card row matching the reference mockup."""
        row = QFrame()
        row.setObjectName("season_row")
        row.setStyleSheet("""
            QFrame#season_row {
                background-color: #1d1f29;
                border: 1px solid #242938;
                border-radius: 10px;
                padding: 6px 10px;
            }
        """)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        # 1. Badge (S1, S2, SP, MOV)
        rel = s.get("relation_type", "SEASON")
        s_num = s.get("season_number", 1)
        if rel == "COLLECTION":
            tag_text = "ALT"
        elif rel == "MOVIE":
            tag_text = "MOV"
        elif rel in ("OVA", "SPECIAL"):
            tag_text = "SP"
        else:
            tag_text = f"S{s_num}" if s_num and not self.continuous_episodes else "EP"

        tag_lbl = QLabel(tag_text)
        tag_lbl.setFixedSize(28, 28)
        tag_lbl.setAlignment(Qt.AlignCenter)
        tag_lbl.setContentsMargins(0, 0, 0, 0)
        tag_lbl.setStyleSheet("""
            background-color: #242938;
            color: #b0b3c2;
            border-radius: 6px;
            padding: 0;
            font-size: 11px;
            font-weight: 700;
        """)
        layout.addWidget(tag_lbl)

        # 2. Title & Subtitle Info
        info_box = QVBoxLayout()
        info_box.setSpacing(1)

        # Title
        t_display = s.get("title_display") or f"Season {s_num}"
        if s.get("franchise_id") != self.franchise["id"] and s.get("release_title") and s["release_title"] not in t_display:
            t_display = s["release_title"] + " · " + t_display
        eps_info = f" · {s.get('episodes_total')} episodes" if s.get("episodes_total") else ""
        if self.continuous_episodes and rel == "SEASON":
            interval = self.episode_coverage["folder_ranges"].get(s["id"])
            if interval:
                first, last = interval
                t_display = f"Episode {first}" if first == last else f"Episodes {first}–{last}"
            else:
                t_display = "Episode folder"
            eps_info = ""
        t_lbl = QLabel(f"{t_display}{eps_info}")
        t_lbl.setWordWrap(True)
        t_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        t_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #f3f4f6;")
        info_box.addWidget(t_lbl)

        # Subtitle (Folder path or Airing status)
        sub_text = s.get("season_folder_path") or "Folder not set"
        if s.get("airing_status") == "RELEASING":
            sub_text = "Currently Airing · New episode soon"
        sub_lbl = QLabel(sub_text)
        sub_lbl.setWordWrap(True)
        sub_lbl.setTextFormat(Qt.PlainText)
        sub_lbl.setToolTip(sub_text)
        sub_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        sub_lbl.setStyleSheet("font-size: 11px; color: #898d9f;")
        info_box.addWidget(sub_lbl)
        layout.addLayout(info_box, 1)

        # 3. Status Pill
        st = s.get("storage_state", "ON_DISK")
        st_pill = QLabel()
        if st == "ON_DISK":
            st_pill.setText("On disk")
            st_pill.setStyleSheet("background-color: rgba(34, 197, 94, 0.15); color: #22c55e; border-radius: 8px; padding: 2px 8px; font-size: 11px; font-weight: 600;")
        elif st == "WATCHED_REMOVED":
            st_pill.setText("Watched, removed")
            st_pill.setStyleSheet("background-color: #242938; color: #b0b3c2; border-radius: 8px; padding: 2px 8px; font-size: 11px;")
        else:
            st_pill.setText("Announced · Not released" if s.get('airing_status')=='NOT_YET_RELEASED' else "Not downloaded")
            st_pill.setStyleSheet("background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; border-radius: 8px; padding: 2px 8px; font-size: 11px;")
        layout.addWidget(st_pill)

        # 4. Size
        sz_bytes = s.get("size_bytes", 0) or 0
        if sz_bytes >= 1024 ** 3:
            sz_str = f"{sz_bytes / (1024 ** 3):.1f} GB"
        elif sz_bytes > 0:
            sz_str = f"{sz_bytes / (1024 ** 2):.0f} MB"
        else:
            sz_str = "—"
        sz_lbl = QLabel(sz_str)
        sz_lbl.setStyleSheet("color: #b0b3c2; font-size: 12px; font-weight: 600;")
        layout.addWidget(sz_lbl)

        # Health indicator
        video_files = []
        try:
            video_files = json.loads(s.get("video_files_json", "[]"))
        except Exception:
            pass

        if st == "ON_DISK" and video_files and not (self.continuous_episodes and rel == "SEASON"):
            health = self.episode_coverage["seasons"].get(s["id"]) or season_health(s)
            if health["missing_episodes"]:
                miss_str = f"Missing: {', '.join(f'{m:02d}' for m in health['missing_episodes'][:3])}"
                health_pill = QLabel(miss_str)
                health_pill.setStyleSheet("background-color: rgba(242, 185, 75, 0.15); color: #f2b94b; border-radius: 8px; padding: 2px 8px; font-size: 10px; font-weight: 600;")
                health_pill.setToolTip("Missing within the checked interval: " + ", ".join(map(str, health["missing_episodes"])) + "\n" + health["range_note"])
                layout.addWidget(health_pill)
            elif rel in ("SEASON", "COLLECTION"):
                count = QLabel(f"{health['found_count']} episodes" + (" · range unverified" if not health["range_verified"] else ""))
                count.setStyleSheet("color: #b0b3c2; font-size: 10px; padding: 0;")
                count.setToolTip(health["range_note"])
                layout.addWidget(count)

        if rel == "SEASON" and st == "ON_DISK" and not self.continuous_episodes:
            rematch = QPushButton("Match season")
            rematch.setStyleSheet("padding: 4px 8px; font-size: 11px;")
            rematch.clicked.connect(lambda checked=False, sid=s["id"]: self._match_season(sid))
            layout.addWidget(rematch)

        # 5. Action Buttons (Play / Delete... or Locate)
        if st == "ON_DISK":
            if video_files:
                play_btn = QPushButton("Play")
                play_btn.setCursor(Qt.PointingHandCursor)
                play_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1e2230;
                        color: #f3f4f6;
                        border: 1px solid #383a44;
                        border-radius: 6px;
                        padding: 2px 10px;
                        font-size: 11px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #8c6cff;
                        color: #ffffff;
                    }
                """)
                play_btn.clicked.connect(lambda checked=False, s_data=s: self._on_play_season(s_data))
                layout.addWidget(play_btn)

            btn = QPushButton("Delete...")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #ef4444;
                    border: 1px solid rgba(239, 68, 68, 0.35);
                    border-radius: 6px;
                    padding: 2px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(239, 68, 68, 0.15);
                }
            """)
            btn.clicked.connect(lambda checked=False, s_data=s: self._delete_season(s_data))
            layout.addWidget(btn)
        elif s.get('airing_status')=='NOT_YET_RELEASED':
            layout.addWidget(QLabel('Not released'))
        else:
            btn = QPushButton("Locate")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #242938;
                    color: #f3f4f6;
                    border: none;
                    border-radius: 6px;
                    padding: 2px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #2e3447;
                }
            """)
            btn.clicked.connect(lambda checked=False, sid=s["id"]: self._locate_season(sid))
            layout.addWidget(btn)

        return row

    def _update_rating_title_text(self, rating: int):
        """Update header text indicator for user rating."""
        if rating and rating > 0:
            labels = {
                1: "Appalling", 2: "Horrible", 3: "Very Bad", 4: "Bad",
                5: "Average", 6: "Fine", 7: "Good", 8: "Very Good",
                9: "Great", 10: "Masterpiece"
            }
            lbl = labels.get(rating, "")
            self.rating_title.setText(f"YOUR RATING:  ★ {rating}/10  ·  {lbl}")
            self.rating_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #df2545; letter-spacing: 0.5px;")
        else:
            self.rating_title.setText("YOUR RATING:  Not Rated Yet (Click 1-10)")
            self.rating_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #b0b3c2; letter-spacing: 0.5px;")

    def _on_play_episode(self):
        """Play first available local video file across all on-disk seasons."""
        self.seasons = db.get_series_seasons(self.franchise_id)
        sorted_seasons = sorted(self.seasons, key=lambda x: (x.get("season_number") or 99))
        if self.continuous_episodes:
            ranges = self.episode_coverage["folder_ranges"]
            sorted_seasons.sort(key=lambda row: (
                row["relation_type"] != "SEASON", ranges.get(row["id"], (10000,))[0]
            ))
        for s in sorted_seasons:
            folder = s.get("season_folder_path")
            if not folder or not Path(folder).is_dir():
                continue
            try:
                files = json.loads(s.get("video_files_json", "[]"))
                if self.continuous_episodes and s["relation_type"] == "SEASON":
                    files.sort(key=lambda name: min(extract_episode_numbers(name), default=10000))
                for fname in files:
                    first_file = Path(folder) / fname
                    if first_file.is_file():
                        launch_video_file(str(first_file))
                        return
            except Exception:
                pass

        # Fallback: check root folder path directly
        rf = self.franchise.get("root_folder_path")
        if rf and Path(rf).is_dir():
            try:
                for entry in sorted(Path(rf).iterdir(), key=lambda x: x.name.lower()):
                    if entry.is_file() and entry.suffix.lower() in VIDEO_EXTENSIONS:
                        from app.core.scanner import index_local_folder
                        index_local_folder(rf, self.franchise['display_title'])
                        launch_video_file(str(entry))
                        return
            except Exception:
                pass

        QMessageBox.information(
            self,
            "No Video Files Found",
            f"No playable video files were found on disk for '{self.franchise.get('display_title')}'.\n\n"
            f"Check if the anime folder exists on disk or rematch the entry.",
        )

    def _on_play_season(self, season: dict):
        """Play first video file in this specific season."""
        season = db.get_season(season['id']) or season
        folder = season.get("season_folder_path")
        if folder and Path(folder).is_dir():
            try:
                files = json.loads(season.get("video_files_json", "[]"))
                for fname in files:
                    first_file = Path(folder) / fname
                    if first_file.is_file():
                        launch_video_file(str(first_file))
                        return
            except Exception:
                pass

        QMessageBox.information(
            self,
            "No Video Files in Season",
            f"No video files were found on disk for {season.get('title_display', 'this season')}.",
        )

    def _on_rematch(self):
        """Open manual AniList rematch dialog."""
        dlg = RematchDialog(self.franchise_id, self)
        dlg.rematched.connect(self._on_rematched)
        navigate(dlg)

    def _match_season(self, sid):
        season=db.get_season(sid)
        if not season:
            self._on_rematched(self.franchise_id)
            return
        owner = season["franchise_id"]
        dlg = RematchDialog(owner, self, season_id=sid)
        dlg.rematched.connect(self._on_rematched)
        navigate(dlg)

    def _on_rematched(self, fid: int):
        self.franchise_id = fid
        self._reload_async(notify=True)

    def _play_on_streaming_site(self):
        """Open local streaming bridge in browser and save state."""
        from app.api.server import api_base_url

        endpoint = api_base_url()
        if not endpoint:
            QMessageBox.information(self, "Streaming unavailable", "The local streaming API could not start.")
            return
        set_last_franchise_id(self.franchise_id)
        url = f"{endpoint}/api/franchise/{self.franchise_id}"
        set_last_streaming_url(url)
        webbrowser.open(url)


    def _set_rating(self, rating: int):
        db.update_franchise_field(self.franchise_id, "user_rating", rating)
        self.franchise["user_rating"] = rating
        self._update_rating_title_text(rating)
        for idx, btn in enumerate(self.rating_buttons):
            if idx + 1 == rating:
                btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #d92468, stop:1 #8e2de2);
                        color: #ffffff;
                        border: none;
                        border-radius: 7px;
                        font-weight: 700;
                        font-size: 13px;
                        padding: 0;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1d1f29;
                        color: #94a3b8;
                        border: 1px solid #383a44;
                        border-radius: 7px;
                        font-weight: 600;
                        font-size: 13px;
                        padding: 0;
                    }
                    QPushButton:hover {
                        background-color: #272d3d;
                        color: #ffffff;
                        border-color: #3b4256;
                    }
                """)
        self.data_changed.emit()


    def _save_notes(self):
        notes = self.notes_edit.toPlainText().strip()
        db.update_franchise_field(self.franchise_id, "user_notes", notes)
        self.data_changed.emit()

    def _open_folder(self):
        series = db.get_series(self.franchise_id) or self.franchise
        preferred = series.get("root_folder_path")
        folders = []
        for season in db.get_series_seasons(self.franchise_id):
            folder = season.get("season_folder_path")
            if not folder or season["storage_state"] != "ON_DISK":
                continue
            folder = Path(folder)
            for name in json.loads(season.get("video_files_json") or "[]"):
                file = folder / name
                if not file.is_file():
                    continue
                if preferred and Path(preferred) in file.parents:
                    os.startfile(preferred)
                    return
                scan_root = season.get("scan_root")
                if scan_root and Path(scan_root) in file.parents:
                    folders.append(Path(scan_root))
                else:
                    folders.append(folder)
                break
        if folders:
            os.startfile(str(folders[0]))
        elif preferred and Path(preferred).is_dir():
            os.startfile(preferred)
        else:
            QMessageBox.information(self, "Folder Missing", "No folder with indexed episodes was found. Use Find missing files in Organizer.")

    def _edit_entry(self):
        dialog = CustomEntryDialog(franchise_data=self.franchise, parent=self)
        def completed(result):
            if result != QDialog.Accepted:
                return
            self._reload_async(notify=True)
        navigate(dialog, completed)


    def _delete_all_files(self):
        dialog = DeleteConfirmDialog(self.franchise, self.seasons, self)
        def completed(result):
            if result != QDialog.Accepted:
                return
            self.data_changed.emit()
            self.accept()
        navigate(dialog, completed)


    def _delete_season(self, season: dict):
        dialog = DeleteConfirmDialog(self.franchise, [season], self)
        def completed(result):
            if result != QDialog.Accepted:
                return
            self._reload_async(notify=True)
        navigate(dialog, completed)


    def _locate_season(self, season_id: int):
        folder = QFileDialog.getExistingDirectory(self, "Select Season Folder")
        if folder:
            from app.ui.io_task import start
            start(self,lambda: db.update_season_folder(season_id,folder),self._located_season)

    def _located_season(self, _):
        self._reload_async(notify=True)
