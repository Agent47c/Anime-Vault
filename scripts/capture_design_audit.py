"""Render every supplied Manga surface against isolated, populated fixtures.

Run with the test interpreter. No live network, torrent or personal DB access.
Output is review evidence, not an automatic visual-fidelity certification.
"""
import os, sys, json, traceback
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PyQt5.QtCore import QThread, Qt, QEvent, QCoreApplication
from PyQt5.QtWidgets import QLabel, QPushButton, QWidget, QStackedWidget, QVBoxLayout, QDialog, QMainWindow
from PyQt5.QtTest import QTest
from PIL import Image, ImageDraw, ImageOps
import test_ui_regressions as support
from app import db
from app.ui.theme import apply_theme


def main():
    output = ROOT/'data'/'design-audit-complete-2026-11-16'
    output.mkdir(parents=True, exist_ok=True)
    fixture = support.Regressions()
    fixture.setUpClass(); fixture.setUp()
    app = fixture.app
    findings = []
    try:
        with ExitStack() as stack:
            # Patch before imports so aliases receive the safe synchronous reader.
            def immediate(owner, operation, success): success(operation())
            stack.enter_context(patch('app.ui.io_task.start', side_effect=immediate))
            stack.enter_context(patch.object(QThread, 'start'))
            stack.enter_context(patch('app.ui.pages.library_page.LibraryPage._request_home_facts'))
            apply_theme(app, 'manga_light')
            temp = Path(fixture.temp.name)
            folder = temp/'Example Anime'/'Season 01'; folder.mkdir(parents=True)
            files = [f'Example Anime - S01E{i:02}.mkv' for i in range(1,9)]
            for name in files: (folder/name).write_bytes(b'fixture')
            media = dict(id=21,title=dict(english='Example Anime',romaji='Example Romaji',native='アニメ'),
                         description='A group of friends sets out on an extraordinary adventure. This is fixture metadata for layout review.',
                         status='RELEASING',format='TV',genres=['Action','Adventure'],episodes=24,
                         startDate=dict(year=2026,month=10,day=1),averageScore=82,
                         nextAiringEpisode=dict(episode=9,airingAt=1794920000),relations=dict(edges=[]))
            db.upsert_franchise(dict(id=fixture.fid,anilist_id=21,display_title='Example Anime',metadata_json=json.dumps(media),
                                    synopsis=media['description'],watch_status='WATCHING',storage_state='ON_DISK',
                                    has_new_update=1,update_details='Episode 9 airing soon'))
            # upsert_franchise uses provider identity; recover its actual fixture ID.
            fid = fixture.fid
            sid = db.upsert_season(dict(franchise_id=fid,title_display='Season 01',season_number=1,anilist_id=21,
                                  season_folder_path=str(folder),storage_state='ON_DISK',episode_count=8,
                                  video_files_json=json.dumps(files),size_bytes=8*1024**3))
            for i in range(2,13): db.upsert_franchise(dict(display_title=f'Example Series {i}',watch_status='PLAN_TO_WATCH'))
            from app.ui.pages.library_page import LibraryPage
            from app.ui.pages.detail_modal import DetailModal
            from app.ui.pages.release_news_page import ReleaseNewsPage
            from app.ui.pages.episode_page import EpisodePage
            from app.ui.dialogs.adult_password_dialog import AdultPasswordDialog
            from app.ui.main_window import QuitConfirmDialog
            from app.ui.pages.release_search_page import ConfirmCoverage, DownloadReview, ReleaseSearchPage
            from app.ui.pages.group_series_page import GroupReview, GroupSeriesPage
            from app.ui.downloads import DownloadsDrawer
            from app.ui.pages.downloads_page import DownloadsPage
            from app.ui.dialogs.custom_entry import CustomEntryDialog
            from app.ui.dialogs.season_file_moves import SeasonFileMoves
            from app.ui.pages.coverage_page import CoveragePage
            from app.ui.pages.full_calendar_page import FullCalendarPage
            from app.ui.dialogs.watched_import_dialog import WatchedImportDialog
            from app.ui.pages.merge_page import MergePage
            from app.ui.pages.organizer_page import OrganizerPage
            from app.ui.pages.update_review_page import UpdateReviewPage
            from app.ui.dialogs.rematch_dialog import RematchDialog
            from app.ui.pages.duplicate_page import DuplicatePage
            from app.ui.download_setup import DownloadSetup
            from app.ui.pages.settings_page import SettingsPage
            from app.ui.pages.storage_page import StoragePage
            from app.ui.pages.updates_page import UpdatesPage
            from app.ui.components.operation_progress import OperationProgress
            stack.enter_context(patch.object(ReleaseNewsPage, 'load'))
            stack.enter_context(patch.object(UpdateReviewPage, 'load'))
            record = dict(db.get_franchise(fid))
            context = dict(title='Example Anime',fid=fid,season=1,local={},pending={},missing=['EPISODE:S1:9'])
            entries = [dict(title=f'[Encoder] Example Anime - {i:02} [1080p]',episodes=[i],season=1,
                            episode_keys=[f'EPISODE:S1:{i}'],quality='1080p',group='Encoder',size='420 MB') for i in (9,10)]
            def broadcast():
                page=ReleaseNewsPage(media_id=21)
                page.render(dict(Media=media,Page=dict(pageInfo=dict(hasNextPage=False),airingSchedules=[dict(episode=9,airingAt=1794920000)])))
                return page
            def news():
                page=ReleaseNewsPage()
                page.render(([dict(media,id=i,title=dict(english=f'Example release {i}')) for i in range(100,108)],True))
                return page
            def episode():
                page=EpisodePage(fid)
                page._loaded([dict(title=f'Episode {i}',type='Season 01',kind='SEASON',season_id=sid,episode=i,episodes=[i],path=str(folder/name),season=1,
                                   release_state='AIRED',release_title='Season 01') for i,name in enumerate(files,1)],[])
                return page
            def full_calendar():
                import calendar
                from datetime import timedelta
                page=FullCalendarPage();first=page.month-timedelta(days=page.month.weekday())
                last=page.month.replace(day=calendar.monthrange(page.month.year,page.month.month)[1]);last+=timedelta(days=6-last.weekday())
                page.render(first,last,[dict(franchise_id=fid,title='Example Anime',episode=9,airing_at=1794920000)])
                return page
            def transfers():
                page=DownloadsPage()
                page.items=[dict(id=str(i),title='Example Anime',release_title=f'Example Anime - {i:02} [1080p]',
                                 status=state,episode_keys=[f'EPISODE:S1:{i}'],destination=str(folder),
                                 downloaded=420*1024**2,total=420*1024**2,progress=1) for i,state in enumerate(('Completed','Seeding','Paused','Downloading'),1)]
                page.render();return page
            def search():
                page=ReleaseSearchPage(None,fid)
                page.results=[dict(entry,identity=str(i),source='Nyaa',seeders=40,status='Match Uncertain') for i,entry in enumerate(entries)]
                page.render();return page
            def importer():
                page=WatchedImportDialog()
                page._add_item_row(dict(raw_title='Example Anime',matched_title='Example Anime',status='MATCHED',confidence=95,anilist_media=media))
                page._refresh_summary();return page
            def organizer():
                page=OrganizerPage();item=dict(anime_name='Example Anime',anime_path=str(folder.parent),video_count=8,
                                               status_badge='Season 01',is_organized=False,moves=[])
                page._on_scan_finished(dict(unorganized=[item],organized=[],all=[item]))
                return page
            def merge():
                page=MergePage();page.plan=dict(destination=str(temp/'Library'),errors=[],moves=[dict(series='Example Anime',source=str(folder/files[0]),
                     target=str(temp/'Library'/'Example Anime'/'Season 01'/files[0]),bytes=1024**3,review_reason='')])
                page.render();return page
            def changes(title):
                page=UpdateReviewPage(None,title,['Episode 9 airing soon'],[fid],fid)
                page._entries=[dict(fid=fid,raw='Episode 9 airing soon',text='Episode 9 airing soon',title=title,date=(2026,10,1),assignment_context=context)]
                page.render(['Episode 9 airing soon']);page.status.setText('Saved updates loaded.');return page
            def master():
                # Build the real shell without tray, watchers, startup scans,
                # connectivity checks, geometry persistence or playback polling.
                from app.ui.main_window import MainWindow
                from PyQt5.QtCore import QTimer
                page=MainWindow.__new__(MainWindow);QMainWindow.__init__(page)
                page._updater_thread=None;page._unread_updates=0;page._setup_ui()
                for timer in page.findChildren(QTimer):timer.stop()
                return page
            def rematch():
                page=RematchDialog(fid);page._on_results_ready([media,dict(media,id=22,title=dict(english='Example Anime Season 2'))]);return page
            def duplicates():
                page=DuplicatePage();page._results(([dict(files=[dict(path=str(folder/name),title='Example Anime',episodes=[1],signature=[100,0,0]) for name in files[:3]])],[]));page.tree.expandAll();return page
            def progress():
                page=OperationProgress(None,'Scanning library files');page.report('Checking Example Anime - S01E09.mkv',68,100);return page
            factories = [
                ('Anime Details',lambda:DetailModal(fid)),('broadcast_release_updates_',broadcast),
                ('change_password',lambda:AdultPasswordDialog(mode='change')),('choose_episode',episode),
                ('close_anime_vault',lambda:QuitConfirmDialog()),
                ('confirm_2_selected_downloads',lambda:ConfirmCoverage(None,entries,context,lambda _:None)),
                ('confirm_review_downloads_',lambda:DownloadReview(None,fid,entries,context)),
                ('confirm_series_grouping',lambda:GroupReview(dict(title='Example Anime',target=fid,records=[record]))),
                ('downloads_transfer_engine',lambda:DownloadsDrawer(fid=fid)),('downloads_transfers_',transfers),
                ('Edit Anime Entry',lambda:CustomEntryDialog(record)),('edit_season_numbers',lambda:SeasonFileMoves(fid)),
                ('episode_coverage',lambda:CoveragePage(fid)),('find_download_files',search),
                ('full_calendar',full_calendar),('group_seasons_arcs',lambda:GroupSeriesPage(fid)),
                ('import_watched_list',importer),('Main Screen',master),
                ('merge_libraries',merge),('new_anime_releases Light',news),
                ('new_anime_releases Tags',lambda:tag_popup(news())),('Operation Progress',progress),
                ('organize_file_management',organizer),
                ('overlord_view_changes',lambda:changes('Overlord')),
                ('Rematch Anime Metadata',rematch),('review_duplicate_files',duplicates),
                ('set_up_downloads_5_steps',lambda:DownloadSetup()),('settings_preferences',lambda:SettingsPage()),
                ('Storage Light',lambda:StoragePage()),
                ('the_rising_of_the_shield_hero',lambda:changes('The Rising of the Shield Hero')),
                ('unlock_adult_anime',lambda:AdultPasswordDialog(mode='unlock')),('Updates Light',lambda:UpdatesPage()),
            ]
            references=sorted((ROOT/'Light Theme (Manga Brutalism)').iterdir())
            for number,(prefix,factory) in enumerate(factories,1):
                reference=next(p for p in references if p.is_dir() and p.name.startswith(prefix))
                row=dict(number=number,reference=reference.name)
                widget=None; host=None
                try:
                    widget=factory()
                    # Use the actual navigation embedder; centered workflows
                    # must not be misreported as full-width standalone dialogs.
                    if isinstance(widget,QDialog) and not isinstance(widget,(AdultPasswordDialog,QuitConfirmDialog,OperationProgress)) and number!=21:
                        from app.ui.navigation import navigate
                        host=QWidget();host.resize(1440,900);outer=QVBoxLayout(host);outer.setContentsMargins(0,0,0,0)
                        host.stacked_widget=QStackedWidget();outer.addWidget(host.stacked_widget)
                        previous=QLabel('Library — fixture background');previous.setAlignment(Qt.AlignCenter)
                        previous.setStyleSheet('background:#ebedf2;color:#555b6e;')
                        host.stacked_widget.addWidget(previous);host.show();app.processEvents()
                        widget.setParent(host);navigate(widget);capture=host
                    else:
                        if not isinstance(widget,(AdultPasswordDialog,QuitConfirmDialog,OperationProgress)) and number!=21:widget.resize(1440,900)
                        widget.show();capture=widget
                    QTest.qWait(260);app.processEvents()
                    destination=output/f'{number:02}-current.png';capture.grab().save(str(destination))
                    if isinstance(widget,SettingsPage):
                        for section in range(widget.tabs.count()):
                            widget.tabs.setCurrentIndex(section);app.processEvents()
                            widget.grab().save(str(output/f'28-settings-{section:02}.png'))
                    row.update(runtime=type(widget).__name__,capture=destination.name,size=[widget.width(),widget.height()],
                               labels=[w.text() for w in widget.findChildren(QLabel) if w.isVisible()][:65],
                               buttons=[w.text() for w in widget.findChildren(QPushButton) if w.isVisible()])
                    png=next(reference.glob('*.png'))
                    board=Image.new('RGB',(1440,510),'#ebedf2');draw=ImageDraw.Draw(board)
                    draw.text((12,8),f'{number:02}  {reference.name}',fill='#111111')
                    for x,path,label in ((12,png,'SUPPLIED'),(730,destination,'CURRENT FIXTURE')):
                        draw.text((x,32),label,fill='#111111')
                        raw=Image.open(path).convert('RGBA');paper=Image.new('RGBA',raw.size,'#ebedf2')
                        picture=Image.alpha_composite(paper,raw).convert('RGB');picture.thumbnail((698,450))
                        board.paste(picture,(x,55))
                    board.save(output/f'{number:02}-comparison.png')
                    print(f'{number:02} OK {reference.name}',flush=True)
                except Exception:
                    row['error']=traceback.format_exc();print(row['error'],flush=True)
                finally:
                    if widget is not None:
                        for timer in widget.findChildren(__import__('PyQt5.QtCore',fromlist=['QTimer']).QTimer):timer.stop()
                        widget.hide();widget.deleteLater()
                        QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
                    if host is not None:host.hide();host.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
                findings.append(row)
            (output/'inventory.json').write_text(json.dumps(findings,indent=2,ensure_ascii=False),encoding='utf-8')
            for begin in range(0,32,4):
                board=Image.new('RGB',(1440,2040),'white')
                for offset in range(4):
                    image=output/f'{begin+offset+1:02}-comparison.png'
                    if image.exists():board.paste(Image.open(image),(0,offset*510))
                board.save(output/f'comparison-{begin+1:02}-{begin+4:02}.png')
    finally:
        apply_theme(app,'dark');fixture.tearDown()


def tag_popup(page):
    page.genre_filter.showPopup()
    # Keep the page alive while its popover is captured.
    popup=page.genre_filter.popup;popup._audit_owner=page
    return popup


if __name__=='__main__':main()
