"""Scoped Twilight Sakura presentation for numbering and episode selection."""
from app.ui.review_reference_style import reference_colors
from app.ui.home_style import px,load_fonts


def style(name):
    load_fonts();c=reference_colors();r=f'QWidget#{name}'
    background=c['raised'] if name=='season_numbers' else c['bg']
    return f'''
    {r} {{background:{background};color:{c['text']};font-family:'Plus Jakarta Sans';}}
    {r} QLabel {{background:transparent;border:none;color:{c['muted']};font-size:{px(13)}px;}}
    {r} QLabel#heading, {r} QLabel#workflow_title {{color:{c['text']};font-size:{px(24)}px;font-weight:700;}}
    {r} QLabel#workflow_row_title {{color:{c['text']};font-size:{px(16)}px;font-weight:700;}}
    {r} QLabel#season_label {{color:{c['text']};font-size:{px(14)}px;}}
    {r} QWidget#workflow_body, {r} QWidget#stepper, {r} QScrollArea, {r} QScrollArea>QWidget {{background:transparent;border:none;}}
    {r} QFrame#workflow_card {{background:{c['panel']};border:1px solid {c['line']};border-radius:14px;}}
    {r} QFrame#playback_footer {{background:{c['panel']};border:1px solid {c['line']};border-radius:14px;}}
    {r} QFrame#playback_footer QLineEdit {{background:transparent;border:none;color:{c['muted']};padding:0;}}
    {r} QLabel#season_badge {{background:{c['raised']};color:{c['ok']};border:1px solid {c['line']};border-radius:5px;padding:4px 8px;font-size:{px(11)}px;font-weight:600;}}
    {r} QLabel#season_badge[metadata='true'] {{color:{c['amber']};}}
    {r} QLineEdit, {r} QSpinBox {{background:{c['bg']};color:{c['text']};border:1px solid {c['line']};border-radius:8px;padding:6px 10px;font-family:'JetBrains Mono';font-size:{px(12)}px;}}
    {r} QSpinBox {{font-size:{px(18)}px;}}
    {r} QSpinBox:focus {{border:1px solid {c['coral']};}}
    {r} QToolButton {{background:{c['panel']};border:1px solid {c['line']};border-radius:4px;}}
    {r} QToolButton:hover {{border-color:{c['coral']};background:{c['raised']};}}
    {r} QLabel#season_notice, {r} QLabel#episode_availability {{background:{c['panel']};border:1px solid {c['line']};border-radius:10px;padding:16px;}}
    {r} QFrame#workflow_footer {{background:{c['panel']};border-top:1px solid {c['line']};}}
    {r} QPushButton {{background:{c['panel']};color:{c['text']};border:1px solid {c['line']};border-radius:10px;min-height:40px;padding:0 18px;font-size:{px(13)}px;font-weight:600;}}
    {r} QPushButton:hover {{background:{c['raised']};border-color:{c['coral']};}}
    {r} QPushButton[accent='true'] {{background:{c['coral']};color:{c['on_coral']};}}
    {r} QPushButton:disabled {{background:{c['panel']};color:{c['muted']};}}
    {r} QComboBox {{background:{c['panel']};color:{c['text']};border:1px solid {c['line']};border-radius:10px;min-height:40px;padding:0 14px;}}
    {r} QListView#episode_grid {{background:transparent;border:none;outline:none;padding:0;}}
    {r} QCheckBox {{background:transparent;color:{c['text']};spacing:12px;font-size:{px(14)}px;}}
    {r} QCheckBox::indicator {{width:20px;height:20px;border:1px solid {c['line']};border-radius:5px;background:{c['bg']};}}
    {r} QCheckBox::indicator:checked {{background:{c['coral']};border-color:{c['coral']};}}
    '''
