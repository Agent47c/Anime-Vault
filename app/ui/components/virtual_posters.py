"""Viewport-sized reusable HomePoster slots inside the existing Home scroller.

Records and selection belong to LibraryPage, never to a recycled widget. Image
decoding runs on a dedicated bounded pool. Stale completions cannot update a rebound slot.
"""
import math
from PyQt5.QtCore import QObject,QRunnable,pyqtSignal,QPoint,QTimer,Qt
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QSizePolicy
from app.config import COVERS_DIR
from app.ui.components.home_poster import HomePosterCard


class _Images(QObject):
    ready=pyqtSignal(object,object)


class _Read(QRunnable):
    def __init__(self,key,path,signals):
        super().__init__();self.key=key;self.path=path;self.signals=signals
    def run(self):
        from app.ui.refresh import cached_refresh_image
        try:image=cached_refresh_image(self.path)
        except (OSError,ValueError):image=QImage()
        self.signals.ready.emit(self.key,image)


class VirtualPosters(QObject):
    def __init__(self,page,fingerprint):
        super().__init__(page);self.page=page;self.fingerprint=fingerprint
        self.active=False;self.slots=[];self.records=[];self.images={};self.pending=set();self.revision=0
        self.signals=_Images();self.signals.ready.connect(self.image_ready)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(0);self.timer.timeout.connect(self.sync)
        page.page_scroll.verticalScrollBar().valueChanged.connect(self.schedule)
        page.grid_container.navigate_virtual_card=self.navigate

    def schedule(self,*_):
        if self.active and self.page.isVisible():self.timer.start()

    def set_records(self,records):
        if not self.active:
            while self.page.grid_layout.count():self.page.grid_layout.takeAt(0)
            self.slots=[card for _,card in self.page._card_pool.values()]
            for card in self.slots:card.hide()
        self.active=True;self.records=records;self.page._display_franchises=records;self.revision+=1
        self.reflow()

    def reflow(self):
        if self.page.view_mode!='grid':return
        page=self.page;margins=page.page_scroll.widget().layout().contentsMargins()
        page.grid_container.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred)
        width=max(1,page.page_scroll.viewport().width()-margins.left()-margins.right())
        self.cols=max(1,(width+20)//(HomePosterCard.CARD_WIDTH+20))
        self.width=max(1,(width-(self.cols-1)*20)//self.cols)
        # Text is capped to two lines in the existing card; equal row geometry
        # keeps the scrollbar stable as slots change identity.
        from app.ui.home_style import px
        self.row_height=round(self.width*1.5)+px(100)+20
        height=max(100,math.ceil(len(self.records)/self.cols)*self.row_height+30)
        page.grid_container.setMinimumHeight(height);page.views_stack.setMinimumHeight(height)
        page._grid_columns=self.cols
        self.sync()

    def sync(self):
        if not self.active or self.page.view_mode!='grid':return
        page=self.page;viewport=page.page_scroll.viewport()
        offset=page.grid_container.mapTo(viewport,QPoint()).y()
        top=max(0,-offset);bottom=max(0,viewport.height()-offset)
        first=max(0,top//self.row_height-1)
        last=min(math.ceil(len(self.records)/self.cols),max(first+2,bottom//self.row_height+2))
        indices=list(range(first*self.cols,min(len(self.records),last*self.cols)))
        # Above/below the viewport retain a small first row only; do not keep
        # allocating the whole collection when the hero/calendar occupies Home.
        if offset>viewport.height():indices=list(range(min(len(self.records),self.cols*2)))
        capacity=(math.ceil(viewport.height()/self.row_height)+4)*self.cols
        indices=indices[:capacity]
        signature=(tuple(indices),self.width,self.row_height,self.revision,page._selection_mode,tuple(sorted(page.selected_fids)))
        if getattr(self,'_visible_signature',None)==signature:return
        self._visible_signature=signature
        while len(self.slots)>capacity:
            self.slots.pop().deleteLater()
        current={card.franchise_id:card for card in self.slots}
        needed={self.records[i]['id'] for i in indices}
        available=[card for card in self.slots if card.franchise_id not in needed]
        visible=[]
        for index in indices:
            record=self.records[index];key=(record.get('cover_filename'),record.get('_cover_version'))
            prepared={**record,'_prepared_poster':self.images.get(key,QImage())}
            card=current.get(record['id'])
            if card is None:
                if available:card=available.pop();card.bind_record(prepared)
                else:
                    card=HomePosterCard(prepared,page.grid_container)
                    card.clicked.connect(page.card_clicked.emit);card.selection_changed.connect(page._on_item_checked)
                    self.slots.append(card)
                card._virtual_fingerprint=self.fingerprint(record)
            elif getattr(card,'_virtual_fingerprint',None)!=self.fingerprint(record):
                card.bind_record(prepared);card._virtual_fingerprint=self.fingerprint(record)
            card.set_card_width(self.width)
            card.resize(self.width,card.sizeHint().height())
            card.set_selected(record['id'] in page.selected_fids);card.set_selection_mode(page._selection_mode)
            card.update_facts(page._home_facts.get(record['id'],{}),page._download_badges.get(record['id']))
            card.move((index%self.cols)*(self.width+20),10+(index//self.cols)*self.row_height)
            card.show();visible.append(card)
            if key[0] and key not in self.images and key not in self.pending:
                from app.ui.refresh import thumbnail_pool
                self.pending.add(key);thumbnail_pool().start(_Read(key,COVERS_DIR/key[0],self.signals))
        for card in self.slots:
            if card not in visible:card.hide()
        page._cards=visible
        page._card_pool={card.franchise_id:(self.fingerprint(card.franchise_data),card) for card in visible}
        # A few screens of QImages are enough; the shared decoded-image cache
        # remains bounded independently and avoids repeat disk decoding.
        while len(self.images)>max(24,capacity*2):self.images.pop(next(iter(self.images)))

    def image_ready(self,key,image):
        self.pending.discard(key);self.images[key]=image
        for card in self.slots:
            record=card.franchise_data
            if (record.get('cover_filename'),record.get('_cover_version'))==key:
                record['_prepared_poster']=image;card._source_key=None
                card.poster_label.setPixmap(card._create_poster_pixmap())
        if image.isNull():
            from app.ui.artwork import artwork_loader
            record=next((row for row in self.records if (row.get('cover_filename'),row.get('_cover_version'))==key),None)
            if record:artwork_loader().request(record)

    def invalidate_artwork(self,fid,franchise):
        import time
        for record in self.records:
            if record['id']==fid:
                record['cover_filename']=franchise.get('cover_filename')
                record['_cover_version']=time.monotonic_ns()
        self.revision+=1;self.sync()

    def navigate(self,card,key):
        index=next((i for i,row in enumerate(self.records) if row['id']==card.franchise_id),0)
        target=index+{Qt.Key_Left:-1,Qt.Key_Right:1,Qt.Key_Up:-self.cols,Qt.Key_Down:self.cols}[key]
        if not 0<=target<len(self.records):return
        point=self.page.grid_container.mapTo(self.page.page_scroll.widget(),QPoint(0,(target//self.cols)*self.row_height))
        self.page.page_scroll.ensureVisible(point.x(),point.y()+self.row_height//2,0,self.row_height//2)
        self.sync()
        for slot in self.slots:
            if slot.franchise_id==self.records[target]['id']:slot.setFocus();break
