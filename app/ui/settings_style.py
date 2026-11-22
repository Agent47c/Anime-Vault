"""Reference settings layout, retaining existing controls and their callbacks."""
from PyQt5.QtCore import Qt,QRectF
from PyQt5.QtGui import QPainter,QColor,QPen,QFont
from PyQt5.QtWidgets import QWidget,QFrame,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QScrollArea,QGridLayout
from app.ui.home_style import colors,px,load_fonts
from app.ui.button_system import unified


SECTION_NAMES = {
    'Appearance & Accessibility': 'Appearance & Behavior',
    'Scanning & Organization': 'Library Roots',
    'Watchers & Import Lists': 'Monitoring & Imports',
    'Media Player': 'Media Player',
    'Downloads & Sources': 'Downloads & Sources',
    'Database & Backup': 'Database & Backups',
    'Naming & Organization': 'File Naming & Organization',
    'Metadata & AniList': 'Metadata & Adult Access',
}


def add_settings_row(box, title, hint='', control=None):
    widget=QWidget();widget.setObjectName('settings_row')
    row=QHBoxLayout(widget);row.setContentsMargins(0,10,0,10);row.setSpacing(16)
    labels=QVBoxLayout();labels.setSpacing(2)
    label=QLabel(title);label.setObjectName('settings_label');label.setWordWrap(True);labels.addWidget(label)
    if hint:
        detail=QLabel(hint);detail.setObjectName('settings_hint');detail.setWordWrap(True);labels.addWidget(detail)
    row.addLayout(labels,1)
    if control is not None:
        row.addWidget(control,0,Qt.AlignVCenter)
        control.setAccessibleName(title);control.setAccessibleDescription(hint)
    box.addWidget(widget)
    divider=QFrame();divider.setObjectName('settings_divider');divider.setFixedHeight(1);box.addWidget(divider)
    return widget


def settings_row_qss(root):
    from app.ui.manga_pages import active

    c=colors();manga=active()
    row=f'{root} QWidget#settings_row'
    switch_height=30 if manga else 36
    return f'''
    {row} {{background:transparent;border:none;}}
    {row} QLabel#settings_label {{background:transparent;color:{c['text']};font-size:{px(14)}px;font-weight:600;}}
    {row} QLabel#settings_hint {{background:transparent;color:{c['muted']};font-size:{px(14 if manga else 12)}px;}}
    {root} QFrame#settings_divider {{background:{c['raised'] if manga else c['line']};border:none;}}
    {row} SettingsSwitch {{min-height:{switch_height}px;max-height:{switch_height}px;}}
    '''


class ThemeCard(QPushButton):
    PREVIEWS={
        'dark':('#14121d','#2b2834','#ff6584'),
        'light':('#f7f3f6','#e7dce8','#b0284b'),
        'manga_light':('#eef0f5','#d9dde7','#ff2e93'),
        'manga_dark':('#121315','#2c2e33','#ff2e93'),
    }

    def __init__(self,label,description,value,parent=None):
        super().__init__(parent);self.setObjectName('settings_theme_card');self.label=label;self.description=description;self.value=value;self.setCheckable(True);self.setMinimumSize(135,170);self.setCursor(Qt.PointingHandCursor);self.setAccessibleName(label);self.setAccessibleDescription(description)

    def paint_preview(self,painter,preview):
        canvas,panel,accent=self.PREVIEWS[self.value]
        def box(x,y,w,h,color,radius=3):
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(x,y,w,h),radius,radius)

        painter.setPen(Qt.NoPen)
        x,y,w=preview.x(),preview.y(),preview.width()
        box(x,y,w,preview.height(),canvas,8)
        sidebar=self.value.startswith('manga_')
        if sidebar:
            box(x+8,y+8,22,48,panel,4)
            for n in range(4):
                box(x+14,y+13+n*10,10,5,accent if n==0 else canvas,2)
        else:
            center=x+w/2
            box(center-38,y+8,76,13,panel,5)
            for n in (-1,0,1):
                box(center-9+n*22,y+12,18,5,accent if n==0 else canvas,2)

        left=x+38 if sidebar else x+10
        width=x+w-10-left
        box(left,y+(8 if sidebar else 27),width,16 if sidebar else 12,panel)
        for n in range(4):
            gap=4
            cell=(width-3*gap)/4
            box(left+n*(cell+gap),y+(30 if sidebar else 44),cell,17 if sidebar else 13,panel)

    def paintEvent(self,event):
        c=colors();p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        from app.ui.manga_pages import active
        from app.ui.theme_catalog import is_manga_dark
        manga=active();rect=self.rect().adjusted(8,8,-8,-8) if manga else self.rect().adjusted(2,2,-2,-2)
        if manga:
            from app.ui.components.neumorphic import paint_depth
            if not self.isDown():paint_depth(p,QRectF(rect))
        face=c['raised'] if self.isChecked() or self.underMouse() else c['panel']
        if manga and not is_manga_dark():face='white' if self.isChecked() else '#f3f4f8'
        p.setPen(QPen(QColor(c['coral'] if self.isChecked() or self.hasFocus() else c['line']),2 if self.isChecked() else 1));p.setBrush(QColor(face));p.drawRoundedRect(QRectF(rect),12,12)
        if manga and self.isDown():paint_depth(p,QRectF(rect),True)
        preview=rect.adjusted(14,14,-14,-rect.height()+78)
        self.paint_preview(p,QRectF(preview))
        p.setPen(QColor(c['coral'] if self.isChecked() else c['text']));font=QFont('Plus Jakarta Sans');font.setPixelSize(px(13));font.setBold(True);p.setFont(font);p.drawText(rect.adjusted(14,88,-12,0),Qt.AlignTop|Qt.TextWordWrap,self.label)
        font.setPixelSize(px(11));font.setBold(False);p.setFont(font);p.setPen(QColor(c['muted']));p.drawText(rect.adjusted(14,112,-12,-6),Qt.AlignTop|Qt.TextWordWrap,self.description)


