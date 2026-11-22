"""Shared Manga master surfaces, ink and accent roles."""
import re
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsDropShadowEffect

COLORS=dict(bg='#eef0f5',panel='#ffffff',raised='#e2e5ed',text='#111217',muted='#596175',line='#c4c9d4',coral='#ff2e93',on_coral='#0a0a0a',amber='#805000',ok='#0e7a4d',blue='#1865b4',orange='#b05a00')
DARK_COLORS=dict(bg='#121315',panel='#16171a',raised='#222429',text='#e5e2e1',
                 muted='#b8929e',line='#2c2e33',coral='#ff2e93',on_coral='#0a0a0a',
                 amber='#efc078',ok='#5dd7a8',blue='#8dc5ff',orange='#ffb974',inset='#0e0f11')


def manga_colors():
    from app.ui.theme_catalog import is_manga_dark
    return DARK_COLORS if is_manga_dark() else COLORS


# Adapt legacy Manga recipes at their presentation boundary. Keep semantic
# foregrounds independent of their surfaces (e.g. pink and gold button ink).
_SURFACES={
    '#ffffff':'#16171a','white':'#16171a','#fefefe':'#16171a',
    '#eef0f5':'#121315','#eceef3':'#121315','#f6f7fb':'#191a1e',
    '#f3f5f9':'#191a1e','#f3f4f8':'#191a1e','#f5f6fa':'#191a1e','#f0f2f6':'#191a1e','#f1f3f7':'#191a1e',
    '#e2e5ed':'#222429','#e4e7ed':'#202126','#e4e7ee':'#16171a',
    '#dfe3ed':'#0e0f11','#dce0e9':'#0e0f11','#d6dbe5':'#25272b',
    '#ffe0ef':'#3a2030','#fff8fc':'#30212a','#fff1f0':'#332022','#fff3cf':'#332a20','#e1f4ec':'#192d26',
    '#e8f8f0':'#192d26','#d0d5df':'#0e0f11','#aeb5c4':'#55505a',
}
_INK={
    '#111217':'#e5e2e1','#535b6d':'#b8929e','#596175':'#b8929e',
    '#7c8599':'#ac939d','#8a91a2':'#a09198','#c4005f':'#ff73ae',
    '#805000':'#efc078','#0e7a4d':'#5dd7a8','#087b60':'#5dd7a8','#b3261e':'#ffada6','#1865b4':'#8dc5ff','#b05a00':'#ffb974',
}
_EDGES={
    '#ffffff':'#2c2e33','white':'#2c2e33','#c4c9d4':'#2c2e33',
    '#d6dae2':'#2c2e33','#bac1ce':'#303137','#aeb7ca':'#303137',
    '#e2e5ed':'#292b30','#f0b4ad':'#75434a','#b8bec9':'#292b30','#dce1eb':'#292b30','#c6ecd6':'#345447',
}
_DECLARATION=re.compile(r'(?P<key>[-\w]+)(?P<colon>:\s*)(?P<value>[^;{}]+)(?=[;}]|$)')
_COLOR=re.compile(r'#[0-9a-fA-F]{6}\b|\bwhite\b',re.I)


def material(qss):
    """Resolve the mode-specific roles of an existing Manga stylesheet."""
    from app.ui.theme_catalog import is_manga_dark
    if not is_manga_dark():
        return qss

    def declaration(match):
        key,value=match['key'],match['value']
        if key in ('color','selection-color','placeholder-text-color'):
            palette=_INK
        elif 'border' in key or key in ('gridline-color','outline'):
            palette=_EDGES
        elif 'background' in key or key=='stop':
            palette=_SURFACES
        else:
            return match[0]
        return key+match['colon']+_COLOR.sub(lambda token:palette.get(token[0].lower(),token[0]),value)

    def block(match):
        raw=match[0]
        transformed=_DECLARATION.sub(declaration,raw)
        if re.search(r'background(?:-color)?:\s*#(?:ffd336|ff2e93)\b',raw,re.I):
            transformed=re.sub(r'(?<![\w-])color:\s*#e5e2e1\b','color:#121315',transformed)
        return transformed

    # Process declaration blocks only, so a selector containing a colon
    # cannot consume the first declaration in its block.
    if '{' in qss:
        return re.sub(r'(?<=\{)[^{}]+(?=\})',block,qss)
    return block(re.match(r'(?s).*',qss))


def set_material(widget,qss):
    """Keep the original recipe so open widgets can switch modes in place."""
    widget.setProperty('mangaMaterialSource',qss)
    widget.setProperty('mangaMaterialMode',None)
    refresh_material(widget)


def clear_material(widget):
    """Return a widget to its inherited style and forget its inline recipe."""
    if widget.property('mangaMaterialSource') is not None:
        widget.setProperty('mangaMaterialSource',None)
        widget.setProperty('mangaMaterialMode',None)
    if widget.styleSheet():
        widget.setStyleSheet('')


def refresh_material(widget):
    from app.ui.theme_catalog import is_manga_dark
    source=widget.property('mangaMaterialSource')
    dark=is_manga_dark()
    if source is None or widget.property('mangaMaterialMode')==dark:
        return
    widget.setProperty('mangaMaterialMode',dark)
    style=material(source)
    if widget.styleSheet()!=style:
        widget.setStyleSheet(style)
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
        chip.setFixedSize(110 if chip.text() else 0,28);set_material(chip,'background:transparent;color:#c4005f;font:600 12px Inter;')
    else:
        from app.ui.home_style import colors
        c=colors();chip.setText('');chip.setFixedSize(28,28);chip.setPixmap(icon('calendar' if glyph=='\u653e\u9001' else 'updates' if glyph=='\u65b0\u7740' else 'library',c['amber'] if glyph=='\u653e\u9001' else c['coral']).pixmap(18,18));chip.setStyleSheet(f'background:{c["panel"]};border:none;border-radius:8px;')


def shadow(widget,blur=18,offset=7):
    """Bounded effects for shell/hero and six visible posters, never a whole grid."""
    from PyQt5.QtWidgets import QApplication
    if QApplication.instance().property('animevaultHighContrast'):widget.setGraphicsEffect(None);return
    from app.ui.theme_catalog import is_manga_dark
    effect=QGraphicsDropShadowEffect(widget);effect.setBlurRadius(blur);effect.setOffset(0,offset);effect.setColor(QColor(0,0,0,180) if is_manga_dark() else QColor(22,25,34,105));widget.setGraphicsEffect(effect)


def controls_qss():
    c=COLORS
    from app.ui.home_style import px
    return material(f'''
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
    ''')


def library_qss():
    return material(controls_qss()+'''
    QWidget#home_library,QWidget#home_content,QWidget#home_grid,QWidget#home_filter_strip,QWidget#home_sort_controls,QStackedWidget#home_views {background:#eef0f5;border:none;}
    QWidget#home_release_heading,QScrollArea#home_release_strip,QScrollArea#home_release_strip>QWidget,
    QWidget#home_release_content,QWidget#home_release_content QFrame#poster_card {background:#eef0f5;border:none;}
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
    ''')
