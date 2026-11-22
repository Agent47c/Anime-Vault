"""Names for preserved visual families; persisted dark/light IDs stay compatible.

Sakura includes the current layouts, typography, controls and decorative effects.
New families must provide their own presentation adapters rather than replacing it.
"""
SAKURA_FAMILY='sakura'
SAKURA_CHOICES=(('Sakura Dark','dark'),('Sakura Light','light'))
MANGA_CHOICES=(('Manga Brutalism Light','manga_light'),('Manga Brutalism Dark','manga_dark'))
THEME_CHOICES=SAKURA_CHOICES+MANGA_CHOICES
DEFAULT_THEME='dark'
THEME_IDS=frozenset(value for _,value in THEME_CHOICES)


def normalize_theme(value):
    return value if value in THEME_IDS else DEFAULT_THEME


def is_manga():
    from PyQt5.QtWidgets import QApplication
    app=QApplication.instance()
    return bool(app and app.property('animevaultThemeFamily')=='manga')


def is_manga_dark():
    from PyQt5.QtWidgets import QApplication
    app=QApplication.instance()
    return bool(app and app.property('animevaultRequestedTheme')=='manga_dark'
                and not app.property('animevaultHighContrast'))
