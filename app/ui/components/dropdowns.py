"""Keep combo popups consistent across Windows and Qt styles."""
from PyQt5.QtCore import QObject, QEvent
from PyQt5.QtWidgets import QComboBox, QStyledItemDelegate


class DropdownStyler(QObject):
    def style_combo(self, combo):
        if combo.property("animevaultStyledDropdown"):
            return
        # Qt's native menu delegate bypasses popup item QSS on Windows.
        combo.setItemDelegate(QStyledItemDelegate(combo))
        combo.view().setMouseTracking(True)
        combo.setProperty("animevaultStyledDropdown", True)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Polish and isinstance(obj, QComboBox):
            self.style_combo(obj)
        return False


def install_dropdown_style(app):
    if not hasattr(app, "_dropdown_styler"):
        app._dropdown_styler = DropdownStyler(app)
        app.installEventFilter(app._dropdown_styler)
    for widget in app.allWidgets():
        if isinstance(widget, QComboBox):
            app._dropdown_styler.style_combo(widget)
