"""Home poster presentation, retaining the existing card/hover contract."""
import json,math
from PyQt5.QtCore import Qt,pyqtSignal,QRectF,QPointF
from PyQt5.QtGui import QColor,QPainter,QPainterPath,QPen,QPixmap,QPolygonF
from PyQt5.QtWidgets import QAbstractButton,QLabel,QProgressBar,QHBoxLayout,QMenu
from app.config import COVERS_DIR
from app.ui.components.poster_card import PosterCard
from app.ui.refresh import refresh_pixmap,refresh_image_exists
from app.ui.home_style import colors,px


class SelectionBox(QAbstractButton):
    def __init__(self,parent=None):
        super().__init__(parent);self.setCheckable(True);self.setFixedSize(44,44);self.setCursor(Qt.PointingHandCursor)
    def paintEvent(self,event):
        c=colors();p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        rect=QRectF(8,8,22,22);p.setPen(QPen(QColor(c['coral'] if self.isChecked() else c['muted']),1.5))
        p.setBrush(QColor(c['coral']) if self.isChecked() else QColor(20,18,29,210));p.drawRoundedRect(rect,6,6)
        if self.isChecked():
            p.setPen(QPen(QColor(c['on_coral']),2.2,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
            path=QPainterPath();path.moveTo(13,19);path.lineTo(17,23);path.lineTo(25,15);p.drawPath(path)
        if self.hasFocus():p.setBrush(Qt.NoBrush);p.setPen(QPen(QColor(c['coral']),2));p.drawRoundedRect(rect.adjusted(-3,-3,3,3),8,8)


class HomePosterCard(PosterCard):
    selection_changed=pyqtSignal(int,bool)
    CARD_WIDTH=220
    POSTER_HEIGHT=330
    def _setup_ui(self):
        super()._setup_ui();self.setFocusPolicy(Qt.StrongFocus);self.setProperty('homePoster',True)
        self.title_label.parentWidget().setStyleSheet('background:transparent;')
        self.poster_slot.setStyleSheet('background:transparent;')
        c=colors();self.title_label.setStyleSheet(f"color:{c['text']};font-family:'Plus Jakarta Sans';font-size:13px;font-weight:600;")
        self.selection_box=SelectionBox(self.poster_label);self.selection_box.move(0,0)
        self.selection_box.hide()
        self.selection_box.setAccessibleName('Select '+self.franchise_data.get('display_title','anime'))
        self.selection_box.toggled.connect(lambda checked:self.selection_changed.emit(self.franchise_id,checked))
        self.coverage_bar=QProgressBar();self.coverage_bar.setRange(0,1000);self.coverage_bar.setTextVisible(False);self.coverage_bar.setFixedHeight(3)
        self.layout().insertWidget(1,self.coverage_bar)
        self.subline_label.setObjectName('home_meta');self.subline_label.setStyleSheet('font-family:"JetBrains Mono";font-size:11px;')
        self.download_label=QLabel();self.download_label.setStyleSheet(f"color:{c['coral']};font-family:'JetBrains Mono';font-size:11px;")
        meta=QHBoxLayout();meta.setContentsMargins(2,0,2,0);meta.addWidget(self.subline_label);meta.addStretch();meta.addWidget(self.download_label)
        # The old subline is not inside the original card layout, so it can be
        # safely placed beside the live download/storage label.
        self.layout().addLayout(meta)
        # The base card creates this label without a parent. Showing it before
        # adding the layout briefly opens a native captioned window per poster.
        self.subline_label.show()
        self.update_facts({})
        self.restyle()

    def restyle(self):
        c=colors()
        for widget in (self.title_label,self.subline_label,self.download_label):widget.setProperty('animevaultOwnScaledStyle',True)
        self.title_label.setStyleSheet(f'background:transparent;color:{c["text"]};font-family:"Plus Jakarta Sans";font-size:{px(13)}px;font-weight:600;')
        self.subline_label.setStyleSheet(f'background:transparent;color:{c["muted"]};font-family:"JetBrains Mono";font-size:{px(11)}px;')
        self._status_color=None;self.update_facts(getattr(self,'facts',{}),getattr(self,'badge',None));self._update_title()

    def _create_poster_pixmap(self):
        ratio=self.devicePixelRatioF();pix=QPixmap(round(self.CARD_WIDTH*ratio),round(self.POSTER_HEIGHT*ratio));pix.setDevicePixelRatio(ratio);pix.fill(Qt.transparent)
        p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.SmoothPixmapTransform)
        path=QPainterPath();path.addRoundedRect(QRectF(0,0,self.CARD_WIDTH,self.POSTER_HEIGHT),12,12);p.setClipPath(path)
        cover=self.franchise_data.get('cover_filename')
        key=(cover,self.franchise_data.get('_cover_version'))
        if not hasattr(self,'_source_poster') or getattr(self,'_source_key',None)!=key:
            self._source_key=key
            image=self.franchise_data.get('_prepared_poster')
            self._source_poster=QPixmap.fromImage(image) if image is not None else refresh_pixmap(COVERS_DIR/cover) if cover and refresh_image_exists(COVERS_DIR/cover) else QPixmap()
        if not self._source_poster.isNull():
            scaled=self._source_poster.scaled(round(self.CARD_WIDTH*ratio),round(self.POSTER_HEIGHT*ratio),Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation);scaled.setDevicePixelRatio(ratio)
            p.drawPixmap(round((self.CARD_WIDTH-scaled.width()/ratio)/2),round((self.POSTER_HEIGHT-scaled.height()/ratio)/2),scaled)
        else:
            c=colors();p.fillRect(pix.rect(),QColor(c['raised']));p.setPen(QColor(c['text']))
            font=self.font();font.setPixelSize(56);font.setBold(True);p.setFont(font)
            p.drawText(QRectF(0,0,self.CARD_WIDTH,self.POSTER_HEIGHT),Qt.AlignCenter,(self.franchise_data.get('display_title') or '?')[0])
        try:media=json.loads(self.franchise_data.get('metadata_json') or '{}') or {}
        except (TypeError,ValueError):media={}
        score=media.get('averageScore');rating=self.franchise_data.get('user_rating')
        if score or rating:
            label=f'{score/10:.1f}' if score else f'{rating}/10'
            c=colors();p.setClipping(False);p.setPen(Qt.NoPen);p.setBrush(QColor(15,13,23,225));p.drawRoundedRect(QRectF(self.CARD_WIDTH-72,9,63,23),11,11)
            star=QPolygonF([QPointF(self.CARD_WIDTH-59+math.cos(-math.pi/2+n*math.pi/5)*(4.5 if n%2==0 else 2),20+math.sin(-math.pi/2+n*math.pi/5)*(4.5 if n%2==0 else 2)) for n in range(10)])
            p.setBrush(QColor(c['amber']));p.drawPolygon(star)
            font=self.font();font.setPixelSize(11);p.setFont(font);p.setPen(QColor(c['amber']));p.drawText(QRectF(self.CARD_WIDTH-50,9,39,23),Qt.AlignCenter,label)
        p.end();return pix

    def bind_record(self,record):
        """Rebind a visible slot; no signals/widgets are reconstructed."""
        self._lift.stop();self.poster_label.move(0,self.HOVER_LIFT)
        self.franchise_data=record;self.franchise_id=record['id']
        self._raw_title=record.get('display_title') or 'Unknown title'
        self._source_key=None
        self.poster_label.setPixmap(self._create_poster_pixmap())
        self._update_title();self._setup_tooltip()
        self.selection_box.setAccessibleName('Select '+self._raw_title)
        self.setAccessibleName(self._raw_title)

    def update_facts(self,facts,badge=None):
        self.facts=facts;self.badge=badge;found=facts.get('found',0);total=facts.get('total',0)
        self.subline_label.setText(f'{found} / {total} eps' if facts.get('verified_total') else f'{found} local eps' if found else self.franchise_data.get('storage_state','NOT_DOWNLOADED').replace('_',' ').title())
        self.coverage_bar.setValue(round(found/total*1000) if total else 0)
        self.coverage_bar.setAccessibleName(f'{found} local episodes, {total} known episodes' if total else 'Episode coverage unverified')
        label=badge.get('label') if badge else 'On disk' if self.franchise_data.get('storage_state')=='ON_DISK' else 'Partial' if self.franchise_data.get('storage_state')=='PARTIALLY_ON_DISK' else ''
        self.download_label.setText(label or '');self.download_label.setToolTip(label or '')
        c=colors();color=c['coral'] if badge else c['ok'] if label=='On disk' else c['muted']
        if getattr(self,'_status_color',None)!=(color,px(11)):
            self._status_color=(color,px(11));self.download_label.setStyleSheet(f'color:{color};font-family:"JetBrains Mono";font-size:{px(11)}px;')
        if badge:
            self.coverage_bar.setValue(round(badge['progress']*1000));self.coverage_bar.setAccessibleName(label+' · '+self.coverage_bar.accessibleName())

    def set_selected(self,selected):
        self.selection_box.blockSignals(True);self.selection_box.setChecked(selected);self.selection_box.blockSignals(False)
        self.setProperty('selected',selected);self.update()

    def set_selection_mode(self,enabled):
        self._selection_mode=bool(enabled)
        self.selection_box.setVisible(enabled)

    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton and getattr(self,'_selection_mode',False):
            self.selection_box.toggle();event.accept()
        else:super().mousePressEvent(event)

    def contextMenuEvent(self,event):
        owner=self.parentWidget()
        while owner is not None and not hasattr(owner,'show_series_menu'):owner=owner.parentWidget()
        if owner is not None:
            fid=self.franchise_id
            owner.show_series_menu(dict(self.franchise_data),self,event.globalPos(),lambda:owner._on_item_checked(fid,fid not in owner.selected_fids))
            event.accept();return
        menu=QMenu(self)
        action=menu.addAction('Unselect' if self.selection_box.isChecked() else 'Select')
        action.triggered.connect(self.selection_box.toggle)
        menu.exec_(event.globalPos())
        event.accept()

    def keyPressEvent(self,event):
        if event.key() in (Qt.Key_Return,Qt.Key_Enter):self.clicked.emit(self.franchise_id);event.accept()
        elif event.key()==Qt.Key_Space:self.selection_box.toggle();event.accept()
        elif event.key() in (Qt.Key_Left,Qt.Key_Right,Qt.Key_Up,Qt.Key_Down):
            navigate=getattr(self.parentWidget(),'navigate_virtual_card',None)
            if navigate:
                navigate(self,event.key());event.accept();return
            layout=self.parentWidget().layout() if self.parentWidget() else None
            if layout and hasattr(layout,'getItemPosition'):
                index=layout.indexOf(self);row,column,_,_=layout.getItemPosition(index)
                dr,dc={Qt.Key_Left:(0,-1),Qt.Key_Right:(0,1),Qt.Key_Up:(-1,0),Qt.Key_Down:(1,0)}[event.key()]
                item=layout.itemAtPosition(row+dr,column+dc)
                if item and item.widget():
                    target=item.widget();target.setFocus()
                    ancestor=self.parentWidget()
                    while ancestor:
                        if hasattr(ancestor,'ensureWidgetVisible'):ancestor.ensureWidgetVisible(target);break
                        ancestor=ancestor.parentWidget()
            event.accept()
        else:super().keyPressEvent(event)
