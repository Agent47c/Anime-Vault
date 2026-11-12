import json,unittest
from pathlib import Path
from unittest.mock import patch
import test_ui_regressions as support
from app import db
from app.core import duplicates
from PyQt5.QtCore import Qt

class RequestedUIFixes(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_saved_duplicates_are_revalidated_and_previous_snapshots_kept(self):
        root=Path(self.temp.name);files=[]
        for name in ('ep1.mkv','ep1-copy.mkv'):
            path=root/name;path.write_bytes(b'same');files.append(dict(path=str(path),signature=duplicates.signature(path),title='Test',episodes=[1]))
        group={'hash':'old','files':files};duplicates.save_review(([group],[]))
        self.assertEqual(len(duplicates.load_review()[0]),1)
        (root/'ep1-copy.mkv').rename(root/'moved.mkv')
        groups,errors=duplicates.load_review();self.assertEqual(groups,[]);self.assertIn('Missing, moved or changed',errors[0])
        duplicates.save_review(([],[]));self.assertEqual(len(json.loads(db.get_state('duplicates.review_history'))),2)
    def test_saved_review_stops_and_drive_scan_stops_before_disk_work(self):
        duplicates.save_review(([{'files':[{'path':'not-read'}]}],[]))
        with self.assertRaises(InterruptedError):duplicates.load_review(lambda:True)
        with self.assertRaises(InterruptedError):duplicates.find_duplicates(lambda:True)
    def test_group_card_uses_matched_details_without_changing_identity(self):
        old=db.upsert_franchise({'display_title':'Fairy Tail'})
        matched=db.upsert_franchise({'display_title':'Fairy Tail matched','anilist_id':999,'synopsis':'Full story','cover_filename':'poster.jpg'})
        db.group_with_series(matched,old)
        card=db.get_series(old);self.assertEqual(card['id'],old);self.assertEqual(card['synopsis'],'Full story');self.assertEqual(card['cover_filename'],'poster.jpg')
        self.assertIsNone(db.get_franchise(old)['anilist_id'])
    def test_search_hides_home_promotions_and_restores_configured_order(self):
        from app.ui.pages.library_page import LibraryPage
        page=LibraryPage();page.set_search_query('One Piece')
        for widget in (page.hero_card,page.calendar_panel,page.release_scroll,page.release_heading_widget):self.assertTrue(widget.isHidden())
        db.set_state('home.release_position','above_hero');page.set_search_query('')
        self.assertLess(page._content_layout.indexOf(page.release_heading_widget),page._content_layout.indexOf(page.hero_card))
        self.assertFalse(page.hero_card.isHidden());page.deleteLater()
    def test_watch_buttons_point_and_synopsis_scroll_is_optional(self):
        from app.ui.pages.detail_modal import DetailModal
        from PyQt5.QtWidgets import QScrollArea
        db.update_franchise_field(self.fid,'synopsis','A short synopsis.')
        page=DetailModal(self.fid);page.resize(1200,850);page.show();self.app.processEvents()
        self.assertTrue(all(button.cursor().shape()==Qt.PointingHandCursor for button in page.watch_status_buttons.buttons()))
        synopsis=next(scroll for scroll in page.findChildren(QScrollArea) if scroll.widget() is page.synopsis_label)
        self.assertEqual(synopsis.verticalScrollBarPolicy(),Qt.ScrollBarAsNeeded)
        self.assertEqual(synopsis.verticalScrollBar().maximum(),0)
        page.hide();page.deleteLater()

    def test_organizer_embedded_actions_fit_without_global_cell_padding(self):
        from app.ui.pages.organizer_page import OrganizerPage
        from PyQt5.QtWidgets import QPushButton,QLabel
        page=OrganizerPage();page._data[page._current_tab]=[dict(anime_name='Test',video_count=1,status_badge='Download ready',is_organized=False)]
        page._render_table();page.resize(1280,900);page.show();self.app.processEvents()
        for col,kind in ((2,QLabel),(3,QPushButton)):
            cell=page.table.cellWidget(0,col);control=cell.findChild(kind)
            self.assertGreaterEqual(cell.width(),control.width())
            self.assertGreaterEqual(control.width(),control.fontMetrics().horizontalAdvance(control.text())+12)
        page.close();page.deleteLater()
