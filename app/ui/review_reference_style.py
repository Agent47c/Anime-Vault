"""Scoped presentation for the approved list, grouping and duplicate references."""
from app.ui.home_style import colors,px
from PyQt5.QtWidgets import QApplication

def reference_colors():
    c=colors()
    app=QApplication.instance()
    if app.property('animevaultTheme')!='light' and not app.property('animevaultHighContrast'):
        c.update(bg='#14121d',panel='#1c1a27',raised='#232032',line='#2e293f',coral='#ff6584')
    return c

def list_style():
    c=reference_colors();r='QTableWidget#library_list'
    return f'''
    {r} {{background:{c['panel']};color:{c['text']};border:1px solid {c['line']};border-radius:12px;gridline-color:transparent;}}
    {r}::item {{padding:0;border:none;border-bottom:1px solid {c['line']};}}
    {r} QWidget {{background:transparent;}}
    {r} QLabel {{border:none;background:transparent;color:{c['text']};}}
    {r} QLabel#list_title {{font-size:{px(14)}px;font-weight:700;}}
    {r} QLabel#list_subtitle {{font-size:{px(12)}px;color:{c['muted']};font-style:italic;}}
    {r} QLabel#list_status {{background:{c['raised']};border:1px solid {c['line']};border-radius:11px;padding:2px 8px;color:{c['amber']};font-size:{px(12)}px;}}
    {r} QLabel#list_status[state='ON_DISK'] {{color:{c['ok']};}}
    {r} QPushButton {{background:{c['raised']};color:{c['text']};border:1px solid {c['line']};border-radius:7px;min-height:32px;padding:0 12px;font-size:{px(12)}px;}}
    {r} QPushButton:hover {{border-color:{c['coral']};}}
    {r} QHeaderView::section {{background:{c['panel']};color:{c['muted']};padding:10px 8px;border:none;border-bottom:1px solid {c['line']};font-size:{px(11)}px;font-weight:700;}}
    '''

def grouping_style():
    c=reference_colors();r='QWidget#group_review'
    return f'''
    {r} {{background:{c['panel']};color:{c['text']};border:1px solid {c['line']};border-radius:20px;}}
    {r} QLabel {{border:none;background:transparent;color:{c['muted']};font-size:{px(14)}px;}}
    {r} QLabel#workflow_title {{color:{c['text']};font-size:{px(24)}px;font-weight:700;}}
    {r} QLabel#workflow_row_title {{color:{c['text']};font-size:{px(16)}px;font-weight:700;}}
    {r} QWidget#workflow_body, {r} QScrollArea, {r} QScrollArea>QWidget {{background:transparent;border:none;}}
    {r} QFrame#workflow_card {{background:{c['raised']};border:1px solid {c['line']};border-radius:14px;}}
    {r} QFrame#workflow_card[primary='true'] {{border-color:{c['coral']};}}
    {r} QLabel#group_anchor {{background:{c['bg']};color:{c['amber']};border:1px solid {c['amber']};border-radius:12px;padding:14px;}}
    {r} QLabel#group_badge {{color:{c['coral']};background:{c['panel']};border:1px solid {c['line']};border-radius:7px;padding:6px 10px;font-size:{px(12)}px;}}
    {r} QCheckBox {{color:{c['text']};background:{c['raised']};border:1px solid {c['coral']};border-radius:10px;padding:12px;spacing:10px;}}
    {r} QPushButton {{background:{c['raised']};color:{c['text']};border:1px solid {c['line']};border-radius:12px;padding:0 22px;min-height:44px;}}
    {r} QPushButton[accent='true'] {{background:{c['coral']};color:{c['on_coral']};}}
    {r} QPushButton:disabled {{color:{c['muted']};background:{c['bg']};}}
    '''
