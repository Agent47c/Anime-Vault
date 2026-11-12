"""Release discovery and per-anime timeline, using existing navigation and IO."""
from datetime import datetime
from contextlib import closing
from PyQt5.QtCore import Qt,QThread,pyqtSignal,QEvent,QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QScrollArea,QWidget,QFrame,QComboBox,QGridLayout,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox,QCheckBox,QSizePolicy
from app import db
from app.core import release_news as news
from app.core.anilist_client import resolve_display_title
from app.ui.io_task import IOTask,track
from app.ui.navigation import navigate
from app.ui.components.flow_layout import FlowLayout
from app.ui.transfer_style import qss
from app.ui.components.tag_picker import TagPicker

class NewsArtwork(QThread):
    image_ready=pyqtSignal(int,object)
    def __init__(self,items,allow_network=False):super().__init__(QApplication.instance());self.items=items;self.allow_network=allow_network
    def run(self):
        from app.core import anilist_client as api
        from app.core.image_profiles import load_cached_image
        from app.config import COVERS_DIR
        try:
            with api.cancellable(self.isInterruptionRequested):
                for media in self.items:
                    if self.isInterruptionRequested():break
                    from app.config import is_offline
                    name=api.download_cover(media,media['id'],allow_network=self.allow_network and not is_offline())
                    if name:self.image_ready.emit(media['id'],load_cached_image(COVERS_DIR/name))
        except (InterruptedError,ValueError,OSError):pass