@unified('QWidget#settings_page')
def qss():
    from app.ui.manga_pages import active
    r='QWidget#settings_page'
    if active():
        from app.ui.manga_additional import qss as extra_qss
        return extra_qss('settings_page')+settings_row_qss(r)
    c=dict(colors())
    from PyQt5.QtWidgets import QApplication
    if QApplication.instance().property('animevaultTheme')!='light' and not QApplication.instance().property('animevaultHighContrast'):
        c.update(panel='#1c1a27',raised='#221f30',line='#2e2a40')
    return f'''
    {r}, {r} QWidget#settings_content, {r} QScrollArea, {r} QScrollArea > QWidget {{background:{c['bg']};border:none;}}
    {r} {{color:{c['text']};font-family:'Plus Jakarta Sans';}}
    {r} QLabel {{background:transparent;color:{c['text']};border:none;font-size:{px(13)}px;}}
    {r} QLabel#settings_heading {{font-size:{px(24)}px;font-weight:700;}}
    {r} QLabel#settings_subtitle, {r} QLabel#settings_hint {{color:{c['muted']};font-size:{px(12)}px;}}
    {r} QFrame#settings_panel, {r} QFrame#settings_navigation {{background:{c['panel']};border:1px solid {c['line']};border-radius:10px;}}
    {r} QLabel#settings_panel_title {{font-size:{px(17)}px;font-weight:600;margin-bottom:8px;}}
    {r} QPushButton[settingsSection='true'] {{text-align:left;border:1px solid transparent;background:transparent;}}
    {r} QPushButton[settingsSection='true']:checked {{color:{c['coral']};background:{c['raised']};border-left:2px solid {c['coral']};}}
    {r} QWidget#settings_row {{background:transparent;border:none;}}
    {r} QFrame#settings_divider {{background:{c['line']};border:none;}}
    {r} QPushButton {{background:{c['raised']};color:{c['text']};border:1px solid {c['line']};border-radius:10px;padding:6px 12px;min-height:30px;font-size:{px(12)}px;}}
    {r} QPushButton:hover, {r} QPushButton:focus {{border-color:{c['coral']};}}
    {r} QPushButton:checked {{color:{c['coral']};background:{c['raised']};border-color:{c['coral']};}}
    {r} QPushButton#settings_theme_card {{min-height:{px(170)}px;max-height:{px(170)}px;padding:0;}}
    {r} QPushButton[settingsPlayerCard='true'] {{min-height:{px(70)}px;}}
    {r} QWidget#settings_choices {{background:transparent;border:none;}}
    {r} QTabWidget#settings_tabs::pane {{border:none;background:{c['bg']};}}
    {r} QPushButton[accent='true'] {{background:{c['coral']};color:{c['on_coral']};}}
    {r} QComboBox, {r} QLineEdit {{background:{c['bg']};color:{c['text']};border:1px solid {c['line']};border-radius:10px;padding:0 12px;min-height:40px;font-size:{px(12)}px;}}
    {r} QComboBox QAbstractItemView, {r} QListWidget, {r} QTableWidget {{background:{c['panel']};color:{c['text']};border:1px solid {c['line']};selection-background-color:{c['raised']};}}
    {r} QListWidget::item {{padding:10px;min-height:26px;}}
    {r} QFrame#settings_segments {{background:{c['raised']};border-radius:10px;}}
    {r} QScrollBar:vertical {{width:8px;background:transparent;}}
    {r} QScrollBar::handle:vertical {{background:{c['line']};border-radius:4px;min-height:24px;}}
    {r} QScrollBar::add-line:vertical, {r} QScrollBar::sub-line:vertical {{height:0;}}
    '''+settings_row_qss(r)


