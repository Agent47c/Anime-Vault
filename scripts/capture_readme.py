"""Render README screenshots from fictional, isolated data, without network access.

Run: python scripts/capture_readme.py
Does not open main.py, start an API/torrent server, or read the personal library.
"""
import json
import os
import sys
import tempfile
import time
from contextlib import ExitStack
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['OFFLINE_MODE']='true'
os.environ['APP_PROFILE']='0'


def artwork(path, title, index, banner=False):
    from PIL import Image,ImageDraw,ImageFont
    width,height=(1600,600) if banner else (440,660)
    colors=[((39,25,72),(118,58,108)),((19,49,72),(50,117,137)),((58,30,57),(173,75,86)),((24,51,46),(51,126,103)),((55,40,24),(155,111,59)),((31,33,74),(91,78,163)),((49,27,55),(150,72,130)),((28,52,60),(81,128,129))]
    first,last=colors[index%len(colors)]
    image=Image.new('RGB',(width,height));draw=ImageDraw.Draw(image)
    for y in range(height):
        t=y/max(1,height-1)
        draw.line((0,y,width,y),fill=tuple(round(a*(1-t)+b*t) for a,b in zip(first,last)))
    for step in range(5):
        x=int(width*(.3+step*.17));y=int(height*(.35+step*.08));radius=int(width*(.12+step*.035))
        draw.ellipse((x-radius,y-radius,x+radius,y+radius),outline=tuple(min(255,c+24) for c in first),width=3)
    font=ImageFont.truetype(str(ROOT/'assets/fonts/PlusJakartaSans.ttf'),92 if banner else 110)
    draw.text((int(width*.13),int(height*.59)),''.join(word[0] for word in title.split()[:2]),font=font,fill='#f5f3f8')
    image.save(path)


