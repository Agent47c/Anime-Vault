"""Presentation-only segmented choices synchronized with existing entry fields."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget,QHBoxLayout,QPushButton,QButtonGroup


def configure_choices(dialog,active):
    if not hasattr(dialog,'_manga_choices'):
        if not active:return
        dialog._manga_choices=[]
        for combo in (dialog.watch_status_combo,getattr(dialog,'rating_combo',None)):
            if combo is None:continue
            panel=QWidget(combo.parentWidget());box=QHBoxLayout(panel);box.setContentsMargins(0,4,0,4);box.setSpacing(6)
            group=QButtonGroup(panel);group.setExclusive(True)
            for index in range(combo.count()):
                button=QPushButton('—' if combo is getattr(dialog,'rating_combo',None) and index==0 else combo.itemText(index));button.setCheckable(True);button.setCursor(Qt.PointingHandCursor);button.setToolTip(combo.itemText(index));button.setAccessibleName(combo.accessibleName()+': '+combo.itemText(index));group.addButton(button,index);box.addWidget(button)
                if combo is getattr(dialog,'rating_combo',None):button.setFixedWidth(36);button.setStyleSheet('padding:0;min-height:36px;')
                button.setProperty('entryChoice',True);button.setProperty('ratingChoice',combo is getattr(dialog,'rating_combo',None))
            is_rating=combo is getattr(dialog,'rating_combo',None)
            def sync(value,g=group,rating=is_rating):
                for button in g.buttons():
                    button.setChecked(g.id(button)==value)
                    if rating:
                        button.setProperty('ratingFilled',0<g.id(button)<=value)
                        button.style().unpolish(button);button.style().polish(button);button.update()
            combo.currentIndexChanged.connect(sync);group.idClicked.connect(combo.setCurrentIndex);sync(combo.currentIndex())
            combo.parentWidget().layout().addWidget(panel);dialog._manga_choices.append((combo,panel))
    for combo,panel in getattr(dialog,'_manga_choices',[]):combo.setVisible(not active);panel.setVisible(active)
