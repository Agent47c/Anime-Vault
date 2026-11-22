"""Live extension status and discovery pagination preserve every visible title."""
import time
import unittest
from unittest.mock import patch
from PyQt5.QtTest import QTest
import test_ui_regressions as support
from app import db
from app.core import source_bridge,release_news as news


class ExtensionReleaseRowsTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def test_registration_alone_is_red_and_live_heartbeat_expires(self):
        db.set_state('chrome.capture_extension','a'*32)
        self.assertFalse(source_bridge.connection()['connected'])
        with patch('app.core.source_bridge.time.time',return_value=100):source_bridge.heartbeat('https://nyaa.si',True)
        with patch('app.core.source_bridge.time.time',return_value=110):self.assertTrue(source_bridge.connection()['connected'])
        with patch('app.core.source_bridge.time.time',return_value=116):self.assertFalse(source_bridge.connection()['connected'])
        source_bridge.heartbeat('https://nyaa.si',False,online=False)
        self.assertFalse(source_bridge.connection()['connected'])

    def test_indicator_updates_from_real_temporary_database_connection(self):
        from app.ui.components.extension_connection import ExtensionConnection
        source_bridge.heartbeat('https://nyaa.si',False)
        widget=ExtensionConnection();self.addCleanup(widget.deleteLater);widget.show()
        deadline=time.monotonic()+2
        while (widget.worker or not widget.indicator.connected) and time.monotonic()<deadline:QTest.qWait(10)
        self.assertTrue(widget.indicator.connected);self.assertIn('Website capture is off',widget.label.text())
        source_bridge.heartbeat('https://nyaa.si',False,online=False);widget.check()
        deadline=time.monotonic()+2
        while (widget.worker or widget.indicator.connected) and time.monotonic()<deadline:QTest.qWait(10)
        self.assertFalse(widget.indicator.connected);self.assertIn('disconnected',widget.label.text())
        widget.hide();self.assertFalse(widget.timer.isActive())

    def test_six_column_pages_carry_all_provider_remainders_forward(self):
        records=[dict(id=n,title={'english':f'Anime {n}'},isAdult=False) for n in range(1,46)]
        def response(query,variables):
            start=(variables['page']-1)*20
            return dict(Page=dict(media=records[start:start+20],pageInfo=dict(hasNextPage=start+20<len(records))))
        visible=[]
        with patch.object(news.api,'_graphql_request',side_effect=response) as request:
            for page,count,more in ((1,18,True),(2,18,True),(3,9,False)):
                cards,next_page=news.discover_grid(page=page,capacity=18,fetch_missing=True)
                self.assertEqual(len(cards),count);self.assertEqual(next_page,more)
                visible.extend(item['id'] for item in cards)
            self.assertEqual(request.call_count,3)  # Earlier source pages came from cache.
        self.assertEqual(visible,list(range(1,46)))

    def test_cached_twenty_items_show_full_rows_and_keep_last_two_for_next_page(self):
        records=[dict(id=n,title={'english':f'Anime {n}'}) for n in range(1,21)]
        with patch.object(news.api,'_graphql_request',return_value=dict(Page=dict(media=records,pageInfo=dict(hasNextPage=False)))):
            news.discover(force=True)
        with patch.object(news.api,'_graphql_request',side_effect=AssertionError('Use existing cache')):
            first,more=news.discover_grid(capacity=18)
            final,last_more=news.discover_grid(page=2,capacity=18)
        self.assertEqual(len(first),18);self.assertTrue(more)
        self.assertEqual([m['id'] for m in final],[19,20]);self.assertFalse(last_more)

    def test_provider_side_filtered_pages_do_not_drop_or_repeat_visible_items(self):
        pages={1:([dict(id=n) for n in range(1,11)],True),2:([dict(id=n) for n in range(11,31)],False)}
        with patch.object(news,'discover',side_effect=lambda upcoming,page,*args,**kwargs:pages[page]):
            first,more=news.discover_grid(capacity=18)
            final,last_more=news.discover_grid(page=2,capacity=18)
        self.assertEqual([m['id'] for m in first+final],list(range(1,31)))
        self.assertTrue(more);self.assertFalse(last_more)

    def test_visible_page_uses_actual_column_count_for_complete_rows(self):
        from app.ui.pages.release_news_page import ReleaseNewsPage
        from app.ui.theme import apply_theme
        apply_theme(self.app,'manga_light')
        self.addCleanup(lambda:apply_theme(self.app,'dark'))
        records=[dict(id=n,title={'english':f'Anime {n}'}) for n in range(1,51)]
        def response(query,variables):
            start=(variables['page']-1)*20
            return dict(Page=dict(media=records[start:start+20],pageInfo=dict(hasNextPage=start+20<len(records))))
        with patch.object(ReleaseNewsPage,'load'):
            page=ReleaseNewsPage();page.resize(1900,900);page.show();QTest.qWait(20)
        self.addCleanup(page.deleteLater)
        with patch.object(page,'run',side_effect=lambda operation,ready:ready(operation())),\
             patch.object(news.api,'_graphql_request',side_effect=response),patch('app.ui.pages.release_news_page.NewsArtwork.start'):
            page.load(True);QTest.qWait(20)
            self.assertEqual(page._discovery_columns,7)
            self.assertEqual(len(page._discovery_cards),21)
            self.assertEqual(len(page._discovery_cards)%page._discovery_columns,0)
        page.hide()
