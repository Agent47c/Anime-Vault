"""In-app source results with conservative coverage and an explicit review."""
from PyQt5.QtCore import Qt,QAbstractTableModel,QModelIndex,QEvent,QTimer,pyqtSignal
from PyQt5.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QLineEdit,QComboBox,QPushButton,QTableView,QHeaderView,QAbstractItemView,QProgressBar,QCheckBox,QSpinBox,QSizePolicy,QFrame,QScrollArea,QWidget,QListView
from app import db
from app.core import download_discovery as discovery,downloads,download_queries
from app.ui.io_task import IOTask,track,start
from app.ui.navigation import navigate
from app.ui.dialogs.drawer import DrawerDialog
from app.ui.components.workflow import chrome,button,field
from app.ui.magnet_capture import review_text as text


class ReleaseModel(QAbstractTableModel):
    headers=['Select / release','Episodes','Quality / group','Size','Seeders','Source','Availability']
    def __init__(self,parent=None):super().__init__(parent);self.rows=[];self.selected=set()
    def rowCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.rows)
    def columnCount(self,parent=QModelIndex()):return len(self.headers)
    def headerData(self,section,orientation,role=Qt.DisplayRole):
        if orientation==Qt.Horizontal and role==Qt.DisplayRole:return self.headers[section]
    def data(self,index,role=Qt.DisplayRole):
        if not index.isValid():return None
        entry=self.rows[index.row()]
        if role==Qt.CheckStateRole and index.column()==0:return Qt.Checked if entry['identity'] in self.selected else Qt.Unchecked
        if role==Qt.ToolTipRole:return entry['title']+'\n'+entry.get('reason','')+'\nA source result is not proof that peers can currently deliver it.'
        if role!=Qt.DisplayRole:return None
        eps=entry.get('episode_keys') or []
        coverage=discovery.coverage_label(eps) if eps else 'Confirm match'
        return [entry['title'],coverage,(entry.get('quality') or '—')+' / '+(entry.get('group') or '—'),entry.get('size') or '—',entry.get('seeders') if entry.get('seeders') is not None else 'Unknown',entry['source'],entry['status']][index.column()]
    def flags(self,index):
        flags=Qt.ItemIsEnabled|Qt.ItemIsSelectable
        if index.isValid() and self.rows[index.row()].get('_submitted'):return flags
        return flags|Qt.ItemIsUserCheckable if index.column()==0 else flags
    def setData(self,index,value,role=Qt.EditRole):
        if role!=Qt.CheckStateRole or index.column()!=0:return False
        if self.rows[index.row()].get('_submitted'):return False
        identity=self.rows[index.row()]['identity']
        if value==Qt.Checked:self.selected.add(identity)
        else:self.selected.discard(identity)
        self.dataChanged.emit(index,index,[Qt.CheckStateRole]);return True


class AvailabilityModel(QAbstractTableModel):
    def __init__(self,parent=None):super().__init__(parent);self.rows=[]
    def rowCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.rows)
    def columnCount(self,parent=QModelIndex()):return 2
    def headerData(self,section,orientation,role=Qt.DisplayRole):
        if role==Qt.DisplayRole and orientation==Qt.Horizontal:return ['Episode','Availability'][section]
    def data(self,index,role=Qt.DisplayRole):
        if index.isValid():
            row=self.rows[index.row()]
            if role in (Qt.ToolTipRole,Qt.AccessibleTextRole):return discovery.episode_label(row['episode'])+' · '+row['status']
            if role==Qt.DisplayRole:return discovery.episode_label(row['episode']) if index.column()==0 else row['status']


