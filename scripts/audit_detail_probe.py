# AUDIT-START
"""First-visible Details timings on a DB/artwork copy, never the real database."""
import os
os.environ['APP_PROFILE']='1';os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['OFFLINE_MODE']='true'
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.audit_profile import bootstrap,attach,detach,emit,_original_connect
bootstrap()
import json
import shutil
import tempfile
import time
from contextlib import ExitStack
from unittest.mock import patch
from PyQt5.QtWidgets import QApplication,QWidget,QVBoxLayout,QStackedWidget
from PyQt5.QtTest import QTest
from app import db,config


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--render-tag')
    options=parser.parse_args()
    if options.render_tag and not options.render_tag.replace('-','').isalnum():raise ValueError('Use a simple render tag.')
    original_db=db.DB_PATH;original_covers=config.COVERS_DIR
    with tempfile.TemporaryDirectory(prefix='anime-details-audit-') as directory:
        root=Path(directory);covers=root/'covers';covers.mkdir()
        source=_original_connect(original_db.resolve().as_uri()+'?mode=ro',uri=True)
        copy=_original_connect(str(root/'copy.db'))
        try:source.backup(copy)
        finally:source.close();copy.close()
        for module in (db,config):
            module.DATA_DIR=root;module.COVERS_DIR=covers;module.EXPORTS_DIR=root/'exports'
        db.DB_PATH=root/'copy.db';config.OFFLINE_MODE=True
        connection=db.get_connection()
        try:
            candidates=[tuple(row) for row in connection.execute('SELECT f.id,count(s.id) FROM franchises f LEFT JOIN seasons s ON s.franchise_id=f.id GROUP BY f.id ORDER BY count(s.id),f.id')]
        finally:connection.close()
        local=[row for row in candidates if row[1]]
        selected=[]
        for row in (candidates[0],local[0],local[len(local)//2],local[-1]):
            if row[0] not in [item[0] for item in selected]:selected.append(row)
        for fid,_ in selected:
            series=db.get_series(fid)
            name=series.get('cover_filename')
            if name and (original_covers/name).is_file():shutil.copyfile(original_covers/name,covers/name)
        started=time.perf_counter();app=QApplication([]);attach(app,(time.perf_counter()-started)*1000)
        from app.ui.theme import apply_theme
        apply_theme(app)
        from app.ui.pages.detail_modal import DetailModal
        from app.ui.components.detail_episodes import DetailEpisodes
        from app.ui.navigation import navigate
        from app.ui.io_task import running
        from app.ui.detail_data import prepare_details
        host=QWidget();host.stacked_widget=QStackedWidget();QVBoxLayout(host).addWidget(host.stacked_widget)
        host.stacked_widget.addWidget(QWidget());host.resize(1450,900);host.show()
        results=[];active={}
        builder=DetailModal._build_ui_steps
        def timed_builder(dialog):
            iterator=builder(dialog);number=0
            while True:
                start=time.perf_counter()
                try:value=next(iterator)
                except StopIteration:
                    active['steps'].append(dict(step=number,final=True,ms=round((time.perf_counter()-start)*1000,3)))
                    return
                active['steps'].append(dict(step=number,final=False,ms=round((time.perf_counter()-start)*1000,3)))
                number+=1;yield value
        def measured_prepare(fid):
            start=time.perf_counter();value=prepare_details(fid)
            active['prepare_ms']=round((time.perf_counter()-start)*1000,3)
            return value
        def method_timer(name):
            original=getattr(DetailModal,name)
            def measured(dialog,*args,**kwargs):
                start=time.perf_counter()
                try:return original(dialog,*args,**kwargs)
                finally:active.setdefault('methods',{}).setdefault(name,[]).append(round((time.perf_counter()-start)*1000,3))
            return measured
        original_style=QWidget.setStyleSheet
        def measured_style(widget,stylesheet):
            start=time.perf_counter()
            try:return original_style(widget,stylesheet)
            finally:
                key='style_set' if stylesheet else 'style_clear'
                stat=active.setdefault(key,dict(calls=0,ms=0.))
                stat['calls']+=1;stat['ms']+=round((time.perf_counter()-start)*1000,3)
        emit('audit.detail_probe_begin',fixture=True,item_count=len(selected),render_tag=options.render_tag,source='read-only database backup and copied covers',excluded='deferred episode indexing/previews and network')
        with ExitStack() as instrumentation:
            instrumentation.enter_context(patch.object(DetailModal,'_build_ui_steps',timed_builder))
            instrumentation.enter_context(patch('app.ui.detail_data.prepare_details',measured_prepare))
            instrumentation.enter_context(patch.object(DetailEpisodes,'start'))
            instrumentation.enter_context(patch.object(QWidget,'setStyleSheet',measured_style))
            for name in ('_create_season_table','_create_modal_poster','refresh_home_style'):
                instrumentation.enter_context(patch.object(DetailModal,name,method_timer(name)))
            for fid,_ in selected:
                for visit in ('first','repeat'):
                    active.clear();active.update(fid=fid,visit=visit,steps=[])
                    start=time.perf_counter();loaded=[]
                    dialog=DetailModal(fid,host,async_load=True);dialog.loaded.connect(lambda:loaded.append(time.perf_counter()))
                    navigate(dialog)
                    end=time.perf_counter()+15
                    while not loaded and time.perf_counter()<end:QTest.qWait(5)
                    if not loaded:raise RuntimeError('Details failed to load within 15 seconds')
                    active['loaded_ms']=round((loaded[0]-start)*1000,3)
                    active['season_count']=len(dialog.seasons)
                    active['font_scale']=app.property('animevaultScale')
                    result=json.loads(json.dumps(active));results.append(result)
                    emit('audit.detail_probe_result',active['loaded_ms'],len(dialog.seasons),fixture=True,result=result)
                    if options.render_tag and visit=='first':
                        QTest.qWait(50)
                        print('Layout check',fid,'scroll',dialog.right_scroll.horizontalScrollBar().maximum(),
                              'content',dialog.right_scroll.widget().width(),'viewport',dialog.right_scroll.viewport().width(),
                              'rating',[(b.width(),b.minimumWidth(),b.minimumSizeHint().width()) for b in dialog.rating_buttons[:1]])
                        host.grab().save(str(Path(__file__).resolve().parents[1]/'audit_logs'/f'details-{options.render_tag}-{fid}.png'))
                    dialog.reject();QTest.qWait(20)
        host.hide();host.deleteLater();QTest.qWait(20)
        end=time.perf_counter()+5
        while running() and time.perf_counter()<end:QTest.qWait(10)
        detach(app);emit('audit.detail_probe_end',fixture=True,item_count=len(results))
        print(json.dumps(results,indent=2))


if __name__=='__main__':main()
# AUDIT-END
