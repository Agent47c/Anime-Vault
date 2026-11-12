"""Delegate-painted Library rows; no per-anime labels/buttons/checkbox widgets."""
from PyQt5.QtCore import Qt,QAbstractTableModel,QModelIndex,QRectF,QEvent
from PyQt5.QtGui import QColor,QPainter,QPen,QPixmap,QFont,QPainterPath
from PyQt5.QtWidgets import QTableView,QStyledItemDelegate,QHeaderView,QAbstractItemView,QStyle,QShortcut
from app.config import COVERS_DIR
from app.ui.home_style import px,colors
from app.ui.components.virtual_posters import _Images,_Read


class LibraryRows(QAbstractTableModel):
    def __init__(self,view):super().__init__(view);self.view=view;self.rows=[]
    def rowCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.rows)
    def columnCount(self,parent=QModelIndex()):return 7
    def headerData(self,section,orientation,role=Qt.DisplayRole):
        if orientation==Qt.Horizontal and role==Qt.DisplayRole:return ('','COVER','TITLE','STATUS','SIZE','RATING','ACTION')[section]
    def flags(self,index):
        value=Qt.ItemIsEnabled|Qt.ItemIsSelectable
        return value|Qt.ItemIsUserCheckable if index.column()==0 else value
    def data(self,index,role=Qt.DisplayRole):
        if not index.isValid():return None
        row=self.rows[index.row()];column=index.column()
        if role==Qt.UserRole:return row
        if role==Qt.CheckStateRole and column==0:return Qt.Checked if row['id'] in self.view.page.selected_fids else Qt.Unchecked
        if role==Qt.ToolTipRole:return row.get('display_title','')+'\n'+(row.get('title_romaji') or '')
        if role in (Qt.DisplayRole,Qt.AccessibleTextRole):
            size=row.get('total_size_bytes') or 0;rating=row.get('user_rating')
            return ('','',row.get('display_title',''),row.get('storage_state','').replace('_',' ').title(),f'{size/1024**3:.1f} GB',f'{rating}/10' if rating else '—','Details')[column]
    def setData(self,index,value,role=Qt.EditRole):
        if not index.isValid() or role!=Qt.CheckStateRole or index.column()!=0:return False
        self.view.page._on_item_checked(self.rows[index.row()]['id'],value==Qt.Checked)
        self.dataChanged.emit(index,index,[Qt.CheckStateRole]);return True


