"""Restyle visible UI sections immediately and hidden sections when opened."""
import re
from PyQt5.QtCore import QObject, QEvent
from PyQt5.QtWidgets import QWidget


def scale_inline(widget, scale):
    if widget.property('animevaultOwnScaledStyle'):return
    local = widget.styleSheet()
    if not local or "font-size" not in local or local == widget.property("animevaultScopeStyle"):
        return
    base = widget.property("animevaultBaseStyle") if widget.property("animevaultScaledStyle") == local else local
    widget.setProperty("animevaultBaseStyle", base)
    scaled = re.sub(r"(font-size:\s*)(\d+)px", lambda match: f"{match[1]}{round(int(match[2]) * scale)}px", base)
    widget.setProperty("animevaultScaledStyle", scaled)
    if local != scaled:
        widget.setStyleSheet(scaled)


class ThemeScopes(QObject):
    def __init__(self, app):
        super().__init__(app)
        self.stylesheet = None
        self.font = None
        self.applying = False

    def apply_scope(self, widget):
        if not self.stylesheet or widget.property("animevaultScopeStyle") == self.stylesheet:
            return
        if widget.property("animevaultScopeStyle") is None and self.parent().styleSheet() == self.stylesheet:
            if hasattr(widget,'refresh_home_style'):
                widget.setProperty('animevaultScopeStyle',self.stylesheet);widget.refresh_home_style()
            return
        self.applying = True
        widget.setProperty("animevaultScopeStyle", self.stylesheet)
        widget.setStyleSheet(self.stylesheet)
        if self.font is not None:
            widget.setFont(self.font)
        if hasattr(widget,'refresh_home_style'):widget.refresh_home_style()
        self.applying = False

    def update(self, stylesheet, font):
        self.stylesheet, self.font = stylesheet, font
        app = self.parent()
        scoped_windows = [w for w in app.topLevelWidgets() if w.isVisible() and w.property("animevaultScopedWindow")]
        if not scoped_windows:
            if app.styleSheet() != stylesheet:
                app.setStyleSheet(stylesheet)
            if app.font() != font:
                app.setFont(font)
            for widget in app.allWidgets():
                if widget.isVisible() and hasattr(widget,'refresh_home_style'):self.apply_scope(widget)
        else:
            scopes = [w for w in app.allWidgets() if w.isVisible() and w.property("animevaultThemeScope")]
            windows = [w for w in app.topLevelWidgets() if w.isVisible() and not w.property("animevaultScopedWindow")]
            for widget in scopes + windows:
                self.apply_scope(widget)
        scale = app.property("animevaultScale") or 1.0
        for widget in app.allWidgets():
            if widget.isVisible():
                scale_inline(widget, scale)

    def eventFilter(self, widget, event):
        if not self.applying and event.type() == QEvent.Show and isinstance(widget, QWidget):
            if widget.property("animevaultThemeScope") or widget.isWindow() and not widget.property("animevaultScopedWindow"):
                self.apply_scope(widget)
            scale_inline(widget, self.parent().property("animevaultScale") or 1.0)
        return False


def update_theme_scopes(app, stylesheet, font):
    if not hasattr(app, "_theme_scopes"):
        app._theme_scopes = ThemeScopes(app)
        app.installEventFilter(app._theme_scopes)
    app._theme_scopes.update(stylesheet, font)
