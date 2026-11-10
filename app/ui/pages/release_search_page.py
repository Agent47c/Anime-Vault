"""In-app source results with conservative coverage and an explicit review."""
from PyQt5.QtCore import Qt,QAbstractTableModel,QModelIndex
from PyQt5.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QLineEdit,QComboBox,QPushButton,QTableView,QHeaderView,QAbstractItemView,QProgressBar,QCheckBox,QSpinBox,QSizePolicy
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
        return flags|Qt.ItemIsUserCheckable if index.column()==0 else flags
    def setData(self,index,value,role=Qt.EditRole):
        if role!=Qt.CheckStateRole or index.column()!=0:return False
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
        if index.isValid() and role==Qt.DisplayRole:return discovery.episode_label(self.rows[index.row()]['episode']) if index.column()==0 else self.rows[index.row()]['status']


class ConfirmCoverage(DrawerDialog):
    def __init__(self,parent,entry,context,callback):
        super().__init__(parent);self.entry=entry;self.context=context;self.callback=callback
        body,self.apply_button=chrome(self,'Confirm release match','Choose the actual numbering. This confirmation does not download anything.','照合','Confirm match',self.apply)
        body.addWidget(text(entry['title'],'workflow_row_title'));body.addWidget(text(entry.get('reason') or 'Review this release.'))
        self.kind=QComboBox()
        for label,key in [('Episode','EPISODE'),('Movie','MOVIE'),('Special / OVA','SPECIAL')]:self.kind.addItem(label,key)
        field(body,'Release type',self.kind)
        self.season=QSpinBox();self.season.setRange(0,100);self.season.setSpecialValueText('Absolute / continuing');self.season.setValue(context.get('season') or 0)
        field(body,'Season (0 = absolute)',self.season)
        self.first=QSpinBox();self.first.setRange(1,9999);self.first.setValue(min(entry.get('episodes') or [1]));field(body,'First episode / item',self.first)
        self.last=QSpinBox();self.last.setRange(1,9999);self.last.setValue(max(entry.get('episodes') or [1]));field(body,'Last episode / item',self.last)
        self.confirm=QCheckBox('I checked this title and its release numbering');body.addWidget(self.confirm)
        self.validation=text('');body.addWidget(self.validation)
        self.apply_button.setEnabled(False);self.confirm.toggled.connect(self.apply_button.setEnabled)
        body.addStretch()
    def apply(self):
        first,last=self.first.value(),self.last.value()
        if last<first:self.validation.setText('Last episode must be the same as or greater than the first.');return
        if not self.confirm.isChecked():self.validation.setText('Confirm the title and release numbering first.');return
        entry=dict(self.entry);season=self.season.value()
        entry.update(episode_keys=[discovery.episode_key(season==0,season,n,self.kind.currentData()) for n in range(first,last+1)],
                     season=season,match_confirmed=True,status='Missing — Release Found',reason='Match confirmed by user')
        self.callback(entry);self.accept()


class DownloadReview(DrawerDialog):
    def __init__(self,parent,fid,entries,context):
        super().__init__(parent);self.fid=fid;self.entries=entries
        covered={key for entry in entries for key in entry['episode_keys']}
        missing=set(context['missing'])-covered
        body,self.apply_button=chrome(self,'Review downloads','Check episode coverage and destinations before adding transfers.','取込',f'Add {len(entries)} downloads',self.apply)
        for entry in entries:
            body.addWidget(text(entry['title'],'workflow_row_title'))
            body.addWidget(text('Covers: '+discovery.coverage_label(entry['episode_keys'])))
            overlap=set(entry['episode_keys'])&set(context['local'])
            if overlap:body.addWidget(text(f'Batch includes {len(overlap)} episodes already in the library. Use file selection to exclude them.'))
        body.addWidget(text('Still missing after these releases: '+(discovery.coverage_label(sorted(missing)) if missing else 'None within verified boundaries.')))
        body.addWidget(text('Destination: '+downloads.settings()['destination']))
        body.addWidget(text('Seeder counts describe the source listing, not guaranteed download availability.'))
        self.checked=QCheckBox('I reviewed the selected releases and episode coverage');body.addWidget(self.checked)
        self.apply_button.setEnabled(False);self.checked.toggled.connect(self.apply_button.setEnabled)
        self.message=text('');body.addWidget(self.message)
    def apply(self):
        if not self.checked.isChecked():self.message.setText('Review the selected releases and coverage first.');return
        def done(paths):
            from app.ui.downloads import monitor
            monitor().check();self.message.setText(f'{len(paths)} transfers added. Use Downloads to choose files and monitor progress.');self.accept()
        start(self,lambda:discovery.submit(self.fid,self.entries),done)


