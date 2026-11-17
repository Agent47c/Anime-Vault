"""Approved release-view controls using cached data and exact episode identities."""
import json
from datetime import datetime
from app import db


def filter_broadcasts(rows,mode,context,now):
    from app.core.download_discovery import episode_key
    def accepts(row):
        aired=row['airingAt']<=now
        if mode==1:return aired
        if mode==2:return not aired
        if mode==3:return datetime.fromtimestamp(row['airingAt']).date()==datetime.fromtimestamp(now).date()
        present=episode_key(context.get('continuous',False),context.get('season'),row['episode']) in context.get('local',{})
        if mode==4:return present
        if mode==5:return bool(context) and aired and not present
        return True
    return [row for row in rows if accepts(row)]


def presets():
    try:
        value=json.loads(db.get_state('release_filter_presets.v1','{}'))
        return value if isinstance(value,dict) else {}
    except (ValueError,TypeError):return {}


def save_preset(name,values):
    name=name.strip()[:80]
    if not name:raise ValueError('Enter a preset name.')
    data=presets();data[name]=values;db.set_state('release_filter_presets.v1',json.dumps(data))


def preset_menu(page):
    from PyQt5.QtWidgets import QMenu,QInputDialog
    menu=QMenu(page)
    def save():
        name,ok=QInputDialog.getText(page,'Save release filters','Preset name')
        if ok and name.strip():save_preset(name,dict(period=page.period.currentIndex(),sort=page.sort.currentIndex(),genres=page.genre_filter.currentData(),themes=page.theme_filter.currentData(),formats=page.format_filter.currentData(),adult=page.adult_filter.isChecked(),adult_only=page.adult_only.isChecked()))
    menu.addAction('Save current filters…',save)
    for name,values in presets().items():menu.addAction(name,lambda v=values:apply_preset(page,v))
    menu.exec_(page.presets_button.mapToGlobal(page.presets_button.rect().bottomLeft()))


def apply_preset(page,values):
    controls=[page.period,page.sort,page.genre_filter,page.theme_filter,page.format_filter,page.adult_filter,page.adult_only]
    for control in controls:control.blockSignals(True)
    try:
        page.period.setCurrentIndex(max(0,min(2,int(values.get('period',0)))));page.sort.setCurrentIndex(max(0,min(3,int(values.get('sort',0)))))
        for picker,key in ((page.genre_filter,'genres'),(page.theme_filter,'themes'),(page.format_filter,'formats')):
            chosen=values.get(key);chosen=chosen if isinstance(chosen,(tuple,list)) else [chosen]
            picker._set_selected({i for i,(_,value) in enumerate(picker.items) if value is not None and value in chosen})
        allowed=page._adult_allowed
        page.adult_filter.setChecked(allowed and bool(values.get('adult')));page.adult_only.setChecked(allowed and bool(values.get('adult_only')))
    finally:
        for control in controls:control.blockSignals(False)
    page.reset()
