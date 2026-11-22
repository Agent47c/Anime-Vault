"""Theme-wide master control states, including lazily opened workflows.

Only individual visible controls are decorated; no page rebuild or timer scans.
Local styles are restored when returning to Sakura. Existing custom effects and
effect-bearing ancestors are retained to avoid nested Qt source rendering bugs.
"""
from PyQt5.QtCore import QObject,QEvent
from PyQt5.QtWidgets import QPushButton,QToolButton,QComboBox,QLineEdit,QMessageBox


def control_rules(widget):
    from app.ui.manga_style import material
    if widget.objectName()=='airing_release':
        return material('QPushButton,QPushButton:hover,QPushButton:pressed,QPushButton:focus{background:transparent;color:#111217;border:none;border-radius:0;padding:0;outline:none;}')
    if isinstance(widget,QLineEdit):
        if isinstance(widget.parentWidget(),QComboBox):return material('QLineEdit{background:transparent;color:#111217;border:none;padding:0;}')
        return material('QLineEdit{background:#e2e5ed;color:#111217;border:1px solid #bac1ce;border-radius:8px;}QLineEdit:focus{border-color:#ff2e93;}')
    if isinstance(widget,QComboBox):
        return material('QComboBox{background:white;color:#111217;border:1px solid #d6dae2;border-radius:8px;}QComboBox:hover{background:#eef0f5;border-color:#c4c9d4;color:#111217;}QComboBox:focus{border-color:#ff2e93;}QComboBox:disabled{background:#e4e7ed;color:#8a91a2;}QComboBox::drop-down{background:transparent;border:none;}')
    primary=bool(widget.property('accent') or widget.property('role')=='primary' or widget.objectName() in ('detail_play_main','detail_play_arrow'))
    status=widget.objectName()=='watch_status_option' or widget.property('entryChoice')
    # Icon-only transparent surfaces and painted controls keep their anatomy.
    rules='QPushButton{background:white;color:#111217;border:1px solid #d6dae2;border-radius:8px;outline:none;}QPushButton:hover{background:#eef0f5;color:#111217;border-color:#c4c9d4;}QPushButton:pressed{background:#dce0e9;color:#111217;}QPushButton:focus{border-color:#ff2e93;}QPushButton:checked{background:#e2e5ed;color:#111217;border-color:#ff2e93;}'
    if widget.property('chip'):
        rules+='QPushButton:checked{background:white;color:#111217;border-color:#ff2e93;}'
    if status:
        rules+='QPushButton:checked{background:#ff2e93;color:#0a0a0a;}'
    if primary:
        rules+='QPushButton{background:#ff2e93;color:#0a0a0a;}QPushButton:hover{background:#ff3b9a;color:#0a0a0a;}QPushButton:pressed{background:#ed2586;color:#0a0a0a;}'
    if widget.property('ratingChoice') or widget.property('detailRating'):
        rules+="QPushButton:checked{background:white;color:#111217;}QPushButton[ratingFilled='true'],QPushButton[rated='true']{background:#ffd336;color:#111217;border-color:#d6b128;}"
        if widget.property('ratingFilled') or widget.property('rated'):
            rules+='QPushButton,QPushButton:hover,QPushButton:checked{background:#ffd336;color:#111217;border-color:#d6b128;}'
    if widget.property('detailRating'):
        rules+='QPushButton{min-height:0;padding:0;border-radius:4px;}'
    if widget.property('role')=='destructive' or widget.property('danger') or widget.objectName()=='storage_delete':
        rules+='QPushButton{color:#b3261e;border-color:#f0b4ad;}'
    rules+='QPushButton:disabled{background:#e4e7ed;color:#8a91a2;border-color:#c4c9d4;}'
    if widget.property('quietAction'):
        rules='QPushButton{background:transparent;color:#596175;border:none;}QPushButton:hover{background:#eef0f5;color:#111217;}'
    if widget.objectName()=='watch_status_option':
        rules='QPushButton{background:transparent;color:#596175;border:none;border-radius:6px;padding:0 10px;min-height:30px;font-size:11px;}QPushButton:hover{background:#eef0f5;color:#111217;}QPushButton:checked{background:#ff2e93;color:#0a0a0a;}'
    rules=material(rules)
    from app.ui.theme_catalog import is_manga_dark
    parent=widget.parentWidget()
    if is_manga_dark() and parent and parent.objectName()=='pagination':
        rules+='QPushButton:checked{background:#e5e2e1;color:#121315;border-color:#e5e2e1;}'
    if is_manga_dark() and widget.property('ratingFilled'):
        rules+='QPushButton{color:#17120b;}'
    return rules.replace('QPushButton','QToolButton')+'QToolButton::menu-button{background:transparent;border:none;}' if isinstance(widget,QToolButton) else rules


