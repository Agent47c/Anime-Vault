"""UI-only notifications emitted after a settings worker has saved successfully."""
from PyQt5.QtCore import QObject,pyqtSignal
from PyQt5.QtWidgets import QApplication

class SettingsEvents(QObject):
    downloads_changed=pyqtSignal(object)

_events=None
def settings_events():
    global _events
    if _events is None:_events=SettingsEvents(QApplication.instance())
    return _events