class LibraryRowDelegate(QStyledItemDelegate):
    def editorEvent(self,event,model,option,index):
        if index.column()==0 and event.type() in (QEvent.MouseButtonPress,QEvent.MouseButtonRelease) and event.button()==Qt.LeftButton:
            if event.type()==QEvent.MouseButtonRelease:model.setData(index,Qt.Unchecked if index.data(Qt.CheckStateRole)==Qt.Checked else Qt.Checked,Qt.CheckStateRole)
            return True
        return super().editorEvent(event,model,option,index)
    def paint(self,painter,option,index):
        c=colors();row=index.data(Qt.UserRole);column=index.column();painter.save();painter.setClipRect(option.rect);painter.setRenderHint(QPainter.Antialiasing)
        active=option.state&(QStyle.State_Selected|QStyle.State_MouseOver)
        painter.fillRect(option.rect,QColor(c['raised'] if active else c['panel']))
        painter.setPen(QColor(c['line']));painter.drawLine(option.rect.bottomLeft(),option.rect.bottomRight())
        rect=option.rect.adjusted(10,8,-10,-8)
        if column==0:
            r=QRectF(rect.center().x()-9,rect.center().y()-9,18,18);checked=index.data(Qt.CheckStateRole)==Qt.Checked
            painter.setPen(QPen(QColor(c['coral'] if checked else c['line']),1.5));painter.setBrush(QColor(c['coral'] if checked else c['bg']));painter.drawRoundedRect(r,5,5)
            if checked:
                painter.setPen(QPen(QColor(c['on_coral']),2));x,y=r.x(),r.y();painter.drawLine(int(x+4),int(y+9),int(x+8),int(y+13));painter.drawLine(int(x+8),int(y+13),int(x+14),int(y+5))
        elif column==1:
            image=self.parent().poster(row)
            r=QRectF(rect.center().x()-20,rect.center().y()-29,40,58)
            path=QPainterPath();path.addRoundedRect(r,6,6);painter.setClipPath(path)
            if image is not None:painter.drawPixmap(r.toRect(),image)
            else:
                painter.fillRect(r,QColor(c['raised']));painter.setPen(QColor(c['text']));painter.drawText(r,Qt.AlignCenter,(row.get('display_title') or '?')[0])
        else:
            font=QFont('Plus Jakarta Sans');font.setPixelSize(px(13));font.setBold(column==2);painter.setFont(font)
            painter.setPen(QColor(c['text']))
            if column==2:
                title=painter.fontMetrics().elidedText(row.get('display_title',''),Qt.ElideRight,rect.width());painter.drawText(rect.adjusted(0,0,0,-rect.height()//2),Qt.AlignVCenter,title)
                font.setBold(False);font.setPixelSize(px(11));painter.setFont(font);painter.setPen(QColor(c['muted']))
                subtitle=row.get('title_romaji') or row.get('title_native') or ''
                painter.drawText(rect.adjusted(0,rect.height()//2,0,0),Qt.AlignVCenter,painter.fontMetrics().elidedText(subtitle,Qt.ElideRight,rect.width()))
            elif column in (3,6):
                r=QRectF(rect.left(),rect.center().y()-17,rect.width(),34)
                painter.setBrush(QColor(c['raised']));painter.setPen(QPen(QColor(c['line']),1));painter.drawRoundedRect(r,10,10)
                painter.setPen(QColor(c['ok'] if column==3 and row.get('storage_state')=='ON_DISK' else c['text']))
                painter.drawText(r,Qt.AlignCenter,painter.fontMetrics().elidedText(index.data(),Qt.ElideRight,rect.width()-8))
            else:painter.drawText(rect,Qt.AlignVCenter|Qt.AlignRight,index.data())
        if option.state&QStyle.State_HasFocus:
            painter.setClipping(False);painter.setPen(QPen(QColor(c['coral']),2));painter.setBrush(Qt.NoBrush);painter.drawRect(option.rect.adjusted(1,1,-2,-2))
        painter.restore()


class VirtualLibraryList(QTableView):
    def __init__(self,page):
        super().__init__();self.page=page;self.setObjectName('library_list');self.rows_model=LibraryRows(self);self.setModel(self.rows_model)
        self.setItemDelegate(LibraryRowDelegate(self));self.setEditTriggers(QAbstractItemView.NoEditTriggers);self.setSelectionBehavior(QAbstractItemView.SelectRows);self.setShowGrid(False);self.verticalHeader().hide();self.setMouseTracking(True);self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setMinimumHeight(500);self.setMaximumHeight(800)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed);self.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch)
        for col,width in ((0,44),(1,76),(3,170),(4,105),(5,90),(6,120)):self.setColumnWidth(col,px(width))
        self.images={};self.pending=set();self.signals=_Images();self.signals.ready.connect(self.image_ready)
        self.clicked.connect(self.activate)
        shortcut=QShortcut('Return',self);shortcut.activated.connect(lambda:self.page.card_clicked.emit(self.currentIndex().data(Qt.UserRole)['id']) if self.currentIndex().isValid() else None)
        self.refresh_style()
    def refresh_style(self):
        from app.ui.review_reference_style import list_style
        self.setStyleSheet(list_style().replace('QTableWidget','QTableView'));self.verticalHeader().setDefaultSectionSize(px(78))
    def present(self,rows):
        model=self.rows_model
        if [r['id'] for r in rows]==[r['id'] for r in model.rows]:
            model.rows=rows
            if rows:model.dataChanged.emit(model.index(0,0),model.index(len(rows)-1,6))
        else:
            model.beginResetModel();model.rows=rows;model.endResetModel()
        self.setColumnHidden(0,not self.page._selection_mode)
    def activate(self,index):
        if index.column()==6:self.page.card_clicked.emit(index.data(Qt.UserRole)['id'])
    def contextMenuEvent(self,event):
        index=self.indexAt(event.pos())
        if not index.isValid():return
        record=dict(index.data(Qt.UserRole));fid=record['id']
        self.page.show_series_menu(record,self,event.globalPos(),lambda:self.page._on_item_checked(fid,fid not in self.page.selected_fids))
        event.accept()
    def poster(self,row):
        key=(row.get('cover_filename'),row.get('_cover_version'))
        if key in self.images:return self.images[key]
        if key[0] and key not in self.pending:
            from app.ui.refresh import thumbnail_pool
            self.pending.add(key);thumbnail_pool().start(_Read(key,COVERS_DIR/key[0],self.signals))
        return None
    def image_ready(self,key,image):
        self.pending.discard(key)
        self.images[key]=QPixmap.fromImage(image).scaled(40,58,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation) if not image.isNull() else None
        while len(self.images)>96:self.images.pop(next(iter(self.images)))
        self.viewport().update()
