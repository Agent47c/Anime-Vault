"""Names for preserved visual families; persisted dark/light IDs stay compatible.

Sakura includes the current layouts, typography, controls and decorative effects.
New families must provide their own presentation adapters rather than replacing it.
"""
SAKURA_FAMILY='sakura'
SAKURA_CHOICES=(('Sakura · Match Windows','system'),('Sakura Dark','dark'),('Sakura Light','light'))
THEME_CHOICES=SAKURA_CHOICES+(('Manga Brutalism Light','manga_light'),)


def is_manga():
    from PyQt5.QtWidgets import QApplication
    app=QApplication.instance()
    return bool(app and app.property('animevaultThemeFamily')=='manga')
