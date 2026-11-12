"""Organizer reference presentation; existing scanners and move review stay intact."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget,QLabel,QPushButton,QVBoxLayout,QHBoxLayout,QScrollArea,QFrame,QSizePolicy
from app.ui.home_style import colors,px,load_fonts
from app.ui.transfer_style import qss as base_qss
from app.ui.components.flow_layout import FlowLayout
from app.ui.button_system import unified


@unified('QWidget#organizer_screen')
def qss():
    c=colors();r='QWidget#organizer_screen'
    return base_qss('organizer_screen')+f'''
    {r} QFrame#organizer_card {{background:{c['panel']};border:1px solid {c['line']};border-radius:14px;}}
    {r} QWidget#organizer_clear, {r} QWidget#organizer_cell {{background:transparent;border:none;}}
    {r} QFrame#organizer_row {{background:{c['raised']};border-radius:10px;border:1px solid {c['line']};}}
    {r} QLabel#organizer_title {{font-size:{px(24)}px;font-weight:700;}}
    {r} QLabel#organizer_section_title {{font-size:{px(18)}px;font-weight:600;}}
    {r} QLabel#organizer_meta {{color:{c['muted']};font-size:{px(11)}px;}}
    {r} QLabel#organizer_badge {{color:{c['coral']};background:{c['raised']};border:1px solid {c['line']};border-radius:12px;padding:0 6px;}}
    {r} QFrame#organizer_divider {{background:{c['line']};border:none;max-height:1px;}}
    {r} QFrame#organizer_drop {{background:transparent;border:1px dashed {c['muted']};border-radius:12px;}}
    {r} QCheckBox {{background:transparent;color:{c['text']};}}
    {r} QHeaderView::section {{background:{c['bg']};color:{c['muted']};border:none;padding:10px;font-size:{px(11)}px;}}
    {r} QTableWidget {{background:{c['panel']};border:none;selection-background-color:{c['raised']};}}
    {r} QTableWidget#organizer_preview_table::item {{padding:0;border:none;}}
    {r} QPushButton {{min-height:34px;border-radius:17px;}}
    {r} QPushButton#organizer_review {{min-height:44px;max-height:44px;border-radius:12px;padding:0 10px;}}
    {r} QPushButton:checked {{color:{c['coral']};background:{c['raised']};border-color:{c['coral']};}}
    {r} QScrollBar:vertical {{width:8px;background:transparent;}}
    {r} QScrollBar::handle:vertical {{background:{c['line']};border-radius:4px;min-height:24px;}}
    {r} QScrollBar::add-line:vertical, {r} QScrollBar::sub-line:vertical {{height:0;}}
    '''


def style_cells(page):
    if not getattr(page,'_reference_organizer',False):return
    for row in range(page.table.rowCount()):
        for col in range(4):
            cell=page.table.cellWidget(row,col)
            if not cell:continue
            for widget in [cell,*cell.findChildren(QWidget)]:
                widget.setStyleSheet('')
                if isinstance(widget,QLabel) and col==2:widget.setObjectName('organizer_badge')


def apply_layout(page):
    load_fonts();page._reference_organizer=True;page.season_tab.setObjectName('organizer_screen');page.season_tab.setAttribute(Qt.WA_StyledBackground,True)
    left=page.controls_scroll.widget().layout();roots=left.itemAt(0).widget();rules=left.itemAt(1).widget();preview=page.preview_card
    old=page.season_tab.layout();page._old_reference_items=[]
    while old.count():
        item=old.takeAt(0);page._old_reference_items.append(item)
        if item.widget():item.widget().hide()
    scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);old.addWidget(scroll)
    content=QWidget();content.setObjectName('organizer_clear');layout=QVBoxLayout(content);layout.setContentsMargins(0,0,0,0);layout.setSpacing(20);scroll.setWidget(content);page.organizer_reference_scroll=scroll
    heading_row=QHBoxLayout();headings=QVBoxLayout()
    title=QLabel('Organize & File Management');title.setObjectName('organizer_title');title.setWordWrap(True);headings.addWidget(title)
    hint=QLabel('Scan folders, review proposed moves and organize your library safely.');hint.setObjectName('organizer_meta');hint.setWordWrap(True);headings.addWidget(hint)
    headings.addWidget(page.top_status_badge,0,Qt.AlignLeft);page.top_status_badge.show()
    heading_row.addLayout(headings,1)
    action_widget=QWidget();action_widget.setObjectName('organizer_clear');action_widget.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Preferred);actions=QHBoxLayout(action_widget);actions.setContentsMargins(0,0,0,0);actions.setSpacing(8)
    page.duplicates_btn.setParent(page);page.duplicates_btn.hide()
    for control in (page.scan_btn,page.find_missing_btn,page.stop_btn):actions.addWidget(control);control.show()
    heading_row.addWidget(action_widget,0,Qt.AlignTop|Qt.AlignRight);layout.addLayout(heading_row);page.scan_btn.setProperty('accent',True)
    cards=QHBoxLayout();cards.setSpacing(20);cards.addWidget(rules,3);cards.addWidget(roots,2);rules.show();roots.show();layout.addLayout(cards)
    preview.setMinimumHeight(510);preview.setMaximumHeight(16777215);preview.show();layout.addWidget(preview,1)
    page.controls_scroll.hide()
    for widget in page.season_tab.findChildren(QWidget):
        if widget is not page.season_tab:widget.setStyleSheet('')
        if isinstance(widget,QLabel):widget.setWordWrap(True)
        if isinstance(widget,QFrame) and widget.frameShape()==QFrame.HLine:widget.setObjectName('organizer_divider')
    for child in roots.findChildren(QFrame,options=Qt.FindDirectChildrenOnly):
        if child.layout():child.setObjectName('organizer_drop')
    roots.layout().addStretch()
    page.top_status_badge.setWordWrap(False);page.top_status_badge.setObjectName('organizer_meta')
    page.preview_card.layout().itemAt(0).layout().setStretch(0,1)
    page.search_filter.setMaximumWidth(420)
    title.setObjectName('organizer_title');hint.setObjectName('organizer_meta')
    for card,new_title in ((rules,'Detection Rules & Parsing Parameters'),(roots,'Configured Library Roots')):
        heading=card.layout().itemAt(0).widget();heading.setText(new_title);heading.setObjectName('organizer_section_title')
    page.scan_btn.setProperty('accent',True);page.organize_btn.setProperty('accent',True)
    page.table.setShowGrid(False);page.table.setAlternatingRowColors(False)
    for button in (page.tab_unorg_btn,page.tab_org_btn,page.tab_all_btn):button.setCheckable(True)
    page._update_tab_styles()


def refresh(page):
    page.season_tab.setStyleSheet(qss());style_cells(page)
    c=colors()
    page.organizer_tabs.setStyleSheet(f"QTabWidget#organizer_tabs::pane {{border:none;background:{c['bg']};}} QTabBar::tab {{background:{c['panel']};color:{c['muted']};padding:12px 20px;border:none;}} QTabBar::tab:selected {{color:{c['coral']};border-bottom:2px solid {c['coral']};}}")
