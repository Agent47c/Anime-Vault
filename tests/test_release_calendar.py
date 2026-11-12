"""Calendar history, two-week layout and bounded provider fetching."""
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
import test_ui_regressions as support
from app import db
from app.core import release_calendar as calendar


class CalendarTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def test_metadata_replacement_keeps_previous_episode_and_corrects_dates(self):
        now = int(datetime.now().timestamp())
        for ep in (10, 11):
            db.cache_media(self.fid, {'id': 21, 'title': {}, 'nextAiringEpisode': {
                'episode': ep, 'airingAt': now + (ep-11)*86400}})
        self.assertEqual({r['episode'] for r in calendar.saved()}, {10, 11})
        calendar.remember([dict(mediaId=21, episode=11, airingAt=now+3600)])
        self.assertEqual(len(calendar.saved()), 2)
        self.assertEqual(next(r for r in calendar.saved() if r['episode'] == 11)['airingAt'], now+3600)

    def test_full_week_includes_past_days_and_week_navigation_uses_no_network(self):
        from app.ui.pages.library_page import LibraryPage
        sunday = datetime.now().replace(hour=12) + timedelta(days=6-datetime.now().weekday())
        monday = (sunday-timedelta(days=6)).replace(hour=19)
        calendar.remember([dict(mediaId=21, episode=10, airingAt=int(monday.timestamp()))])
        with patch('app.ui.pages.library_page.datetime') as clock, \
             patch('app.core.anilist_client._graphql_request', side_effect=AssertionError('UI network')):
            clock.now.return_value = sunday
            clock.fromtimestamp.side_effect = datetime.fromtimestamp
            page = LibraryPage()
            self.assertEqual(page.airing_week.count(), 7)
            first = page.airing_week.itemAt(0).widget()
            self.assertEqual(first.date, monday.date())
            self.assertEqual(first.release_button.entries[0]['episode'], 10)
            page._change_calendar_week(-1)
            self.assertEqual(page.airing_week.itemAt(0).widget().date, monday.date()-timedelta(days=7))
            page._change_calendar_week(0)
            self.assertEqual(page.airing_week.itemAt(0).widget().date, monday.date())
            page.deleteLater()

    def test_paginated_fetch_includes_aired_and_future_and_preserves_on_failure(self):
        stamp = int(datetime.now().timestamp())
        responses = [dict(Page=dict(pageInfo=dict(hasNextPage=True), airingSchedules=[
            dict(mediaId=21, episode=10, airingAt=stamp-86400)])),
            dict(Page=dict(pageInfo=dict(hasNextPage=False), airingSchedules=[
            dict(mediaId=21, episode=11, airingAt=stamp+86400)]))]
        with patch('app.core.anilist_client._graphql_request', side_effect=responses) as request:
            calendar.refresh()
            query, variables = request.call_args.args
            self.assertNotIn('notYetAired', query)
            self.assertEqual(variables['ids'], [21])
            self.assertEqual(variables['page'], 2)
        before = calendar.saved()
        with patch('app.core.anilist_client._graphql_request', return_value=None):
            calendar.refresh()
        self.assertEqual(calendar.saved(), before)

    def test_retention_and_cancel(self):
        old = int((datetime.now()-timedelta(weeks=13)).timestamp())
        calendar.remember([dict(mediaId=21, episode=1, airingAt=old)])
        self.assertEqual(calendar.saved(), [])
        with patch('app.core.anilist_client._graphql_request') as request:
            with self.assertRaises(InterruptedError):
                calendar.refresh(cancelled=lambda: True)
            request.assert_not_called()
