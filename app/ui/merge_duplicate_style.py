"""Twilight Sakura styles for existing merge and duplicate review workflows."""
from app.ui.home_style import colors,px,load_fonts
from app.ui.transfer_style import qss as base_qss
from app.ui.button_system import unified


@unified(lambda name:f'QWidget#{name}')
def qss(name):
    c=colors();r=f'QWidget#{name}'
    if name=='duplicate_page':
        from app.ui.review_reference_style import reference_colors
        c=reference_colors()
    return base_qss(name)+f'''
    {r} QWidget#merge_content, {r} QWidget#merge_title_cell, {r} QWidget#merge_pill_cell {{background:transparent;border:none;}}
    {r} QWidget#merge_panel {{background:{c['panel']};border:1px solid {c['line']};border-radius:14px;}}
    {r} QLabel#merge_heading, {r} QLabel#duplicate_heading {{font-size:{px(24)}px;font-weight:700;}}
    {r} QLabel#merge_panel_title {{font-size:{px(19)}px;font-weight:600;}}
    {r} QLabel#merge_hint, {r} QLabel#merge_path {{color:{c['muted']};font-size:{px(12)}px;}}
    {r} QLabel#merge_title {{font-weight:600;}}
    {r} QFrame#duplicate_stat {{background:{c['bg']};border:1px solid {c['line']};border-radius:8px;}}
    {r} QLabel#duplicate_value {{color:{c['text']};font-size:{px(16)}px;font-weight:700;}}
    {r} QTreeWidget::item:selected {{background:{c['raised']};color:{c['coral']};}}
    {r} QTreeWidget::item:hover {{background:{c['raised']};}}
    {r} QLabel#merge_pill, {r} QLabel#merge_state {{color:{c['coral']};background:{c['raised']};border:1px solid {c['line']};border-radius:12px;padding:2px 8px;}}
    {r} QLabel#merge_pill[review='true'] {{color:{c['amber']};}}
    {r} QPushButton {{min-height:40px;border-radius:20px;}}
    {r} QHeaderView::section {{background:{c['bg']};color:{c['muted']};border:none;padding:10px;font-size:{px(11)}px;}}
    {r} QTableWidget, {r} QTreeWidget {{background:{c['panel']};color:{c['text']};border:1px solid {c['line']};border-radius:12px;selection-background-color:{c['raised']};outline:none;}}
    {r} QTreeWidget::item {{padding:10px 6px;min-height:30px;border-bottom:1px solid {c['line']};}}
    {r} QListWidget {{background:{c['raised']};border:1px solid {c['line']};border-radius:12px;color:{c['text']};}}
    {r} QListWidget::item {{min-height:28px;padding:8px;}}
    {r} QCheckBox {{background:transparent;color:{c['text']};spacing:8px;}}
    {r} QTreeWidget::indicator {{width:20px;height:20px;border:1px solid {c['muted']};border-radius:5px;background:{c['bg']};}}
    {r} QTreeWidget::indicator:checked {{background:{c['coral']};border-color:{c['coral']};}}
    {r} QFrame#merge_divider {{background:{c['line']};border:none;}}
    {r} QScrollArea, {r} QScrollArea > QWidget {{background:{c['bg']};border:none;}}
    {r} QScrollBar:vertical {{width:8px;background:transparent;}}
    {r} QScrollBar::handle:vertical {{background:{c['line']};border-radius:4px;min-height:24px;}}
    {r} QScrollBar::add-line:vertical, {r} QScrollBar::sub-line:vertical {{height:0;}}
    '''


def apply_merge(page):
    from PyQt5.QtWidgets import QLabel
    load_fonts()
    for label in page.findChildren(QLabel):
        if label.objectName()=='merge_heading':label.setText('Merge libraries')
    page.refresh_home_style()
