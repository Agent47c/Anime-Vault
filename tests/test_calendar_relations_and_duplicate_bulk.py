import json,unittest
from datetime import datetime,timedelta
from unittest.mock import patch
from PyQt5.QtCore import Qt
import test_ui_regressions as support
from app import db
from app.core import release_calendar,calendar_view
from app.ui.pages.duplicate_page import DuplicatePage

class Followups(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_sequel_without_local_season_appears_in_both_calendar_data_and_fetch_ids(self):
        stamp=int(datetime.now().timestamp())
        node=dict(id=999,title={'english':'Season two'},nextAiringEpisode=dict(episode=7,airingAt=stamp))
        db.update_franchise_field(self.fid,'metadata_json',json.dumps({'relations':{'edges':[dict(relationType='SEQUEL',node=node)]}}))
        release_calendar.remember([dict(mediaId=999,episode=7,airingAt=stamp)])
        today=datetime.now().date();rows=calendar_view.entries(today,today)
        self.assertTrue(any(r['release_id']==999 and r['fid']==self.fid for r in rows))
        with patch('app.core.anilist_client._graphql_request',return_value={'Page':{'airingSchedules':[],'pageInfo':{'hasNextPage':False}}}) as query:
            release_calendar.refresh()
        self.assertIn(999,query.call_args.args[1]['ids'])
    def test_unknown_date_is_not_invented_for_announced_sequel(self):
        db.update_franchise_field(self.fid,'metadata_json',json.dumps({'relations':{'edges':[dict(relationType='SEQUEL',node=dict(id=999,title={'english':'Soon'}))]}}))
        today=datetime.now().date();self.assertFalse(calendar_view.entries(today,today+timedelta(days=365)))
    def test_per_anime_and_bulk_selection_never_select_protected_originals(self):
        page=DuplicatePage();self.addCleanup(page.deleteLater)
        groups=[dict(files=[dict(path=f'{title}-{i}.mkv',title=title,episodes=[1],signature=(100,1,i)) for i in range(3)]) for title in ('First','Second')]
        page._results((groups,[]))
        first=page.tree.topLevelItem(0);first.setCheckState(0,Qt.Checked)
        self.assertEqual(len(page._selected()),2)
        page._select_all();self.assertEqual(len(page._selected()),4)
        for n in range(2):
            original=page.tree.topLevelItem(n).child(0).child(0)
            self.assertFalse(original.flags()&Qt.ItemIsUserCheckable)
            self.assertNotEqual(original.checkState(0),Qt.Checked)
