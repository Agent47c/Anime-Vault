import unittest
from datetime import date
from unittest.mock import Mock, patch
import test_ui_regressions as support
from app import db
from app.core import anilist_client, release_news as news

class ReleaseNewsTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_cache_reuses_response_and_failure_does_not_replace_it(self):
        with patch.object(news.api,'_graphql_request',return_value={'Media':{'id':5}}) as request:
            self.assertEqual(news.cached('a','query',{}),news.cached('a','query',{}));self.assertEqual(request.call_count,1)
        with patch.object(news.api,'_graphql_request',return_value=None):
            with self.assertRaises(ValueError):news.cached('a','query',{},True)
            self.assertEqual(news.cached('a','query',{}),{'Media':{'id':5}})
    def test_discover_uses_fuzzy_date_int_and_calendar_month_boundary(self):
        seen=[]
        def fake_request(query,variables):
            seen.append((query,variables))
            return {'Page':{'pageInfo':{'hasNextPage':False},'media':[{'id':7,'title':{'english':'Spring'},'isAdult':False}]}}
        with patch('app.core.release_news.datetime') as fake_dt,patch.object(news.api,'_graphql_request',side_effect=fake_request):
            fake_dt.now.return_value.date.return_value=date(2026,11,1)
            items,more=news.discover(upcoming=True,force=True)
        self.assertFalse(more);self.assertEqual([item['id'] for item in items],[7])
        query,variables=seen[0]
        self.assertIn('$from:FuzzyDateInt',query);self.assertIn('$to:FuzzyDateInt',query)
        self.assertEqual(variables['from'],20261031);self.assertEqual(variables['to'],20270130)

    def test_custom_premiere_dates_include_both_endpoints_and_use_separate_caches(self):
        dates=(date(2026,12,1),date(2027,1,31))
        data={'Page':{'media':[{'id':7}],'pageInfo':{'hasNextPage':False}}}
        with patch.object(news.api,'_graphql_request',return_value=data) as request:
            self.assertEqual(news.discover(force=True,date_range=dates),([{'id':7}],False))
            query,variables=request.call_args.args
            self.assertIn('startDate_greater:$from,startDate_lesser:$to',query)
            self.assertEqual((variables['from'],variables['to']),(20261130,20270201))
            self.assertEqual(news.discover(date_range=dates),([{'id':7}],False))
            with self.assertRaises(news.CacheMiss):news.discover()
            with self.assertRaises(news.CacheMiss):news.discover(date_range=(dates[0],dates[0]))
            with self.assertRaises(ValueError):news.discover(date_range=dates[::-1])
            request.assert_called_once()

    def test_release_controls_never_show_as_separate_windows_during_construction(self):
        from PyQt5.QtCore import QObject, QEvent
        from PyQt5.QtWidgets import QApplication, QWidget
        from app.ui.pages.release_news_page import ReleaseNewsPage
        appeared=[]
        class WindowTrace(QObject):
            def eventFilter(self,widget,event):
                if event.type()==QEvent.Show and isinstance(widget,QWidget) and widget.isWindow():
                    appeared.append(widget.metaObject().className())
                return False
        app=QApplication.instance()
        trace=WindowTrace()
        app.installEventFilter(trace)
        try:
            with patch.object(ReleaseNewsPage,'load'):
                for media_id in (None,7):
                    page=ReleaseNewsPage(media_id=media_id)
                    page.deleteLater()
            self.assertEqual(appeared,[])
        finally:
            app.removeEventFilter(trace)

    def test_custom_premiere_controls_fit_all_themes_and_only_apply_to_discovery(self):
        from PyQt5.QtCore import QDate, QPoint, Qt
        from PyQt5.QtTest import QTest
        from PyQt5.QtWidgets import QApplication, QTableView
        from app.ui.pages.release_news_page import ReleaseNewsPage
        from app.ui.theme import apply_theme
        app=QApplication.instance()
        old_theme=app.property('animevaultRequestedTheme') or 'dark'
        today=QDate.currentDate()
        try:
            with patch.object(ReleaseNewsPage,'load'):
                page=ReleaseNewsPage();timeline=ReleaseNewsPage(media_id=7)
            page.resize(760,720);page.show()
            self.assertEqual(timeline.period.findData('custom'),-1)
            self.assertTrue(page.date_controls.isHidden())
            with patch.object(page,'run',side_effect=lambda operation,ready:ready(operation())),patch.object(news,'discover_grid',return_value=([],False)) as discover:
                page.period.setCurrentIndex(page.period.findData('custom'))
                start=page.premiere_from;end=page.premiere_to
                self.assertEqual(start.minimumDate(),QDate(today.year()-2,1,1))
                self.assertEqual(end.maximumDate(),QDate(today.year()+2,12,31))
                start.setDate(today.addDays(-90));page.refresh_button.click()
                self.assertTrue(discover.call_args.args[2])
                self.assertEqual(discover.call_args.kwargs['date_range'],(today.addDays(-90).toPyDate(),today.toPyDate()))
                start.setDate(today.addDays(1))
                self.assertFalse(page.refresh_button.isEnabled())
                self.assertIn('start date',page.status.text())
                end.setDate(start.date())
                self.assertTrue(page.refresh_button.isEnabled())
                for theme in ('dark','light','manga_dark','manga_light'):
                    with self.subTest(theme=theme):
                        apply_theme(app,theme);page.refresh_home_style();app.processEvents()
                        start_rect=start.rect().translated(start.mapTo(page.date_controls,QPoint()))
                        end_rect=end.rect().translated(end.mapTo(page.date_controls,QPoint()))
                        self.assertFalse(start_rect.intersects(end_rect))
                        self.assertTrue(page.date_controls.rect().contains(start_rect))
                        self.assertTrue(page.date_controls.rect().contains(end_rect))
                        for picker in (start,end):
                            editor=picker.lineEdit()
                            self.assertEqual(editor.text(),picker.date().toString(picker.displayFormat()))
                            self.assertIsNone(editor.graphicsEffect())
                            self.assertGreaterEqual(editor.width(),editor.fontMetrics().horizontalAdvance(editor.text()))
                            calendar=picker.calendarWidget()
                            QTest.mouseClick(picker,Qt.LeftButton,pos=QPoint(picker.width()-12,picker.height()//2))
                            self.assertTrue(calendar.isVisible())
                            self.assertTrue(calendar.navigation.isVisible())
                            grid=calendar.findChild(QTableView,'qt_calendar_calendarview')
                            self.assertEqual(grid.rowAt(0),0)
                            self.assertEqual(grid.verticalScrollBar().maximum(),0)
                            for control in (calendar.previous_month,calendar.month,calendar.year,calendar.next_month):
                                self.assertGreater(control.width(),0)
                                self.assertTrue(calendar.navigation.rect().contains(control.geometry()))
                            calendar.year.setCurrentIndex(calendar.year.findData(today.year()+2))
                            calendar.month.setCurrentIndex(calendar.month.findData(12))
                            self.assertEqual((calendar.yearShown(),calendar.monthShown()),(today.year()+2,12))
                            self.assertFalse(calendar.next_month.isEnabled())
                            QTest.mouseClick(calendar.previous_month,Qt.LeftButton)
                            self.assertEqual(calendar.monthShown(),11)
                            QTest.mouseClick(calendar.next_month,Qt.LeftButton)
                            self.assertEqual(calendar.monthShown(),12)
                            QTest.mouseClick(calendar.year,Qt.LeftButton)
                            self.assertTrue(calendar.year.view().isVisible())
                            QTest.keyClick(calendar.year.view(),Qt.Key_Escape)
                            self.assertTrue(calendar.isVisible())
                            original=picker.date()
                            model=grid.model()
                            day=next(model.index(row,column)
                                     for row in range(1,model.rowCount()) for column in range(model.columnCount())
                                     if str(model.index(row,column).data())=='15')
                            QTest.mouseClick(grid.viewport(),Qt.LeftButton,pos=grid.visualRect(day).center())
                            self.assertEqual(picker.date(),QDate(today.year()+2,12,15))
                            self.assertEqual(editor.text(),picker.date().toString(picker.displayFormat()))
                            self.assertFalse(calendar.isVisible())
                            picker.setDate(original)
                page.period.setCurrentIndex(0)
                self.assertTrue(page.date_controls.isHidden())
                self.assertNotIn('date_range',discover.call_args.kwargs)
        finally:
            page.reject();page.deleteLater();timeline.deleteLater()
            apply_theme(app,old_theme)
    def test_graphql_errors_preserve_none_return_and_surface_reason(self):
        import requests
        bad=Mock(status_code=400);bad.json.return_value={'data':None,'errors':[{'message':'Variable "$from" of type "Int" used in position expecting type "FuzzyDateInt".'}]}
        bad.raise_for_status.side_effect=requests.HTTPError('400 Client Error',response=bad)
        with patch.object(anilist_client,'_rate_limit'),patch.object(anilist_client.requests,'post',return_value=bad):
            self.assertIsNone(anilist_client._graphql_request('query',{}))
            self.assertIn('FuzzyDateInt',anilist_client.last_error())
        with patch.object(anilist_client.requests,'post',return_value=bad),patch.object(anilist_client,'_rate_limit'):
            with self.assertRaises(ValueError) as error:news.cached('broken','query',{})
        self.assertIn('FuzzyDateInt',str(error.exception))
        db.set_state('release_news:corrupt','{not-json')
        with patch.object(news.api,'_graphql_request',return_value={'Page':{'pageInfo':{'hasNextPage':False},'media':[]}}):
            self.assertEqual(news.cached('corrupt','query',{}),{'Page':{'pageInfo':{'hasNextPage':False},'media':[]}})

    def test_discovery_is_cache_only_until_explicit_refresh_and_survives_day_change(self):
        data={'Page':{'media':[{'id':7,'title':{'english':'Saved anime'}}],'pageInfo':{}}}
        with patch.object(news.api,'_graphql_request',return_value=data) as request:
            with self.assertRaises(news.CacheMiss):news.discover()
            request.assert_not_called()
            self.assertEqual(news.discover(force=True)[0][0]['id'],7)
            self.assertEqual(request.call_count,1)
        info={}
        with patch.object(news.api,'_graphql_request',side_effect=AssertionError('Must stay offline')),patch('app.core.release_news.datetime') as day:
            day.now.return_value.date.return_value=date(2027,1,15)
            self.assertEqual(news.discover(cache_info=info)[0][0]['id'],7)
        self.assertEqual(info['source'],'cache')
        with patch.object(news.api,'_graphql_request',return_value=None),patch.object(news.api,'last_error',return_value='Request timed out'):
            info={};self.assertEqual(news.discover(force=True,cache_info=info)[0][0]['id'],7)
        self.assertIn('Showing your saved results',info['warning'])
        self.assertEqual(news.discover()[0][0]['id'],7)

    def test_previous_date_keyed_cache_is_reused_without_network(self):
        import json
        from app.preferences import save
        save('allow_mature',True)
        filters=json.dumps([None,None,None,True],separators=(',',':'))
        db.set_state('release_news:discover:2026-10-01:False:1:False:START_DATE:'+filters,
            json.dumps({'time':1000,'data':{'Page':{'media':[{'id':9}],'pageInfo':{}}}}))
        with patch.object(news.api,'_graphql_request',side_effect=AssertionError('Must reuse prior cache')):
            self.assertEqual(news.discover()[0][0]['id'],9)
            with self.assertRaises(news.CacheMiss):news.discover(theme='Isekai')

    def test_release_page_cache_miss_is_honest_and_reopen_uses_saved_results(self):
        from app.ui.pages.release_news_page import ReleaseNewsPage,NewsArtwork
        data={'Page':{'media':[{'id':7,'title':{'english':'Saved anime'}}],'pageInfo':{}}}
        with patch.object(ReleaseNewsPage,'load'):page=ReleaseNewsPage()
        with patch.object(page,'run',side_effect=lambda operation,ready:ready(operation())),patch.object(NewsArtwork,'start'),patch.object(news.api,'_graphql_request',return_value=data) as request:
            page.load();self.assertIn('No saved results',page.status.text());request.assert_not_called()
            page.load(True);self.assertEqual(request.call_count,1);self.assertIn('Updated and saved',page.status.text())
            self.assertTrue(page._artwork.allow_network)
            page.load();self.assertEqual(request.call_count,1);self.assertFalse(page._artwork.allow_network)
            self.assertIn('Saved results',page.status.text());self.assertIn('Last checked:',page.status.text())
        page.reject();page.deleteLater()

    def test_thumbnail_reopen_reads_disk_and_never_retries_missing_images(self):
        from pathlib import Path
        from PyQt5.QtGui import QImage
        from app.ui.pages.release_news_page import NewsArtwork
        media=dict(id=7,coverImage={'large':'https://example.test/7.jpg'})
        covers=Path(self.temp.name)/'art';covers.mkdir()
        def download(url,filename):
            image=QImage(20,30,QImage.Format_RGB32);image.fill(0);image.save(str(covers/filename));return filename
        with patch.object(anilist_client,'COVERS_DIR',covers),patch('app.config.COVERS_DIR',covers),patch('app.config.is_offline',return_value=False),patch.object(anilist_client,'_download_artwork',side_effect=download) as request:
            worker=NewsArtwork([media],allow_network=True);worker.run();self.assertEqual(request.call_count,1)
            images=[];reopen=NewsArtwork([media]);reopen.image_ready.connect(lambda mid,image:images.append(image));reopen.run()
            self.assertEqual(request.call_count,1);self.assertEqual(len(images),1);self.assertFalse(images[0].isNull())
            missing=NewsArtwork([dict(media,id=8)]);missing.run();self.assertEqual(request.call_count,1)
    def test_import_is_watching_without_files_and_idempotent(self):
        media={'id':12345,'title':{'english':'New anime'},'status':'NOT_YET_RELEASED'}
        fid,added=news.import_watching(media);self.assertTrue(added)
        record=db.get_franchise(fid);self.assertEqual(record['watch_status'],'WATCHING');self.assertEqual(record['storage_state'],'NOT_DOWNLOADED');self.assertTrue(record['has_new_update'])
        self.assertEqual(db.get_seasons_for_franchise(fid)[0]['airing_status'],'NOT_YET_RELEASED')
        db.update_franchise_field(fid,'user_notes','Keep');self.assertEqual(news.import_watching(media),(fid,False));self.assertEqual(db.get_franchise(fid)['user_notes'],'Keep')

    def test_discovery_filters_apply_before_pagination_and_keep_separate_caches(self):
        data={'Page':{'media':[{'id':1,'isAdult':True},{'id':2,'isAdult':False}],'pageInfo':{'hasNextPage':True}}}
        from app.preferences import save
        save('allow_mature',True)
        with patch.object(news,'cached',return_value=data) as cached:
            items,more=news.discover(sort='POPULARITY_DESC',genre='Fantasy',theme='Isekai',media_format='TV',include_adult=False)
            first=cached.call_args
            self.assertEqual([m['id'] for m in items],[2]);self.assertTrue(more)
            self.assertIn('sort:POPULARITY_DESC',first.args[1])
            self.assertIn('genre:$genre,tag:$tag,format:$format,isAdult:$adult',first.args[1])
            self.assertEqual({k:first.args[2][k] for k in ('genre','tag','format','adult')},dict(genre='Fantasy',tag='Isekai',format='TV',adult=False))
            news.discover(genre='Romance',include_adult=True)
            self.assertNotEqual(first.args[0],cached.call_args.args[0])
            self.assertNotIn('adult',cached.call_args.args[2])
            save('allow_mature',False)
            items,_=news.discover(include_adult=True)
            self.assertEqual([m['id'] for m in items],[2]);self.assertIs(cached.call_args.args[2]['adult'],False)

    def test_discovery_controls_follow_adult_setting_and_send_selected_filters(self):
        from app.preferences import save
        from app.ui.pages.release_news_page import ReleaseNewsPage
        for allowed in (False,True):
            save('allow_mature',allowed)
            with patch.object(ReleaseNewsPage,'load'):page=ReleaseNewsPage()
            try:
                self.assertEqual(page.adult_filter.isChecked(),allowed)
                self.assertEqual(page.adult_filter.isEnabled(),allowed)
                with patch.object(page,'run',side_effect=lambda operation,ready:operation()),patch.object(news,'discover',return_value=([],False)) as discover:
                    page.theme_filter.setCurrentText('Isekai');page.sort.setCurrentText('Most popular')
                    self.assertEqual(discover.call_args.args[4],'POPULARITY_DESC')
                    self.assertEqual(discover.call_args.kwargs['theme'],'Isekai')
                    self.assertEqual(discover.call_args.kwargs['include_adult'],allowed)
            finally:page.deleteLater()

    def test_discovery_cards_have_equal_widths_with_long_titles_and_after_resize(self):
        from app.ui.pages.release_news_page import ReleaseNewsPage
        with patch.object(ReleaseNewsPage,'load'):page=ReleaseNewsPage()
        items=[dict(id=n,title={'english':('CARDFIGHT!! VANGUARD DivineZ: Parallactic Fate ' if n==0 else 'Short title')},isAdult=False) for n in range(12)]
        # No network/artwork worker is required to verify layout geometry.
        with patch('app.ui.pages.release_news_page.NewsArtwork.start'):
            page.render((items,False));page.show()
            try:
                from PyQt5.QtTest import QTest
                for width in (1900,1100,1500):
                    page.resize(width,820);QTest.qWait(30)
                    widths=[card.width() for card in page._discovery_cards]
                    self.assertLessEqual(max(widths)-min(widths),1)
                    self.assertLessEqual(page.scroll.horizontalScrollBar().maximum(),0)
                    grid=page._discovery_grid
                    expected=max(1,(page.scroll.viewport().width()-18+grid.spacing())//280)
                    self.assertEqual(page._discovery_columns,expected)
                    from PyQt5.QtWidgets import QLabel
                    for card in page._discovery_cards:
                        title=card.findChild(QLabel,'update_title')
                        poster=next(label for label in card.findChildren(QLabel) if label.accessibleName().startswith('Poster for '))
                        self.assertGreater(title.y(),poster.geometry().bottom())
            finally:page.reject();page.deleteLater()
    def test_timeline_render_distinguishes_scheduled_and_unknown(self):
        from app.ui.pages.release_news_page import ReleaseNewsPage
        from PyQt5.QtWidgets import QLabel,QTableWidget
        with patch.object(ReleaseNewsPage,'load'):page=ReleaseNewsPage(media_id=5)
        page.render({'Media':{'id':5,'title':{'english':'Test'}},'Page':{'pageInfo':{'hasNextPage':False},'airingSchedules':[{'episode':1,'airingAt':1000000000},{'episode':2,'airingAt':1893456000}]}})
        texts=' '.join(label.text() for label in page.findChildren(QLabel))
        texts+=' '.join(table.item(row,col).text() for table in page.findChildren(QTableWidget) for row in range(table.rowCount()) for col in range(4))
        self.assertIn('Aired',texts);self.assertIn('Scheduled',texts);self.assertIn('????-??-??',texts)
        page.render({'Media':{'id':5,'title':{'english':'Empty'},'relations':None},'Page':{'pageInfo':None,'airingSchedules':None}})
        page.deleteLater()
