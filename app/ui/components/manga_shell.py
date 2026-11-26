"""Master-reference shell adapters. All commands use existing application routes."""
from app.ui.manga_style import set_material
from PyQt5.QtCore import Qt,QSize,pyqtSignal
from PyQt5.QtGui import QPainter,QColor
from PyQt5.QtWidgets import QFrame,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QLineEdit,QSizePolicy
from app.ui.icons import app_icon, icon
from app.ui.manga_style import controls_qss,shadow,COLORS


class ApiStatusDot(QLabel):
    clicked=pyqtSignal()
    def __init__(self):
        super().__init__();self.connected=False;self.setFixedSize(18,24)
        self.setFocusPolicy(Qt.StrongFocus);self.setCursor(Qt.PointingHandCursor)
        self.set_status(dict(services={},description='AniList: Status unchecked\nJikan: Status unchecked'))
    def set_status(self,result):
        services=result['services'];self.connected=services.get('AniList') is True and services.get('Jikan') is True
        message=result['description']+'\nClick to check APIs'
        self.set_connection(self.connected,message)
    def set_connection(self,connected,message):
        self.connected=bool(connected)
        self.setToolTip(message);self.setAccessibleName(message);self.update()
    def set_checking(self):self.set_status(dict(services={},description='Checking AniList and Jikan…'))
    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:self.clicked.emit()
        else:super().mousePressEvent(event)
    def keyPressEvent(self,event):
        if event.key() in (Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space):self.clicked.emit()
        else:super().keyPressEvent(event)
    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing);painter.setPen(Qt.NoPen)
        painter.setBrush(QColor('#087b60' if self.connected else '#df2545'));painter.drawRoundedRect(self.width()//2-5,self.height()//2-5,10,10,3,3);painter.end()


class MangaHeader(QFrame):
    def __init__(self,host):
        super().__init__();self.host=host;self.setObjectName('manga_header');self.setFixedHeight(70)
        row=QHBoxLayout(self);row.setContentsMargins(20,10,24,10);row.setSpacing(14)
        self.mark=QLabel();self.mark.setFixedSize(52,50);self.mark.setAlignment(Qt.AlignCenter)
        self.mark.setPixmap(app_icon().pixmap(50,50))
        set_material(self.mark,'background:transparent;');row.addWidget(self.mark);shadow(self.mark)
        self.search=QLineEdit();self.search.setAccessibleName('Search library');self.search.setPlaceholderText('Search by English title');self.search.setClearButtonEnabled(True);self.search.setMaximumWidth(720);self.search.setMinimumWidth(260)
        self.search.setProperty('mangaOwnPlaceholder',True)
        self.search.addAction(icon('search',COLORS['muted']),QLineEdit.LeadingPosition);self.search.textChanged.connect(host.top_search_input.setText);self.search.returnPressed.connect(host.library_page.focus_search_results)
        host.top_search_input.textChanged.connect(self.sync_search);row.addWidget(self.search,1);row.addStretch()
        self.refresh=QPushButton('Refresh');self.refresh.setProperty('mangaDisabledRaised',True);self.refresh.setMinimumWidth(135);self.refresh.setIcon(icon('refresh',COLORS['text']));self.refresh.setMenu(host.refresh_button.menu());row.addWidget(self.refresh)
        add=QPushButton('Add Anime');add.setMinimumWidth(176);add.setProperty('accent',True);add.setIcon(icon('plus',COLORS['text']));add.clicked.connect(host._open_custom_entry_dialog);row.addWidget(add)
        more=QPushButton();more.setObjectName('manga_more');more.setFixedWidth(44);more.setIcon(icon('list',COLORS['text']));more.setMenu(host.home_header.options.menu());more.setAccessibleName('More actions');more.setToolTip('More actions');row.addWidget(more)
        self.api_status=ApiStatusDot();self.api_status.clicked.connect(host._initial_online_check);row.addWidget(self.api_status)
        more.menu().anchor_widget=more
        self.refresh.menu().anchor_widget=self.refresh
        for button in (self.refresh,add,more):button.setCursor(Qt.PointingHandCursor);shadow(button,15,5)
        self.setProperty('animevaultThemeScope',True);self.refresh_home_style()
    def refresh_home_style(self):
        from app.ui.home_style import px
        from app.ui.manga_style import manga_colors
        from PyQt5.QtGui import QPalette
        colors=manga_colors()
        self.refresh.setIcon(icon('refresh',colors['text']))
        self.findChild(QPushButton,'manga_more').setIcon(icon('list',colors['text']))
        self.setFixedHeight(px(70));set_material(self,controls_qss()+'QFrame#manga_header{background:#eef0f5;border-bottom:1px solid #b8bec9;} QPushButton#manga_more::menu-indicator{image:none;width:0;height:0;}')
        palette=self.search.palette()
        palette.setColor(QPalette.PlaceholderText,QColor(colors['muted']))
        self.search.setPalette(palette)
        from app.ui.components.neumorphic import install
        install(self.search,inset=True)
        for button in self.findChildren(QPushButton):install(button)
    def sync_search(self,text):
        if self.search.text()!=text:self.search.blockSignals(True);self.search.setText(text);self.search.blockSignals(False)


from app.ui.components.manga_navigation import RailMotion


class MangaRail(RailMotion,QFrame):
    def __init__(self,host):
        super().__init__();self.setObjectName('manga_rail');self.setFixedWidth(94);self.buttons={};self.badges={}
        column=QVBoxLayout(self);column.setContentsMargins(18,18,18,18);column.setSpacing(14)
        for title,name,index in [('Library','library',0),('Updates','updates',2),('Downloads','downloads',5),('Organizer','organizer',1),('Storage','storage',3),('Settings','settings',4)]:
            button=QPushButton();button.setFixedSize(56,56);button.setIconSize(QSize(24,24));button.setCheckable(True);button.setAccessibleName(title);button.setToolTip(title);button.clicked.connect(lambda checked=False,i=index:host._on_nav_clicked(i));button.setProperty('iconName',name);self.buttons[index]=button;column.addWidget(button);shadow(button,18,7)
            if index in (2,5):
                badge=QLabel(button);badge.setAlignment(Qt.AlignCenter);badge.setAttribute(Qt.WA_TransparentForMouseEvents);set_material(badge,'background:#ff2e93;color:#0a0a0a;border:none;border-radius:7px;font:700 10px Inter;');badge.hide();self.badges[index]=badge
        column.addSpacing(14)
        for label,state in [('Watching','WATCHING'),('Plan to watch','PLAN_TO_WATCH'),('Watched','WATCHED'),('Dropped','DROPPED'),('Watched, removed','WATCHED_REMOVED')]:
            button=QPushButton('●');button.setFixedSize(48,44);button.setAccessibleName(label);button.setToolTip(label);button.clicked.connect(lambda checked=False,s=state:host._on_collection_clicked(s));column.addWidget(button)
            set_material(button,'background:#111217;color:#ff2e93;border:1px solid black;border-radius:10px;')
        column.addStretch();drive=QPushButton();drive.setIcon(icon('storage',COLORS['coral']));drive.setToolTip('Review storage');drive.setAccessibleName('Review storage');drive.clicked.connect(lambda:host._on_nav_clicked(3));column.addWidget(drive)
        self.collection_buttons=[]
        # Keep existing collection actions and expose their labels when the rail opens.
        labels=['Watching','Plan to watch','Watched','Dropped','Watched, removed']
        collection=[b for b in self.findChildren(QPushButton) if b.text()=='●']
        for button,label in zip(collection,labels):
            button.setText('');button.setIcon(icon('library',COLORS['coral']));button.setProperty('railLabel',label)
            set_material(button,'QPushButton{background:white;color:#111217;border:1px solid #c4c9d4;border-radius:10px;}QPushButton:checked{background:#ffe0ef;color:#c4005f;border-color:#ff2e93;}')
            self.collection_buttons.append(button)
        for button,state in zip(collection,['WATCHING','PLAN_TO_WATCH','WATCHED','DROPPED','WATCHED_REMOVED']):button.setCheckable(True);button.setProperty('watchStatus',state)
        for button in self.buttons.values():button.setProperty('railLabel',button.accessibleName())
        self.setup_motion([list(self.buttons.values()),self.collection_buttons])
        set_material(self,controls_qss()+'QFrame#manga_rail{background:#eef0f5;border-right:1px solid #c4c9d4;} QPushButton{padding:0;border-radius:14px;}')
        for button in self.findChildren(QPushButton):button.setCursor(Qt.PointingHandCursor)
    def activate(self,index):
        from app.ui.manga_style import manga_colors
        colors=manga_colors()
        for key,button in self.buttons.items():
            button.setChecked(key==index);button.setIcon(icon(button.property('iconName'),colors['coral'] if key==index else colors['muted']))
        if self._expanded:self._blur_group(None)
    def set_count(self,index,count):
        badge=self.badges[index];text=str(count);badge.setText(text);badge.setGeometry(56-max(18,len(text)*7+6),2,max(18,len(text)*7+6),16);badge.setVisible(count>0)
        name='Updates' if index==2 else 'Downloads';self.buttons[index].setToolTip(f'{name} · {count}');self.buttons[index].setAccessibleName(f'{name}, {count}')
    def set_collection_counts(self,counts):
        for button in self.collection_buttons:
            count=int(counts.get(button.property('watchStatus'),0))
            button.setProperty('collectionCount',count)
            label=button.property('railLabel')
            button.setText(f'{label}  {count}' if self.width()>155 else '')
            button.setToolTip(f'{label} · {count}');button.setAccessibleName(f'{label}, {count}')


class MangaFooter(QFrame):
    def __init__(self,host):
        super().__init__();self.host=host;self.setFixedHeight(34);self.row=QHBoxLayout(self);self.row.setContentsMargins(18,0,18,0);self.row.setSpacing(20)
        from app.ui.components.design import ElidedLabel
        self.operation=ElidedLabel('Ready');self.operation.setAccessibleName('Current background operation');self.row.addWidget(self.operation,1)
        self.transfers=QLabel('Speed: 0 KB/s · Downloading: 0');self.row.addWidget(self.transfers)
        set_material(self,'QFrame{background:#e4e7ee;border-top:1px solid #c4c9d4;}QLabel{background:transparent;border:none;color:#535b6d;font:11px "JetBrains Mono";}')
    def activate(self,active):
        for widget in (self.host.status_pill,self.host.scan_stats_label,self.host.bottom_free_label):
            if widget.parentWidget() is self:self.row.removeWidget(widget)
        if active:
            self.host.library_page.service_status_row.insertWidget(0,self.host.scan_stats_label);self.host.scan_stats_label.show()
            self.host.status_pill.hide();self.host.bottom_free_label.hide()
        else:
            self.host.library_page.service_status_row.insertWidget(0,self.host.status_pill);self.host.library_page.service_status_row.insertWidget(1,self.host.scan_stats_label);self.host.bottom_bar.layout().addWidget(self.host.bottom_free_label)
            self.host.status_pill.show();self.host.scan_stats_label.show();self.host.bottom_free_label.show()
        self.setVisible(active)
    def set_operation(self,message):
        self.operation.set_full_text(message or 'Ready');self.operation.setToolTip(message or 'No background operation in progress')
    def update_downloads(self,jobs):
        from app.core.storage import format_bytes
        from app.core.download_queue import status
        downloading=[job for job in jobs if status(job)=='Downloading']
        rate=sum(j.get('download_rate') or 0 for j in downloading)
        from app.core.storage import format_rate
        self.transfers.setText(f'Speed: {format_rate(rate)} · Downloading: {len(downloading)}')