class ReleaseNewsPage(QDialog):
    full_page=True
    dispose_on_leave=True
    def refresh_home_style(self):
        from app.ui.five_screen_style import qss
        self.setProperty('animevaultOwnScaledStyle',True)
        self.setStyleSheet(qss('release_news'))
    def __init__(self,parent=None,media_id=None):
        super().__init__(parent);self.media_id=media_id;self.page=1;self.worker=None;self.generation=0
        from app.ui.five_screen_style import qss
        self.setObjectName('release_news');self.setWindowTitle('Broadcast & Release Updates' if media_id else 'New anime releases');self.resize(1200,820);self.setStyleSheet(qss('release_news'))
        layout=QVBoxLayout(self);layout.setContentsMargins(24,20,24,20);layout.setSpacing(16)
        title=QLabel(self.windowTitle());title.setObjectName('transfer_heading');heading=QHBoxLayout();heading.addWidget(title,1)
        refresh=QPushButton('Check updates');refresh.clicked.connect(lambda:self.load(True));heading.addWidget(refresh);layout.addLayout(heading)
        controls=QHBoxLayout()
        self.period=QComboBox();self.period.addItems(['Released in the last 30 days','Upcoming in the next 90 days','Announced · date may be unknown']);self.period.setAccessibleName('Release period');self.period.setVisible(not media_id);controls.addWidget(self.period)
        self.sort=TagPicker('Sort releases',multiple=False);self.sort.addItems(['Premiere: newest first','Premiere: earliest first','English title A–Z','Most popular']);self.sort.setAccessibleName('Sort releases');self.sort.setVisible(not media_id);self.sort.currentIndexChanged.connect(self.reset);controls.addWidget(self.sort)
        self.broadcast_filter=QComboBox();self.broadcast_filter.addItems(['All broadcasts','Aired episodes','Scheduled episodes']);self.broadcast_filter.setVisible(bool(media_id));self.broadcast_filter.currentIndexChanged.connect(self.refilter);controls.addWidget(self.broadcast_filter)
        controls.addStretch();layout.addLayout(controls)
        self.discovery_filters=QWidget();self.discovery_filters.setObjectName('transfer_clear');filters=FlowLayout(self.discovery_filters)
        self.genre_filter=TagPicker('Genres');self.genre_filter.addItem('All genres',None)
        for value in news.GENRES:self.genre_filter.addItem(value,value)
        self.theme_filter=TagPicker('Themes');self.theme_filter.addItem('All themes',None)
        for value in news.THEMES:self.theme_filter.addItem(value,value)
        self.format_filter=TagPicker('Formats');self.format_filter.addItem('All formats',None)
        for value in news.FORMATS:self.format_filter.addItem(value.replace('_',' '),value)
        for widget,name in ((self.genre_filter,'Filter by genre'),(self.theme_filter,'Filter by theme'),(self.format_filter,'Filter by format')):
            widget.setAccessibleName(name);widget.setCursor(Qt.PointingHandCursor);filters.addWidget(widget);widget.currentIndexChanged.connect(self.reset)
        from app.preferences import enabled
        self.adult_filter=QCheckBox('Include adult (18+)');self.adult_filter.setChecked(enabled('allow_mature'));self.adult_filter.setEnabled(enabled('allow_mature'))
        self.adult_filter.setToolTip('Follows Settings → Metadata and AniList → Allow mature (18+) titles.');self.adult_filter.setCursor(Qt.PointingHandCursor)
        filters.addWidget(self.adult_filter);self.adult_filter.toggled.connect(self.reset)
        self.discovery_filters.setVisible(not media_id);layout.addWidget(self.discovery_filters)
        self.status=QLabel('Times use your computer’s local timezone. Historical schedules may be incomplete.');self.status.setWordWrap(True);layout.addWidget(self.status)
        scroll=QScrollArea();self.scroll=scroll;scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);scroll.viewport().installEventFilter(self)
        content=QWidget();content.setObjectName('transfer_clear');self.rows=QVBoxLayout(content);self.rows.setAlignment(Qt.AlignTop);scroll.setWidget(content);layout.addWidget(scroll,1)
        footer=QHBoxLayout();self.previous=QPushButton('Previous');self.previous.clicked.connect(lambda:self.change_page(-1));footer.addWidget(self.previous)
        self.next=QPushButton('Next');self.next.clicked.connect(lambda:self.change_page(1));footer.addWidget(self.next);footer.addStretch();close=QPushButton('Back');close.clicked.connect(self.reject);footer.addWidget(close);layout.addLayout(footer)
        self.period.currentIndexChanged.connect(self.reset);self.finished.connect(self.stop);self.load()

    def stop(self,*_):
        self.generation+=1
        if self.worker:self.worker.requestInterruption()
        if getattr(self,'_artwork',None):self._artwork.requestInterruption()

    def reset(self,*_):self.page=1;self.load()
    def change_page(self,delta):self.page=max(1,self.page+delta);self.load()

    def run(self,operation,ready,on_error=None):
        if self.worker:self.worker.requestInterruption()
        self.generation+=1;generation=self.generation
        worker=IOTask(operation);self.worker=worker;track(worker)
        from PyQt5 import sip
        def loaded(value):
            if not sip.isdeleted(self) and generation==self.generation:ready(value)
        def failed(message):
            if not sip.isdeleted(self) and generation==self.generation:
                self.status.setText(message)
                if on_error:on_error()
        def finished():
            if not sip.isdeleted(self) and self.worker is worker:self.worker=None
            worker.deleteLater()
        worker.succeeded.connect(loaded);worker.failed.connect(failed);worker.finished.connect(finished);worker.start()

    def load(self,force=False):
        self.status.setText('Checking AniList…' if force else 'Loading release details…' if self.media_id else 'Loading saved results…');page=self.page;upcoming=self.period.currentIndex()==1;mid=self.media_id;announced=self.period.currentIndex()==2;sort=('START_DATE_DESC','START_DATE','TITLE_ENGLISH','POPULARITY_DESC')[self.sort.currentIndex()]
        genre=self.genre_filter.currentData();theme=self.theme_filter.currentData();media_format=self.format_filter.currentData();include_adult=self.adult_filter.isChecked()
        def operation():
            from app.core import anilist_client
            with anilist_client.cancellable(QThread.currentThread().isInterruptionRequested):
                info={}
                try:
                    if not mid:
                        result=news.discover(upcoming,page,force,announced,sort,genre=genre,theme=theme,media_format=media_format,include_adult=include_adult,cache_info=info)
                        return result,info
                    result=news.timeline(mid,page,force,cache_info=info)
                except news.CacheMiss as error:
                    return ({} if mid else ([],False)),dict(source='empty',warning=str(error))
                from app.core.download_discovery import library_context
                with closing(db.get_connection()) as conn:row=conn.execute('SELECT franchise_id,season_number FROM seasons WHERE anilist_id=?',(mid,)).fetchone()
                if row:
                    result=dict(result);result['_library']=library_context(row['franchise_id'],row['season_number'])
                return result,info
        def ready(value):
            result,info=value
            self._allow_artwork_network=info.get('source')=='network'
            self._cache_info=info;self.render(result)
            if force and info.get('source')!='empty':
                from app.ui.search_navigation import focus_results
                focus_results(self,self.scroll.widget())
        self.run(operation,ready)

    def panel(self,title,detail):
        frame=QFrame();frame.setObjectName('transfer_panel');box=QVBoxLayout(frame)
        heading=QLabel(title);heading.setTextFormat(Qt.PlainText);heading.setWordWrap(True);heading.setObjectName('update_title');box.addWidget(heading)
        label=QLabel(detail);label.setTextFormat(Qt.PlainText);label.setWordWrap(True);box.addWidget(label);self.rows.addWidget(frame)
        return box

    def render(self,result):
        if getattr(self,'_artwork',None):self._artwork.requestInterruption()
        self._last_result=result
        while self.rows.count():
            item=self.rows.takeAt(0)
            if item.widget():item.widget().deleteLater()
        self.previous.setEnabled(self.page>1)
        if self.media_id:
            # Issue: Nullable Page/airingSchedules/relations subfields in AniList responses could raise KeyError/TypeError.
            # Fix: Guard nested response keys safely before rendering panels.
            media=result.get('Media') or {};schedule=result.get('Page') or {};self.next.setEnabled(bool((schedule.get('pageInfo') or {}).get('hasNextPage')))
            self.panel(resolve_display_title(media),f"Premiere: {news.date_label(media.get('startDate'))} · {media.get('status','Unknown')}\n"+(media.get('description') or 'No synopsis available.'))
            for edge in (media.get('relations') or {}).get('edges') or []:
                node=(edge or {}).get('node') or {}
                if node.get('type')=='ANIME' and node.get('id') and edge.get('relationType') in ('SEQUEL','PREQUEL'):
                    box=self.panel(resolve_display_title(node),f"{edge['relationType']} · {node.get('status','Unknown')} · Premiere {news.date_label(node.get('startDate'))}")
                    button=QPushButton('Release details');button.clicked.connect(lambda checked=False,mid=node['id']:open_release_news(self,mid));box.addWidget(button,0,Qt.AlignLeft)
            schedules=schedule.get('airingSchedules') or []
            mode=self.broadcast_filter.currentIndex();now=datetime.now().timestamp()
            schedules=[r for r in schedules if mode==0 or (r['airingAt']<=now)==(mode==1)]
            table=QTableWidget(len(schedules),5);table.setHorizontalHeaderLabels(['EPISODE','BROADCAST · LOCAL TIME','STATE','LIBRARY','ACTION']);table.verticalHeader().hide();table.setShowGrid(False);table.setEditTriggers(QTableWidget.NoEditTriggers);table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
            table.setMinimumHeight(max(160,min(600,50+len(schedules)*64)));self.rows.addWidget(table)
            from app.ui.home_style import px
            table.horizontalHeader().setSectionResizeMode(4,QHeaderView.Fixed);table.setColumnWidth(4,px(180))
            context=result.get('_library') or {}
            from app.core.download_discovery import episode_key
            for i,row in enumerate(schedules):
                dt=datetime.fromtimestamp(row['airingAt']).astimezone()
                aired=row['airingAt']<=now;key=episode_key(context.get('continuous',False),context.get('season'),row['episode']);path=context.get('local',{}).get(key)
                values=[f"Episode {row['episode']}",dt.strftime('%A, %d %B %Y · %H:%M %Z'),'Aired' if aired else 'Scheduled','In library' if path else 'Queued' if key in context.get('pending',[]) else 'Not available locally' if aired and context else 'Upcoming' if not aired else 'Not linked']
                for col,value in enumerate(values):table.setItem(i,col,QTableWidgetItem(value))
                action=QPushButton('Play' if path else 'Auto-Grab' if aired else 'Notify me');action.setCursor(Qt.PointingHandCursor)
                if path:action.clicked.connect(lambda checked=False,p=path:self.play(p))
                elif aired:
                    action.setEnabled(bool(context) and key not in context.get('pending',[]));action.clicked.connect(lambda checked=False,ep=row['episode'],fid=context.get('fid'):self._auto_grab(fid,ep))
                else:action.clicked.connect(lambda checked=False,r=dict(row),t=resolve_display_title(media):self.remind(r,t))
                table.setCellWidget(i,4,action);table.setRowHeight(i,64)
            if not schedules:self.panel('No episode schedule published','No dates are assumed. Check updates again later.')
        else:
            items,more=result;self.next.setEnabled(more)
            grid_widget=QWidget();grid_widget.setObjectName('transfer_clear');grid=QGridLayout(grid_widget);grid.setContentsMargins(0,0,0,0);grid.setSpacing(20);self.rows.addWidget(grid_widget)
            self._discovery_cards=[];self._discovery_grid=grid;posters={}
            for media in items:
                frame=QFrame();frame.setObjectName('transfer_panel');box=QVBoxLayout(frame)
                frame.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred);frame.setMinimumWidth(0)
                from app.ui.components.workflow import thumbnail
                poster=thumbnail(resolve_display_title(media),None,220,180);box.addWidget(poster,0,Qt.AlignCenter)
                posters[media['id']]=poster
                title=QLabel(resolve_display_title(media));title.setWordWrap(True);title.setTextFormat(Qt.PlainText);title.setObjectName('update_title');title.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred);title.setMinimumWidth(0);box.addWidget(title)
                detail=QLabel(f"Premiere: {news.date_label(media.get('startDate'))}\n{media.get('format','Unknown')} · {media.get('status','Unknown')}");detail.setWordWrap(True);box.addWidget(detail)
                actions=FlowLayout();box.addLayout(actions)
                details=QPushButton('Release details');details.clicked.connect(lambda checked=False,mid=media['id']:open_release_news(self,mid));actions.addWidget(details)
                button=QPushButton('Import as Watching');button.clicked.connect(lambda checked=False,m=media,b=button:self.import_media(m,b));actions.addWidget(button)
                self._discovery_cards.append(frame)
            self.arrange_cards()
            if items:
                worker=NewsArtwork(items,allow_network=getattr(self,'_allow_artwork_network',False));self._artwork=worker;track(worker)
                from PyQt5 import sip
                def image_ready(mid,image):
                    if sip.isdeleted(self) or self._artwork is not worker or worker.isInterruptionRequested():return
                    label=posters.get(mid)
                    if label is not None and not sip.isdeleted(label):
                        pix=QPixmap.fromImage(image).scaled(440,360,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation);pix.setDevicePixelRatio(2);label.setPixmap(pix)
                def artwork_done():
                    if not sip.isdeleted(self) and self._artwork is worker:self._artwork=None
                    worker.deleteLater()
                worker.image_ready.connect(image_ready);worker.finished.connect(artwork_done);worker.start()
            if not items:
                info=getattr(self,'_cache_info',{})
                if info.get('source')=='empty':self.panel('No saved results for these filters yet','Click Check updates to fetch and save this release period and filter combination.')
                else:self.panel('No releases found for this period and filters','Try clearing selected tags or click Check updates to check the latest information. Previously saved results are kept until you refresh.')
        info=getattr(self,'_cache_info',{})
        stamp=info.get('saved_at')
        checked=datetime.fromtimestamp(stamp).astimezone().strftime('%d %b %Y · %H:%M') if stamp else 'not checked yet'
        message=info.get('warning') or ('Updated and saved' if info.get('source')=='network' else 'Saved results')
        self.status.setText(f'{message} · Page {self.page} · Last checked: {checked}. Click Check updates to refresh online.')

    def arrange_cards(self):
        if not hasattr(self,'_discovery_grid'):return
        grid=self._discovery_grid
        width=self.scroll.viewport().width()-self.rows.contentsMargins().left()-self.rows.contentsMargins().right()
        cols=max(1,(width+grid.spacing())//280)
        for col in range(max(cols,getattr(self,'_discovery_columns',0))):
            grid.setColumnStretch(col,1 if col<cols else 0);grid.setColumnMinimumWidth(col,0)
        self._discovery_columns=cols
        card_width=max(1,(width-(cols-1)*grid.spacing())//cols)
        for i,card in enumerate(self._discovery_cards):
            # Reserve wrapped title and action height as well as the fixed
            # poster; otherwise Qt can squeeze labels over the image.
            card.setMinimumHeight(max(card.layout().minimumSize().height(),card.layout().totalHeightForWidth(card_width)))
            self._discovery_grid.addWidget(card,i//cols,i%cols)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if not self.media_id:self.arrange_cards()
    def eventFilter(self,watched,event):
        if watched is self.scroll.viewport() and event.type()==QEvent.Resize and not self.media_id:
            if not getattr(self,'_arrange_pending',False):
                self._arrange_pending=True;QTimer.singleShot(0,self._arrange_after_resize)
        return super().eventFilter(watched,event)
    def _arrange_after_resize(self):
        self._arrange_pending=False;self.arrange_cards()
    def refilter(self,*_):
        if hasattr(self,'_last_result'):self.render(self._last_result)
    def play(self,path):
        from app.config import launch_video_file
        self.run(lambda:launch_video_file(path),lambda _:self.status.setText('Episode opened in your media player.'))
    def remind(self,row,title):
        from app.core.release_actions import remind
        mid=self.media_id
        self.run(lambda:remind(mid,row['episode'],row['airingAt'],title),lambda _:self.status.setText('Reminder saved. Anime Vault must be running to notify you.'))
    def _auto_grab(self,fid,episode):
        if QMessageBox.question(self,'Auto-Grab episode?',f'Search your configured source and download a verified match for episode {episode}? Ambiguous releases will not be downloaded.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        from app.core.release_actions import auto_grab
        mid=self.media_id
        self.run(lambda:auto_grab(fid,mid,episode,QThread.currentThread().isInterruptionRequested),self.status.setText)

    def import_media(self,media,button):
        button.setEnabled(False)
        def done(result):
            fid,added=result;button.setText('Added to Watching' if added else 'Already in library')
            if added:
                from app.ui.downloads import monitor
                from app.ui.artwork import artwork_loader
                artwork_loader().request(db.get_franchise(fid),allow_network=True)
                monitor().changed.emit()
        self.run(lambda:news.import_watching(media),done,lambda:button.setEnabled(True))

def open_release_news(parent,media_id=None):
    navigate(ReleaseNewsPage(parent,media_id))
