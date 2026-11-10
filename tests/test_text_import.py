"""Numbered list parsing, Unicode identity, write-time dedupe and safe repair."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import test_ui_regressions as support
from app import db
from app.core.parser import parse_txt_line
from app.core.text_import import read_text_list,title_key,ImportIndex
from app.core.entry_service import apply_import
from app.core.import_repair import plan,apply_repair


class TextImportTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def item(self,title,**extra):
        return dict(raw_line=title,raw_title=parse_txt_line(title)['title'],matched_title=parse_txt_line(title)['title'],notes='',enabled=True,**extra)

    def test_common_list_markers_are_not_titles(self):
        for line in ('1) Naruto','2. Naruto','3] Naruto','(4) Naruto','[5] Naruto','6 - Naruto','7: Naruto','8 (Naruto)','- Naruto','* [x] Naruto','• Naruto','\ufeff9) Naruto'):
            with self.subTest(line=line):self.assertEqual(parse_txt_line(line)['title'],'Naruto')
        for line in ('1)','[2]','(3)','4. ',' # header',''):
            self.assertIsNone(parse_txt_line(line))

    def test_real_numbers_brackets_seasons_and_notes_are_preserved(self):
        for title in ('86','91 Days','2.5 Dimensional Seduction','3-gatsu no Lion','[Oshi no Ko]','Fate/stay night: Unlimited Blade Works','Fairy Tail (2018) Season 1','One Piece Season 2'):
            self.assertEqual(parse_txt_line(title)['title'],title)
        self.assertEqual(parse_txt_line('10) Fairy Tail (2018) | favourite'),dict(title='Fairy Tail (2018)',notes='favourite'))

    def test_decoding_utf8_utf16_and_windows_ansi_without_replacement_titles(self):
        file=Path(self.temp.name)/'list.txt'
        for encoding,text in [('utf-8-sig','1) 進撃の巨人'),('utf-16','1) 進撃の巨人'),('cp1252','1) Hero’s Party – Season 1')]:
            file.write_bytes(text.encode(encoding))
            self.assertEqual(read_text_list(file),[text])
        self.assertNotEqual(title_key('進撃の巨人'),title_key('鬼滅の刃'))
        self.assertEqual(title_key("Hero’s Party"),title_key("HERO'S PARTY"))
        self.assertEqual(title_key('Seasons 1–2'),title_key('Seasons 1 & 2'))
        self.assertNotEqual(title_key('Season 1–2'),title_key('Season 12'))

    def test_worker_dedupes_numbering_and_punctuation_without_collapsing_japanese(self):
        from app.ui.dialogs.watched_import_dialog import ParseAndMatchWorker
        file=Path(self.temp.name)/'list.txt'
        file.write_text("1) Hero's Party\n2) HERO’S PARTY\n3) 進撃の巨人\n4) 鬼滅の刃\n",encoding='utf-8')
        worker=ParseAndMatchWorker(str(file));output=[];worker.finished.connect(output.append)
        with patch('app.ui.dialogs.watched_import_dialog.is_offline',return_value=True):worker.run()
        self.assertEqual([item['raw_title'] for item in output[0] if item['status']!='DUPLICATE'],["Hero's Party",'進撃の巨人','鬼滅の刃'])
        self.assertEqual(output[0][1]['status'],'DUPLICATE')

    def test_apply_dedupes_new_rows_and_reimport_preserves_local_fields_and_notes(self):
        items=[self.item('1) Example Anime'),self.item('2) EXAMPLE ANIME')]
        self.assertEqual(apply_import(items,'WATCHED'),(1,1))
        existing=db.find_franchise_by_title('Example Anime')
        db.update_franchise_field(existing['id'],'root_folder_path',self.temp.name)
        db.update_franchise_field(existing['id'],'user_rating',9)
        db.update_franchise_field(existing['id'],'user_notes','Keep my note')
        again=self.item('3) Example Anime');again['notes']='New note'
        self.assertEqual(apply_import([again],'WATCHING'),(0,1))
        row=db.get_franchise(existing['id'])
        self.assertEqual(row['root_folder_path'],self.temp.name);self.assertEqual(row['user_rating'],9)
        self.assertIn('Keep my note',row['user_notes']);self.assertIn('New note',row['user_notes'])

    def test_same_provider_different_titles_merge_without_resetting_media(self):
        db.update_franchise_field(self.fid,'user_notes','Original')
        media={'id':21,'title':{'english':'ONE PIECE','romaji':'ONE PIECE'}}
        item=self.item('1) One Piece',anilist_media=media);item['notes']='Imported'
        before=len(db.get_all_franchises())
        self.assertEqual(apply_import([item],'WATCHED'),(0,1))
        self.assertEqual(len(db.get_all_franchises()),before)
        self.assertEqual(db.get_franchise(self.fid)['user_notes'],'Original\nImported')

    def test_ambiguous_same_name_different_provider_is_not_automatically_merged(self):
        for aid in (7001,7002):db.upsert_franchise(dict(display_title='Same title',anilist_id=aid))
        self.assertEqual(len(ImportIndex().matches('Same title')),2)
        with self.assertRaisesRegex(ValueError,'Multiple library entries'):apply_import([self.item('1) Same title')],'WATCHED')

    def test_repair_backs_up_renames_groups_and_keeps_every_record_and_file(self):
        file=Path(self.temp.name)/'keep.mkv';file.write_bytes(b'keep')
        old=db.upsert_franchise(dict(display_title='1) One Piece',title_romaji='1) One Piece',raw_import_name='1) One Piece',user_notes='Imported notes'))
        before=len(db.get_all_franchises());preview=plan()
        result=apply_repair(preview)
        self.assertTrue(Path(result['backup']).is_file())
        self.assertEqual(db.get_franchise(old)['display_title'],'One Piece')
        self.assertEqual(db.get_franchise(old)['user_notes'],'Imported notes')
        self.assertEqual(len(db.get_all_franchises()),before);self.assertEqual(file.read_bytes(),b'keep')
        self.assertEqual(json.loads(db.get_state('series_overrides'))[str(old)],self.fid)
        self.assertEqual(len(ImportIndex().matches('One Piece')),1)
        self.assertEqual(plan()['updates'],[]);self.assertEqual(plan()['groups'],[])

    def test_repair_does_not_overwrite_manual_titles_or_distinct_provider_releases(self):
        manual=db.upsert_franchise(dict(display_title='My chosen name',raw_import_name='1) Original title'))
        for aid in (7101,7102):db.upsert_franchise(dict(display_title='Same release name',anilist_id=aid,raw_import_name='2) Same release name'))
        preview=plan()
        self.assertNotIn(manual,[u['id'] for u in preview['updates']])
        self.assertEqual(preview['groups'],[]);self.assertTrue(preview['ambiguous'])

    def test_repair_rejects_a_stale_plan_and_recovers_exact_original_encoding(self):
        file=Path(self.temp.name)/'ansi.txt';raw='1) Hero’s Party'.encode('cp1252');file.write_bytes(raw)
        broken=raw.decode('utf-8',errors='replace')
        fid=db.upsert_franchise(dict(display_title=broken,raw_import_name=broken))
        preview=plan([file]);self.assertEqual(preview['updates'][0]['changes']['display_title'],'Hero’s Party')
        db.update_franchise_field(fid,'user_notes','Changed after preview')
        with self.assertRaisesRegex(ValueError,'Library changed'):apply_repair(preview)
        self.assertEqual(db.get_franchise(fid)['display_title'],broken)
