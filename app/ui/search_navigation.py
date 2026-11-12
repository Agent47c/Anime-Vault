"""Optional result focus after explicit search submission, never live typing."""
from PyQt5 import sip
from PyQt5.QtCore import Qt,QTimer,QPoint
from PyQt5.QtWidgets import QScrollArea,QApplication
from app import preferences


def focus_results(owner,target):
    """Reveal a results control without activating its window or a result."""
    if not preferences.enabled('search_results_focus'):return
    def reveal():
        if sip.isdeleted(owner) or sip.isdeleted(target) or not owner.isVisible() or not target.isVisible():return
        if QApplication.activePopupWidget() is not None:return
        if not preferences.enabled('search_results_focus') or not target.isEnabled():return
        ancestor=target.parentWidget()
        while ancestor:
            if isinstance(ancestor,QScrollArea) and ancestor.widget():
                top=target.mapTo(ancestor.widget(),QPoint()).y()
                ancestor.verticalScrollBar().setValue(max(0,top-16))
            ancestor=ancestor.parentWidget()
        if target.focusPolicy()==Qt.NoFocus:target.setFocusPolicy(Qt.StrongFocus)
        target.setFocus(Qt.OtherFocusReason)
    QTimer.singleShot(0,reveal)
