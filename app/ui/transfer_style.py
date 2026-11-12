"""Shared Twilight Sakura presentation for Updates and Downloads."""
from app.ui.home_style import colors,px
from app.ui.button_system import unified

@unified(lambda page:f'QWidget#{page}')
def qss(page):
    c=colors();root=f'QWidget#{page}'
    return f'''
    {root} {{background:{c['bg']};color:{c['text']};font-family:'Plus Jakarta Sans';}}
    {root} QLabel {{color:{c['text']};background:transparent;border:none;font-size:{px(13)}px;}}
    {root} QLabel#transfer_heading {{font-size:{px(24)}px;font-weight:700;}}
    {root} QLabel#transfer_meta, {root} QLabel#subheading {{font-family:'JetBrains Mono';color:{c['muted']};font-size:{px(11)}px;}}
    {root} QWidget#transfer_clear {{background:transparent;border:none;}}
    {root} QFrame#transfer_panel, {root} QFrame#update_card, {root} QFrame#final_panel {{background:{c['panel']};border:1px solid {c['line']};border-radius:14px;}}
    {root} QFrame#update_card:hover {{border-color:{c['coral']};}}
    {root} QFrame#update_card[selected='true'] {{border:2px solid {c['coral']};}}
    {root} QFrame#update_card[muted='true'] {{background:{c['bg']};}}
    {root} QFrame#update_card QLabel#update_title {{font-size:{px(20)}px;font-weight:600;}}
    {root} QFrame#final_panel QLabel#update_title {{font-size:{px(20)}px;font-weight:600;}}
    {root} QLabel#update_poster {{background:{c['raised']};border-radius:8px;font-size:26px;font-weight:700;}}
    {root} QFrame#update_card QLabel#update_tag {{font-family:'JetBrains Mono';font-size:{px(10)}px;color:{c['coral']};}}
    {root} QPushButton {{background:{c['raised']};color:{c['text']};border:1px solid {c['line']};border-radius:16px;min-height:32px;padding:0 12px;font-size:{px(12)}px;}}
    {root} QPushButton:hover {{border-color:{c['coral']};}}
    {root} QPushButton:focus {{border:2px solid {c['coral']};}}
    {root} QFrame#update_card QPushButton {{padding:0 8px;font-size:{px(12)}px;}}
    {root} QPushButton[accent='true'], {root} QPushButton[chip='true']:checked {{background:{c['coral']};color:{c['on_coral']};border:none;}}
    {root} QComboBox, {root} QLineEdit, {root} QSpinBox {{background:{c['bg']};color:{c['text']};border:1px solid {c['line']};border-radius:12px;min-height:36px;padding:0 12px;}}
    {root} QTableView {{background:{c['bg']};border:none;outline:none;}}
    {root} QScrollArea, {root} QScrollArea > QWidget {{background:{c['bg']};border:none;}}
    {root} QMenu, {root} QComboBox QAbstractItemView {{background:{c['panel']};color:{c['text']};border:1px solid {c['line']};padding:6px;}}
    {root} QMenu::item:selected {{background:{c['raised']};color:{c['coral']};}}
    {root} QCheckBox::indicator {{width:20px;height:20px;background:{c['bg']};border:1px solid {c['muted']};border-radius:5px;}}
    {root} QCheckBox::indicator:checked {{background:{c['coral']};border-color:{c['coral']};}}
    '''