class ReleaseSearchPage(QDialog):
    dispose_on_leave=True
    def __init__(self,parent,fid):
        super().__init__(parent);self.fid=fid;self._worker=None;self._generation=0;self.results=[];self.context=None
        self.setObjectName('release_search_page')
        self.setWindowTitle('Find Download Files')
        box=QVBoxLayout(self);box.setContentsMargins(24,16,24,24);box.setSpacing(16)
        title=QLabel('Find Download Files');title.setObjectName('download_heading');box.addWidget(title)
        self.subtitle=text((db.get_series(fid) or {}).get('display_title','Anime'));box.addWidget(self.subtitle)
        options=QHBoxLayout();self.season=QComboBox();self.season.addItem('Continuing / choose season',None)
        series=db.get_series(fid) or {};continuous=db.uses_continuous_episodes(series) or series.get('anilist_id')==21
        self.query_series=series;self.query_config=downloads.settings()
        seen=set()
        for item in db.get_series_seasons(fid):
            number=item.get('season_number')
            if item.get('relation_type')=='SEASON' and number and number not in seen:
                seen.add(number);self.season.addItem(f'Season {number} · {item["title_display"]}',number)
        if len(seen)==1 and not continuous:self.season.setCurrentIndex(1)
        if continuous:self.season.setEnabled(False)
        self.source=QComboBox()
        self.sources=discovery.sources()
        for source in self.sources:self.source.addItem(source['name'],source)
        selected=next((i for i,s in enumerate(self.sources) if s['url']==downloads.settings()['source']),0);self.source.setCurrentIndex(selected)
        options.addWidget(self.season,1);options.addWidget(self.source,1);box.addLayout(options)
        title_row=QHBoxLayout();self.title_choice=QComboBox()
        self.title_choice.setMinimumContentsLength(20);self.title_choice.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed)
        self.title_choice.setAccessibleName('Search title language')
        title_row.addWidget(QLabel('Search title'));title_row.addWidget(self.title_choice,1)
        use_title=QPushButton('Use title');use_title.clicked.connect(self.use_title);title_row.addWidget(use_title);box.addLayout(title_row)
        self.alternatives=QCheckBox('Try other saved titles if this query has no results');box.addWidget(self.alternatives)
        search=QHBoxLayout();self.query=QLineEdit();self.query.setPlaceholderText('Edit the exact words to search on the selected website')
        self.query.setClearButtonEnabled(True);self._generated_query=''
        search.addWidget(self.query,1);self.search_button=QPushButton('Search releases');self.search_button.setMinimumHeight(44);self.search_button.clicked.connect(self.search);search.addWidget(self.search_button)
        self.search_button.setProperty('accent',True)
        stop=QPushButton('Cancel search');stop.clicked.connect(self.cancel_search);search.addWidget(stop);box.addLayout(search)
        self.source_url=QLineEdit();self.source_url.setReadOnly(True);self.source_url.setAccessibleName('Source search URL')
        self.source_url.setToolTip('The exact URL sent to Chrome. You can copy it or use Open source in Chrome.')
        url_row=QHBoxLayout();url_row.addWidget(QLabel('Search URL'));url_row.addWidget(self.source_url,1);box.addLayout(url_row)
        self.loading=QProgressBar();self.loading.setRange(0,0);self.loading.setFixedHeight(4);self.loading.hide();box.addWidget(self.loading)
        self.status=text('Search through your connected Chrome extension. No download starts until you review and confirm.');box.addWidget(self.status)
        filters=QHBoxLayout();self.filter=QComboBox();self.filter.addItems(['All results','Missing releases','Match uncertain','In library / queued'])
        self.quality=QLineEdit();self.quality.setPlaceholderText('Filter quality/group/title')
        self.sort=QComboBox();self.sort.addItems(['Most seeders','Title A–Z','Episode number'])
        for control in (self.season,self.source,self.filter,self.sort):
            control.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon);control.setMinimumContentsLength(16)
            control.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed)
        for control in (self.filter,self.quality,self.sort):filters.addWidget(control,1)
        box.addLayout(filters)
        self.model=ReleaseModel(self);self.table=QTableView();self.table.setModel(self.model);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setTextElideMode(Qt.ElideRight);self.table.setWordWrap(False);self.table.verticalHeader().hide();self.table.verticalHeader().setDefaultSectionSize(56);self.table.setShowGrid(False)
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        for column in range(1,7):self.table.horizontalHeader().setSectionResizeMode(column,QHeaderView.ResizeToContents)
        box.addWidget(self.table,1)
        self.coverage=text('Local episode coverage will appear after searching.');box.addWidget(self.coverage)
        show_episodes=QCheckBox('Show episode availability');box.addWidget(show_episodes)
        self.availability_model=AvailabilityModel(self);self.availability=QTableView();self.availability.setModel(self.availability_model);self.availability.setMaximumHeight(180);self.availability.setMinimumHeight(140)
        self.availability.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);self.availability.verticalHeader().hide();self.availability.hide()
        show_episodes.toggled.connect(self.availability.setVisible);box.addWidget(self.availability)
        actions=QGridLayout()
        for index,(label,callback) in enumerate([('Confirm highlighted match',self.confirm_match),('Download Missing Episodes',self.missing),('Review selected downloads',self.review),('Paste magnet / torrent',self.manual),('Open source in Chrome',self.open_browser)]):
            control=QPushButton(label);control.setMinimumHeight(44);control.clicked.connect(callback);actions.addWidget(control,index//3,index%3)
            if label=='Review selected downloads':control.setProperty('accent',True)
        box.addLayout(actions)
        self.filter.currentIndexChanged.connect(self.render);self.quality.textChanged.connect(self.render);self.sort.currentIndexChanged.connect(self.render)
        self.query.returnPressed.connect(self.search)
        self.query.textChanged.connect(self.invalidate)
        self.season.currentIndexChanged.connect(self.invalidate);self.source.currentIndexChanged.connect(self.invalidate)
        self.query.textChanged.connect(self.update_url);self.source.currentIndexChanged.connect(self.update_url)
        self.title_choice.currentIndexChanged.connect(self.use_title)
        self.season.currentIndexChanged.connect(self.refresh_titles)
        self.alternatives.toggled.connect(self.invalidate)
        self.refresh_titles()

    def refresh_titles(self,*_):
        edited=bool(self.query.text() and self.query.text()!=self._generated_query)
        previous=self.title_choice.currentData()
        self.title_choice.blockSignals(True);self.title_choice.clear()
        for role,title in download_queries.title_options(self.fid,self.season.currentData()):
            self.title_choice.addItem(role+' · '+title,title)
            self.title_choice.setItemData(self.title_choice.count()-1,title,Qt.ToolTipRole)
        self.title_choice.setCurrentIndex(max(0,self.title_choice.findData(previous)))
        self.title_choice.blockSignals(False)
        if not edited:self.use_title()
        else:self.update_url()

    def use_title(self,*_):
        title=self.title_choice.currentData()
        if title:
            self._generated_query=download_queries.default_query(self.fid,title,self.season.currentData(),self.query_series,self.query_config)
            self.query.setText(self._generated_query);self.update_url()

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
        self._generation+=1;generation=self._generation
        self.results=[];self.context=None;self.model.selected=set();self.render()
        self.availability_model.beginResetModel();self.availability_model.rows=[];self.availability_model.endResetModel()
        season=self.season.currentData();source=self.source.currentData();query=self.query.text().strip()
        if not query:self.status.setText('Enter a search query or choose a title and click Use title.');return
        alternatives=[download_queries.default_query(self.fid,self.title_choice.itemData(i),season,self.query_series,self.query_config) for i in range(min(4,self.title_choice.count()))] if self.alternatives.isChecked() else []
        worker=IOTask(lambda:discovery.search(self.fid,season,source,query,worker.isInterruptionRequested,alternatives));self._worker=worker;track(worker)
        self.loading.show();self.search_button.setEnabled(False);self.status.setText('Searching the source through Chrome and checking local episodes…')
        worker.succeeded.connect(lambda result:self.loaded(result) if generation==self._generation else None)
        worker.failed.connect(lambda message:self.status.setText(message) if generation==self._generation else None)
        worker.finished.connect(self.search_finished);worker.start()
    def search_finished(self):
        self.loading.hide();self.search_button.setEnabled(True)
        self._worker.deleteLater();self._worker=None
    def cancel_search(self):
        self._generation+=1
        if self._worker:self._worker.requestInterruption()
        self.status.setText('Search cancelled. No downloads were started.')
    def loaded(self,result):
        self.context=result['context'];self.results=result['results'];self.model.selected=set();self.render()
        self.update_coverage()
        self.status.setText(f'{len(self.results)} releases found. Seeder counts do not guarantee availability.' if self.results else 'No releases found for this search. Try another title, source, group or quality; use Retry/Search releases.')
        if result.get('query_used'):self.status.setText(self.status.text()+' Searched: '+result['query_used'])

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
    def highlighted(self):
        rows=self.table.selectionModel().selectedRows();return self.model.rows[rows[0].row()] if rows else None
    def confirm_match(self):
        entry=self.highlighted()
        if not entry or not self.context:self.status.setText('Search and highlight a result first.');return
        def saved(value):
            from PyQt5 import sip
            if sip.isdeleted(self):return
            self.results=[value if r['identity']==entry['identity'] else r for r in self.results];self.render();self.update_coverage()
        navigate(ConfirmCoverage(self,entry,self.context,saved))
    def missing(self):
        if not self.context:return
        rows,remaining=discovery.missing_plan(self.context,self.results)
        self.model.selected={row['identity'] for row in rows};self.render()
        if not rows:self.status.setText('No confident releases cover only missing episodes. Review uncertain matches or partial batches manually.');return
        self.review()
    def review(self):
        selected=[r for r in self.results if r['identity'] in self.model.selected]
        if not selected:self.status.setText('Select release checkboxes first.');return
        if any(not r.get('episode_keys') for r in selected):self.status.setText('Confirm uncertain matches before adding downloads.');return
        def completed(result):
            from PyQt5 import sip
            if result==QDialog.Accepted and not sip.isdeleted(self):self.refresh_local()
        navigate(DownloadReview(self,self.fid,selected,self.context),completed)

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
    def reject(self): self.cancel_search();super().reject()


def open_release_search(parent,fid): navigate(ReleaseSearchPage(parent,fid))
