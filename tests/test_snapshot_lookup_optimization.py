import unittest
from unittest.mock import patch
from app import db
from app.core.home_facts import download_badges
from app.core.identity import mapped_inventory_files


class CountedList(list):
    def __iter__(self):
        self.visits=getattr(self,'visits',0)+len(self)
        return super().__iter__()


class SnapshotLookupTests(unittest.TestCase):
    def test_season_owner_lookup_is_indexed_and_import_append_invalidates(self):
        rows=CountedList(dict(id=i,franchise_id=i//10,season_number=i%10,relation_type='SEASON') for i in range(1000))
        snapshot={'season_rows':rows}
        with db.refresh_view(snapshot):
            for fid in range(100):self.assertEqual(len(db.get_seasons_for_franchise(fid)),10)
            self.assertEqual(rows.visits,1000)
            selected=db.get_seasons_for_franchise(1);selected[0]['season_number']=999
            self.assertNotEqual(db.get_seasons_for_franchise(1)[0]['season_number'],999)
            rows.append(dict(id=1001,franchise_id=100,season_number=1,relation_type='SEASON'))
            self.assertEqual(db.get_seasons_for_franchise(100)[0]['id'],1001)

    def test_verified_mapping_reused_only_in_its_snapshot_and_returns_copies(self):
        season=dict(id=1,season_folder_path='Example',video_files_json='[]')
        with patch('app.core.identity._mapped_inventory_files',return_value={'example':[7]}) as read:
            with db.refresh_view({}):
                mapped_inventory_files(season,True)['example'].append(8)
                self.assertEqual(mapped_inventory_files(season,True),{'example':[7]})
                read.assert_called_once()
            with db.refresh_view({}):mapped_inventory_files(season,True)
            self.assertEqual(read.call_count,2)

    def test_badge_jobs_are_read_once_and_keep_input_order_and_status(self):
        jobs=CountedList([dict(fid=2,status='Downloading',progress=.2),dict(fid=1,status='Downloading',progress=.6),dict(fid=1,status='Indexed',progress=1)])
        groups=[dict(id=1,series_member_ids=[1,2])]+[dict(id=n) for n in range(3,103)]
        badge=download_badges(groups,jobs)[1]
        self.assertEqual(jobs.visits,3)
        self.assertEqual(badge['jobs'],jobs[:2]);self.assertEqual(badge['label'],'DL 40%')