def apply_layout(page):
    load_fonts();page.setAttribute(Qt.WA_StyledBackground,True)
    layout=page.layout();header=layout.itemAt(0).widget();header.hide();layout.removeWidget(header)
    title=QLabel('Settings');title.setObjectName('settings_heading');layout.insertWidget(0,title)
    subtitle=QLabel('Your library, playback and download preferences · Changes save automatically');subtitle.setObjectName('settings_subtitle');subtitle.setWordWrap(True);layout.insertWidget(1,subtitle)
    layout.removeWidget(page.tabs);page.tabs.tabBar().hide()
    columns=QHBoxLayout();columns.setSpacing(24);layout.addLayout(columns,1)
    from app.ui.components.paper_card import PaperCard
    nav=PaperCard();nav.setObjectName('settings_navigation');nav.setFixedWidth(242);navbox=QVBoxLayout(nav);navbox.setContentsMargins(22,26,22,26);navbox.setSpacing(6)
    side=QVBoxLayout();nav_scroll=QScrollArea();nav_scroll.setWidgetResizable(True);nav_scroll.setFrameShape(QFrame.NoFrame);nav_scroll.setFixedWidth(258);nav_scroll.setWidget(nav);side.addWidget(nav_scroll);columns.addLayout(side)
    columns.addWidget(page.tabs,1);page.tabs.show();page.settings_scroll=page.tabs.currentWidget()
    page.section_targets=[];page.section_buttons=[]
    from app.ui.icons import icon
    icons=['settings','organizer','updates','play','downloads','storage','organizer','updates']
    for n,(name,column) in enumerate(page._tab_layouts.items()):
        label=SECTION_NAMES[name]
        old_scroll=page.tabs.widget(n);group=old_scroll.widget();column.setContentsMargins(0,0,8,0);page.section_targets.append(group)
        button=QPushButton(label.replace('&','&&'));button.setCheckable(True);button.setChecked(n==0);button.setIcon(icon(icons[n],colors()['coral'] if n==0 else colors()['muted']));button.setMinimumHeight(44);button.setCursor(Qt.PointingHandCursor);button.setAccessibleName(label);button.clicked.connect(lambda checked=False,i=n:page.tabs.setCurrentIndex(i) if page.tabs.currentIndex()!=i else page._show_settings_section(i));navbox.addWidget(button);page.section_buttons.append(button)
        button.setProperty('settingsSection',True)
    for button in page.section_buttons:navbox.removeWidget(button)
    for caption,indices in [('CORE SYSTEM',(0,1,6,7)),('AUTOMATION & INGESTION',(2,4,3)),('MAINTENANCE',(5,))]:
        heading=QLabel(caption);heading.setObjectName('settings_hint');navbox.addSpacing(10);navbox.addWidget(heading)
        for index in indices:navbox.addWidget(page.section_buttons[index])
    navbox.addStretch()
    page.tabs.currentChanged.connect(page._show_settings_section)
    page.theme_cards=[]
    panel=next(p for p in page.findChildren(QFrame) if p.property('settings_section')=='Appearance and accessibility')
    page.theme_combo.parentWidget().hide();cards=QWidget();cards.setObjectName('settings_choices');grid=QGridLayout(cards);grid.setContentsMargins(0,0,0,0);grid.setSpacing(12)
    from app.ui.theme_catalog import THEME_CHOICES
    hints=('Dark canvas · Center navigation','Light canvas · Center navigation','Paper canvas · Left navigation','Charcoal canvas · Left navigation')
    for n,((label,value),hint) in enumerate(zip(THEME_CHOICES,hints)):
        button=ThemeCard(label,hint,value);button.clicked.connect(lambda checked=False,v=value:(page.theme_combo.setCurrentIndex(page.theme_combo.findData(v)),sync_theme()));grid.addWidget(button,n//3,n%3);page.theme_cards.append(button)
    panel.layout().insertWidget(panel.layout().indexOf(page.theme_combo.parentWidget()),cards)
    def sync_theme():
        for card in page.theme_cards:card.setChecked(card.value==page.theme_combo.currentData());card.update()
    page.theme_combo.currentIndexChanged.connect(sync_theme);sync_theme()
    page.player_combo.parentWidget().hide();panel=next(p for p in page.findChildren(QFrame) if p.property('settings_section')=='Media player')
    players=QWidget();players.setObjectName('settings_choices');grid=QGridLayout(players);grid.setContentsMargins(0,0,0,0);page.player_cards=[]
    for n in range(page.player_combo.count()):
        button=QPushButton(page.player_combo.itemText(n));button.setProperty('settingsPlayerCard',True);button.setCheckable(True);button.setMinimumHeight(70);value=page.player_combo.itemData(n);button.clicked.connect(lambda checked=False,v=value:(page.player_combo.setCurrentIndex(page.player_combo.findData(v)),sync_player()));grid.addWidget(button,n//3,n%3);page.player_cards.append((value,button))
        from PyQt5.QtWidgets import QStyle
        from PyQt5.QtCore import QSize
        button.setIcon(page.style().standardIcon(QStyle.SP_ComputerIcon if value=='default' else QStyle.SP_FileIcon if value=='custom' else QStyle.SP_MediaPlay));button.setIconSize(QSize(32,32))
    panel.layout().insertWidget(panel.layout().indexOf(page.player_combo.parentWidget()),players)
    def sync_player():
        for value,button in page.player_cards:button.setChecked(value==page.player_combo.currentData())
    page.player_combo.currentIndexChanged.connect(sync_player);sync_player()
    compact_actions(page)
    # Follow the reference's scanning sequence without mixing categories.
    column=page._tab_layouts['Scanning & Organization']
    root_panel=next(panel for panel in page.findChildren(QFrame) if panel.property('settings_section')=='Library roots and scanning')
    column.removeWidget(root_panel);column.insertWidget(0,root_panel)
    layout_download_form(page)


def layout_download_form(page):
    config=page.download_config;column=page._tab_layouts['Downloads & Sources']
    index=column.indexOf(config);column.removeWidget(config)
    panel,box=page._panel('Download engine');box.addWidget(config);column.insertWidget(index,panel)
    def pair(left,right):
        first,second=left.parentWidget(),right.parentWidget();parent=first.parentWidget();layout=parent.layout()
        if second.parentWidget() is not parent or layout is None:return
        index=layout.indexOf(first)
        if index<0:return
        layout.removeWidget(first);layout.removeWidget(second);row=QWidget();row.setObjectName('settings_choices');horizontal=QHBoxLayout(row);horizontal.setContentsMargins(0,0,0,0);horizontal.setSpacing(16);horizontal.addWidget(first,1);horizontal.addWidget(second,1);layout.insertWidget(index,row)
    pair(config.controls['group'],config.controls['quality']);pair(config.download_limit,config.upload_limit)
    browse=next((button for button in config.findChildren(QPushButton) if button.text()=='Choose destination…'),None)
    if browse:
        control=config.controls['destination'];group=control.parentWidget();old=browse.parentWidget();group.layout().removeWidget(control)
        row=QWidget();row.setObjectName('workflow_field');horizontal=QHBoxLayout(row);horizontal.setContentsMargins(0,0,0,0);horizontal.addWidget(control,1);horizontal.addWidget(browse);group.layout().addWidget(row)
        if old and old.layout() and old.layout().count()==0:old.hide()


def arrange_theme_cards(page):
    cards=getattr(page,'theme_cards',[])
    if not cards:return
    from app.ui.manga_pages import active
    columns=(4 if page.width()>=1300 else 2 if page.width()>=850 else 1) if active() else 3
    if columns==getattr(page,'_theme_card_columns',None):return
    page._theme_card_columns=columns
    grid=cards[0].parentWidget().layout()
    for index,card in enumerate(cards):grid.addWidget(card,index//columns,index%columns)


def compact_actions(page):
    """Group existing vertical action buttons without changing their callbacks."""
    from app.ui.components.flow_layout import FlowLayout
    def compact(layout):
        if not isinstance(layout,QVBoxLayout):return
        index=0
        while index<layout.count():
            item=layout.itemAt(index);widget=item.widget()
            if isinstance(widget,QPushButton) and not isinstance(widget,ThemeCard):
                buttons=[]
                while index<layout.count() and isinstance(layout.itemAt(index).widget(),QPushButton):buttons.append(layout.takeAt(index).widget())
                holder=QWidget();holder.setObjectName('settings_choices');flow=FlowLayout(holder)
                for button in buttons:button.setSizePolicy(button.sizePolicy().Preferred,button.sizePolicy().Fixed);flow.addWidget(button)
                layout.insertWidget(index,holder)
            elif item.layout():compact(item.layout())
            if widget and widget.layout():compact(widget.layout())
            index+=1
    for column in page._tab_layouts.values():compact(column)
