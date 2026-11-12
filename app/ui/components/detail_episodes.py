"""Virtualized episode rows with lazily prepared previews and real watch dates."""
from datetime import datetime
import time
from PyQt5 import sip
from PyQt5.QtCore import Qt,QSize,QTimer,QThread,pyqtSignal,QEvent,QPoint
from PyQt5.QtGui import QColor,QPainter,QPen,QPixmap,QFont
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QListView,QStyledItemDelegate,QApplication,QAbstractItemView,QMessageBox
from app.ui.pages.episode_page import EpisodeWorker,EpisodeModel
from app.ui.home_style import colors,px
from app.ui.io_task import track
from app.core.episode_preview import enrich_rows,load_preview


class DetailEpisodeWorker(EpisodeWorker):
    rich_ready=pyqtSignal(list,list)
    def __init__(self,fid):
        super().__init__(fid)
        self.ready.connect(self.enrich,Qt.DirectConnection)
    def enrich(self,rows,warnings):
        try:
            if not self.isInterruptionRequested():self.rich_ready.emit(enrich_rows(rows),warnings)
        except Exception as error:
            if not self.isInterruptionRequested():self.failed.emit(str(error))


class PreviewWorker(QThread):
    ready=pyqtSignal(str,object)
    def __init__(self,rows):super().__init__(QApplication.instance());self.rows=rows
    def run(self):
        for row in self.rows:
            if self.isInterruptionRequested():break
            try:data=load_preview(row,self.isInterruptionRequested)
            except Exception:data={'description':'Episode preview unavailable.'}
            if not self.isInterruptionRequested():self.ready.emit(row['path'],data)


class DetailEpisodeModel(EpisodeModel):
    def data(self,index,role=Qt.DisplayRole):
        if index.isValid() and role in (Qt.ToolTipRole,Qt.AccessibleDescriptionRole):
            row=self.rows[index.row()];stamp=row.get('last_played')
            return '\n'.join((row.get('episode_name') or row['title'],row.get('description') or 'Episode description unavailable.',
                'Last played '+datetime.fromtimestamp(stamp).strftime('%d %b %Y') if stamp else 'No watch date recorded',row['name']))
        return super().data(index,role)


