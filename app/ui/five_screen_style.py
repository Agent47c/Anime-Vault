"""Shared native Qt presentation for the five approved Twilight Sakura screens."""
from app.ui.review_reference_style import reference_colors
from app.ui.home_style import px,load_fonts

def qss(name):
    load_fonts()
    from app.ui.home_style import colors
    c=colors() if name=='release_news' else reference_colors();r=f'QWidget#{name}'
    return f'''
    {r} {{background:{c['bg']};color:{c['text']};font-family:'Plus Jakarta Sans';}}
    {r} QLabel {{background:transparent;border:none;color:{c['muted']};font-size:{px(13)}px;}}
    {r} QLabel#transfer_heading, {r} QLabel#download_heading, {r} QLabel#workflow_title {{font-size:{px(24)}px;font-weight:700;color:{c['text']};}}
    {r} QLabel#workflow_row_title, {r} QLabel#update_title {{font-size:{px(18)}px;font-weight:700;color:{c['text']};}}
    {r} QFrame#transfer_panel, {r} QFrame#workflow_card, {r} QFrame#result_card {{background:{c['panel']};border:1px solid {c['line']};border-radius:14px;}}
    {r} QFrame#result_card[selected='true'] {{border:2px solid {c['coral']};}}
    {r} QWidget#workflow_field, {r} QWidget#workflow_body, {r} QWidget#transfer_clear, {r} QScrollArea, {r} QScrollArea>QWidget {{background:transparent;border:none;}}
    {r} QLabel#workflow_match {{background:{c['raised']};color:{c['ok']};border:1px solid {c['line']};border-radius:12px;padding:4px 10px;}}
    {r} QPushButton {{background:{c['raised']};color:{c['text']};border:1px solid {c['line']};border-radius:10px;padding:0 18px;min-height:40px;}}
    {r} QPushButton:hover {{border-color:{c['coral']};}}
    {r} QPushButton[accent='true'] {{background:{c['coral']};color:{c['on_coral']};}}
    {r} QPushButton:disabled {{background:{c['panel']};color:{c['muted']};}}
    {r} QLineEdit, {r} QComboBox {{background:{c['panel']};color:{c['text']};border:1px solid {c['line']};border-radius:10px;min-height:44px;padding:0 14px;}}
    {r} QListView {{background:{c['panel']};color:{c['text']};border:1px solid {c['line']};border-radius:14px;padding:16px;}}
    {r} QListView::item {{background:{c['raised']};border:1px solid {c['line']};border-radius:12px;padding:16px;margin:6px;}}
    {r} QListView::item:selected {{border:1px solid {c['coral']};color:{c['text']};}}
    {r} QTableWidget {{background:{c['panel']};color:{c['text']};border:1px solid {c['line']};border-radius:12px;}}
    {r} QTableWidget::item {{padding:10px;border-bottom:1px solid {c['line']};}}
    {r} QHeaderView::section {{background:{c['bg']};color:{c['muted']};padding:14px;border:none;}}
    {r} QCheckBox, {r} QRadioButton {{background:transparent;color:{c['text']};spacing:10px;}}
    {r} QCheckBox::indicator, {r} QRadioButton::indicator {{width:20px;height:20px;border:1px solid {c['muted']};background:{c['bg']};border-radius:5px;}}
    {r} QRadioButton::indicator {{border-radius:10px;}}
    {r} QCheckBox::indicator:checked, {r} QRadioButton::indicator:checked {{background:{c['coral']};border-color:{c['coral']};}}
    '''
