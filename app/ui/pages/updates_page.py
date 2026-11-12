from collections import defaultdict
from contextlib import closing
from app.core.library_health import episode_inventory, season_health
from app.ui.components.design import MotifHeader
from app.ui.refresh import refresh_pixmap, refresh_image_exists, artwork_version
"""
Updates Page — New season & airing sequel alerts.
Shows anime that have new sequels, movies, or currently airing seasons.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QDialog, QComboBox, QButtonGroup, QMessageBox,QMenu,QCheckBox,
)
from PyQt5.QtGui import QFont, QPixmap, QColor
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer

from app import db
from app.ui.navigation import navigate
from app.config import COVERS_DIR, cached_online
from app.core.episode_updates import is_episode_change


class UpdateActionWorker(QThread):
    """Keep HDD commits and checkpoints outside the GUI event loop."""
    def __init__(self, fid, action, parent=None):
        super().__init__(parent)
        self.fids=list(fid) if isinstance(fid,(list,tuple,set)) else [fid]
        self.fid,self.action,self.error=self.fids[0] if self.fids else 0,action,None
        self.records = {}
        self.successful = []

    @staticmethod
    def perform(fid, action):
        if action == "watched":
            db.mark_watched_and_ignore_updates(fid)
        elif action == "dismiss":
            db.dismiss_updates(fid)
        else:
            db.set_update_disposition(fid, action)

    def run(self):
        failures=[]
        for fid in self.fids:
            if self.isInterruptionRequested():failures.append('Stopped before the next anime. Already saved choices are kept.');break
            try:
                series = db.get_series(fid) if self.action == 'watched' else None
                members = series.get('series_member_ids', [fid]) if series else [fid]
                previous = {member: (db.get_franchise(member) or {}).get('watch_status') for member in members}
                self.perform(fid,self.action)
                self.successful.append(fid)
                for member in members:
                    record = db.get_franchise(member)
                    if record:
                        record['_update_disposition'] = db.update_disposition(member)
                        record['_previous_watch_status'] = previous[member]
                        self.records[member] = record
            except Exception as error:
                record=db.get_franchise(fid) or {};failures.append(f"{record.get('display_title',fid)}: {error}")
        self.error='\n'.join(failures) if failures else None


class UpdateCard(QFrame):
    """A card showing an anime with an available update."""

    clicked = pyqtSignal(int)  # franchise_id
    dismissed = pyqtSignal()
    action_requested = pyqtSignal(int, str)
    selection_changed = pyqtSignal(int,bool)

    def __init__(self, franchise: dict, parent=None, async_actions=False):
        super().__init__(parent)
        self.async_actions = async_actions
        self.franchise_id = franchise["id"]
        self.display_title = franchise.get('display_title', 'Anime')
        self.disposition = franchise.get("_update_disposition", "new")
        self.setProperty('muted',self.disposition=='muted')
        self.setObjectName("update_card")
        self.setProperty("singleLineActions", True)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame#update_card {
                background-color: #15161d;
                border: 1px solid #303139;
                border-radius: 12px;
                padding: 4px;
            }
            QFrame#update_card:hover {
                border-color: #b0b3c2;
                background-color: #1d1f29;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(12)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        outer.addLayout(layout)
        self.checkbox=QCheckBox();self.checkbox.setAccessibleName('Select '+franchise.get('display_title','anime'));self.checkbox.hide();self.checkbox.toggled.connect(lambda checked:self.selection_changed.emit(self.franchise_id,checked));layout.addWidget(self.checkbox)

        # Mini poster
        poster = QLabel()
        poster.setFixedSize(64, 96)
        poster.setObjectName('update_poster');poster.setText((franchise.get('display_title') or '?')[0])
        poster.setAlignment(Qt.AlignCenter)
        poster.setStyleSheet("border-radius: 6px; background-color: #0d1117;")
        cover = franchise.get("cover_filename")
        if cover:
            cover_path = COVERS_DIR / cover
            if refresh_image_exists(cover_path):
                pixmap = refresh_pixmap(cover_path).scaled(
                    64, 96, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
                poster.setPixmap(pixmap)
        layout.addWidget(poster)

        # Info
        info = QVBoxLayout()
        info.setSpacing(4)

        from app.ui.components.design import ElidedLabel
        title=ElidedLabel(franchise.get('display_title','Unknown'));title.setObjectName('update_title')
        if self.disposition=='muted':
            font=title.font();font.setStrikeOut(True);title.setFont(font)

        from app.ui.update_release_dates import dated_changes
        self.changes = dated_changes(franchise)
        count = len(self.changes)
        tag=QLabel(('Muted notification rule' if self.disposition=='muted' else 'Episode update' if any(change.lower().startswith('episode ') for change in self.changes) else 'Release / metadata update')+(f" · AniList #{franchise['anilist_id']}" if franchise.get('anilist_id') else ''));tag.setObjectName('update_tag');info.addWidget(tag);info.addWidget(title)
        summary = QLabel(f"{count} change{'s' if count != 1 else ''} · New releases, announcements or airing episodes")
        summary.setStyleSheet("color: #b0b3c2; font-size: 12px; border: none; padding: 0;")
        summary.setWordWrap(True)
        info.addWidget(summary)
        if self.disposition != "new":
            saved = QLabel({"later": "Saved for later", "not_interested": "Not interested", "muted": "Updates muted"}[self.disposition])
            saved.setObjectName("subheading")
            info.addWidget(saved)
        preview = ElidedLabel(self.changes[0] if self.changes else "Update available")
        preview.setObjectName('subheading')
        preview.setTextFormat(Qt.PlainText)
        preview.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        preview.setStyleSheet("color: #dddfea; font-size: 12px; border: none; padding: 0;")
        info.addWidget(preview)
        dates=[change.rsplit(' · ',1)[-1] for change in self.changes if ' — ' in change]
        if dates:
            date_label=QLabel(dates[0]);date_label.setObjectName('update_tag');info.addWidget(date_label)

        layout.addLayout(info, 1)

        first = QHBoxLayout()
        first.setSpacing(10)
        first.addStretch()
        downloadable=self.disposition=='new' and any(change.lower().startswith('episode ') for change in self.changes)
        view_btn = QPushButton("Find Download Files" if downloadable else "View changes")
        view_btn.setProperty("accent", True)
        view_btn.setCursor(Qt.PointingHandCursor)
        view_btn.clicked.connect(self._find_download_files if downloadable else self._show_changes)
        first.addWidget(view_btn)
        if self.disposition != "new":
            restore = QPushButton("Restore updates")
            restore.setCursor(Qt.PointingHandCursor)
            restore.setToolTip("Return this anime's updates to the active list")
            restore.clicked.connect(self._restore)
            first.addWidget(restore)
        else:
            later = QPushButton("Later")
            later.setToolTip("Save this anime's updates for later until you restore them")
            later.clicked.connect(lambda: self._defer("later"))
            first.addWidget(later)
            not_interested = QPushButton("Not interested")
            not_interested.setToolTip("Keep this anime out of active updates until restored")
            not_interested.clicked.connect(lambda: self._defer("not_interested"))
            first.addWidget(not_interested)
            mute = QPushButton("Mute anime")
            mute.setToolTip("Hide all future updates for this anime until restored")
            mute.clicked.connect(self._mute)
            first.addWidget(mute)
            watched = QPushButton("Watched and ignore")
            watched.setToolTip("Mark all seasons in this series as watched and ignore current updates. New changes can still appear later.")
            watched.clicked.connect(self._watched_and_ignore)
            first.addWidget(watched)
            dismiss_btn = QPushButton("Dismiss")
            dismiss_btn.clicked.connect(self._dismiss)
            first.addWidget(dismiss_btn)
        if downloadable:
            changes=QPushButton('View changes');changes.clicked.connect(self._show_changes);first.addWidget(changes)
        from app.ui.components.flow_layout import FlowLayout
        action_content=QWidget();action_content.setObjectName('transfer_clear')
        visible_actions=FlowLayout(action_content);visible_actions.setSpacing(8)
        while first.count():
            item=first.takeAt(0)
            if item.widget():visible_actions.addWidget(item.widget())
        remove = QPushButton('Remove anime')
        remove.clicked.connect(self._remove_anime)
        visible_actions.addWidget(remove)
        from app.ui.home_style import px
        action_content.setMaximumWidth(px(138)*visible_actions.count()+8*(visible_actions.count()-1))
        action_content.setAccessibleName('Update actions')
        action_content.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        actions_row=QHBoxLayout();actions_row.setContentsMargins(0,0,0,0);actions_row.addStretch();actions_row.addWidget(action_content,1)
        outer.addLayout(actions_row)
        for control in self.findChildren(QPushButton):
            control.setCursor(Qt.PointingHandCursor)
            control.setMinimumHeight(px(36))
            control.setFixedWidth(px(138))
            control.setAccessibleName(control.text() + " for " + franchise.get("display_title", "anime"))
        self.setStyleSheet('')
        for label in (title,summary,preview,poster):label.setStyleSheet('')

    def _remove_anime(self):
        from app.ui.remove_anime import open_remove_anime
        open_remove_anime(self, self.franchise_id, self.hide)

    def set_selection(self,enabled,selected):
        self.checkbox.setCursor(Qt.PointingHandCursor)
        self.checkbox.setVisible(enabled);self.checkbox.blockSignals(True);self.checkbox.setChecked(selected);self.checkbox.blockSignals(False)
        if self.property('selected')!=bool(selected):
            self.setProperty('selected',bool(selected));self.style().unpolish(self);self.style().polish(self)

    def _find_download_files(self):
        from app.ui.pages.release_search_page import open_release_search
        open_release_search(self,self.franchise_id)

    def _perform_action(self, action):
        if self.async_actions:
            self.action_requested.emit(self.franchise_id, action)
            return
        UpdateActionWorker.perform(self.franchise_id, action)
        self.hide()
        self.dismissed.emit()

    def _watched_and_ignore(self):
        self._perform_action("watched")

    def _defer(self, disposition):
        self._perform_action(disposition)

    def _restore(self):
        self._perform_action("new")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.checkbox.isHidden():self.checkbox.toggle();event.accept();return
            # Opening details can run a nested event loop that refreshes the
            # updates list and deletes this card. Do not touch self afterward.
            event.accept()
            self.clicked.emit(self.franchise_id)
            return
        super().mousePressEvent(event)

    def _mute(self):
        self._perform_action("muted")

    def _dismiss(self):
        self._perform_action("dismiss")

    def _show_changes(self):
        show_update_changes(self, self.display_title, self.changes, (self.franchise_id,))


def show_update_changes(parent, title, changes, identifiers=(), franchise_id=None):
    from app.ui.pages.update_review_page import UpdateReviewPage
    dialog=UpdateReviewPage(parent,title,changes,identifiers,franchise_id=franchise_id)
    owner=parent
    while owner is not None:
        if isinstance(owner,UpdatesPage):
            dialog.refreshed.connect(owner.data_changed.emit)
            break
        owner=owner.parentWidget()
    navigate(dialog)


class UpdatesPage(QWidget):
    """Page showing all anime with detected updates."""

    card_clicked = pyqtSignal(int)  # franchise_id
    data_changed = pyqtSignal()
    refresh_requested = pyqtSignal()
    action_finished = pyqtSignal(int)
    choices_changed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._apply_worker = None
        self._pending_actions = []
        self._update_card_pool = {}
        self._health_card_pool = {}
        self.selected_fids=set();self._selection_mode=False;self._health_worker=None;self._health_generation=0
        self.setObjectName('updates_page')
        self.setAttribute(Qt.WA_StyledBackground,True)
        self._setup_ui()
        for control in self.findChildren(QPushButton):control.setCursor(Qt.PointingHandCursor)
        self.refresh_home_style()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 12)
        layout.setSpacing(16)

        from app.ui.home_style import load_fonts
        from app.ui.components.flow_layout import FlowLayout
        load_fonts();masthead=QFrame();masthead.setObjectName('transfer_panel')
        header_layout = QHBoxLayout(masthead)
        header_layout.setContentsMargins(24,20,24,20)
        headings = QVBoxLayout()
        headings.setAlignment(Qt.AlignTop)
        title = QLabel("Updates")
        title.setObjectName("transfer_heading")
        headings.addWidget(title)
        desc = QLabel("Metadata, new episodes, seasons and local health warnings")
        desc.setObjectName("subheading")
        desc.setWordWrap(True)
        title.setToolTip(desc.text())
        header_layout.addLayout(headings, 1)
        refresh_button = QPushButton("Refresh metadata")
        refresh_button.setProperty("accent", True)
        refresh_button.clicked.connect(self.refresh_requested.emit)
        header_actions = QHBoxLayout()
        header_actions.setSpacing(8)
        header_layout.addLayout(header_actions)
        header_layout.setAlignment(header_actions,Qt.AlignTop)
        layout.addWidget(masthead)
        episodes=QPushButton('New episode updates');episodes.clicked.connect(lambda:self._select_filter('Episodes'));header_actions.addWidget(episodes)
        releases=QPushButton('New anime releases')
        def show_releases():
            from app.ui.pages.release_news_page import open_release_news
            open_release_news(self)
        releases.clicked.connect(show_releases);header_actions.addWidget(releases);header_actions.addWidget(refresh_button)

        connection = QFrame()
        connection.setObjectName("final_panel")
        connection_row = QHBoxLayout(connection)
        connection_row.setContentsMargins(0,0,0,0)
        self.status_pill = QLabel()
        connection_row.addWidget(self.status_pill)
        headings.addWidget(connection)
        connection.setObjectName('transfer_clear')

        filters = FlowLayout()
        self._filter = "All"
        self._filter_buttons = QButtonGroup(self)
        for category in ("All", "Episodes", "Seasons", "Health", "New", "Later", "Not interested", "Muted"):
            button = QPushButton(category)
            button.setCheckable(True)
            button.setProperty("chip", True)
            button.setChecked(category == "All")
            button.setProperty('category',category)
            self._filter_buttons.addButton(button)
            button.clicked.connect(lambda checked=False, value=category: self._select_filter(value))
            filters.addWidget(button)
        sort_controls=QWidget();sort_controls.setObjectName('transfer_clear');sort_controls.setProperty('homeAlignRight',True);sort_row=QHBoxLayout(sort_controls);sort_row.setContentsMargins(0,0,0,0);sort_row.setSpacing(8)
        self.sort=QComboBox();self.sort.addItems(['Severity & date','Latest checked','Oldest checked','Title A to Z']);self.sort.setAccessibleName('Sort updates');self.sort.setToolTip('Severity uses change counts, or gap/repeated-number counts for health; dates use the last metadata check.');self.sort.currentIndexChanged.connect(self._render_cards);sort_row.addWidget(self.sort)
        self.select_button=QPushButton('Select');self.select_button.setCheckable(True);self.select_button.setAccessibleName('Select multiple update cards');self.select_button.toggled.connect(self.set_selection_mode);sort_row.addWidget(self.select_button);filters.addWidget(sort_controls)
        layout.addLayout(filters)
        self.batch=QFrame();self.batch.setObjectName('transfer_panel');bar=FlowLayout(self.batch);bar.setContentsMargins(12,8,12,8);bar.setSpacing(8)
        self.batch_count=QLabel();bar.addWidget(self.batch_count)
        for label,action in [('Later','later'),('Dismiss','dismiss'),('Watched and ignore','watched'),('Not interested','not_interested'),('Mute anime','muted')]:
            button=QPushButton(label);button.clicked.connect(lambda checked=False,a=action:self.batch_action(a));bar.addWidget(button)
        clear=QPushButton('Clear selection');clear.clicked.connect(lambda:self.set_selection_mode(False));bar.addWidget(clear);self.batch.hide();layout.addWidget(self.batch)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.list_widget = QWidget()
        self.list_widget.setObjectName('transfer_clear')
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setSpacing(8)
        self.list_layout.setAlignment(Qt.AlignTop)

        scroll.setWidget(self.list_widget)
        layout.addWidget(scroll, 1)
        self.footer=QLabel();self.footer.setObjectName('transfer_meta');layout.addWidget(self.footer)

    def refresh_home_style(self):
        from app.ui.transfer_style import qss
        from app.ui.icons import icon
        from app.ui.home_style import colors
        self.setProperty('animevaultOwnScaledStyle',True)
        style=qss('updates_page')
        if self.styleSheet()!=style:self.setStyleSheet(style)
        self.select_button.setIcon(icon('select-multiple',colors()['muted']))
    def set_selection_mode(self,enabled):
        self._selection_mode=bool(enabled)
        if not enabled:self.selected_fids.clear()
        self.select_button.blockSignals(True);self.select_button.setChecked(enabled);self.select_button.blockSignals(False)
        for _,card in self._update_card_pool.values():card.set_selection(enabled,card.franchise_id in self.selected_fids)
        self._batch_state()
    def select_card(self,fid,checked):
        if checked:self.selected_fids.add(fid)
        else:self.selected_fids.discard(fid)
        cached=self._update_card_pool.get(fid)
        if cached:cached[1].set_selection(self._selection_mode,checked)
        self._batch_state()
    def _batch_state(self):
        self.batch.setVisible(bool(self.selected_fids));self.batch_count.setText(f'{len(self.selected_fids)} anime selected')
    def batch_action(self,action):
        if self.selected_fids:self._start_update_action(sorted(self.selected_fids),action)

    def refresh(self, check_artwork=True):
        """Reload updates and per-anime saved choices from persistent storage."""
        # Update status pill
        online = cached_online()
        if online is None:
            self.status_pill.setText("AniList · Online status unchecked")
            self.status_pill.setObjectName("status_offline")
        elif not online:
            self.status_pill.setText("AniList · Offline")
            self.status_pill.setObjectName("status_offline")
        else:
            self.status_pill.setText("AniList · Online")
            self.status_pill.setObjectName("status_online")
        self.status_pill.setStyleSheet(self.status_pill.styleSheet())  # Force refresh

        franchises = db.get_all_franchises()
        import time
        from app.core.release_calendar import saved
        schedule={};now=time.time()
        for entry in saved():schedule.setdefault(entry.get('mediaId'),[]).append(entry)
        choices = db.update_dispositions()
        for record in franchises:
            history=schedule.get(record.get('anilist_id'),[]);record['_release_schedule']=history
            record['_episode_schedule_version']=tuple((e.get('episode'),e.get('airingAt'),(e.get('airingAt') or 0)<=now) for e in history)
            cached = self._update_card_pool.get(record["id"])
            record["_cover_version"] = artwork_version(record.get("cover_filename")) if check_artwork or cached is None else cached[0][-1]
            record["_update_disposition"] = choices.get(record["id"], "new")
        self._updates = [record for record in franchises if record.get("has_new_update") and record["_update_disposition"] == "new"]
        self._saved_updates = [record for record in franchises if record["_update_disposition"] != "new"]
        self._health_records = franchises
        self._health = None
        self._health_generation+=1
        self._render_cards()

    def _select_filter(self, value):
        self._filter = value
        for button in self._filter_buttons.buttons():
            button.setChecked(button.property('category') == value)
        self._render_cards()

    def show_changes(self, franchise_id, member_ids=(), title=None):
        from app.ui.update_release_dates import dated_changes
        identifiers = {franchise_id, *member_ids}
        records = [item for item in self._health_records if item['id'] in identifiers]
        changes = list(dict.fromkeys(change for item in records for change in dated_changes(item)))
        title = title or next((item['display_title'] for item in records if item['id']==franchise_id), None) or 'Anime updates'
        show_update_changes(self, title, changes, identifiers, franchise_id=franchise_id)

    def _read_health(self, franchises):
        by_franchise = defaultdict(list)
        with closing(db.get_connection()) as conn:
            for row in conn.execute(
                "SELECT * FROM seasons WHERE storage_state='ON_DISK' AND relation_type='SEASON'"
            ):
                by_franchise[row["franchise_id"]].append(dict(row))
        alerts = []
        for record in franchises:
            seasons = by_franchise[record["id"]]
            if not seasons:
                continue
            if db.uses_continuous_episodes(record):
                inventory = episode_inventory(seasons, continuous=True)
                gap_count = len(inventory["missing_episodes"])
                duplicate_count = len({episode for result in inventory["seasons"].values()
                                       for episode in result["duplicate_episodes"]})
            else:
                results = [season_health(season) for season in seasons]
                gap_count = sum(len(result["missing_episodes"]) for result in results)
                duplicate_count = sum(len(result["duplicate_episodes"]) for result in results)
            if gap_count or duplicate_count:
                alerts.append((record, gap_count, duplicate_count))
        return alerts

    def _start_update_action(self, fid, action):
        if self._apply_worker is not None:
            self._pending_actions.append((fid, action))
            for target in ([fid] if isinstance(fid, int) else fid):
                cached = self._update_card_pool.get(target)
                if cached: cached[1].setEnabled(False)
            return
        fids = [fid] if isinstance(fid, int) else fid
        for target in fids:
            cached = self._update_card_pool.get(target)
            if cached: cached[1].setEnabled(False)
        self.batch.setEnabled(False)
        self.status_pill.setText("Saving your choice...")
        self._apply_worker = UpdateActionWorker(fid, action, self)
        self._apply_worker.finished.connect(self._update_action_finished)
        self._apply_worker.start()

    def _update_action_finished(self):
        worker = self._apply_worker
        self._apply_worker = None
        self.batch.setEnabled(True)
        for fid in worker.fids:
            cached = self._update_card_pool.get(fid)
            if cached: cached[1].setEnabled(True)
        self._apply_choices(worker.records)
        self.status_pill.setText('Choice saved' if not worker.error else 'Some choices could not be saved')
        if worker.error:
            QMessageBox.warning(self, "Could not save update choice", worker.error)
        self.set_selection_mode(False)
        if worker.records: self.choices_changed.emit(worker.records)
        self.action_finished.emit(worker.fid)
        worker.deleteLater()
        if self._pending_actions:
            QTimer.singleShot(0, self._next_update_action)

    def _next_update_action(self):
        if self._pending_actions and self._apply_worker is None:
            fid, action = self._pending_actions.pop(0)
            self._start_update_action(fid, action)

    def _apply_choices(self, records):
        """Patch committed records without disturbing other cards or scroll position."""
        for fid, record in records.items():
            previous = next((r for r in self._health_records if r['id'] == fid), {})
            record['_cover_version'] = previous.get('_cover_version')
            for key in ('_release_schedule','_episode_schedule_version'):
                if key in previous:record[key]=previous[key]
        self._health_records = [records.get(r['id'], r) for r in self._health_records]
        self._updates = [r for r in self._health_records if r.get('has_new_update') and r['_update_disposition'] == 'new']
        self._saved_updates = [r for r in self._health_records if r['_update_disposition'] != 'new']
        # A saved choice moves out of the current category. Build its destination
        # card lazily when that category is opened, keeping other widgets intact.
        removed_visible = False
        for fid in records:
            cached = self._update_card_pool.pop(fid, None)
            if cached:
                removed_visible |= self.list_layout.indexOf(cached[1]) >= 0
                self.list_layout.removeWidget(cached[1]);cached[1].hide();cached[1].deleteLater()
        shown = sum(isinstance(self.list_layout.itemAt(i).widget(), UpdateCard) for i in range(self.list_layout.count()))
        if removed_visible and not shown and self._filter != 'Health':
            empty = QLabel('No updates in this category.');empty.setObjectName('subheading');empty.setAlignment(Qt.AlignCenter);empty.setMinimumHeight(120)
            self.list_layout.insertWidget(0, empty)
        self._update_counts(shown)

    def _remove_update(self, fid):
        self.refresh()
        self.data_changed.emit()

    def _render_cards(self,*_):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                if not isinstance(item.widget(), UpdateCard) and not item.widget().property('healthCard'):
                    item.widget().deleteLater()

        known = {record["id"] for record in self._updates + self._saved_updates}
        self.selected_fids.intersection_update(known);self._batch_state()
        for fid in list(self._update_card_pool):
            if fid not in known:
                self._update_card_pool.pop(fid)[1].deleteLater()
        health_ids={record['id'] for record in self._health_records}
        for fid in list(self._health_card_pool):
            if fid not in health_ids:self._health_card_pool.pop(fid)[1].deleteLater()
        shown = 0
        if self._filter != "Health":
            saved_filter = {"Later": "later", "Not interested": "not_interested", "Muted": "muted"}.get(self._filter)
            records = [record for record in self._saved_updates if record["_update_disposition"] == saved_filter] if saved_filter else self._updates
            records=self._sorted(records)
            for record in records:
                changes = (record.get("update_details") or "").split(" | ")
                is_episode = is_episode_change
                if self._filter == "Episodes" and not any(map(is_episode, changes)):
                    continue
                if self._filter == "Seasons" and not any(change.strip() and not is_episode(change) for change in changes):
                    continue
                fingerprint = tuple(record.get(key) for key in ("display_title", "cover_filename", "update_details", "_update_disposition", "metadata_json", "_episode_schedule_version", "_cover_version"))
                cached = self._update_card_pool.get(record["id"])
                if cached is None or cached[0] != fingerprint:
                    if cached is not None:
                        cached[1].deleteLater()
                    card = UpdateCard(record, self.list_widget, async_actions=True)
                    card.action_requested.connect(self._start_update_action)
                    card.clicked.connect(lambda fid, item=card:item._show_changes())
                    card.dismissed.connect(lambda fid=record["id"]: self._remove_update(fid))
                    card.selection_changed.connect(self.select_card)
                    self._update_card_pool[record["id"]] = (fingerprint, card)
                else:
                    card = cached[1]
                self.list_layout.addWidget(card)
                card.set_selection(self._selection_mode,record['id'] in self.selected_fids)
                card.show()
                shown += 1
        if self._filter == "Health":
            if self._health is None:
                self._request_health()
            health=self._health or []
            if self.sort.currentIndex()==0:health=sorted(health,key=lambda item:(item[1]+item[2],item[0].get('last_checked_at') or ''),reverse=True)
            else:
                positions={r['id']:i for i,r in enumerate(self._sorted([item[0] for item in health]))};health=sorted(health,key=lambda item:positions[item[0]['id']])
            for record, gaps, duplicates in health:
                fingerprint=(record.get('display_title'),record.get('cover_filename'),record.get('_cover_version'),gaps,duplicates)
                cached=self._health_card_pool.get(record['id'])
                if cached and cached[0]==fingerprint:
                    self.list_layout.addWidget(cached[1]);cached[1].show();shown+=1;continue
                if cached:cached[1].deleteLater()
                card = QFrame()
                card.setProperty('healthCard',True)
                card.setObjectName("final_panel")
                row = QHBoxLayout(card)
                row.setContentsMargins(16, 12, 16, 12)
                poster = QLabel((record.get("display_title") or "?")[0].upper())
                poster.setAlignment(Qt.AlignCenter)
                poster.setFixedSize(44, 64)
                poster.setStyleSheet("background: #1e2230; border-radius: 8px; font-size: 22px; font-weight: 700;")
                poster.setObjectName('update_poster');poster.setStyleSheet('')
                cover = record.get("cover_filename")
                if cover and refresh_image_exists(COVERS_DIR / cover):
                    poster.setPixmap(refresh_pixmap(COVERS_DIR / cover).scaled(
                        44, 64, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                row.addWidget(poster)
                details = QVBoxLayout()
                heading = QLabel(record["display_title"])
                heading.setObjectName('update_title')
                heading.setTextFormat(Qt.PlainText)
                heading.setWordWrap(True)
                details.addWidget(heading)
                summary = QLabel(f"Episode gaps: {gaps}  /  Repeated episode numbers: {duplicates}")
                summary.setObjectName("subheading")
                details.addWidget(summary)
                if duplicates:
                    note = QLabel("May be revised episodes or different encodes. Use Organizer to check exact duplicates.")
                    note.setWordWrap(True)
                    note.setObjectName("subheading")
                    details.addWidget(note)
                row.addLayout(details, 1)
                review = QPushButton("Review files")
                review.setProperty("accent", True)
                review.clicked.connect(lambda checked=False, fid=record["id"]: self.card_clicked.emit(fid))
                row.addWidget(review)
                self.list_layout.addWidget(card)
                self._health_card_pool[record['id']]=(fingerprint,card)
                shown += 1
        if not shown:
            empty = QLabel("Checking local library health…" if self._filter=='Health' and self._health is None else "No updates in this category.")
            empty.setObjectName("subheading")
            empty.setAlignment(Qt.AlignCenter)
            empty.setMinimumHeight(120)
            self.list_layout.addWidget(empty)
        self.list_layout.addStretch()
        self._update_counts(shown)

    def _update_counts(self, shown):
        self.select_button.setEnabled(self._filter!='Health')
        counts={'All':len(self._updates),'New':len(self._updates),'Episodes':sum(any(is_episode_change(p) for p in (r.get('update_details') or '').split(' | ')) for r in self._updates),'Seasons':sum(any(p.strip() and not (is_episode_change(p)) for p in (r.get('update_details') or '').split(' | ')) for r in self._updates),'Health':len(self._health) if self._health is not None else None}
        for label,state in [('Later','later'),('Not interested','not_interested'),('Muted','muted')]:counts[label]=sum(r['_update_disposition']==state for r in self._saved_updates)
        for button in self._filter_buttons.buttons():
            name=button.property('category');count=counts[name];button.setText(name+(f'  {count}' if count is not None else ''))
        self.footer.setText(f'Showing {shown} anime · '+('Health cards are inspected individually.' if self._filter=='Health' else 'Saved choices persist until restored.'))

    def _sorted(self,records):
        mode=self.sort.currentIndex()
        if mode==3:return sorted(records,key=lambda r:(r.get('display_title') or '').casefold())
        if mode in (1,2):return sorted(records,key=lambda r:(r.get('last_checked_at') or '',r.get('display_title') or ''),reverse=mode==1)
        return sorted(records,key=lambda r:(len([p for p in (r.get('update_details') or '').split(' | ') if p.strip()]),r.get('last_checked_at') or ''),reverse=True)

    def _request_health(self):
        if self._health_worker is not None:return
        from app.ui.io_task import IOTask,track
        from PyQt5 import sip
        generation=self._health_generation;records=list(self._health_records);worker=IOTask(lambda:self._read_health(records));self._health_worker=worker;track(worker)
        def ready(result):
            if not sip.isdeleted(self) and generation==self._health_generation:self._health=result
        def finished():
            if not sip.isdeleted(self):
                self._health_worker=None
                self._render_cards()
            worker.deleteLater()
        def failed(message):
            if not sip.isdeleted(self) and generation==self._health_generation:self._health=[];self.status_pill.setText(message)
        worker.succeeded.connect(ready);worker.failed.connect(failed);worker.finished.connect(finished);worker.start()
