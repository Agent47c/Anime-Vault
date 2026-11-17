"""Temporary-data visual evidence for the approved compact Manga overlays."""
import os,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ['QT_QPA_PLATFORM']='offscreen'
import test_ui_regressions as support
from PyQt5.QtCore import QThread,QTimer,QCoreApplication,QEvent,Qt
from PyQt5.QtGui import QPainter,QPixmap,QLinearGradient,QColor
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtTest import QTest
from app.ui.theme import apply_theme


def write_comparisons(output):
    from PIL import Image,ImageDraw
    references=ROOT/'Light Theme (Manga Brutalism)'
    pairs=[('change-password','change_password'),('unlock','unlock_adult_anime'),('exit-choice','close_anime_vault'),('confirm-grouping','confirm_series_grouping')]
    gallery=Image.new('RGB',(1440,2000),'#eef0f5')
    for index,(name,prefix) in enumerate(pairs):
        reference=next(path/'screen.png' for path in references.iterdir() if path.name.startswith(prefix))
        sheet=Image.new('RGB',(1440,500),'#eef0f5');draw=ImageDraw.Draw(sheet)
        for x,path,title in ((10,reference,'Supplied: '+name),(730,output/(name+'.png'),'Current: '+name)):
            draw.text((x,8),title,fill='#111217')
            picture=Image.open(path).convert('RGB');picture.thumbnail((700,460));sheet.paste(picture,(x,32))
        sheet.save(output/(name+'-comparison.png'));gallery.paste(sheet,(0,index*500))
    gallery.save(output/'all-modal-comparisons.png')


def main():
    support.Regressions.setUpClass();case=support.Regressions();case.setUp()
    output=ROOT/'data'/'compact-modal-review';output.mkdir(parents=True,exist_ok=True)
    try:
        with patch.object(QThread,'start'),patch('app.ui.pages.library_page.LibraryPage._request_home_facts'):
            apply_theme(case.app,'manga_light')
            from app.ui.main_window import MainWindow,QuitConfirmDialog
            from app.ui.dialogs.adult_password_dialog import AdultPasswordDialog
            from app.ui.pages.group_series_page import GroupReview
            from app.ui.navigation import navigate
            window=MainWindow.__new__(MainWindow);QMainWindow.__init__(window);window._updater_thread=None;window._unread_updates=0;window._setup_ui()
            for timer in window.findChildren(QTimer):timer.stop()
            window.resize(1600,1000);window.show();QTest.qWait(30)
            banner=QPixmap(1400,450);p=QPainter(banner);gradient=QLinearGradient(0,0,1400,450);gradient.setColorAt(0,QColor('#8297ac'));gradient.setColorAt(1,QColor('#233950'));p.fillRect(banner.rect(),gradient)
            for x in range(0,1400,60):p.fillRect(x,0,8,450,QColor(220,230,245,70))
            p.end();hero=window.library_page.hero_card;hero._banner=banner;hero._scaled_banner_size=None;hero.show();hero.update();QTest.qWait(30)
            window.grab().save(str(output/'hero-current.png'))
            factories=[('change-password',lambda:AdultPasswordDialog(window,mode='change')),
                       ('unlock',lambda:AdultPasswordDialog(window,mode='unlock')),
                       ('exit-choice',lambda:QuitConfirmDialog(window)),
                       ('confirm-grouping',lambda:GroupReview(dict(title='Example Anime',target=1,records=[dict(id=i,display_title='Example Anime'+('' if i==1 else f' · Season {i}')) for i in range(1,5)]),window))]
            for name,factory in factories:
                page=factory()
                if isinstance(page,GroupReview):navigate(page)
                else:page.show()
                QTest.qWait(80);case.app.processEvents()
                result=window.grab();p=QPainter(result);point=window.mapFromGlobal(page.pos());p.drawPixmap(point,page.grab());p.end()
                result.save(str(output/(name+'.png')))
                print(name,'face',page._compact_modal.content.width(),'outer',page.width(),page.height(),flush=True)
                page.reject();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
                if not isinstance(page,AdultPasswordDialog):page.deleteLater()
                QTest.qWait(10)
            window.hide();window.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
            write_comparisons(output)
    finally:
        apply_theme(case.app,'dark');case.tearDown()


if __name__=='__main__':main()
