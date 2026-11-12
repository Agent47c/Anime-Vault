"""Twilight Sakura presentation tokens for the approved Home reference."""
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase
from app.ui.button_system import unified

_fonts_loaded=False
def load_fonts():
    global _fonts_loaded
    if _fonts_loaded:return
    for name in ('PlusJakartaSans.ttf','JetBrainsMono.ttf'):
        path=Path(__file__).resolve().parents[2]/'assets'/'fonts'/name
        if path.is_file():QFontDatabase.addApplicationFont(str(path))
    # Qt's offscreen/native font databases can omit CJK fallback faces even
    # when installed on Windows. Register the system face without copying it.
    japanese=Path('C:/Windows/Fonts/YuGothR.ttc')
    if japanese.is_file():QFontDatabase.addApplicationFont(str(japanese))
    _fonts_loaded=True

def colors():
    app=QApplication.instance()
    if app.property('animevaultHighContrast'):
        palette=app.palette()
        return dict(bg=palette.window().color().name(),panel=palette.base().color().name(),raised=palette.alternateBase().color().name(),
                    text=palette.windowText().color().name(),muted=palette.text().color().name(),line=palette.windowText().color().name(),
                    coral=palette.highlight().color().name(),on_coral=palette.highlightedText().color().name(),amber=palette.text().color().name(),ok=palette.text().color().name())
    if app.property('animevaultTheme')=='light':
        return dict(bg='#f7f3f6',panel='#ffffff',raised='#eee6ee',text='#292335',muted='#66586f',line='#d4c6d6',coral='#b0284b',on_coral='#ffffff',amber='#86500c',ok='#087b60')
    return dict(bg='#14121d',panel='#201e2a',raised='#2b2834',text='#f5f3f8',muted='#b6afc7',line='#353047',coral='#ff6584',on_coral='#15131e',amber='#ffb86c',ok='#24d3a4')

def px(value):return round(value*(QApplication.instance().property('animevaultScale') or 1))

@unified('QWidget#home_library')
def qss():
    c=colors();s=QApplication.instance().property('animevaultScale') or 1
    small=round(11*s);body=round(13*s)
    return f'''
    QWidget#home_library, QWidget#home_content, QScrollArea#home_scroll, QScrollArea#home_scroll > QWidget {{ background:{c['bg']}; border:none; }}
    QWidget#home_library {{ color:{c['text']}; font-family:"Plus Jakarta Sans"; font-size:{body}px; }}
    QWidget#home_grid, QWidget#home_filter_strip, QWidget#home_sort_controls, QStackedWidget#home_views {{ background:{c['bg']};border:none; }}
    QWidget#home_library QLabel {{ color:{c['text']}; background:transparent; border:none; }}
    QWidget#home_library QLabel#home_meta {{ color:{c['muted']}; font-family:"JetBrains Mono"; font-size:{small}px; }}
    QWidget#home_library QLabel#library_connectivity {{color:{c['muted']};background:transparent;border:none;padding:0;font-size:{small}px;}}
    QWidget#home_library QLabel#library_connectivity[online='true'] {{color:{c['ok']};}}
    QWidget#home_library QLabel#library_connectivity[online='false'] {{color:{c['amber']};}}
    QWidget#home_library QFrame#home_calendar, QWidget#home_library QFrame#home_batch {{ background:{c['panel']}; border:1px solid {c['line']}; border-radius:12px; }}
    QWidget#home_library QPushButton {{ min-height:32px; border-radius:16px; padding:0 12px; background:{c['panel']}; border:1px solid {c['line']}; color:{c['text']}; }}
    QWidget#home_library QPushButton:hover {{ background:{c['raised']}; border-color:{c['coral']}; }}
    QWidget#home_library QPushButton:focus {{ border:2px solid {c['coral']}; }}
    QWidget#home_library QComboBox {{ background:{c['panel']}; border:1px solid {c['line']}; border-radius:17px; color:{c['text']}; min-height:34px; padding:0 28px 0 12px; }}
    QWidget#home_library QFrame#poster_card {{ background:transparent; border:none; }}
    QWidget#home_library QProgressBar {{ background:{c['raised']}; border:none; border-radius:2px; min-height:3px; max-height:4px; }}
    QWidget#home_library QProgressBar::chunk {{ background:{c['coral']}; border-radius:2px; }}
    QWidget#home_library QLabel#library_heading {{ font-size:{round(18*s)}px; font-weight:600; }}
    QWidget#home_library QWidget#airing_day {{ background:{c['panel']}; border:1px solid {c['line']}; border-radius:9px; }}
    QWidget#home_library QWidget#airing_day[today="true"] {{ background:{c['raised']}; border-color:{c['coral']}; }}
    QWidget#home_library QPushButton#airing_release {{ padding:0; border:none; background:transparent; text-align:left; }}
    QWidget#home_library QLabel#airing_release_title {{ font-size:{body}px; }}
    QWidget#home_library QLabel#airing_release_time, QWidget#home_library QLabel#airing_date {{ font-family:"JetBrains Mono"; font-size:{small}px; color:{c['muted']}; }}
    QWidget#home_library QLabel#airing_more {{ color:{c['coral']}; font-size:{small}px; }}
    '''
