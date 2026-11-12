import csv,json,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from PyQt5.QtTest import QTest,QSignalSpy
import test_ui_regressions as support
from app import db

class AuditFixTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_sql_identifiers_and_sort_are_not_interpreted_as_code(self):
        self.assertEqual(len(db.get_all_franchises(sort_order='ASC, (SELECT value FROM app_state)')),1)
        with self.assertRaises(ValueError):db.update_franchise_field(self.fid,'user_notes=(SELECT value FROM app_state),user_notes','x')
        with self.assertRaises(ValueError):db.update_season_field(1,'id=id--',1)
        from app.core.entry_service import save_entry
        with self.assertRaises(ValueError):save_entry({'display_title=? WHERE 1=1--':'bad'},db.get_franchise(self.fid))
    def test_api_enforces_token_origin_and_keeps_inspector_private_data(self):
        from fastapi.testclient import TestClient
        from app.api import server
        db.update_franchise_field(self.fid,'root_folder_path','E:/Private/Anime');db.update_franchise_field(self.fid,'user_notes','Private note')
        with patch.object(server,'API_ACCESS_TOKEN','secret'),TestClient(server.api) as client:
            self.assertEqual(client.get('/api/library').status_code,401)
            headers={'Authorization':'Bearer secret'}
            self.assertEqual(client.get('/api/library',headers={**headers,'Origin':'https://evil.test'}).status_code,403)
            result=client.get('/api/library',headers=headers);self.assertEqual(result.status_code,200)
            self.assertNotIn('root_folder_path',result.json()[0]);self.assertNotIn('user_notes',result.json()[0])
            self.assertEqual(client.get('/api/library?sort_order=ASC,bad',headers=headers).status_code,422)
        self.assertEqual(server.franchise_payload(self.fid)['user_notes'],'Private note')
    def test_cover_path_cannot_escape_cache(self):
        from fastapi.testclient import TestClient
        from app.api import server
        db.update_franchise_field(self.fid,'cover_filename','../outside.jpg')
        with patch.object(server,'API_ACCESS_TOKEN',''),TestClient(server.api) as client:
            self.assertEqual(client.get(f'/api/cover/{self.fid}').status_code,403)
    def test_csv_neutralizes_formulas_without_changing_json(self):
        from app.core import exporter
        db.update_franchise_field(self.fid,'display_title','=HYPERLINK("evil")')
        with patch.object(exporter,'EXPORTS_DIR',Path(self.temp.name)):
            path=exporter.export_csv()
        with open(path,encoding='utf-8',newline='') as stream:rows=list(csv.reader(stream))
        self.assertTrue(rows[1][2].startswith("'="));self.assertTrue(db.get_franchise(self.fid)['display_title'].startswith('='))
    def test_notes_coalesce_flush_and_rating_does_not_restyle_dialog(self):
        from app.ui.pages.detail_modal import DetailModal
        from app.ui.user_edits import user_edits
        page=DetailModal(self.fid)
        with patch.object(page,'refresh_home_style') as restyle:
            page._set_rating(8);restyle.assert_not_called()
        page.notes_edit.setPlainText('First');page.notes_edit.setPlainText('Final saved note')
        page.done(0)
        service=user_edits();service.flush()
        for _ in range(500):
            if not service.worker and not service.pending:break
            QTest.qWait(10)
        record=db.get_franchise(self.fid);self.assertEqual(record['user_notes'],'Final saved note');self.assertEqual(record['user_rating'],8)
        page.deleteLater()
    def test_artwork_is_bounded_and_rejects_plaintext(self):
        from app.core import anilist_client as api
        with patch.object(api.requests,'get') as get:self.assertIsNone(api._download_artwork('http://example.test/a.jpg','x.jpg'));get.assert_not_called()
        response=Mock(status_code=200,headers={'Content-Length':str(17*1024**2)})
        with patch.object(api.requests,'get',return_value=response):self.assertIsNone(api._download_artwork('https://example.test/a.jpg','x.jpg'))
        response.close.assert_called()

    def test_personal_rating_patches_compact_cell_without_rebuilding_rows(self):
        from app.ui.pages.library_page import LibraryPage
        page=LibraryPage();page._set_view_mode('compact')
        original=page.compact_table.cellWidget(0,2)
        page._library_index.by_id[self.fid]['user_rating']=9
        for group in page._library_index.groups:
            if group['id']==self.fid:group['user_rating']=9
        with patch.object(db,'get_connection',side_effect=AssertionError('No DB read for cached edit')):
            page.refresh_user_fields({self.fid:{'user_rating':9}})
        self.assertIs(page.compact_table.cellWidget(0,2),original)
        self.assertEqual(page.compact_table.item(0,5).text(),'★ 9/10');page.deleteLater()