class DetailEpisodeDelegate(QStyledItemDelegate):
    def sizeHint(self,option,index):return QSize(600,px(120))
    def paint(self,painter,option,index):
        row=index.data(Qt.UserRole);c=colors();painter.save();painter.setRenderHint(QPainter.Antialiasing)
        rect=option.rect.adjusted(0,4,-2,-4);last=index.data(Qt.UserRole+1)
        painter.setBrush(QColor(c['raised'] if last else c['panel']));painter.setPen(QPen(QColor(c['coral'] if last else c['line']),1))
        painter.drawRoundedRect(rect,12,12)
        thumb=rect.adjusted(10,10,0,-10);thumb.setWidth(px(150))
        image=row.get('pixmap')
        if image is not None and not image.isNull():
            scaled=image.scaled(thumb.size(),Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
            painter.drawPixmap(thumb,scaled,scaled.rect())
        else:
            painter.fillRect(thumb,QColor(c['bg']));painter.setPen(QColor(c['muted']))
            painter.drawText(thumb,Qt.AlignCenter,'No thumbnail available')
        x=thumb.right()+px(16);right=rect.right()-px(112);width=max(20,right-x)
        font=QFont('Plus Jakarta Sans');font.setPixelSize(px(15));font.setBold(True);painter.setFont(font);painter.setPen(QColor(c['text']))
        title=row.get('episode_name') or row['title']
        title=f"{row.get('subtitle','Episode')} · {title}"
        painter.drawText(x,rect.y()+px(28),painter.fontMetrics().elidedText(title,Qt.ElideRight,width))
        font.setBold(False);font.setPixelSize(px(12));painter.setFont(font);painter.setPen(QColor(c['muted']))
        description=' '.join((row.get('description') or 'Loading episode description…').split())
        painter.drawText(x,rect.y()+px(54),painter.fontMetrics().elidedText(description,Qt.ElideRight,width))
        stamp=row.get('last_played');date='Last played '+datetime.fromtimestamp(stamp).strftime('%d %b %Y') if stamp else 'No watch date recorded'
        font.setFamily('JetBrains Mono');font.setPixelSize(px(10));painter.setFont(font)
        painter.drawText(x,rect.y()+px(81),painter.fontMetrics().elidedText(date,Qt.ElideRight,width))
        button=rect.adjusted(rect.width()-px(102),px(34),-10,-px(34))
        painter.setBrush(QColor(c['coral'] if last else c['raised']));painter.setPen(Qt.NoPen);painter.drawRoundedRect(button,16,16)
        painter.setPen(QColor(c['on_coral'] if last else c['text']));painter.drawText(button,Qt.AlignCenter,'Resume' if last else 'Play')
        painter.restore()


class DetailEpisodes(QWidget):
    def __init__(self,fid,seasons,parent=None):
        super().__init__(parent);self.fid=fid;self._worker=None;self._previews=None;self._stopped=False;self._rows=[];self._requested=set();self._indexed=False;self._images=[]
        self.setObjectName('detail_episode_panel');box=QVBoxLayout(self);box.setContentsMargins(0,12,0,0);box.setSpacing(12)
        header=QHBoxLayout();title=QLabel('Episodes');title.setStyleSheet('font-size:20px;font-weight:600;');header.addWidget(title);header.addStretch()
        self.season_combo=QComboBox();self.season_combo.addItem('All seasons and movies',None)
        for season in seasons:self.season_combo.addItem(season.get('title_display') or f"Season {season.get('season_number') or '?'}",season['id'])
        self.season_combo.setMaximumWidth(320);self.season_combo.setAccessibleName('Episode release');self.season_combo.currentIndexChanged.connect(self.filter_rows);header.addWidget(self.season_combo);box.addLayout(header)
        self.status=QLabel('Open this section to load the local episodes.');self.status.setWordWrap(True);box.addWidget(self.status)
        self.model=DetailEpisodeModel(self);self.view=QListView();self.view.setModel(self.model);self.view.setItemDelegate(DetailEpisodeDelegate(self.view));self.view.setUniformItemSizes(True)
        self.view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel);self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.view.setMinimumHeight(px(240));self.view.setMaximumHeight(px(600));self.view.setMouseTracking(True)
        self.view.setAccessibleName('Episode thumbnails, descriptions and watch dates');self.view.viewport().installEventFilter(self)
        self.view.clicked.connect(self.click_row);self.view.activated.connect(self.play);box.addWidget(self.view)
        self.view.verticalScrollBar().valueChanged.connect(self.schedule_previews)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(150);self.timer.timeout.connect(self.load_visible)
        self.refresh_style()
    def refresh_style(self):
        c=colors();self.setStyleSheet(f'QWidget#detail_episode_panel{{background:{c["bg"]};border:none;}}');self.view.setStyleSheet(f'QListView{{background:{c["bg"]};border:none;outline:none;}}')
    def eventFilter(self,obj,event):
        if event.type()==QEvent.Paint and not self._stopped:
            if not self._indexed and self._worker is None:QTimer.singleShot(0,self.start)
            self.schedule_previews()
        return False
    def start(self):
        if self._worker is not None or self._stopped or self._indexed:return
        worker=DetailEpisodeWorker(self.fid);self._worker=worker;track(worker)
        def ready(rows,warnings):
            if sip.isdeleted(self) or self._stopped:return
            self._indexed=True;self._rows=rows;self.filter_rows();self.status.setText(f'{len(rows)} local video files'+(' · Some folders are unavailable' if warnings else '')+'. Descriptions require a verified release match; dates come from playback history.')
        worker.rich_ready.connect(ready)
        worker.failed.connect(lambda message:self.status.setText(message) if not sip.isdeleted(self) and not self._stopped else None)
        def finished():
            if not sip.isdeleted(self):self._worker=None
            worker.deleteLater()
        worker.finished.connect(finished);worker.start()
    def filter_rows(self):
        sid=self.season_combo.currentData();self.model.replace([r for r in self._rows if sid is None or r['season_id']==sid]);self.schedule_previews()
        self.view.setFixedHeight(px(min(600,max(240,len(self.model.rows)*120))))
    def schedule_previews(self,*args):
        if not self._stopped and not self.timer.isActive():self.timer.start()
    def load_visible(self):
        if self._stopped or self.view.visibleRegion().isEmpty() or self._previews is not None:return
        rows=[]
        top=self.view.indexAt(QPoint(5,5))
        first=top.row() if top.isValid() else max(0,self.view.verticalScrollBar().value()//px(120))
        for number in range(first,min(len(self.model.rows),first+self.view.viewport().height()//px(120)+2)):
            row=self.model.rows[number]
            if row['path'] not in self._requested and self.view.visualRect(self.model.index(number)).intersects(self.view.viewport().rect()):
                rows.append(dict(row));self._requested.add(row['path'])
                if len(rows)==3:break
        if not rows:return
        worker=PreviewWorker(rows);self._previews=worker;track(worker)
        def ready(path,data):
            if sip.isdeleted(self) or self._stopped:return
            if data.get('image') is not None:data['pixmap']=QPixmap.fromImage(data.pop('image'))
            data['preview_ready']=True
            for row in self._rows:
                if row['path']==path:row.update(data)
            if data.get('pixmap') is not None:
                self._images.append(path)
                if len(self._images)>48:
                    expired=self._images.pop(0);self._requested.discard(expired)
                    for row in self._rows:
                        if row['path']==expired:row.pop('pixmap',None);row.pop('preview_ready',None)
            for number,row in enumerate(self.model.rows):
                if row['path']==path:
                    index=self.model.index(number);self.model.dataChanged.emit(index,index)
        def done():
            if not sip.isdeleted(self):self._previews=None;self.schedule_previews()
            worker.deleteLater()
        worker.ready.connect(ready);worker.finished.connect(done);worker.start()
    def click_row(self,index):
        if self.view.mapFromGlobal(self.cursor().pos()).x()>=self.view.viewport().width()-px(112):self.play(index)
    def play(self,index):
        row=index.data(Qt.UserRole)
        if not row:return
        from app.config import launch_video_file,set_last_franchise_id
        try:launch_video_file(row['path']);set_last_franchise_id(self.fid);row['last_played']=int(time.time());self.model.mark_played(row['path'])
        except (OSError,ValueError) as error:QMessageBox.information(self,'Episode unavailable',str(error))
    def stop(self):
        self._stopped=True;self.timer.stop()
        self._requested={r['path'] for r in self._rows if r.get('preview_ready')}
        for worker in (self._worker,self._previews):
            if worker is not None and not sip.isdeleted(worker) and worker.isRunning():worker.requestInterruption()
    def hideEvent(self,event):
        self.stop();super().hideEvent(event)
    def showEvent(self,event):
        self._stopped=False;self.schedule_previews();super().showEvent(event)
