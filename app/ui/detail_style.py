"""Twilight Sakura Details presentation; shares Home's theme and font tokens."""
from app.ui.home_style import colors,px


from app.ui.button_system import unified

@unified('QDialog#series_details')
def qss():
    c=colors()
    return f'''
    QDialog#series_details, QWidget#detail_canvas, QWidget#detail_lower {{background:{c['bg']};border:none;color:{c['text']};font-family:'Plus Jakarta Sans';}}
    QWidget#detail_content, QWidget#detail_surface_clear {{background:transparent;border:none;}}
    QDialog#series_details QLabel {{background:transparent;border:none;color:{c['text']};font-size:{px(13)}px;}}
    QDialog#series_details QWidget#detail_personal {{background:transparent;border:none;}}
    QDialog#series_details QFrame#detail_hero {{background:{c['panel']};border:none;border-radius:14px;}}
    QDialog#series_details QFrame#detail_summary {{background:{c['bg']};border:none;border-radius:10px;}}
    QDialog#series_details QLabel#detail_title {{font-size:{px(28)}px;font-weight:700;}}
    QDialog#series_details QLabel#detail_section_heading {{font-size:{px(20)}px;font-weight:600;}}
    QDialog#series_details QLabel#detail_subtitle {{font-family:'Yu Gothic';font-size:{px(13)}px;color:{c['muted']};}}
    QDialog#series_details QLabel#subheading {{font-family:'JetBrains Mono';font-size:{px(11)}px;color:{c['muted']};}}
    QDialog#series_details QLabel#detail_badge {{background:{c['raised']};color:{c['muted']};border:none;border-radius:10px;padding:4px 10px;font-family:'JetBrains Mono';font-size:{px(11)}px;}}
    QDialog#series_details QLabel#detail_badge[airing='true'] {{color:{c['amber']};}}
    QDialog#series_details QPushButton {{background:{c['raised']};color:{c['text']};border:1px solid {c['line']};border-radius:16px;padding:0 12px;min-height:32px;font-size:{px(12)}px;}}
    QDialog#series_details QPushButton:hover {{background:{c['panel']};border-color:{c['coral']};}}
    QDialog#series_details QPushButton:focus {{border:2px solid {c['coral']};}}
    QDialog#series_details QFrame#detail_play_split {{background:{c['coral']};border:none;border-radius:18px;}}
    QDialog#series_details QPushButton#detail_play_main, QDialog#series_details QPushButton#detail_play_arrow {{background:{c['coral']};color:{c['on_coral']};border:none;border-radius:24px;min-height:48px;font-weight:700;}}
    QDialog#series_details QPushButton#detail_play_main {{border-top-right-radius:0;border-bottom-right-radius:0;}}
    QDialog#series_details QPushButton#detail_play_arrow {{border-top-left-radius:0;border-bottom-left-radius:0;padding:0;}}
    QDialog#series_details QPushButton#detail_play_arrow::menu-indicator {{width:0;height:0;image:none;}}
    QDialog#series_details QPushButton#detail_play_main:hover, QDialog#series_details QPushButton#detail_play_arrow:hover {{background:{c['amber']};color:{c['on_coral']};}}
    QDialog#series_details QFrame#watch_status_track {{background:transparent;border:none;}}
    QDialog#series_details QPushButton#watch_status_option {{min-height:30px;padding:0 8px;background:transparent;border:none;border-radius:14px;font-family:'JetBrains Mono';font-size:{px(11)}px;}}
    QDialog#series_details QPushButton#watch_status_option:checked {{background:{c['coral']};color:{c['on_coral']};}}
    QDialog#series_details QPushButton[detailRating='true'] {{min-height:{px(28)}px;min-width:{px(24)}px;padding:0;border:none;border-radius:5px;background:{c['raised']};color:{c['muted']};font-size:{px(11)}px;}}
    QDialog#series_details QPushButton[detailRating='true'][rated='true'] {{background:{c['amber']};color:{c['on_coral']};}}
    QDialog#series_details QTextEdit {{background:{c['bg']};color:{c['text']};border:1px solid {c['line']};border-radius:10px;padding:8px;font-size:{px(13)}px;}}
    QDialog#series_details QFrame#detail_table {{background:{c['panel']};border:1px solid {c['line']};border-radius:14px;}}
    QDialog#series_details QFrame#detail_table QWidget {{background:transparent;}}
    QDialog#series_details QFrame#detail_table QFrame#detail_row_rule {{background:{c['line']};border:none;}}
    QDialog#series_details QLabel#detail_season_title {{font-weight:700;}}
    QDialog#series_details QFrame#detail_delete_panel {{background:{c['panel']};border:1px solid {c['line']};border-radius:12px;}}
    QDialog#series_details QPushButton[danger='true'] {{color:{c['coral']};}}
    QDialog#series_details QScrollArea {{background:transparent;border:none;}}
    QDialog#series_details QScrollArea > QWidget {{background:transparent;}}
    '''
