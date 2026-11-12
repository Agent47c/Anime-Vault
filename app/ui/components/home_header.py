"""Home navigation capsule; all existing destinations/actions remain reachable."""
from PyQt5.QtCore import Qt,QSize
from PyQt5.QtGui import QFont,QPalette,QColor
from PyQt5.QtWidgets import QFrame,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QLineEdit,QMenu
from app.ui.icons import icon
from app.ui.home_style import colors,load_fonts,px
from app.ui.components.navigation_button import NavigationButton
from app.ui.components.dropdowns import ContainedMenu


class HomeHeader(QFrame):
    def __init__(self,host):
        super().__init__();self.host=host;self.setObjectName('home_header');self.setFixedHeight(76);load_fonts()
        self.setProperty('animevaultOwnScaledStyle',True)
        self.setProperty('animevaultThemeScope',True)
        self.setFont(QFont('Plus Jakarta Sans',12));outer=QVBoxLayout(self);outer.setContentsMargins(20,12,20,12);outer.setSpacing(6)
        row=QHBoxLayout();row.setSpacing(12);outer.addLayout(row);self.main_row=row
        self.brand_side=QWidget();brand=QHBoxLayout(self.brand_side);brand.setContentsMargins(0,0,0,0);mark=QLabel();mark.setObjectName('home_mark');mark.setFixedSize(36,36);self.mark=mark;brand.addWidget(mark)
        names=QVBoxLayout();names.setSpacing(0);name=QLabel('Anime Vault');name.setObjectName('home_brand');names.addWidget(name)
        hint=QLabel('Library & release calendar');hint.setObjectName('home_tagline');names.addWidget(hint);brand.addLayout(names);brand.addStretch();row.addWidget(self.brand_side,1)
        capsule=QFrame();capsule.setObjectName('home_capsule');tabs=QHBoxLayout(capsule);tabs.setContentsMargins(4,4,4,4);tabs.setSpacing(2)
        self.capsule=capsule
        capsule.setFixedHeight(52)
        self.tabs={}
        for title,index in [('Library',0),('Updates',2),('Downloads',5),('Organizer',1),('Storage',3),('Settings',4)]:
            button=NavigationButton(title);button.setProperty('active',index==0)
            button.setAccessibleName(title)
            button.clicked.connect(lambda checked=False,i=index:host._on_nav_clicked(i));tabs.addWidget(button);self.tabs[index]=button
        row.addWidget(capsule)
        self.utility_side=QWidget();utilities=QHBoxLayout(self.utility_side);utilities.setContentsMargins(0,0,0,0);utilities.setSpacing(8);utilities.addStretch();row.addWidget(self.utility_side,1)
        self.search=QLineEdit();self.search.setObjectName('home_quick_find');self.search.setPlaceholderText('Quick Find');self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(180);self.search.setMaximumWidth(260);self.search.setFixedHeight(40);self.search.setAccessibleName('Search library by title')
        self.search.setToolTip('Search library · Ctrl+K');self.search.textChanged.connect(host.top_search_input.setText)
        host.top_search_input.textChanged.connect(self.search.setText);utilities.addWidget(self.search)
        self.search.returnPressed.connect(host.top_search_input.returnPressed.emit)
        self.search.addAction(icon('search',colors()['muted']),QLineEdit.LeadingPosition)
        self.drive=QPushButton('Storage');self.drive.setObjectName('home_drive');self.drive.clicked.connect(lambda:host._on_nav_clicked(3));self.drive.setCursor(Qt.PointingHandCursor)
        self.drive.setMinimumHeight(40);self.drive.setMaximumWidth(140);utilities.addWidget(self.drive)
        self.options=QPushButton();self.options.setObjectName('home_options');self.options.setFixedSize(44,44);self.options.setAccessibleName('Library actions and collections');self.options.setToolTip('Library actions and collections')
        from app.ui.components.vault_menu import VaultMenu
        menu=VaultMenu(self.options)
        self.select_action=menu.addAction('Select multiple anime');self.select_action.setCheckable(True)
        self.select_action.triggered.connect(lambda checked:self._selection_target().set_selection_mode(checked))
        menu.removeAction(self.select_action)  # Selection belongs beside All anime, not global settings/actions.
        menu.add_item('Add anime',host._open_custom_entry_dialog,'plus')
        menu.add_item('Import watched TXT list',host._open_watched_import_dialog,'import','Ctrl+I')
        menu.add_item('Settings',lambda:host._on_nav_clicked(4),'settings')
        menu.addSeparator();self.collections={}
        for title,key in [('Watching','WATCHING'),('Watched','WATCHED'),('Plan to watch','PLAN_TO_WATCH'),('Dropped','DROPPED'),('Watched, removed','WATCHED_REMOVED')]:
            action=menu.add_item(title,lambda checked=False,k=key:host._on_collection_clicked(k),'check' if key=='WATCHED' else 'library');self.collections[key]=(title,action)
        menu.addSeparator();menu.add_item('Refresh local library',lambda:host._request_refresh(False),'refresh');menu.add_item('Refresh and sync with internet',lambda:host._request_refresh(True),'downloads');menu.add_footer()
        menu.aboutToShow.connect(self._collections);self.options.setMenu(menu);utilities.addWidget(self.options)
        self.second_row=QHBoxLayout();outer.addLayout(self.second_row);self._expanded=False
        self.brand_side.setObjectName('home_header_side');self.utility_side.setObjectName('home_header_side')
        for button in self.tabs.values():button.size_changed.connect(self._tab_size_changed)
        self.refresh_style()
    def _tab_size_changed(self):self.capsule.layout().invalidate();self.arrange()
    def _collections(self):
        page=self._selection_target()
        self.select_action.setVisible(getattr(self.host,'_active_nav_index',0)!=5)
        self.select_action.setText('Select multiple updates' if getattr(self.host,'_active_nav_index',0)==2 else 'Select multiple anime')
        self.select_action.setChecked(bool(page and page._selection_mode))
        for key,(title,action) in self.collections.items():
            count=self.host.coll_counts.get(key);action.setText(title+(' · '+count.text() if count else ''))
            active=key==getattr(getattr(self.host,'library_page',None),'_current_filter',None)
            action.setProperty('richActive',active);action.setProperty('richHint','Active' if active else '')
    def _selection_target(self):
        return getattr(self.host,'updates_page' if getattr(self.host,'_active_nav_index',0)==2 else 'library_page',None)
    def refresh_style(self):
        signature=(tuple(colors().items()),px(14))
        if getattr(self,'_style_signature',None)==signature:
            self.arrange();return
        self._style_signature=signature
        self.setFont(QFont('Plus Jakarta Sans',12))
        c=colors();self.mark.setPixmap(icon('flower',c['coral']).pixmap(28,28));self.options.setIcon(icon('list',c['muted']));self.options.setIconSize(QSize(22,22));self.drive.setIcon(icon('storage',c['amber']))
        self.select_action.setIcon(icon('select-multiple',c['coral']))
        palette=self.search.palette();palette.setColor(QPalette.Text,QColor(c['text']));palette.setColor(QPalette.PlaceholderText,QColor(c['muted']));self.search.setPalette(palette)
        self.setStyleSheet(f'''
        QFrame#home_header {{background:{c['bg']};border:none;}}
        QWidget#home_header_side {{background:transparent;}}
        QFrame#home_capsule {{background:{c['panel']};border:none;border-radius:26px;}}
        QLabel#home_brand {{color:{c['text']};font-size:{px(17)}px;font-weight:700;}}
        QLabel#home_tagline {{color:{c['muted']};font-family:'JetBrains Mono';font-size:{px(10)}px;}}
        QLabel#home_mark {{background:{c['panel']};border-radius:12px;}}
        QLineEdit#home_quick_find, QLineEdit#home_quick_find:focus {{background:{c['panel']};color:{c['text']};selection-background-color:{c['coral']};selection-color:{c['on_coral']};border:1px solid {c['line']};border-radius:20px;padding:0 12px;font-size:{px(12)}px;}}
        QPushButton#home_drive, QPushButton#home_options {{background:{c['panel']};border:1px solid {c['line']};border-radius:20px;color:{c['amber']};padding:0 10px;font-family:'JetBrains Mono';font-size:{px(11)}px;}}
        QPushButton#home_options {{padding:0;}}
        QPushButton#home_options::menu-indicator {{image:none;width:0;height:0;}}
        ''')
        self.search.setMinimumWidth(px(180));self.search.setMaximumWidth(px(260));self.drive.setMaximumWidth(px(140));self.arrange()
    def refresh_home_style(self):self.refresh_style()
    def arrange(self):
        from PyQt5.QtWidgets import QApplication
        side=max(self.brand_side.minimumSizeHint().width(),self.utility_side.minimumSizeHint().width())
        expanded=self.width()<self.capsule.sizeHint().width()+2*side+64
        if expanded!=self._expanded:
            self.main_row.removeWidget(self.capsule)
            while self.second_row.count():self.second_row.takeAt(0)
            if expanded:self.second_row.addStretch();self.second_row.addWidget(self.capsule);self.second_row.addStretch()
            else:self.main_row.insertWidget(1,self.capsule)
            self._expanded=expanded
        # Equal side columns keep the capsule centered on the whole window.
        if not expanded:
            self.brand_side.setMinimumWidth(side);self.utility_side.setMinimumWidth(side)
        else:
            self.brand_side.setMinimumWidth(0);self.utility_side.setMinimumWidth(0)
        self.setFixedHeight(132 if expanded else 76)
        if hasattr(self.host,'header_stack') and self.host.header_stack.currentWidget() is self:self.host.header_stack.setFixedHeight(self.height())
    def resizeEvent(self,event):
        super().resizeEvent(event);self.arrange()
    def metrics(self,disk,updates,downloads=None):
        from app.core.storage import format_bytes
        unit=1024**4 if disk.get('total',0)>=1024**4 else 1024**3
        self.drive.setText(f"{disk['used']/unit:.1f} / {disk['total']/unit:.1f} {'TB' if unit==1024**4 else 'GB'}" if disk.get('total') else 'Offline drive')
        self.drive.setToolTip('Review storage · '+(f"{format_bytes(disk['free'])} free" if disk.get('total') else 'Drive unavailable'))
        self.tabs[2].setText('Updates'+(f'  {updates}' if updates else ''))
        if downloads is not None:self.tabs[5].setText('Downloads'+(f'  {downloads}' if downloads else ''))
