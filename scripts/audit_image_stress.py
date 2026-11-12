"""Isolated scrolling/thumbnail regression using copied artwork and no real DB."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['OFFLINE_MODE']='true'
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if os.environ.get('APP_PROFILE')=='1':
    from app.audit_profile import bootstrap,attach,detach,emit,memory_sample
    bootstrap()
else:
    def attach(*args,**kwargs):pass
    def detach(*args,**kwargs):pass
    def emit(*args,**kwargs):pass
    def memory_sample():return dict(rss_bytes=None,peak_rss_bytes=None,private_bytes=None)
import json
import shutil
import tempfile
import time
from PyQt5.QtCore import QTimer,QThreadPool
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication


def main():
    source=Path(__file__).resolve().parents[1]/'data'/'covers'
    synthetic='--synthetic' in sys.argv
    files=[] if synthetic else sorted(source.glob('*.jpg'))[:32]
    if not files and not synthetic:raise RuntimeError('No source artwork for the copied-artwork check.')
    from app import db,config
    with tempfile.TemporaryDirectory(prefix='anime-thumbnail-check-') as directory:
        root=Path(directory);covers=root/'covers';covers.mkdir()
        for n,path in enumerate(files):shutil.copyfile(path,covers/f'{n}.jpg')
        if synthetic:
            from PIL import Image
            for n in range(32):
                path=covers/f'{n}.jpg';Image.new('RGB',(1200,1800),(n*7,80,160)).save(path);files.append(path)
        for module in (db,config):
            module.DATA_DIR=root;module.COVERS_DIR=covers;module.EXPORTS_DIR=root/'exports'
        db.DB_PATH=root/'test.db';config.OFFLINE_MODE=True
        started=time.perf_counter();app=QApplication([]);attach(app,(time.perf_counter()-started)*1000)
        db.init_db();db.set_state('scan_schedule','manual')
        from app.ui.pages.library_page import LibraryPage
        from app.ui.refresh import thumbnail_pool
        page=LibraryPage();page.view_mode='grid';page.resize(1280,850)
        records=[dict(id=n+10000,display_title=f'Fixture {n}',title_romaji='',cover_filename=f'{n%len(files)}.jpg',
                      metadata_json='{}',watch_status='WATCHING',storage_state='NOT_DOWNLOADED',series_member_ids=[n+10000]) for n in range(128)]
        page._render_grid(records);page.show();app.processEvents()
        # Leave Qt's own rendering pool small to expose accidental pool coupling.
        QThreadPool.globalInstance().setMaxThreadCount(2)
        heartbeat=[];last=[time.perf_counter()]
        timer=QTimer();timer.setInterval(20)
        def beat():
            now=time.perf_counter();heartbeat.append(max(0,(now-last[0]-.02)*1000));last[0]=now
        timer.timeout.connect(beat);timer.start()
        emit('audit.image_stress_begin',item_count=128,copied_artwork=len(files),fixture=True)
        tours=[]
        for tour in ('cold','warm'):
            start=time.perf_counter();bar=page.page_scroll.verticalScrollBar()
            for step in list(range(21))+list(range(20,-1,-1)):
                bar.setValue(bar.maximum()*step//20);QTest.qWait(20)
            limit=time.perf_counter()+10
            while page._virtual_posters.pending and time.perf_counter()<limit:QTest.qWait(10)
            if page._virtual_posters.pending:raise RuntimeError('Thumbnail reads did not finish within 10 seconds')
            tours.append(dict(tour=tour,duration_ms=round((time.perf_counter()-start)*1000,3)))
        result=dict(records=128,copied_artwork=0 if synthetic else len(files),synthetic_artwork=len(files) if synthetic else 0,slots=len(page._virtual_posters.slots),
                    gui_stalls_over_100_ms=sum(value>100 for value in heartbeat),
                    max_heartbeat_lateness_ms=round(max(heartbeat,default=0),3),tours=tours,**memory_sample())
        emit('audit.image_stress_end',item_count=128,fixture=True,**{key:value for key,value in result.items() if key!='records'})
        timer.stop();page.hide()
        thumbnail_pool().waitForDone(5000);QThreadPool.globalInstance().waitForDone(5000)
        if hasattr(page,'_facts_worker') and page._facts_worker is not None:page._facts_worker.wait(5000)
        page.deleteLater();QTest.qWait(10);detach(app)
        print(json.dumps(result,indent=2))


if __name__=='__main__':main()
