"""Searchable, poster-based series grouping with a separate confirmation."""
from PyQt5.QtCore import Qt,QAbstractListModel,QModelIndex,QSize,QSortFilterProxyModel,pyqtSignal,QEvent
from PyQt5.QtGui import QImage,QIcon,QPixmap,QPainter,QPainterPath,QPen,QColor
from PyQt5.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLineEdit,QLabel,QListView,QCheckBox,QMessageBox,QStyledItemDelegate,QStyle,QStyleOptionViewItem
from app import db
from app.config import COVERS_DIR
from app.core import series_grouping
from app.ui.components.workflow import button,text,chrome,card
from app.ui.dialogs.drawer import DrawerDialog
from app.ui.io_task import start
from app.ui.navigation import navigate


def load_choices(fid):
    records={row['id']:row for row in db.get_all_franchises()};own=db.get_series(fid)
    if not own:raise ValueError('This library entry no longer exists.')
    choices=[];images={}
    for group in db.get_series_library():
        if set(own['series_member_ids']).intersection(group['series_member_ids']):continue
        item=dict(group);members=[records[i] for i in group['series_member_ids']]
        item['_search']=' '.join((r.get(k) or '') for r in members for k in ('display_title','title_en','title_romaji','title_native'))
        import json
        try:media=json.loads(group.get('metadata_json') or '{}')
        except (TypeError,ValueError):media={}
        item['_state']='Announced · Not released' if isinstance(media,dict) and media.get('status')=='NOT_YET_RELEASED' else group.get('storage_state','').replace('_',' ').title()
        choices.append(item)
        if group.get('cover_filename'):
            image=QImage(str(COVERS_DIR/group['cover_filename']))
            if not image.isNull():
                image=image.scaled(88,132,Qt.KeepAspectRatio,Qt.SmoothTransformation)
                image.setDevicePixelRatio(2);images[group['id']]=image
    return choices,images


class GroupChoiceDelegate(QStyledItemDelegate):
    """Row clicks include the entry; checkbox clicks toggle it exactly once."""
    def paint(self,painter,option,index):
        super().paint(painter,option,index)
        if index.data(Qt.CheckStateRole)!=Qt.Checked:return
        from PyQt5.QtWidgets import QApplication
        from app.ui.theme import COLORS
        option=QStyleOptionViewItem(option);self.initStyleOption(option,index)
        rect=option.widget.style().subElementRect(QStyle.SE_ItemViewItemCheckIndicator,option,option.widget)
        palette=COLORS.get(QApplication.instance().property('animevaultTheme'),COLORS['dark'])
        painter.save();painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(palette['bg_primary']),2.2,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
        path=QPainterPath();path.moveTo(rect.left()+rect.width()*.25,rect.top()+rect.height()*.5)
        path.lineTo(rect.left()+rect.width()*.43,rect.top()+rect.height()*.68)
        path.lineTo(rect.left()+rect.width()*.76,rect.top()+rect.height()*.31)
        painter.drawPath(path);painter.restore()
    def editorEvent(self,event,model,option,index):
        if event.type()==QEvent.MouseButtonRelease and event.button()==Qt.LeftButton and index.isValid():
            option=QStyleOptionViewItem(option);self.initStyleOption(option,index)
            style=option.widget.style()
            indicator=style.subElementRect(QStyle.SE_ItemViewItemCheckIndicator,option,option.widget)
            checked=index.data(Qt.CheckStateRole)==Qt.Checked
            value=Qt.Unchecked if indicator.contains(event.pos()) and checked else Qt.Checked
            option.widget.setCurrentIndex(index)
            return model.setData(index,value,Qt.CheckStateRole)
        return super().editorEvent(event,model,option,index)


class GroupModel(QAbstractListModel):
    def __init__(self,parent=None):
        super().__init__(parent);self.rows=[];self.checked=set();self.icons={}
        from app.ui.icons import icon
        from PyQt5.QtWidgets import QApplication
        from app.ui.theme import COLORS
        palette=COLORS.get(QApplication.instance().property('animevaultTheme'),COLORS['dark'])
        self.fallback=icon('library',palette['text_secondary'])
    def rowCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.rows)
    def data(self,index,role=Qt.DisplayRole):
        if not index.isValid():return
        row=self.rows[index.row()]
        if role==Qt.DisplayRole:
            count=row.get('release_count',1)
            return row['display_title']+'\n'+str(count)+(' library entry · ' if count==1 else ' library entries · ')+row.get('_state',row.get('storage_state','').replace('_',' ').title())
        if role==Qt.DecorationRole:return self.icons.get(row['id'],self.fallback)
        if role==Qt.CheckStateRole:return Qt.Checked if row['id'] in self.checked else Qt.Unchecked
        if role==Qt.UserRole:return row
        if role==Qt.UserRole+1:return row['_search']
        if role==Qt.ToolTipRole:return row['display_title']+'\n'+row['_search']
        if role==Qt.SizeHintRole:return QSize(250,88)
    def flags(self,index):return Qt.ItemIsEnabled|Qt.ItemIsSelectable|Qt.ItemIsUserCheckable
    def setData(self,index,value,role=Qt.EditRole):
        if role!=Qt.CheckStateRole or not index.isValid():return False
        fid=self.rows[index.row()]['id']
        if value==Qt.Checked:self.checked.add(fid)
        else:self.checked.discard(fid)
        self.dataChanged.emit(index,index,[role]);return True


