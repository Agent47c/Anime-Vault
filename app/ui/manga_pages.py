"""Page-specific treatments built from the approved Manga light master tokens."""
from app.ui.manga_style import material
from app.ui.manga_style import controls_qss, COLORS
from app.ui.home_style import px


def active():
    from PyQt5.QtWidgets import QApplication
    from app.ui.theme_catalog import is_manga
    return is_manga() and not QApplication.instance().property('animevaultHighContrast')


def page_qss(name):
    r=f'QWidget#{name}'
    return material(controls_qss()+f'''
    {r} {{background:#eef0f5;color:#111217;}}
    QWidget#metadata_rematch {{background:white;border:1px solid #e2e5ed;border-radius:22px;}}
    {r} QScrollArea, {r} QScrollArea>QWidget, {r} QWidget#workflow_body, {r} QWidget#workflow_field,
    {r} QWidget#transfer_clear {{background:transparent;border:none;}}
    {r} QLabel#workflow_title, {r} QLabel#transfer_heading {{font:800 {px(28)}px 'Noto Serif';color:#111217;}}
    {r} QLabel#workflow_row_title, {r} QLabel#update_title {{font:700 {px(19)}px Inter;color:#111217;}}
    {r} QLabel#subheading, {r} QLabel#workflow_hint {{color:#596175;}}
    {r} QFrame#transfer_panel {{background:transparent;border:none;}}
    {r} QFrame#update_card, {r} QFrame#final_panel, {r} QFrame#result_card {{background:white;border:1px solid white;border-radius:16px;}}
    {r} QFrame#update_card {{border-left:5px solid #ff2e93;}}
    {r} QFrame#update_card QPushButton {{padding:0 5px;font-size:{px(11)}px;}}
    {r} QFrame#update_card[selected='true'], {r} QFrame#result_card[selected='true'] {{border:2px solid #ff2e93;}}
    {r} QFrame#workflow_card {{background:#e2e5ed;border:1px solid #c4c9d4;border-radius:12px;}}
    {r} QLabel#update_tag {{color:#c4005f;font:600 {px(11)}px 'JetBrains Mono';}}
    {r} QLabel#workflow_match {{background:white;color:#0e7a4d;border:1px solid #c4c9d4;border-radius:8px;padding:5px 12px;}}
    {r} QFrame#workflow_footer {{background:#eef0f5;border-top:1px solid #c4c9d4;}}
    {r} QPushButton[chip='true'] {{background:white;border:1px solid white;border-radius:8px;}}
    {r} QPushButton[chip='true']:checked {{background:#ff2e93;color:#0a0a0a;}}
    {r} QCheckBox, {r} QRadioButton {{background:transparent;color:#111217;spacing:10px;}}
    {r} QCheckBox::indicator, {r} QRadioButton::indicator {{width:20px;height:20px;border:2px solid #596175;background:white;border-radius:5px;}}
    {r} QCheckBox::indicator:checked, {r} QRadioButton::indicator:checked {{background:#ff2e93;border-color:#c4005f;}}
    ''')


def details_qss():
    return material(controls_qss()+f'''
    QDialog#series_details, QWidget#detail_canvas, QWidget#detail_lower {{background:#eef0f5;color:#111217;}}
    QWidget#detail_content, QWidget#detail_personal, QWidget#detail_surface_clear {{background:transparent;border:none;}}
    QFrame#detail_hero {{background:#f6f7fb;border:1px solid white;border-radius:22px;}}
    QLabel#detail_title {{font:800 {px(28)}px 'Noto Serif';}}
    QLabel#detail_section_heading {{font:700 {px(22)}px 'Noto Serif';}}
    QLabel#detail_subtitle, QLabel#subheading {{color:#596175;}}
    QLabel#detail_badge {{background:#e2e5ed;color:#535b6d;border:1px solid white;border-radius:6px;padding:5px 10px;}}
    QLabel#detail_badge[airing='true'] {{color:#c4005f;border-color:#ff2e93;}}
    QFrame#detail_summary {{background:transparent;border:none;}}
    QFrame#watch_status_track {{background:#e2e5ed;border:1px solid white;border-radius:12px;}}
    QFrame#detail_personal_band {{background:#dfe3ed;border:1px solid white;border-radius:12px;}}
    QWidget#detail_personal {{background:transparent;border:none;}}
    QDialog#series_details QTextEdit {{background:#eef0f5;border:1px solid white;border-radius:8px;padding:6px;}}
    QPushButton#watch_status_option {{background:transparent;border:none;border-radius:8px;min-height:36px;padding:0 12px;}}
    QPushButton#watch_status_option:checked {{background:#ff2e93;color:#0a0a0a;}}
    QPushButton[detailRating='true'] {{background:white;color:#596175;min-height:0;padding:0;border-radius:5px;}}
    QPushButton[detailRating='true'][rated='true'] {{background:#ffd336;color:#111217;}}
    QDialog#series_details QPushButton#detail_play_main, QDialog#series_details QPushButton#detail_play_arrow {{background:#ff2e93;color:#0a0a0a;border:none;}}
    QDialog#series_details QPushButton#detail_play_main:hover, QDialog#series_details QPushButton#detail_play_arrow:hover {{background:#ff54a5;color:#0a0a0a;}}
    QDialog#series_details QPushButton#detail_play_main, QDialog#series_details QPushButton#detail_play_arrow {{border-radius:8px;}}
    QFrame#detail_table, QFrame#detail_delete_panel {{background:white;border:1px solid white;border-radius:16px;}}
    QFrame#detail_row_rule {{background:#e2e5ed;}}
    QLabel#detail_season_title {{font-weight:700;}}
    QTextEdit {{background:white;color:#111217;border:1px solid #c4c9d4;border-radius:8px;padding:8px;}}
    QScrollArea,QScrollArea>QWidget {{background:transparent;border:none;}}
    ''')


def entry_qss(name):
    r=f'QDialog#{name}'
    return material(controls_qss()+f'''
    {r} {{background:#eef0f5;border:1px solid white;border-radius:20px;}}
    {r} QWidget#twilight_header, {r} QFrame#twilight_footer {{background:#eef0f5;border-bottom:1px solid #c4c9d4;}}
    {r} QWidget#twilight_body, {r} QWidget#twilight_field, {r} QWidget#twilight_field_inner {{background:transparent;border:none;}}
    {r} QLabel#twilight_title {{font:800 {px(28)}px 'Noto Serif';}}
    {r} QLabel#twilight_subtitle, {r} QLabel#entry_field_helper, {r} QLabel#entry_field_meta {{color:#596175;}}
    {r} QLabel#entry_section_heading {{font-weight:700;}}
    {r} QFrame#twilight_section_card {{background:transparent;border:none;}}
    {r} QLabel#workflow_poster {{background:white;border:5px solid white;border-radius:14px;}}
    {r} QTextEdit {{background:#e2e5ed;color:#111217;border:1px solid #bac1ce;border-radius:8px;padding:12px;}}
    {r} QLabel#entry_field_label {{font-weight:600;}}
    {r} QPushButton[entryChoice='true']:checked {{background:#ff2e93;color:#0a0a0a;border-color:#ff2e93;}}
    {r} QPushButton[ratingChoice='true']:checked {{background:#ffd336;color:#111217;border:2px solid #111217;}}
    {r} QPushButton[ratingFilled='true'] {{background:#ffd336;color:#111217;border-color:#d6b128;}}
    {r} QLineEdit#entry_native_input {{font-family:'Yu Gothic UI';}}
    ''')
