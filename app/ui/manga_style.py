"""Shared light master tokens. Sakura never uses this presentation module."""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsDropShadowEffect

COLORS=dict(bg='#eef0f5',panel='#ffffff',raised='#e2e5ed',text='#111217',muted='#596175',line='#c4c9d4',coral='#ff2e93',on_coral='#0a0a0a',amber='#805000',ok='#0e7a4d',blue='#1865b4',orange='#b05a00')
_fonts_loaded=False


def load_fonts():
    global _fonts_loaded
    if _fonts_loaded:return
    from pathlib import Path
    from PyQt5.QtGui import QFontDatabase
    root=Path(__file__).resolve().parents[2]/'assets/fonts'
    for name in ('Inter.ttf','NotoSerif.ttf'):QFontDatabase.addApplicationFont(str(root/name))
    _fonts_loaded=True


def section_chip(chip,glyph):
    from app.ui.theme_catalog import is_manga
    from app.ui.icons import icon
    from PyQt5.QtGui import QPixmap
    if is_manga():
        chip.setPixmap(QPixmap());chip.setText('/// TRACKER' if glyph=='\u653e\u9001' else '/// NEW' if glyph=='\u65b0\u7740' else '')
        chip.setFixedSize(110 if chip.text() else 0,28);chip.setStyleSheet('background:transparent;color:#c4005f;font:600 12px Inter;')
    else:
        from app.ui.home_style import colors
        c=colors();chip.setText('');chip.setFixedSize(28,28);chip.setPixmap(icon('calendar' if glyph=='\u653e\u9001' else 'updates' if glyph=='\u65b0\u7740' else 'library',c['amber'] if glyph=='\u653e\u9001' else c['coral']).pixmap(18,18));chip.setStyleSheet(f'background:{c["panel"]};border:none;border-radius:8px;')


def shadow(widget,blur=18,offset=7):
    """Bounded effects for shell/hero and six visible posters, never a whole grid."""
    from PyQt5.QtWidgets import QApplication
    if QApplication.instance().property('animevaultHighContrast'):widget.setGraphicsEffect(None);return
    effect=QGraphicsDropShadowEffect(widget);effect.setBlurRadius(blur);effect.setOffset(0,offset);effect.setColor(QColor(22,25,34,105));widget.setGraphicsEffect(effect)


def controls_qss():
    c=COLORS
    from app.ui.home_style import px
    return f'''
    QWidget {{color:{c['text']};font-family:Inter;font-size:{px(14)}px;}}
    QLabel {{background:transparent;border:none;}}
    QPushButton {{background:white;color:{c['text']};border:1px solid #d6dae2;border-radius:10px;min-height:{px(40)}px;padding:0 16px;font-weight:600;}}
    QPushButton:hover {{background:#eef0f5;color:#111217;border-color:#c4c9d4;}}
    QPushButton:pressed {{background:#dce0e9;color:#0a0a0a;}}
    QPushButton:checked {{background:{c['raised']};border-color:{c['coral']};}}
    QPushButton[accent='true'],QPushButton[role='primary'] {{background:{c['coral']};color:{c['on_coral']};border:none;}}
    QPushButton[accent='true']:hover,QPushButton[role='primary']:hover {{background:#ff3b9a;color:#0a0a0a;}}
    QPushButton[accent='true']:pressed,QPushButton[role='primary']:pressed {{background:#ed2586;color:#0a0a0a;}}
    QPushButton:disabled {{color:#8a91a2;background:#e4e7ed;}}
    QLineEdit,QComboBox {{background:#e2e5ed;color:{c['text']};border:1px solid #bac1ce;border-radius:8px;min-height:{px(40)}px;padding:0 12px;}}
    QLineEdit:focus,QComboBox:focus {{border:2px solid #c4005f;}}
    QAbstractSpinBox QLineEdit {{min-height:0;border:none;background:transparent;padding:0;}}
    QScrollArea,QScrollArea>QWidget>QWidget {{background:{c['bg']};border:none;}}
    QScrollBar:vertical {{background:transparent;width:10px;}}
    QScrollBar::handle:vertical {{background:#aeb5c4;border-radius:5px;min-height:24px;}}
    QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{height:0;}}
    '''


def library_qss():
    return controls_qss()+'''
    QWidget#home_library,QWidget#home_content,QWidget#home_grid,QWidget#home_filter_strip,QWidget#home_sort_controls,QStackedWidget#home_views {background:#eef0f5;border:none;}
    QFrame#home_calendar {background:transparent;border:none;}
    QLabel#library_heading {font-family:'Noto Serif';font-size:27px;font-weight:800;}
    QLabel#home_meta,QLabel#subheading {color:#596175;}
    QWidget#home_library QComboBox#library_sort {background:white;border:1px solid white;}
    QWidget#home_library QComboBox#library_sort:hover {background:#eef0f5;color:#111217;}
    QFrame#airing_day {background:#f6f7fb;border:1px solid white;border-radius:14px;}
    QFrame#airing_day[today='true'] {background:white;border:2px solid #ff2e93;}
    QLabel#airing_date {color:#596175;font-family:Inter;font-size:12px;font-weight:700;}
    QLabel#airing_today_badge {background:#ff2e93;color:black;border-radius:4px;padding:3px 7px;font-weight:700;}
    QLabel#airing_release_dot {background:#ff2e93;border-radius:4px;}
    QWidget#home_library QPushButton#airing_release {background:transparent;border:none;padding:0;min-height:0;text-align:left;color:#111217;}
    QLabel#airing_empty {color:#7c8599;font-family:Inter;font-size:13px;font-weight:400;}
    QProgressBar {background:#d6dbe5;border:none;border-radius:2px;}
    QProgressBar::chunk {background:#ff2e93;border:none;border-radius:2px;}
    QFrame#pagination {background:white;border:1px solid white;border-radius:18px;}
    QFrame#pagination QPushButton {min-width:34px;padding:0 10px;}
    QWidget#home_filter_strip {background:#dfe3ed;border:none;border-radius:12px;}
    QFrame#pagination QPushButton {background:#eef0f5;border:1px solid white;}
    QFrame#pagination QPushButton:checked {background:white;color:#111217;}
    QFrame#pagination QPushButton:hover:enabled {background:#eef0f5;color:#111217;}
    QFrame#pagination QPushButton:pressed:enabled {background:#dce0e9;color:#0a0a0a;}
    QFrame#pagination QPushButton:disabled {background:#e4e7ed;color:#8a91a2;}
    QFrame#airing_day:hover {border-color:#ff2e93;}
    '''
