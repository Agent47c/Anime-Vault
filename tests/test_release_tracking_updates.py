"""Regression coverage for related-release episodes and exact library ownership."""
import json,time,unittest
from unittest.mock import patch
from PyQt5.QtWidgets import QPushButton
import test_ui_regressions as support
from app import db
from app.core.updater import UpdaterThread
from app.core import release_news as news,release_calendar


class ReleaseTrackingTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def media(self,episode=7,status='RELEASING'):
        return dict(id=21,title={'english':'Black Clover'},status='FINISHED',relations={'edges':[
            dict(relationType='SEQUEL',node=dict(id=195604,title={'english':'Black Clover Season 2'},format='TV',status=status,nextAiringEpisode={'episode':episode,'airingAt':int(time.time()+86400)}))]})

    def test_dismissed_season_does_not_hide_later_episode(self):
        generic='Black Clover Season 2 — Currently Airing'
        db.publish_updates(self.fid,generic);db.dismiss_updates(self.fid)
        worker=UpdaterThread();worker._airing_schedule=[]
        details=worker._check_for_updates(db.get_franchise(self.fid),self.media())
        visible=db.publish_updates(self.fid,details)
        self.assertEqual(visible,'Episode 7 airing soon — Black Clover Season 2')
        db.dismiss_updates(self.fid)
        self.assertIsNone(db.publish_updates(self.fid,details))
        self.assertIn('Episode 8',db.publish_updates(self.fid,worker._check_for_updates(db.get_franchise(self.fid),self.media(8))))
        db.mute_updates(self.fid,True)
        self.assertIsNone(db.publish_updates(self.fid,worker._check_for_updates(db.get_franchise(self.fid),self.media(9))))

    def test_metadata_only_release_still_reports_announcement_and_owned_release_reports_episodes(self):
        sid=db.upsert_season(dict(franchise_id=self.fid,anilist_id=195604,season_number=2,title_display='Season 2',storage_state='NOT_DOWNLOADED'))
        worker=UpdaterThread();worker._airing_schedule=[]
        details=worker._check_for_updates(db.get_franchise(self.fid),self.media(status='NOT_YET_RELEASED'))
        self.assertIn('Announced',details);self.assertNotIn('Episode ',details)
        db.update_season_field(sid,'storage_state','ON_DISK')
        details=worker._check_for_updates(db.get_franchise(self.fid),self.media())
        self.assertIn('Episode 7',details);self.assertNotIn('Currently Airing',details)

    def test_related_episode_history_is_saved_and_qualified_date_is_rendered(self):
        media=self.media();release_calendar.remember_metadata(media)
        self.assertTrue(any(row['mediaId']==195604 and row['episode']==7 for row in release_calendar.saved()))
        from app.ui.update_release_dates import dated_changes
        record=db.get_franchise(self.fid);record.update(metadata_json=json.dumps(media),update_details='Episode 7 airing soon — Black Clover Season 2')
        label=dated_changes(record)[0];self.assertIn('scheduled',label);self.assertIn('local time',label);self.assertIn('Season 2',label)

    def test_import_checks_season_identity_without_overwriting_parent(self):
        db.upsert_season(dict(franchise_id=self.fid,anilist_id=195604,season_number=2,title_display='Season 2',storage_state='NOT_DOWNLOADED'))
        db.update_franchise_field(self.fid,'user_notes','Keep my note')
        before=len(db.get_all_franchises())
        self.assertEqual(news.import_watching({'id':195604,'title':{'english':'Season 2'}}),(self.fid,False))
        self.assertEqual(len(db.get_all_franchises()),before);self.assertEqual(db.get_franchise(self.fid)['user_notes'],'Keep my note')

    def test_linked_later_season_is_checked_once_and_failure_keeps_pending(self):
        sid=db.upsert_season(dict(franchise_id=self.fid,anilist_id=195604,season_number=3,title_display='Later season',storage_state='ON_DISK'))
        root={'id':21,'title':{'english':'Original'},'status':'FINISHED'}
        later=self.media()['relations']['edges'][0]['node']
        worker=UpdaterThread()
        with patch('app.core.updater.is_offline',return_value=False),patch('app.core.release_calendar.refresh'),patch('app.core.series.refresh_series_links'),patch('app.core.anilist_client.get_anime_by_id',side_effect=lambda mid:root if mid==21 else later) as request:
            worker.run()
        self.assertEqual(request.call_count,2);self.assertIn('Episode 7',db.get_franchise(self.fid)['update_details'])
        saved=db.get_franchise(self.fid)['update_details']
        with patch('app.core.updater.is_offline',return_value=False),patch('app.core.release_calendar.refresh'),patch('app.core.series.refresh_series_links'),patch('app.core.anilist_client.get_anime_by_id',side_effect=lambda mid:root if mid==21 else None):
            worker.run()
        self.assertEqual(db.get_franchise(self.fid)['update_details'],saved)

    def test_release_hero_knows_existing_root_and_linked_season_before_click(self):
        from app.ui.pages.release_news_page import ReleaseNewsPage
        db.upsert_season(dict(franchise_id=self.fid,anilist_id=195604,season_number=2,title_display='Season 2',storage_state='NOT_DOWNLOADED'))
        with patch.object(ReleaseNewsPage,'load'):page=ReleaseNewsPage(media_id=195604)
        self.addCleanup(page.deleteLater);self.addCleanup(page.stop)
        page._cache_info={'library_owners':news.library_owners()}
        page.render({'Media':self.media()['relations']['edges'][0]['node'],'Page':{}})
        buttons=[b for b in page.findChildren(QPushButton) if b.text()=='Already in library']
        self.assertEqual(len(buttons),1);self.assertFalse(buttons[0].isEnabled())
        self.assertFalse(page.import_button({'id':21}).isEnabled())
        self.assertTrue(page.import_button({'id':999999}).isEnabled())
