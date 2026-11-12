"""Use verified broadcast times, and keep refresh progress visible across tabs."""
import json,time,unittest
from contextlib import closing
from unittest.mock import patch
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QStackedWidget
from app import db
from app.core.episode_updates import episode_events,episode_notifications,display_episode_change
import test_ui_regressions as support


class EpisodeTimingProgressTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def history(self):return [dict(mediaId=21,episode=20,airingAt=900),dict(mediaId=21,episode=21,airingAt=2000)]
    def media(self):return dict(id=21,status='RELEASING',nextAiringEpisode=dict(episode=21,airingAt=2000))

    def test_latest_aired_and_next_scheduled_are_distinct(self):
        events=episode_events(self.media(),self.history(),now=1000)
        self.assertEqual(events,[(20,'aired',900),(21,'scheduled',2000)])
        self.assertEqual(episode_notifications(self.media(),self.history(),now=1000),['Episode 20 aired','Episode 21 airing soon'])
        self.assertIn('Episode 20 aired',display_episode_change('Episode 20 aired',self.media(),self.history(),1000))
        self.assertIn('Episode 21 scheduled',display_episode_change('Episode 21 airing soon',self.media(),self.history(),1000))

    def test_before_today_broadcast_choose_20_even_if_provider_next_is_21(self):
        self.assertEqual(episode_notifications(self.media(),self.history(),now=800),['Episode 20 airing soon'])

    def test_never_guess_previous_episode_or_treat_unknown_time_as_aired(self):
        self.assertEqual(episode_events(self.media(),[],1000),[(21,'scheduled',2000)])
        media=dict(id=21,nextAiringEpisode=dict(episode=21))
        self.assertEqual(episode_events(media,[],1000),[(21,'unverified',None)])
        self.assertEqual(episode_notifications(media,[],1000),['Episode 21 broadcast time unverified'])

    def test_other_anime_schedule_does_not_change_episode_identity(self):
        self.assertEqual(episode_events(self.media(),[dict(mediaId=22,episode=20,airingAt=900)],1000),[(21,'scheduled',2000)])

    def test_cached_review_corrects_legacy_next_only_message_without_network(self):
        from app.core.release_calendar import remember
        from app.core.update_review import read_changes
        now=int(time.time());media=dict(id=21,status='RELEASING',nextAiringEpisode=dict(episode=21,airingAt=now+86400))
        remember([dict(mediaId=21,episode=20,airingAt=now-60)])
        with closing(db.get_connection()) as c:
            c.execute('UPDATE franchises SET metadata_json=?,update_details=?,has_new_update=1 WHERE id=?',(json.dumps(media),'Episode 21 airing soon',self.fid));c.commit()
        with patch('app.core.anilist_client.get_anime_by_id') as request:result=read_changes([self.fid])
        request.assert_not_called()
        self.assertTrue(any(row.startswith('Episode 20 aired') for row in result['changes']))
        self.assertTrue(any(row.startswith('Episode 21 scheduled') for row in result['changes']))
        db.dismiss_updates(self.fid)
        self.assertEqual(read_changes([self.fid])['changes'],[])

    def test_progress_covers_overlapping_tasks_and_hides_at_completion(self):
        from app.ui.components.refresh_progress import RefreshProgress
        host=QWidget();layout=QVBoxLayout(host);stack=QStackedWidget();stack.addWidget(QWidget());stack.addWidget(QWidget());layout.addWidget(stack)
        bar=RefreshProgress();layout.addWidget(bar);host.resize(1100,720);host.show();self.app.processEvents()
        self.assertFalse(bar.isVisible());bar.begin('library','Refreshing local library');self.assertTrue(bar.isVisible());self.assertEqual(bar.maximum(),0)
        bar.report('library',3,10,'Reading folders');self.assertEqual(bar.value(),3);self.assertEqual(bar.maximum(),10)
        bar.begin('metadata','Refreshing metadata');stack.setCurrentIndex(1);self.assertTrue(bar.isVisible())
        bar.finish('library');self.assertTrue(bar.isVisible());self.assertEqual(bar.height(),4)
        bar.finish('metadata');self.assertFalse(bar.isVisible());host.close();host.deleteLater()
