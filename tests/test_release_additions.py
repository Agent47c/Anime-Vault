import unittest,time
from unittest.mock import patch
import test_ui_regressions as support
from app import db
from app.core import release_actions as actions

class ReleaseAdditions(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_reminders_are_deduplicated_persisted_and_delivered_once(self):
        now=time.time();actions.remind(1,2,now+100,'Example');actions.remind(1,2,now+200,'Example')
        self.assertEqual(actions.due_reminders(now+150),[])
        self.assertEqual(len(actions.due_reminders(now+300)),1);self.assertEqual(actions.due_reminders(now+400),[])
    def test_auto_grab_requires_verified_release_and_exact_episode(self):
        from app.core import download_discovery as discovery,download_queries
        db.upsert_season({'franchise_id':self.fid,'anilist_id':21,'season_number':1,'title_display':'One Piece'})
        context={'continuous':True,'local':{},'pending':[]}
        entries=[{'status':'Match Uncertain','episode_keys':['EPISODE:ABS:7'],'seeders':999},{'status':'Missing — Release Found','episode_keys':['EPISODE:ABS:7','EPISODE:ABS:8'],'seeders':999},{'status':'Missing — Release Found','episode_keys':['EPISODE:ABS:7'],'seeders':1}]
        with patch.object(discovery,'library_context',return_value=context),patch.object(discovery,'sources',return_value=[{'name':'Source','url':'https://example.test/?q={query}'}]),patch.object(discovery,'search',return_value={'results':entries}),patch.object(discovery,'submit') as submit,patch.object(download_queries,'default_query',return_value='One Piece'):
            actions.auto_grab(self.fid,21,7);self.assertEqual(submit.call_args.args[1],[entries[2]])
    def test_announced_discovery_has_no_invented_date_bounds(self):
        from app.core import release_news as news
        with patch.object(news,'cached',return_value={'Page':{'media':[],'pageInfo':{}}}) as call:
            news.discover(announced=True,sort='START_DATE_DESC')
        self.assertIn('status:NOT_YET_RELEASED',call.call_args.args[1]);self.assertNotIn('$from',call.call_args.args[1])
