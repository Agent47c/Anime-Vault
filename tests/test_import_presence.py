"""Existing-title visibility and conservative packaging-aware metadata matching."""
import unittest
import json
from unittest.mock import patch
import test_ui_regressions as support
from app import db
from app.core.text_import import clean_import_name,ImportIndex
from app.core.import_preview import preview_lines
from app.core import import_matching
from app.core.entry_service import apply_import


class ImportPresenceTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def media(self,aid=9001,title='Example Anime',**values):
        return dict(id=aid,title={'english':title,'romaji':title},format='TV',seasonYear=2018,**values)

    def test_cleanup_preserves_years_real_title_numbers_and_bracket_names(self):
        for title in ('Fairy Tail (2018) Season 1','Hunter x Hunter (2011)','86','91 Days','Pseudo Harem','[Oshi no Ko]'):
            self.assertEqual(clean_import_name(title),title)
        cases={'[ASW] Example Anime [1080p HEVC x265 10Bit][AAC] (Batch)':'Example Anime',
               '[AnimeRG] Bleach (Complete Series) EP 001-366 [480p] [Dual-Audio] [pseudo]':'Bleach',
               'Jujutsu Kaisen S01 1080p Dual Audio WEBRip AAC x265-EMBER':'Jujutsu Kaisen S01',
               '[ASW] Shinmai Ossan Boukensha - 01':'Shinmai Ossan Boukensha',
               'Hagure Yuusha no Aesthetica [1080]':'Hagure Yuusha no Aesthetica'}
        for raw,expected in cases.items():self.assertEqual(clean_import_name(raw),expected)

    def test_existing_and_duplicate_titles_are_visible_but_not_reimported(self):
        rows=list(preview_lines(['1) One Piece','2) One Piece'],online=False))
        self.assertEqual([r['status'] for r in rows],['MERGED','DUPLICATE'])
        self.assertEqual(rows[0]['existing_id'],self.fid)
        self.assertTrue(all(not r['enabled'] for r in rows))

    def test_cached_synonyms_and_release_tags_find_existing_identity(self):
        db.update_franchise_field(self.fid,'metadata_json',json.dumps({'synonyms':['Pirate Adventure']}))
        self.assertEqual(ImportIndex().matches('[ASW] Pirate Adventure [1080p]')[0]['id'],self.fid)

    def test_year_and_season_conflicts_require_review(self):
        wrong=self.media(title='Fairy Tail')
        wrong['seasonYear']=2009
        selected,ranked=import_matching.choose('Fairy Tail (2018) Season 1',[wrong])
        self.assertIsNone(selected);self.assertTrue(ranked[0]['conflict'])
        correct=self.media(title='Fairy Tail');correct['seasonYear']=2018
        self.assertIsNotNone(import_matching.choose('Fairy Tail (2018) Season 1',[correct])[0])
        self.assertIsNone(import_matching.choose('Fairy Tail Seasons 1–8',[correct])[0])
        self.assertIsNone(import_matching.choose('Fairy Tail S03',[correct])[0])

    def test_close_alternative_is_not_selected_automatically(self):
        first=self.media();second=self.media(aid=9002)
        self.assertIsNone(import_matching.choose('Example Anime',[first,second])[0])

    def test_existing_unmatched_metadata_is_previewed_then_applied_without_file_changes(self):
        fid=db.upsert_franchise(dict(display_title='Example Anime',raw_import_name='Example Anime',root_folder_path=self.temp.name,user_notes='Keep notes',user_rating=8,is_custom=1))
        media=self.media()
        with patch('app.core.import_matching.search',return_value=(media,[])),patch('app.core.anilist_client.download_cover',return_value=None):
            rows=list(preview_lines(['Example Anime'],online=True,rematch_existing=True))
        self.assertEqual(rows[0]['status'],'EXISTING_MATCHED')
        self.assertIsNone(db.get_franchise(fid)['anilist_id'])
        rows[0]['enabled']=True;apply_import(rows,'WATCHED')
        row=db.get_franchise(fid)
        self.assertEqual(row['anilist_id'],media['id']);self.assertEqual(row['root_folder_path'],self.temp.name)
        self.assertEqual(row['user_notes'],'Keep notes');self.assertEqual(row['user_rating'],8)

    def test_provider_owned_elsewhere_groups_instead_of_deleting_old_record(self):
        fid=db.upsert_franchise(dict(display_title='Pirate Adventure',user_notes='Separate note',is_custom=1))
        item=dict(raw_line='Pirate Adventure',raw_title='Pirate Adventure',matched_title='One Piece',notes='',enabled=True,
                  existing_id=fid,update_metadata=True,anilist_media=self.media(aid=21,title='One Piece'))
        apply_import([item],'WATCHED')
        self.assertIsNotNone(db.get_franchise(fid))
        self.assertEqual(db.get_franchise(fid)['user_notes'],'Separate note')
        self.assertEqual(db.get_franchise(self.fid)['anilist_id'],21)
        self.assertEqual(json.loads(db.get_state('series_overrides'))[str(fid)],self.fid)

    def test_later_alias_row_sees_provider_link_added_earlier_in_same_import(self):
        fid=db.upsert_franchise(dict(display_title='Custom alias',user_notes='Keep note',root_folder_path=self.temp.name,is_custom=1))
        media=self.media()
        items=[dict(raw_line='Custom alias',raw_title='Custom alias',matched_title='Example Anime',notes='',enabled=True,
                    existing_id=fid,update_metadata=True,anilist_media=media),
               dict(raw_line='Example Anime',raw_title='Example Anime',matched_title='Example Anime',notes='Extra',enabled=True,anilist_media=media)]
        self.assertEqual(apply_import(items,'WATCHED'),(0,2))
        row=db.get_franchise(fid)
        self.assertEqual(row['root_folder_path'],self.temp.name)
        self.assertEqual(row['user_notes'],'Keep note\nExtra')

    def test_importer_existing_counter_and_filter(self):
        from app.ui.dialogs.watched_import_dialog import WatchedImportDialog
        dialog=WatchedImportDialog()
        for item in preview_lines(['One Piece','Brand New Anime'],online=False):dialog._add_item_row(item)
        self.assertEqual(dialog._count_labels['existing'].text(),'1')
        dialog.result_filter.setCurrentIndex(1)
        self.assertFalse(dialog.items_layout.itemAt(0).widget().isHidden())
        self.assertTrue(dialog.items_layout.itemAt(1).widget().isHidden())
        dialog.deleteLater()

    def test_list_audit_adds_only_missing_names_and_is_idempotent(self):
        from pathlib import Path
        from app.core.text_list_audit import audit,add_missing
        file=Path(self.temp.name)/'list.txt';file.write_text('1) One Piece\n2) New Title (2018)\n3) New Title (2018)\n',encoding='utf-8')
        rows=audit([file])
        self.assertEqual(rows[0]['status'],'Already in library')
        self.assertTrue(rows[2]['duplicate'])
        result=add_missing(rows)
        self.assertEqual(result['added'],1);self.assertTrue(Path(result['backup']).is_file())
        after=audit([file]);self.assertTrue(all(row['ids'] for row in after))
        self.assertEqual(add_missing(after)['added'],0)
        record=db.get_franchise(after[1]['ids'][0]);self.assertTrue(record['needs_review']);self.assertIsNone(record['anilist_id'])

    def test_list_audit_does_not_add_duplicate_when_existing_match_is_ambiguous(self):
        from pathlib import Path
        from app.core.text_list_audit import audit,add_missing
        for aid in (8001,8002):db.upsert_franchise(dict(display_title='Ambiguous Anime',anilist_id=aid))
        file=Path(self.temp.name)/'list.txt';file.write_text('Ambiguous Anime',encoding='utf-8')
        rows=audit([file]);self.assertEqual(rows[0]['status'],'Present — review match')
        self.assertEqual(add_missing(rows)['added'],0)

    def test_confirmed_import_alias_survives_provider_display_name_and_reimport(self):
        media=self.media(title='Fairy Tail Final Season');media['synonyms']=['Fairy Tail (2018)']
        item=dict(raw_line='Fairy Tail (2018) Season 1',raw_title='Fairy Tail (2018) Season 1',
            matched_title='Fairy Tail Final Season',anilist_media=media,notes='',enabled=True)
        self.assertEqual(apply_import([item],'WATCHED'),(1,0))
        matches=ImportIndex().matches('Fairy Tail (2018) Season 1');self.assertEqual(len(matches),1)
        self.assertEqual(apply_import([item],'WATCHED'),(0,1))
        db.update_franchise_field(matches[0]['id'],'anilist_id',9002)
        self.assertFalse(ImportIndex().matches('Fairy Tail (2018) Season 1'))