class MangaControls(QObject):
    def __init__(self,app):super().__init__(app);self.busy=False

    def apply(self,widget):
        if self.busy or not isinstance(widget,(QPushButton,QToolButton,QComboBox,QLineEdit)):return
        from app.ui.manga_pages import active
        from app.ui.components.neumorphic import install,NeumorphicEffect
        parent=widget.parentWidget()
        enabled=active() and not(parent and parent.objectName()=='app_title_bar') and widget.objectName() not in ('qt_spinbox_lineedit','settings_theme_card')
        if isinstance(widget.window(),QMessageBox) or widget.window().property('stableAlert'):
            install(widget,enabled=False);return
        local=widget.styleSheet();applied=widget.property('mangaControlApplied')
        self.busy=True
        try:
            if isinstance(widget,QLineEdit) and not widget.property('mangaOwnPlaceholder'):
                from PyQt5.QtGui import QColor,QPalette
                from app.ui.theme_catalog import is_manga_dark
                saved=widget.property('mangaPlaceholderBase')
                palette=widget.palette()
                if enabled and is_manga_dark():
                    if saved is None:
                        widget.setProperty('mangaPlaceholderBase',palette.color(QPalette.PlaceholderText))
                    from app.ui.manga_style import manga_colors
                    palette.setColor(QPalette.PlaceholderText,QColor(manga_colors()['muted']))
                    widget.setPalette(palette)
                elif saved is not None:
                    palette.setColor(QPalette.PlaceholderText,saved)
                    widget.setPalette(palette)
                    widget.setProperty('mangaPlaceholderBase',None)
            if not enabled:
                if applied and local==applied:widget.setStyleSheet(widget.property('mangaControlBase') or '')
                if isinstance(widget,QComboBox):
                    from app.ui.components.dropdown_depth import combo_depth
                    combo_depth(widget,False)
                widget.setProperty('mangaControlApplied',None);install(widget,enabled=False);return
            if not widget.isVisible():return
            base=widget.property('mangaControlBase') if applied==local else local
            prefix=base or ''
            # Inline declarations cannot be concatenated with selector rules:
            # Qt silently ignores portions of the resulting invalid stylesheet.
            if prefix.strip() and '{' not in prefix:
                selector='QToolButton' if isinstance(widget,QToolButton) else 'QPushButton' if isinstance(widget,QPushButton) else 'QComboBox' if isinstance(widget,QComboBox) else 'QLineEdit'
                prefix=selector+'{'+prefix+'}'
            styled=prefix+'\n'+control_rules(widget)
            if local!=styled:
                widget.setProperty('mangaControlBase',base or '');widget.setProperty('mangaControlApplied',styled);widget.setStyleSheet(styled)
            if isinstance(widget,QComboBox):
                install(widget,enabled=False)
                from app.ui.components.dropdown_depth import combo_depth
                combo_depth(widget,not self.parent().property('animevaultHighContrast'));return
            if isinstance(widget,QLineEdit) and isinstance(parent,QComboBox):
                install(widget,enabled=False);return
            if widget.objectName()=='watch_status_option' or widget.property('detailRating'):
                install(widget,enabled=False);return
            if widget.property('quietAction'):
                install(widget,enabled=False);return
            # Keep the rail's blur/reveal and other bespoke painted effects.
            if widget.graphicsEffect() and not isinstance(widget.graphicsEffect(),NeumorphicEffect):return
            ancestor=widget.parentWidget()
            while ancestor:
                if ancestor.graphicsEffect():return
                ancestor=ancestor.parentWidget()
            if widget.height()<=130:install(widget,inset=isinstance(widget,QLineEdit))
        finally:
            if enabled and widget.property('mangaOwnPlaceholder'):
                from PyQt5.QtGui import QColor,QPalette
                from app.ui.manga_style import manga_colors
                palette=widget.palette()
                color=QColor(manga_colors()['muted'])
                if palette.color(QPalette.PlaceholderText)!=color:
                    palette.setColor(QPalette.PlaceholderText,color)
                    widget.setPalette(palette)
            self.busy=False

    def eventFilter(self,widget,event):
        if event.type() in (QEvent.Show,QEvent.StyleChange):self.apply(widget)
        elif event.type()==QEvent.DynamicPropertyChange and bytes(event.propertyName()) in (b'rated',b'ratingFilled'):
            self.apply(widget)
        return False


def update(app):
    if not hasattr(app,'_manga_controls'):
        app._manga_controls=MangaControls(app);app.installEventFilter(app._manga_controls)
    for widget in app.allWidgets():
        if widget.isVisible() or widget.property('mangaControlApplied'):app._manga_controls.apply(widget)