class GroupReview(DrawerDialog):
    grouped=pyqtSignal(int)
    def __init__(self,plan,parent=None):
        super().__init__(parent);self.plan=plan
        body,self.confirm=chrome(self,'Confirm series grouping','Review the entries that will appear under one anime card.','統合','Confirm grouping',self.apply)
        body.addWidget(text('Main card: '+plan['title'],'workflow_row_title'))
        for row in plan['records']:
            frame,box=card();box.addWidget(text(row['display_title'],'workflow_row_title'))
            box.addWidget(text('Main series' if row['id']==plan['target'] else 'Season / arc entry'))
            import json
            try:media=json.loads(row.get('metadata_json') or '{}')
            except (TypeError,ValueError):media={}
            if isinstance(media,dict) and media.get('status'):box.addWidget(text(series_grouping.release_status(media['status'])))
            body.addWidget(frame)
        body.addWidget(text('No files move or get deleted. Each record keeps its paths, notes, rating and watch history. Known announced releases appear as metadata-only season entries.'))
        self.reviewed=QCheckBox('These entries belong to the same anime');body.addWidget(self.reviewed)
        self.confirm.setEnabled(False);self.reviewed.toggled.connect(self.confirm.setEnabled)
        body.addStretch()
    def apply(self):
        if self.reviewed.isChecked():start(self,lambda:series_grouping.apply(self.plan),self.applied)
    def applied(self,fid):self.grouped.emit(fid);self.accept()
    def reject(self):
        if getattr(self,'_apply_worker',None) and self._apply_worker.isRunning():return
        super().reject()


class GroupSeriesPage(QDialog):
    grouped=pyqtSignal(int)
    dispose_on_leave=True
    def __init__(self,fid,parent=None):
        super().__init__(parent);self.fid=fid;self.target=None;self.setWindowTitle('Group seasons and arcs')
        box=QVBoxLayout(self);box.setContentsMargins(28,20,28,24);box.setSpacing(16)
        heading=text('Group seasons and arcs','download_heading');box.addWidget(heading)
        box.addWidget(text('Click an anime to select and include it. Check additional season entries to include them; uncheck to remove them. The highlighted anime is the main series.'))
        row=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Search English, Romaji or Japanese titles');self.search.setClearButtonEnabled(True)
        row.addWidget(self.search,1);row.addWidget(button('Search',self.filter));box.addLayout(row)
        self.search.returnPressed.connect(self.filter);self.search.textChanged.connect(self.filter)
        self.model=GroupModel(self);self.proxy=QSortFilterProxyModel(self);self.proxy.setSourceModel(self.model)
        self.proxy.setFilterRole(Qt.UserRole+1);self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.list=QListView();self.list.setObjectName('group_series_choices');self.list.setModel(self.proxy);self.list.setIconSize(QSize(44,66));self.list.setUniformItemSizes(True)
        self.list.setItemDelegate(GroupChoiceDelegate(self.list))
        self.list.setAccessibleName('Choose a main series and check additional season entries');box.addWidget(self.list,1)
        self.list.selectionModel().currentChanged.connect(self.highlight)
        self.model.dataChanged.connect(self.checked_changed)
        self.status=text('Loading your library…');box.addWidget(self.status)
        self.review=button('Review grouping',self.review_group,True);self.review.setEnabled(False);box.addWidget(self.review,0,Qt.AlignRight)
        box.addWidget(button('Reset manual grouping for this series',self.reset),0,Qt.AlignLeft)
        start(self,lambda:load_choices(fid),self.loaded)
    def loaded(self,result):
        rows,images=result;self.model.beginResetModel();self.model.rows=rows
        self.model.icons={fid:QIcon(QPixmap.fromImage(image)) for fid,image in images.items()};self.model.endResetModel()
        self.status.setText(f'{len(rows)} series available. Select the main card to continue.');self.filter()
    def filter(self,*_):
        self.proxy.setFilterFixedString(self.search.text().strip())
        if not self.proxy.rowCount():self.status.setText('No matching series. Try another title. Existing selections are kept.')
    def highlight(self,current,previous):
        if current.isValid():self.target=current.data(Qt.UserRole)['id']
        self.update_summary()
    def checked_changed(self,*_):
        current=self.list.currentIndex()
        current_id=current.data(Qt.UserRole)['id'] if current.isValid() else None
        if current_id in self.model.checked:self.target=current_id
        elif self.target not in self.model.checked:
            self.target=next((row['id'] for row in self.model.rows if row['id'] in self.model.checked),None)
        if self.target is None:
            self.list.setCurrentIndex(QModelIndex());self.list.clearSelection()
        elif self.target!=current_id:
            source=next(i for i,row in enumerate(self.model.rows) if row['id']==self.target)
            visible=self.proxy.mapFromSource(self.model.index(source,0))
            if visible.isValid():self.list.setCurrentIndex(visible)
        self.update_summary()
    def update_summary(self,*_):
        row=next((r for r in self.model.rows if r['id']==self.target),None)
        self.review.setEnabled(bool(row))
        if row:self.status.setText('Main series: '+row['display_title']+f' · {len(self.model.checked-{self.target})} additional entries checked')
        else:self.status.setText('Select an anime or check its box to continue.')
    def review_group(self):
        if self.target is None:return
        target=self.target;extra=sorted(self.model.checked-{target})
        def show(plan):
            if getattr(self,'_embedded',False) and not self.isVisible():return
            dialog=GroupReview(plan,self);dialog.grouped.connect(self.done_group);navigate(dialog)
        start(self,lambda:series_grouping.preview(self.fid,target,extra),show)
    def done_group(self,fid):self.grouped.emit(fid);self.accept()
    def reset(self):
        if QMessageBox.question(self,'Reset manual grouping?','Separate manually grouped records? Files and verified provider season links stay unchanged.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        start(self,lambda:db.reset_manual_grouping(self.fid),lambda _:self.done_group(self.fid))
    def reject(self):
        if getattr(self,'_apply_worker',None) and self._apply_worker.isRunning():return
        super().reject()