def main():
    from app import db,config
    output=ROOT/'docs/screenshots';output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='anime-vault-readme-') as directory,ExitStack() as stack:
        root=Path(directory)
        for module in (db,config):
            for key,value in {'DATA_DIR':root,'DB_PATH':root/'library.db','COVERS_DIR':root/'covers','EXPORTS_DIR':root/'exports'}.items():
                if hasattr(module,key):stack.enter_context(patch.object(module,key,value))
        config.COVERS_DIR.mkdir(parents=True)
        config.OFFLINE_MODE=True
        db.init_db()
        db.set_state('downloads.settings',json.dumps({'destination':'D:/Anime Vault/Downloads','enabled':False}))
        for key,value in {'scan_schedule':'manual','metadata_auto':'0','theme':'dark','reduce_motion':'1','decorations':'1'}.items():db.set_state(key,value)
        titles=['Starlight Academy','Moonlit Voyage','The Last Sky Courier','Beyond the Azure Gate','Echoes of Tomorrow','Crimson Orbit','Silverwind Chronicles','Clockwork Garden']
        calendar=[];identifiers=[]
        monday=datetime.now().replace(hour=20,minute=30,second=0,microsecond=0)-timedelta(days=datetime.now().weekday())
        for i,title in enumerate(titles):
            cover=f'demo-{i}.png';banner=f'banner-{i}.png'
            artwork(config.COVERS_DIR/cover,title,i);artwork(config.COVERS_DIR/banner,title,i,True)
            folder=root/'Demo Library'/title/'Season 01';folder.mkdir(parents=True)
            files=[]
            for ep in range(1,9):
                filename=f'{title} - S01E{ep:02}.mkv';(folder/filename).write_bytes(b'fictional screenshot fixture');files.append(filename)
            stamp=int((monday+timedelta(days=i%7)).timestamp())
            metadata={'id':900000+i,'title':{'english':title,'romaji':title},'format':'TV','status':'RELEASING','episodes':12,'genres':['Adventure','Fantasy'],'nextAiringEpisode':{'episode':9,'airingAt':stamp}}
            fid=db.upsert_franchise({'anilist_id':900000+i,'display_title':title,'title_en':title,'title_romaji':title,'genres':json.dumps(['Adventure','Fantasy']),'synopsis':'A new journey begins beyond the familiar horizon. Follow a small group of friends as they discover a changing world, unexpected allies and the courage to choose their own path.','cover_filename':cover,'banner_filename':banner,'metadata_json':json.dumps(metadata),'storage_state':'ON_DISK','watch_status':'WATCHING' if i%3==0 else 'WATCHED','total_size_bytes':(i+2)*1024**3,'root_folder_path':str(folder.parent)})
            db.upsert_season({'franchise_id':fid,'season_number':1,'title_display':title+' · Season 1','season_folder_path':str(folder),'video_files_json':json.dumps(files),'size_bytes':(i+2)*1024**3,'storage_state':'ON_DISK','episodes_total':12,'airing_status':'RELEASING','next_airing_at':stamp,'next_airing_ep':9})
            calendar.append({'mediaId':900000+i,'episode':9,'airingAt':stamp});identifiers.append(fid)
            if i<3:db.publish_updates(fid,'Episode 9 airing soon')
        db.set_state('release_calendar.v1',json.dumps(calendar));db.set_state('last_franchise_id',str(identifiers[0]))
        from PyQt5.QtWidgets import QApplication,QMainWindow,QLabel,QLineEdit
        from PyQt5.QtGui import QFontDatabase,QFont
        from PyQt5.QtCore import QCoreApplication,QEvent
        from PyQt5.QtTest import QTest
        app=QApplication.instance() or QApplication([])
        for filename in ('segoeui.ttf','segoeuib.ttf'):
            font=Path('C:/Windows/Fonts')/filename
            if font.is_file():QFontDatabase.addApplicationFont(str(font))
        app.setFont(QFont('Segoe UI',10))
        disk={'total':2*1024**4,'used':int(1.4*1024**4),'free':int(.6*1024**4),'label':'Demo drive','configured':True,'unavailable':[]}
        stack.enter_context(patch('app.core.storage.disk_snapshot',return_value=disk))
        stack.enter_context(patch('app.ui.artwork.cached_online',return_value=False))
        stack.enter_context(patch('app.core.player_icons.cached_icons',return_value={}))
        from app.ui.theme import apply_theme
        from app.ui.main_window import MainWindow
        from app.ui.pages.downloads_page import DownloadsPage
        from app.ui.io_task import running
        apply_theme(app,'dark')
        stack.enter_context(patch.object(DownloadsPage,'refresh'))
        window=MainWindow.__new__(MainWindow);QMainWindow.__init__(window)
        window._updater_thread=None;window._unread_updates=3;window._dirty_pages=set();window._shutdown_pending=False;window._navigation_pages=[]
        with patch.object(window,'_on_nav_clicked'),patch.object(DownloadsPage,'refresh'):
            window._setup_ui()
        window.resize(1600,1100);window.show();window._task_timer.stop();window.downloads_page.timer.stop()
        window.home_header.metrics(disk,3,0)
        window.library_page._set_view_mode('grid')
        window.library_page.refresh_display()
        def capture(name,widget):
            index=window.stacked_widget.indexOf(widget)
            for number,button in window.home_header.tabs.items():button.setProperty('active',number==(index if index<6 else 0));button.update()
            window.stacked_widget.setCurrentWidget(widget);QTest.qWait(250)
            for label in window.findChildren(QLabel):
                if str(root) in label.text():label.setText(label.text().replace(str(root),'D:\\Anime Vault Demo'))
            for field in window.findChildren(QLineEdit):
                if str(root) in field.text():field.setText(field.text().replace(str(root),'D:\\Anime Vault Demo'))
            app.processEvents()
            if not window.grab().save(str(output/(name+'.png'))):raise RuntimeError('Could not save '+name)
            print('Rendered',name,flush=True)
        capture('library',window.library_page)
        from app.ui.pages.detail_modal import DetailModal
        details=DetailModal(identifiers[0],window);window.stacked_widget.addWidget(details)
        capture('series-details',details)
        window.updates_page.refresh();capture('updates',window.updates_page)
        capture('organizer',window.organizer_page)
        capture('settings',window.settings_page)
        window.downloads_page.loaded([{'id':'demo-completed','fid':identifiers[0],'title':'Starlight Academy · Episode 8','release_title':'Starlight Academy - S01E08','episode_keys':['EPISODE:S1:8'],'destination':str(root/'Downloads'),'engine':'builtin','indexed':True,'desired':'running','status':'Completed','progress':1,'downloaded':450*1024**2,'total':450*1024**2,'download_rate':0}])
        capture('downloads',window.downloads_page)
        window.hide();end=time.monotonic()+10
        while running() and time.monotonic()<end:QTest.qWait(10)
        if running():raise RuntimeError('Fixture workers did not stop')
        window.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);app.processEvents()


if __name__=='__main__':main()
