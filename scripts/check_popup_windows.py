"""Interactive native-Windows popup check using an isolated temporary database.

Run with the project's Python interpreter; close the QA window to finish.
This does not open, scan or modify the user's library database or media.
"""
import json
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ['QT_QPA_PLATFORM']='windows'
from PyQt5.QtCore import Qt,QTimer,QObject,QEvent
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QLabel,QComboBox,QPushButton,QMenu
from app.ui.theme import apply_theme
from app.ui.components.tag_picker import TagPicker
from test_ui_regressions import Regressions


def main():
    Regressions.setUpClass();case=Regressions();case.setUp();app=case.app
    effects=(Qt.UI_AnimateCombo,Qt.UI_AnimateMenu,Qt.UI_FadeMenu)
    app._dropdown_native_effects={effect:True for effect in effects}
    app.setEffectEnabled(Qt.UI_General,True)
    for effect in effects:app.setEffectEnabled(effect,True)
    before=[app.isEffectEnabled(effect) for effect in effects]
    apply_theme(app,'manga_light')
    records=[dict(phase='theme',platform=app.platformName(),before=before,after=[app.isEffectEnabled(effect) for effect in effects])]
    window=QWidget();window.setWindowTitle('Anime Vault Popup QA - temporary data');window.resize(600,420)
    box=QVBoxLayout(window);box.setContentsMargins(30,30,30,30);box.setSpacing(22)
    box.addWidget(QLabel('Native Windows popup test — temporary data only'))
    combo=QComboBox();combo.setAccessibleName('QA sorting');combo.addItems(['Severity & date','Latest checked','Oldest checked','Title A to Z']);box.addWidget(combo)
    formats=TagPicker('Formats');formats.addItem('All formats',None);formats.addItems(['TV','MOVIE','OVA','ONA']);box.addWidget(formats)
    menu_button=QPushButton('Queue actions');menu=QMenu(menu_button)
    for label in ('Pause','Resume','Stop','Retry','Choose files','Open download folder'):menu.addAction(label)
    menu_button.setMenu(menu);box.addWidget(menu_button)
    status=QLabel('Check sorting, formats and queue actions. No real downloads are attached.');status.setWordWrap(True);box.addWidget(status)
    close=QPushButton('Close QA');close.clicked.connect(window.close);box.addWidget(close)
    class Trace(QObject):
        def eventFilter(self,obj,event):
            if obj.metaObject().className()=='QComboBoxPrivateContainer' and event.type() in (QEvent.Show,QEvent.Paint,QEvent.Hide):
                records.append(dict(event=int(event.type()),preparing=bool(obj.property('mangaPopupPreparing')),opacity=obj.windowOpacity(),geometry=list(obj.geometry().getRect())))
            return False
    trace=Trace(app);app.installEventFilter(trace)
    window.show();QTimer.singleShot(240000,window.close)
    try:app.exec_()
    finally:
        (ROOT/'data'/'popup-windows-native-check.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        app.removeEventFilter(trace);window.deleteLater();case.tearDown()


if __name__=='__main__':main()
