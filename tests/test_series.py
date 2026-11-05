import json
import unittest
import test_ui_regressions as support
from app import db
from app.core.series import build_groups


class SeriesTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def entry(self, fid, aid, title, previous=None, relation='PREQUEL'):
        edges = [{'relationType': relation, 'node': {'id': previous, 'format': 'TV', 'title': {'english': 'Series'}}}] if previous else []
        return {'id': fid, 'anilist_id': aid, 'display_title': title, 'total_size_bytes': 5, 'metadata_json': json.dumps({'id': aid, 'relations': {'edges': edges}})}

    def test_seasons_and_arcs_become_one_card_without_losing_members(self):
        grouped = build_groups([self.entry(1, 100, 'Series'), self.entry(2, 200, 'Series Arc Two', 100)])
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]['display_title'], 'Series')
        self.assertEqual(grouped[0]['series_member_ids'], [1, 2])
        self.assertEqual(grouped[0]['total_size_bytes'], 10)

    def test_intermediate_release_not_owned_can_connect_arcs(self):
        intermediate = {'id': 200, 'title': {'english': 'Middle arc'}, 'relations': {'edges': [{'relationType': 'PREQUEL', 'node': {'id': 100, 'format': 'TV', 'title': {'english': 'Series'}}}]}}
        grouped = build_groups([self.entry(1, 100, 'Series'), self.entry(3, 300, 'Final arc', 200)], [intermediate])
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]['series_member_ids'], [1, 3])

    def test_spinoffs_and_similar_names_remain_separate(self):
        self.assertEqual(len(build_groups([self.entry(1, 100, 'Series'), self.entry(2, 200, 'Series', 100, 'SPIN_OFF')])), 2)

    def test_short_prequel_does_not_rename_television_series(self):
        entry = self.entry(1, 21, 'One Piece')
        entry['metadata_json'] = json.dumps({'id': 21, 'format': 'TV', 'relations': {'edges': [{'relationType': 'PREQUEL', 'node': {'id': 99, 'format': 'ONA', 'title': {'english': 'Short prequel'}}}]}})
        short = {'id': 99, 'format': 'ONA', 'title': {'english': 'Short prequel'}}
        self.assertEqual(build_groups([entry], [short])[0]['display_title'], 'One Piece')
        short_entry = {**self.entry(2, 99, 'Short prequel'), 'metadata_json': json.dumps(short)}
        self.assertEqual(len(build_groups([entry, short_entry])), 2)

    def test_search_for_arc_returns_group_and_all_local_seasons(self):
        base = db.upsert_franchise(self.entry(1, 100, 'Series'))
        arc = db.upsert_franchise(self.entry(2, 200, 'Training Arc', 100))
        for fid in (base, arc):
            db.upsert_season({'franchise_id': fid, 'title_display': 'Owned release'})
        cards = db.get_series_library(search='Training')
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]['display_title'], 'Series')
        self.assertEqual(len(db.get_series_seasons(arc)), 2)
        self.assertIsNotNone(db.get_franchise(arc))

    def test_manual_grouping_and_reset_preserve_records(self):
        other = db.upsert_franchise({'display_title': 'Unmatched arc', 'user_notes': 'Keep this note'})
        db.group_with_series(other, self.fid)
        series = db.get_series(self.fid)
        self.assertIn(other, series['series_member_ids'])
        self.assertEqual(db.get_franchise(other)['user_notes'], 'Keep this note')
        db.reset_manual_grouping(self.fid)
        self.assertNotIn(other, db.get_series(self.fid)['series_member_ids'])

    def test_scanning_same_season_across_roots_preserves_both(self):
        from pathlib import Path
        from app.core.scanner import _update_on_disk_info
        root = Path(self.temp.name)
        first, second = root / 'Drive A', root / 'Drive B'
        for directory in (first, second):
            folder = directory / 'Season 1'
            folder.mkdir(parents=True)
            (folder / 'S01E01.mkv').write_bytes(b'video')
            _update_on_disk_info(self.fid, str(directory))
        _update_on_disk_info(self.fid, str(first))
        seasons = db.get_seasons_for_franchise(self.fid)
        self.assertEqual(len(seasons), 2)
        self.assertEqual(sum(s['size_bytes'] for s in seasons), 10)
        self.assertEqual({s['scan_root'] for s in seasons}, {str(first.resolve()), str(second.resolve())})
        self.assertIsNotNone(db.find_franchise_by_folder_path(str(second.resolve())))
