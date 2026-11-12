"""Reference settings layout, retaining existing controls and their callbacks."""
from PyQt5.QtCore import Qt,QRectF
from PyQt5.QtGui import QPainter,QColor,QPen,QFont
from PyQt5.QtWidgets import QWidget,QFrame,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QScrollArea,QGridLayout
from app.ui.home_style import colors,px,load_fonts
from app.ui.button_system import unified


class ThemeCard(QPushButton):
    def __init__(self,label,description,value,parent=None):
        super().__init__(parent);self.setObjectName('settings_theme_card');self.label=label;self.description=description;self.value=value;self.setCheckable(True);self.setMinimumSize(135,170);self.setCursor(Qt.PointingHandCursor);self.setAccessibleName(label);self.setAccessibleDescription(description)
    def paintEvent(self,event):
        c=colors();p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);rect=self.rect().adjusted(2,2,-2,-2)
        p.setPen(QPen(QColor(c['coral'] if self.isChecked() or self.hasFocus() else c['line']),2 if self.isChecked() else 1));p.setBrush(QColor(c['raised'] if self.isChecked() or self.underMouse() else c['panel']));p.drawRoundedRect(QRectF(rect),12,12)
        preview=rect.adjusted(14,14,-14,-rect.height()+78);p.setPen(Qt.NoPen);p.setBrush(QColor('#e8defa' if self.value=='light' else '#100e18'));p.drawRoundedRect(QRectF(preview),8,8)
        p.setBrush(QColor(c['coral'] if self.value=='dark' else '#605b6a'));p.drawRoundedRect(QRectF(preview.left()+8,preview.bottom()-12,min(60,preview.width()-16),5),2,2)
        p.setPen(QColor(c['coral'] if self.isChecked() else c['text']));font=QFont('Plus Jakarta Sans');font.setPixelSize(px(13));font.setBold(True);p.setFont(font);p.drawText(rect.adjusted(14,88,-12,0),Qt.AlignTop|Qt.TextWordWrap,self.label)
        font.setPixelSize(px(11));font.setBold(False);p.setFont(font);p.setPen(QColor(c['muted']));p.drawText(rect.adjusted(14,112,-12,-6),Qt.AlignTop|Qt.TextWordWrap,self.description)


@unified('QWidget#settings_page')
def qss():
    c=dict(colors());r='QWidget#settings_page'
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
    '''


def apply_layout(page):
    load_fonts();page.setAttribute(Qt.WA_StyledBackground,True)
    layout=page.layout();header=layout.itemAt(0).widget();header.hide();layout.removeWidget(header)
    title=QLabel('Settings');title.setObjectName('settings_heading');layout.insertWidget(0,title)
    subtitle=QLabel('Your library, playback and download preferences · Changes save automatically');subtitle.setObjectName('settings_subtitle');subtitle.setWordWrap(True);layout.insertWidget(1,subtitle)
    layout.removeWidget(page.tabs);page.tabs.tabBar().hide()
    columns=QHBoxLayout();columns.setSpacing(24);layout.addLayout(columns,1)
    nav=QFrame();nav.setObjectName('settings_navigation');nav.setFixedWidth(242);navbox=QVBoxLayout(nav);navbox.setContentsMargins(12,16,12,16);navbox.setSpacing(6)
    side=QVBoxLayout();nav_scroll=QScrollArea();nav_scroll.setWidgetResizable(True);nav_scroll.setFrameShape(QFrame.NoFrame);nav_scroll.setFixedWidth(258);nav_scroll.setWidget(nav);side.addWidget(nav_scroll);columns.addLayout(side)
    columns.addWidget(page.tabs,1);page.tabs.show();page.settings_scroll=page.tabs.currentWidget()
    page.section_targets=[];page.section_buttons=[]
    names=['Appearance & Themes','Library Roots & Scanning','Watchers & TXT Lists','Media Player','Downloads & Sources','Database & Backups','Naming & Organization','Metadata & AniList']
    from app.ui.icons import icon
    icons=['settings','organizer','updates','play','downloads','storage','organizer','updates']
    for n,(name,column) in enumerate(page._tab_layouts.items()):
        old_scroll=page.tabs.widget(n);group=old_scroll.widget();column.setContentsMargins(0,0,8,0);page.section_targets.append(group)
        button=QPushButton(names[n].replace('&','&&'));button.setCheckable(True);button.setChecked(n==0);button.setIcon(icon(icons[n],colors()['coral'] if n==0 else colors()['muted']));button.setMinimumHeight(44);button.setCursor(Qt.PointingHandCursor);button.setAccessibleName(names[n]);button.clicked.connect(lambda checked=False,i=n:page.tabs.setCurrentIndex(i) if page.tabs.currentIndex()!=i else page._show_settings_section(i));navbox.addWidget(button);page.section_buttons.append(button)
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
    for n,(label,hint,value) in enumerate([('Match Windows','Follow system appearance','system'),('Twilight Sakura','Warm dark canvas','dark'),('Sakura Paper','Light canvas','light')]):
        button=ThemeCard(label,hint,value);button.clicked.connect(lambda checked=False,v=value:(page.theme_combo.setCurrentIndex(page.theme_combo.findData(v)),sync_theme()));grid.addWidget(button,0,n);page.theme_cards.append(button)
    panel.layout().insertWidget(2,cards)
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
    panel.layout().insertWidget(2,players)
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