class ConfirmCoverage(QDialog):
    centered_workflow=True
    def __init__(self,parent,entry,context,callback):
        super().__init__(parent);self.entry=entry;self.entries=entry if isinstance(entry,list) else [entry];self.context=context;self.callback=callback
        self.setWindowTitle('Confirm season / episodes');self.setObjectName('release_search_page')
        from app.ui.release_search_style import qss
        self.setStyleSheet(qss());self.setMinimumWidth(480)
        body=QVBoxLayout(self);body.setContentsMargins(24,24,24,24);body.setSpacing(14)
        body.addWidget(text(f"Confirm {len(self.entries)} selected download(s)",'workflow_row_title'))
        body.addWidget(text('Anime: '+context['title']))
        from app.ui.manga_pages import active
        manga=active()
        if manga:
            from app.ui.manga_additional import qss as manga_qss
            self.setObjectName('confirm_selected');self.setStyleSheet(manga_qss('confirm_selected'));self.workflow_width=820
            body.itemAt(0).widget().setObjectName('workflow_title')
        self.kind=QComboBox()
        for label,key in [('Episode','EPISODE'),('Movie','MOVIE'),('Special / OVA','SPECIAL')]:self.kind.addItem(label,key)
        kind_index=self.kind.findData(context.get('kind'))
        if kind_index>=0:self.kind.setCurrentIndex(kind_index)
        field(body,'Release type',self.kind)
        self.continuous=QCheckBox('Continuous episode numbering')
        self.continuous.setChecked(False)
        body.addWidget(self.continuous)
        body.addWidget(text('Choose the season folder and episode numbers for each file. Original file names stay unchanged.'))
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);scroll.setMinimumHeight(120);scroll.setMaximumHeight(320)
        content=QWidget();content.setObjectName('transfer_clear');rows=QVBoxLayout(content);scroll.setWidget(content);body.addWidget(scroll)
        if manga:scroll.setMaximumHeight(520)
        self.episode_inputs=[];self.season_inputs=[];self.assignment_labels=[]
        for release in self.entries:
            entry_rows=rows
            if manga:
                frame=QFrame();frame.setObjectName('workflow_card');entry_rows=QVBoxLayout(frame);entry_rows.setContentsMargins(20,18,20,18);entry_rows.setSpacing(12);rows.addWidget(frame)
            title=text(release['title'],'workflow_row_title');title.setToolTip('');entry_rows.addWidget(title)
            season=QSpinBox();season.setRange(0,100);season.setSpecialValueText('Episodes');season.setValue(release.get('season') if release.get('season') is not None else context.get('season') or 1);season.setMinimumWidth(140)
            season.setButtonSymbols(QSpinBox.NoButtons)
            season.setAccessibleName('Destination season for '+release['title'])
            fields=QHBoxLayout();season_field=QVBoxLayout();episode_field=QVBoxLayout();fields.addLayout(season_field);fields.addLayout(episode_field,1);entry_rows.addLayout(fields)
            field(season_field,'Season / folder',season);self.season_inputs.append(season)
            numbers=release.get('episodes') or []
            if len(self.entries)==1 and context.get('target_episode') and numbers==[context.get('source_episode')]:numbers=[context['target_episode']]
            edit=QLineEdit(', '.join(str(n) for n in numbers));edit.setPlaceholderText('e.g. 6 or 6, 7 or 1-12');edit.setAccessibleName('Episode numbers for '+release['title'])
            field(episode_field,'Episode number(s)',edit);self.episode_inputs.append(edit)
            hint=text('');hint.setToolTip('');entry_rows.addWidget(hint);self.assignment_labels.append(hint)
            season.valueChanged.connect(self._update_assignments);edit.textChanged.connect(self._update_assignments)
        self.season=self.season_inputs[0]
        self.continuous.toggled.connect(self._update_assignments);self._update_assignments()
        if manga:rows.addStretch()
        self.remember=QCheckBox('Remember these alternate titles for this anime and season');body.addWidget(self.remember)
        self.move_completed=QCheckBox('Move to the selected library season when the download completes');body.addWidget(self.move_completed)
        self.move_completed.setChecked(all(release.get('move_when_completed',False) for release in self.entries))
        self.move_completed.setToolTip('Off by default. Files stay in Downloads until you review a move in Organizer.')
        self.validation=text('');body.addWidget(self.validation)
        actions=QHBoxLayout();cancel=QPushButton('Cancel');cancel.clicked.connect(self.reject);actions.addWidget(cancel);actions.addStretch();self.apply_button=QPushButton('Confirm match');self.apply_button.setProperty('accent',True);self.apply_button.clicked.connect(self.apply);actions.addWidget(self.apply_button);body.addLayout(actions)
        for label in self.findChildren(QLabel):label.setStyleSheet('background:transparent;border:none;')
        for control in (cancel,self.apply_button):control.setCursor(Qt.PointingHandCursor);control.setMinimumHeight(44)
    def _update_assignments(self):
        for season,edit,label in zip(self.season_inputs,self.episode_inputs,self.assignment_labels):
            folder=f'Season {season.value():02}' if season.value() else 'Episodes'
            mode='continuous numbering' if self.continuous.isChecked() else f'season {season.value()} numbering'
            label.setText(f"Folder: {folder} · Episode(s): {edit.text() or 'choose numbers'} · {mode}. Move completed files to the anime’s library folder using the reviewed move action.")
    def apply(self):
        import re
        from app.core.match_evidence import base_title
        confirmed=[];seen=set()
        for release,edit,season_control in zip(self.entries,self.episode_inputs,self.season_inputs):
            season=season_control.value()
            continuous=self.continuous.isChecked() and self.kind.currentData()=='EPISODE'
            if not continuous and season==0 and self.kind.currentData()=='EPISODE':
                self.validation.setText('Choose a season of 1 or higher for each file, or enable continuous episode numbering.');return
            numbers=set()
            for token in edit.text().split(','):
                match=re.fullmatch(r'\s*(\d{1,4})(?:\s*[-–]\s*(\d{1,4}))?\s*',token)
                if not match:self.validation.setText('Enter episode numbers for each file, for example 6 or 6, 7.');return
                first=int(match[1]);last=int(match[2] or match[1])
                if not 1<=first<=last<=9999:self.validation.setText('Episode numbers must be between 1 and 9999, with ranges in order.');return
                numbers.update(range(first,last+1))
            value=dict(release)
            # An edited assignment must earn fresh replacement approval. Never
            # carry permission to recycle episode 7 over to a new episode 8.
            for decision in ('duplicate_action','replacement_files','approved_destination'):value.pop(decision,None)
            keys=[discovery.episode_key(continuous,season,n,self.kind.currentData()) for n in sorted(numbers)]
            if seen.intersection(keys):self.validation.setText('Two files are assigned to the same episode. Review their seasons and episode numbers.');return
            seen.update(keys)
            state='In Library' if set(keys)<=set(self.context['local']) else 'Downloading or Queued' if set(keys)<=set(self.context['local'])|set(self.context['pending']) else 'Missing — Release Found'
            value.update(source_episodes=release.get('source_episodes',release.get('episodes') or []),episodes=sorted(numbers),episode_keys=keys,season=season,continuous=continuous,match_confirmed=True,status=state,reason='Match confirmed by user',assignment_version=1,local_season_id=self.context.get('local_season_id'),move_when_completed=self.move_completed.isChecked())
            local=db.get_season(value['local_season_id']) if value['local_season_id'] else None
            if not local or local.get('season_number')!=season:
                candidates=[s for s in db.get_series_seasons(self.context['fid']) if s.get('season_number')==season and s.get('relation_type')==('SEASON' if self.kind.currentData()=='EPISODE' else self.kind.currentData()) and not (s.get('local_scan_key') or '').startswith('download:')]
                metadata=[s for s in candidates if s.get('anilist_id')]
                candidates=metadata or candidates
                value['local_season_id']=candidates[0]['id'] if len(candidates)==1 else None
            from app.ui.components.message_boxes import AppMessageBox as QMessageBox
            from app.core import download_assignment
            try:current=discovery.library_context(self.context['fid'],season,continuous=continuous)
            except ValueError as error:self.validation.setText(str(error));return
            if set(keys)&set(current.get('local') or {}):
                box=QMessageBox(QMessageBox.Question,'Episode already downloaded',discovery.coverage_label(keys)+' is already in your library. What would you like to do?',parent=self)
                replace=box.addButton('Replace old copy',QMessageBox.DestructiveRole)
                skip=box.addButton('Skip this download',QMessageBox.RejectRole)
                another=box.addButton('Download another copy',QMessageBox.AcceptRole)
                box.setInformativeText('Replace keeps the old file during downloading. It is sent to the Recycle Bin only after the new file is verified and moved into the library. Another copy keeps both files.')
                box.setDefaultButton(skip);box.exec_()
                if box.clickedButton() is skip:seen.difference_update(keys);continue
                if box.clickedButton() not in (replace,another):return
                value['duplicate_action']='replace' if box.clickedButton() is replace else 'redownload'
                if value['duplicate_action']=='replace':
                    try:value['replacement_files']=download_assignment.duplicate_files(self.context['fid'],keys)
                    except (ValueError,OSError) as error:self.validation.setText(str(error));return
            if value['move_when_completed']:
                try:target=download_assignment.destination(self.context['fid'],season)
                except (ValueError,OSError) as error:self.validation.setText(str(error));return
                if target['create'] and QMessageBox.question(self,'Create season folder?',f'This season folder does not exist. Create it when moving the completed download?\n\n{target["folder"]}',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
                value['approved_destination']=target
            confirmed.append(value)
        if not confirmed:self.validation.setText('All selected downloads were skipped. No files were changed.');return
        if self.remember.isChecked():
            try:
                for release in confirmed:discovery.remember_confirmed_alias(self.context['fid'],release)
            except ValueError as error:self.validation.setText(str(error));return
        self.callback(confirmed if isinstance(self.entry,list) else confirmed[0]);self.accept()


class DownloadReview(DrawerDialog):
    downloads_added=pyqtSignal(object)
    def __init__(self,parent,fid,entries,context):
        super().__init__(parent);self.fid=fid;self.entries=entries;self.context=context;self._payload_labels=[];self._submitted=False
        covered={key for entry in entries for key in entry['episode_keys']}
        missing=set(context['missing'])-covered
        body,self.apply_button=chrome(self,'Review downloads','Check episode coverage and destinations before adding transfers.','取込',f'Add {len(entries)} downloads',self.apply)
        from app.ui.manga_pages import active
        from app.ui.components.paper_card import PaperCard
        manga=active()
        def section():
            if not manga:return body
            frame=PaperCard();frame.setObjectName('review_payload');box=QVBoxLayout(frame);box.setContentsMargins(26,24,26,24);box.setSpacing(12);body.addWidget(frame);return box
        for entry in entries:
            box=section()
            if manga:
                kicker=text('DETECTED RELEASE PAYLOAD');kicker.setStyleSheet('background:transparent;color:#c4005f;border:none;font-size:11px;');box.addWidget(kicker)
            title=text(entry['title'],'workflow_row_title');title.setToolTip('');coverage=text('Covers: '+discovery.coverage_label(entry['episode_keys']));box.addWidget(title);box.addWidget(coverage)
            details=' · '.join(str(entry[key]) for key in ('quality','group','size','source') if entry.get(key))
            if manga and details:box.addWidget(text(details))
            overlap=set(entry['episode_keys'])&set(context['local'])
            warning=text(f'Batch includes {len(overlap)} episodes already in the library. Use file selection to exclude them.');warning.setVisible(bool(overlap));box.addWidget(warning);self._payload_labels.append((title,coverage,warning))
        box=section()
        if manga:box.addWidget(text('COVERAGE & DESTINATION','workflow_row_title'))
        self._remaining=text('Still missing after these releases: '+(discovery.coverage_label(sorted(missing)) if missing else 'None within verified boundaries.'));box.addWidget(self._remaining)
        box.addWidget(text('Destination: '+downloads.settings()['destination']))
        box.addWidget(text('Downloads use isolated subfolders. Move completed files into the main library using the reviewed move action.'))
        box.addWidget(text('Seeder counts describe the source listing, not guaranteed download availability.'))
        adjust=button('Confirm season / episodes',self.adjust_match);body.addWidget(adjust,0,Qt.AlignLeft)
        self.checked=QCheckBox('I reviewed the selected releases and episode coverage');body.addWidget(self.checked)
        self.apply_button.setEnabled(False);self.checked.toggled.connect(self.apply_button.setEnabled)
        self.message=text('');body.addWidget(self.message)
        body.addStretch()
        self.refresh_home_style()
    def adjust_match(self):
        def saved(entries):
            self.entries=entries
            for (title,coverage,warning),entry in zip(self._payload_labels,entries):
                title.setText(entry['title']);coverage.setText('Covers: '+discovery.coverage_label(entry['episode_keys']))
                overlap=set(entry['episode_keys'])&set(self.context['local']);warning.setText(f'Batch includes {len(overlap)} episodes already in the library. Use file selection to exclude them.');warning.setVisible(bool(overlap))
            missing=set(self.context['missing'])-{key for entry in entries for key in entry['episode_keys']}
            self._remaining.setText('Still missing after these releases: '+(discovery.coverage_label(sorted(missing)) if missing else 'None within verified boundaries.'))
            self.checked.setChecked(False)
        navigate(ConfirmCoverage(self,self.entries,self.context,saved))
    def refresh_home_style(self):
        from app.ui.manga_pages import active
        from app.ui.manga_workflows import qss
        manga=active();self.full_page=manga
        self.setObjectName('download_review' if manga else 'workflow_drawer');self.setProperty('animevaultOwnScaledStyle',True)
        self.setStyleSheet(qss('download_review') if manga else '')
        from app.ui.manga_workflows import finish
        finish(self)
    def apply(self):
        if self._submitted:return
        if not self.checked.isChecked():self.message.setText('Review the selected releases and coverage first.');return
        def done(paths):
            self._submitted=True;self.apply_button.setEnabled(False)
            host=self.parentWidget()
            while host is not None and not hasattr(host,'_on_nav_clicked'):host=host.parentWidget()
            self.downloads_added.emit(self.entries)
            self.accept()
            if host is not None:host._on_nav_clicked(5)
            # Downloads refreshes its queue asynchronously on show. Its existing
            # monitor owns polling; never block this completion on a fresh poll.
        start(self,lambda:discovery.submit(self.fid,self.entries),done)


class ReleaseSearchPage(QDialog):
    dispose_on_leave=True
    full_page=True
    def __init__(self,parent,fid,assignment_context=None):
        super().__init__(parent);self.fid=fid;self._worker=None;self._generation=0;self.results=[];self.context=None;self.assignment_context=assignment_context or {};self._memory_ready=False
        self.setObjectName('release_search_page')
        self.setWindowTitle('Find Download Files')
        root=QVBoxLayout(self);root.setContentsMargins(24,16,24,16);root.setSpacing(16);box=root
        from app.ui.home_style import load_fonts,px
        from app.ui.components.flow_layout import FlowLayout
        from app.ui.release_search_style import ReleaseDelegate,AvailabilityDelegate,SearchCheckBox
        load_fonts();self.setAttribute(Qt.WA_StyledBackground,True)
        heading=FlowLayout();title=QLabel('Find Download Files');title.setObjectName('download_heading');heading.addWidget(title)
        tag=QLabel('RELEASE SEARCH');tag.setObjectName('search_tag');heading.addWidget(tag);box.addLayout(heading)
        self.subtitle=text((db.get_series(fid) or {}).get('display_title','Anime'));box.addWidget(self.subtitle)
        self.subtitle.setObjectName('transfer_meta')
        scroll=QScrollArea();self.scroll=scroll;scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content=QWidget();content.setObjectName('transfer_clear');scroll.setWidget(content);box.addWidget(scroll,1)
        box=QVBoxLayout(content);box.setContentsMargins(0,0,0,0);box.setSpacing(px(18))
        def panel():
            frame=QFrame();frame.setObjectName('search_panel');layout=QVBoxLayout(frame);layout.setContentsMargins(px(20),px(20),px(20),px(20));layout.setSpacing(px(14));return frame,layout
        def label(value):
            result=QLabel(value);result.setObjectName('search_label');return result
        context_panel,form=panel();self.context_panel=context_panel;box.addWidget(context_panel)
        context_labels=QHBoxLayout();context_labels.addWidget(label('ANIME SERIES & SEASON CONTEXT'),2);context_labels.addWidget(label('SOURCE PROVIDER'),1);form.addLayout(context_labels)
        options=QHBoxLayout();self.season=QComboBox();self.season.addItem('Continuing / choose season',None)
        series=db.get_series(fid) or {};continuous=db.uses_continuous_episodes(series)
        self.query_series=series;self.query_config=downloads.settings()
        seen=set()
        for item in db.get_series_seasons(fid):
            number=item.get('season_number')
            if item.get('relation_type')=='SEASON' and number and number not in seen:
                seen.add(number);self.season.addItem(f'Season {number} · {item["title_display"]}',number)
        if len(seen)==1 and not continuous:self.season.setCurrentIndex(1)
        self.source=QComboBox()
        self.sources=discovery.sources()
        for source in self.sources:self.source.addItem(source['name'],source)
        is_adult_series = bool(series.get('is_adult'))
        if is_adult_series:
            selected = next((i for i, s in enumerate(self.sources) if 'sukebei.nyaa.si' in s.get('url', '')), 0)
        else:
            selected = next((i for i, s in enumerate(self.sources) if s['url'] == downloads.settings()['source']), 0)
        self.source.setCurrentIndex(selected)
        options.addWidget(self.season,2);options.addWidget(self.source,1);form.addLayout(options)
        form.addWidget(label('SEARCH TITLE MAPPING'))
        title_row=QHBoxLayout();self.title_choice=QComboBox()
        self.title_choice.setMinimumContentsLength(20);self.title_choice.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed)
        self.title_choice.setAccessibleName('Search title language')
        title_row.addWidget(self.title_choice,1)
        use_title=QPushButton('Use title');use_title.clicked.connect(self.use_title);title_row.addWidget(use_title)
        custom=QPushButton('Use Custom One');custom.setToolTip('Save the current search text for this anime and season, and reuse it next time.');custom.clicked.connect(self.save_custom_query);title_row.addWidget(custom);form.addLayout(title_row)
        self.alternatives=SearchCheckBox('Try other saved titles if this query has no results');form.addWidget(self.alternatives)
        search=QHBoxLayout();self.query=QLineEdit();self.query.setPlaceholderText('Edit the exact words to search on the selected website')
        self.query.setClearButtonEnabled(True);self._generated_query=''
        from app.ui.icons import icon
        from app.ui.home_style import colors
        self.query.addAction(icon('search',colors()['muted']),QLineEdit.LeadingPosition)
        search.addWidget(self.query,1);self.search_button=QPushButton('Search releases');self.search_button.setMinimumHeight(44);self.search_button.clicked.connect(self.search);search.addWidget(self.search_button)
        self.search_button.setProperty('accent',True)
        stop=QPushButton('Cancel search');stop.clicked.connect(self.cancel_search);search.addWidget(stop);form.addLayout(search)
        self.source_url=QLineEdit();self.source_url.setReadOnly(True);self.source_url.setAccessibleName('Source search URL')
        self.source_url.setToolTip('The exact URL sent to Chrome. You can copy it or use Open source in Chrome.')
        self.source_url.setObjectName('search_url')
        url_row=QHBoxLayout();url_row.addWidget(label('SEARCH URL'));url_row.addWidget(self.source_url,1);form.addLayout(url_row)
        self.loading=QProgressBar();self.loading.setRange(0,0);self.loading.setFixedHeight(4);self.loading.hide();form.addWidget(self.loading)
        self.status=text('Search through your connected Chrome extension. No download starts until you review and confirm.');self.status.setObjectName('search_status');form.addWidget(self.status)
        filters=QHBoxLayout();self.filter=QComboBox();self.filter.addItems(['All results','Missing releases','Match uncertain','In library / queued'])
        self.quality=QLineEdit();self.quality.setPlaceholderText('Filter quality/group/title')
        self.sort=QComboBox();self.sort.addItems(['Most seeders','Title A–Z','Episode number'])
        for control in (self.season,self.source,self.filter,self.sort):
            control.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon);control.setMinimumContentsLength(16)
            control.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed)
        for control in (self.filter,self.quality,self.sort):filters.addWidget(control,1)
        self.show_episodes=show_episodes=SearchCheckBox('Show episode availability');show_episodes.setCursor(Qt.PointingHandCursor);filters.addWidget(show_episodes)
        box.addLayout(filters)
        availability_panel,availability_layout=panel();self.availability_panel=availability_panel;box.addWidget(availability_panel)
        self.coverage=text('Local episode coverage will appear after searching.');self.coverage.setObjectName('transfer_meta');availability_layout.addWidget(self.coverage)
        self.availability_model=AvailabilityModel(self);self.availability=QListView();self.availability.setModel(self.availability_model);self.availability.setViewMode(QListView.IconMode);self.availability.setResizeMode(QListView.Adjust);self.availability.setMovement(QListView.Static);self.availability.setWrapping(True);self.availability.setUniformItemSizes(True);self.availability.setItemDelegate(AvailabilityDelegate(self.availability));self.availability.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.availability.setMinimumHeight(px(110));self.availability.setMaximumHeight(px(220));self.availability.hide()
        show_episodes.toggled.connect(self.availability.setVisible);availability_layout.addWidget(self.availability)
        self.model=ReleaseModel(self);self.table=QTableView();self.table.setModel(self.model);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setTextElideMode(Qt.ElideRight);self.table.setWordWrap(False);self.table.verticalHeader().hide();self.table.verticalHeader().setDefaultSectionSize(56);self.table.setShowGrid(False)
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Interactive)
        self.table.setItemDelegate(ReleaseDelegate(self.table));self.table.setMouseTracking(True);self.table.setMinimumHeight(px(290));self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setMinimumSectionSize(px(90));self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        self.table.verticalHeader().setDefaultSectionSize(px(72))
        for column,width in enumerate((380,110,150,80,75,80,190)):
            if column:self.table.horizontalHeader().setSectionResizeMode(column,QHeaderView.Interactive);self.table.setColumnWidth(column,px(width))
        self.table.viewport().installEventFilter(self)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        box.addWidget(self.table,1)
        self.action_panel=QFrame();self.action_panel.setObjectName('search_actions');action_layout=QVBoxLayout(self.action_panel);action_layout.setContentsMargins(12,12,12,12);root.addWidget(self.action_panel)
        dock=QHBoxLayout();dock.setSpacing(16);action_layout.addLayout(dock)
        secondary=QWidget();secondary.setObjectName('transfer_clear');actions=FlowLayout(secondary);dock.addWidget(secondary,1)
        primary=QWidget();self.primary_actions=primary;primary.setObjectName('transfer_clear');primary_actions=FlowLayout(primary);dock.addWidget(primary)
        self.action_buttons={}
        for index,(label,callback) in enumerate([('Confirm season / episodes',self.confirm_match),('Paste magnet / torrent',self.manual),('Open source in Chrome',self.open_browser),('Review selected downloads',self.review)]):
            control=QPushButton(label.replace('&','&&'));control.setMinimumHeight(44);control.clicked.connect(callback)
            (primary_actions if label=='Review selected downloads' else actions).addWidget(control)
            self.action_buttons[label]=control
            if label=='Review selected downloads':control.setProperty('accent',True);self.review_button=control
        self.filter.currentIndexChanged.connect(self.render);self.quality.textChanged.connect(self.render);self.sort.currentIndexChanged.connect(self.render)
        self.query.returnPressed.connect(self.search)
        self.query.textChanged.connect(self.invalidate)
        self.season.currentIndexChanged.connect(self.invalidate);self.source.currentIndexChanged.connect(self.invalidate)
        self.query.textChanged.connect(self.update_url);self.source.currentIndexChanged.connect(self.update_url)
        self.title_choice.currentIndexChanged.connect(self.use_title)
        self.season.currentIndexChanged.connect(self.refresh_titles)
        self.alternatives.toggled.connect(self.invalidate)
        self.refresh_titles()
        self.model.dataChanged.connect(self.update_selection_count)
        self.update_selection_count()
        for control in self.findChildren(QPushButton):control.setCursor(Qt.PointingHandCursor);control.setAccessibleName(control.text().replace('&&','&'))
        self.table.setAccessibleName('Available torrent releases; use checkboxes to select downloads')
        self.availability.setAccessibleName('Episode availability cards')
        self.refresh_home_style()
        memory=download_queries.search_memory(self.fid)
        if memory:
            index=self.season.findData(memory.get('season'))
            if index<0 and memory.get('season') is not None:self.season.addItem('Season '+str(memory['season']),memory['season']);index=self.season.count()-1
            if index>=0:self.season.setCurrentIndex(index)
            index=next((i for i in range(self.source.count()) if self.source.itemData(i).get('url')==memory.get('source')),-1)
            if index>=0:self.source.setCurrentIndex(index)
            index=self.title_choice.findData(memory.get('title'))
            if index>=0:self.title_choice.blockSignals(True);self.title_choice.setCurrentIndex(index);self.title_choice.blockSignals(False)
            self.query.setText(memory.get('query',''))
        if self.assignment_context.get('season') is not None:
            index=self.season.findData(self.assignment_context['season'])
            if index<0:self.season.addItem('Season '+str(self.assignment_context['season']),self.assignment_context['season']);index=self.season.count()-1
            if index>=0:self.season.setCurrentIndex(index)
            self.season.setEnabled(True)
        if self.assignment_context.get('query'):self.query.setText(self.assignment_context['query'])
        elif memory:self.query.setText(memory.get('query',''))
        self._memory_ready=True;self._memory_dirty=False;self._memory_timer=QTimer(self);self._memory_timer.setSingleShot(True);self._memory_timer.setInterval(300);self._memory_timer.timeout.connect(self.save_search_memory)
        self.query.textChanged.connect(self.schedule_search_memory);self.source.currentIndexChanged.connect(self.schedule_search_memory);self.season.currentIndexChanged.connect(self.schedule_search_memory)

    def schedule_search_memory(self,*_):
        if self._memory_ready:self._memory_dirty=True;self._memory_timer.start()

    def save_search_memory(self):
        if not getattr(self,'_memory_ready',False) or not self._memory_dirty:return
        self._memory_timer.stop()
        source=self.source.currentData() or {}
        try:
            download_queries.save_search_memory(self.fid,self.query.text(),self.season.currentData(),source.get('url'),self.title_choice.currentData());self._memory_dirty=False
        except Exception as error:self.status.setText('Could not save this search: '+str(error))

    def hideEvent(self,event):
        self.save_search_memory();super().hideEvent(event)

    def refresh_home_style(self):
        from app.ui.release_search_style import qss
        from app.ui.home_style import colors,px
        from PyQt5.QtGui import QPalette,QColor
        self.setProperty('animevaultOwnScaledStyle',True);self.setStyleSheet(qss())
        for edit in self.findChildren(QLineEdit):
            palette=edit.palette();palette.setColor(QPalette.PlaceholderText,QColor(colors()['muted']));edit.setPalette(palette)
        self.table.verticalHeader().setDefaultSectionSize(px(72));self.availability.doItemsLayout()
        self.table.viewport().update();self.availability.viewport().update()
        primary_buttons=[self.action_buttons['Review selected downloads']]
        self.primary_actions.setMinimumWidth(sum(control.sizeHint().width() for control in primary_buttons)+px(8))
        from app.ui.manga_workflows import finish
        finish(self)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'table'):self._fit_columns()

    def eventFilter(self,watched,event):
        if hasattr(self,'table') and watched is self.table.viewport() and event.type()==QEvent.Resize:
            if not getattr(self,'_fit_pending',False):
                self._fit_pending=True;QTimer.singleShot(0,self._fit_columns)
        return super().eventFilter(watched,event)

    def _fit_columns(self):
        self._fit_pending=False
        from app.ui.home_style import px
        self.table.setColumnWidth(0,max(px(260),self.table.viewport().width()-sum(self.table.columnWidth(i) for i in range(1,7))))

    def update_selection_count(self,*_):
        self.review_button.setText(f'Review selected downloads ({len(self.model.selected)})')
        self.review_button.setEnabled(bool(self.model.selected))

    def refresh_titles(self,*_):
        edited=bool(self.query.text() and self.query.text()!=self._generated_query)
        season=self.season.currentData()
        changed=not hasattr(self,'_title_season') or self._title_season!=season
        self._title_season=season
        if changed:edited=False
        previous=self.title_choice.currentData()
        self.title_choice.blockSignals(True);self.title_choice.clear()
        saved=download_queries.custom_query(self.fid,season)
        if saved.get('query'):
            self.title_choice.addItem('Custom search · '+saved['query'],saved['query'])
            self.title_choice.setItemData(0,True,Qt.UserRole+1)
            self.title_choice.setItemData(0,saved['query'],Qt.ToolTipRole)
        for role,title in download_queries.title_options(self.fid,self.season.currentData()):
            self.title_choice.addItem(role+' · '+title,title)
            self.title_choice.setItemData(self.title_choice.count()-1,title,Qt.ToolTipRole)
        preferred=0 if changed and saved.get('active') else self.title_choice.findData(previous)
        if preferred<0:preferred=1 if saved.get('query') and not saved.get('active') else 0
        self.title_choice.setCurrentIndex(preferred)
        self.title_choice.blockSignals(False)
        if not edited:self.use_title()
        else:self.update_url()

    def use_title(self,*_):
        title=self.title_choice.currentData()
        if title:
            custom=bool(self.title_choice.currentData(Qt.UserRole+1))
            download_queries.activate_custom_query(self.fid,self.season.currentData(),custom)
            self._generated_query=title if custom else download_queries.default_query(self.fid,title,self.season.currentData(),self.query_series,self.query_config)
            self.query.setText(self._generated_query);self.update_url()

    def save_custom_query(self):
        try:query=download_queries.save_custom_query(self.fid,self.season.currentData(),self.query.text())
        except ValueError as error:self.status.setText(str(error));return
        self._generated_query=query;self.query.setText(query)
        del self._title_season
        self.refresh_titles()
        self.status.setText('Custom search saved for this anime and season. It will be used next time. Choose another title and Use title to switch back.')

    def update_url(self,*_):
        source=self.source.currentData()
        try:url=downloads.search_url(source['url'],self.query.text().strip()) if source else ''
        except ValueError:url='Invalid source URL. Check Downloads & Sources settings.'
        self.source_url.setText(url);self.source_url.setToolTip(url)


    def invalidate(self,*_):
        self.cancel_search();self.results=[];self.context=None;self.model.selected=set();self.render()
        self.availability_model.beginResetModel();self.availability_model.rows=[];self.availability_model.endResetModel()
        self.status.setText('Search again to use the changed title, season or source.')

    def search(self):
        if self._worker:self._worker.requestInterruption();self.status.setText('Cancelling the previous search. Retry shortly.');return
        self._memory_dirty=True;self.save_search_memory();self._generation+=1;generation=self._generation
        self.results=[];self.context=None;self.model.selected=set();self.render()
        self.availability_model.beginResetModel();self.availability_model.rows=[];self.availability_model.endResetModel()
        season=self.season.currentData();source=self.source.currentData();query=self.query.text().strip()
        if not query:self.status.setText('Enter a search query or choose a title and click Use title.');return
        alternatives=[self.title_choice.itemData(i) if self.title_choice.itemData(i,Qt.UserRole+1) else download_queries.default_query(self.fid,self.title_choice.itemData(i),season,self.query_series,self.query_config) for i in range(min(4,self.title_choice.count()))] if self.alternatives.isChecked() else []
        worker=IOTask(lambda:discovery.search(self.fid,season,source,query,worker.isInterruptionRequested,alternatives));self._worker=worker;track(worker)
        from app.ui.components.operation_progress import watch
        watch(self,worker,'Searching download releases')
        self.loading.show();self.search_button.setEnabled(False);self.status.setText('Searching the source through Chrome and checking local episodes…')
        worker.succeeded.connect(lambda result:self.loaded(result,focus_results=True) if generation==self._generation else None)
        worker.failed.connect(lambda message:self.status.setText(message) if generation==self._generation else None)
        worker.finished.connect(self.search_finished);worker.start()
    def search_finished(self):
        self.loading.hide();self.search_button.setEnabled(True)
        self._worker.deleteLater();self._worker=None
    def cancel_search(self):
        self._generation+=1
        if self._worker:self._worker.requestInterruption()
        self.status.setText('Search cancelled. No downloads were started.')
    def loaded(self,result,focus_results=False):
        self.context=result['context'];self.results=result['results'];self.model.selected=set();self.render()
        self.context.update({k:v for k,v in self.assignment_context.items() if k not in ('local','pending','fid','title')})
        if self.assignment_context.get('continuous') is not None:
            self.context.update(discovery.library_context(self.fid,self.assignment_context.get('season'),continuous=self.assignment_context['continuous']))
            self.context.update(self.assignment_context)
        self.update_coverage()
        self.status.setText(f'{len(self.results)} releases found. Seeder counts do not guarantee availability.' if self.results else 'No releases found for this search. Try another title, source, group or quality; use Retry/Search releases.')
        if result.get('query_used'):self.status.setText(self.status.text()+' Searched: '+result['query_used'])
        if focus_results:
            from app.ui.search_navigation import focus_results as reveal
            reveal(self,self.table if self.results else self.status)

    def update_coverage(self):
        coverage=discovery.availability_rows(self.context,self.results)
        from collections import Counter
        counts=Counter(row['status'] for row in coverage)
        self.coverage.setText(' · '.join(f'{key}: {value}' for key,value in counts.items()) or 'Episode boundaries are unverified. Confirm result coverage manually.')
        self.availability_model.beginResetModel();self.availability_model.rows=coverage;self.availability_model.endResetModel()
    def render(self,*_):
        rows=list(self.results);mode=self.filter.currentIndex();query=self.quality.text().casefold()
        if mode==1:rows=[r for r in rows if r['status']=='Missing — Release Found']
        elif mode==2:rows=[r for r in rows if r['status']=='Match Uncertain']
        elif mode==3:rows=[r for r in rows if r['status'] in ('In Library','Downloading or Queued')]
        if query:rows=[r for r in rows if query in ' '.join(str(r.get(k) or '') for k in ('title','group','quality')).casefold()]
        key=(lambda r:-(r.get('seeders') or 0)) if self.sort.currentIndex()==0 else (lambda r:r['title'].casefold()) if self.sort.currentIndex()==1 else (lambda r:min(r.get('episodes') or [10000]))
        self.model.beginResetModel();self.model.rows=sorted(rows,key=key);self.model.endResetModel()
        self.update_selection_count()
    def highlighted(self):
        rows=self.table.selectionModel().selectedRows();return self.model.rows[rows[0].row()] if rows else None
    def confirm_match(self):
        entries=[r for r in self.results if r['identity'] in self.model.selected]
        if not entries:
            highlighted=self.highlighted()
            if highlighted:entries=[highlighted]
        if not entries or not self.context:self.status.setText('Check one or more releases, or highlight a result first.');return
        def saved(value):
            from PyQt5 import sip
            if sip.isdeleted(self):return
            by_id={r['identity']:r for r in value}
            if value:self.context=discovery.library_context(self.fid,value[0]['season'],continuous=value[0]['continuous'])
            self.results=[by_id.get(r['identity']) or (r if r.get('match_confirmed') else discovery.classify(r,self.context)) for r in self.results];self.model.selected.update(by_id);self.render();self.update_coverage()
            self.status.setText(f'{len(value)} files confirmed. Click Review selected downloads to start them.')
        navigate(ConfirmCoverage(self,entries,self.context,saved))
    def missing(self):
        if not self.context:return
        rows,remaining=discovery.missing_plan(self.context,self.results)
        self.model.selected={row['identity'] for row in rows};self.render()
        if not rows:self.status.setText('No confident releases cover only missing episodes. Review uncertain matches or partial batches manually.');return
        self.review()
    def review(self):
        selected=[r for r in self.results if r['identity'] in self.model.selected and not r.get('_submitted')]
        if not selected:self.status.setText('Select release checkboxes first.');return
        if not self.context:return
        def confirmed(entries):
            review=DownloadReview(self,self.fid,entries,self.context)
            review.downloads_added.connect(self.downloads_added)
            navigate(review)
        if all(r.get('match_confirmed') for r in selected):confirmed(selected)
        else:navigate(ConfirmCoverage(self,selected,self.context,confirmed))

    def downloads_added(self,entries):
        identities={entry['identity'] for entry in entries}
        for entry in self.results:
            if entry['identity'] in identities:
                entry.update(status='Downloading or Queued',_submitted=True)
        self.model.selected.difference_update(identities)
        if self.context is not None:
            self.context['pending']=sorted(set(self.context['pending'])|{key for entry in entries for key in entry['episode_keys']})
        self.render();self.update_coverage()
        self.status.setText(f'{len(entries)} download(s) added. View their progress in Downloads.')

    def refresh_local(self):
        if self._worker:return
        season=self.season.currentData();entries=list(self.results)
        def reload():
            context=discovery.library_context(self.fid,season);results=[]
            for entry in entries:
                if entry.get('match_confirmed'):
                    keys=set(entry['episode_keys'])
                    state='In Library' if keys<=set(context['local']) else 'Downloading or Queued' if keys<=set(context['local'])|set(context['pending']) else 'Missing — Release Found'
                    results.append({**entry,'status':state})
                else:results.append(discovery.classify(entry,context))
            return dict(context=context,results=results)
        worker=IOTask(reload);self._worker=worker;track(worker)
        worker.succeeded.connect(self.loaded);worker.failed.connect(self.status.setText);worker.finished.connect(self.search_finished);worker.start()
    def manual(self):
        from app.ui.downloads import open_downloads
        open_downloads(self,self.fid)
    def open_browser(self):
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        source=self.source.currentData();query=self.query.text().strip()
        if not query:self.status.setText('Enter a search query first.');return
        QDesktopServices.openUrl(QUrl(downloads.search_url(source['url'],query)))
        self.status.setText('Complete any verification in Chrome, then return and retry the in-app search.')
    def reject(self): self.save_search_memory();self.cancel_search();super().reject()


def open_release_search(parent,fid,assignment_context=None):
    page=ReleaseSearchPage(parent,fid,assignment_context);navigate(page);return page


def confirm_manual_download(parent,fid,source,season,submitted,origin=None):
    """The same locked-anime confirmation for source search, paste and browse."""
    from pathlib import Path
    from app.core.parser import extract_episode_numbers
    def prepare():
        if source.lower().startswith('magnet:?'):
            from app.core.magnet_capture import validate
            name=validate(source).get('name') or 'Magnet download'
        else:
            name=Path(source).stem
        context=discovery.library_context(fid,season,continuous=False if season else None)
        entry=dict(title=name,magnet=source,episodes=extract_episode_numbers(name),season=season,continuous=context['continuous'],source='Manual',origin=origin)
        return entry,context
    def ready(value):
        entry,context=value
        def confirmed(result):start(parent,lambda:discovery.submit(fid,[result]),lambda paths:submitted(paths[0]))
        dialog=ConfirmCoverage(parent,entry,context,confirmed);dialog.apply_button.setText('Confirm and download');navigate(dialog)
    start(parent,prepare,ready)
