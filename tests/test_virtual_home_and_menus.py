"""Bounded Home slots, stable navigation state and shared native menu styling."""
import unittest,time
from unittest.mock import patch
from PyQt5.QtCore import Qt,QPoint
from PyQt5.QtWidgets import QWidget,QComboBox,QMenu,QApplication
from PyQt5.QtTest import QTest
import test_ui_regressions as support
from app import db
from app.ui.pages.library_page import LibraryPage
from app.ui.components.dropdowns import install_dropdown_style,DropdownDelegate


class VirtualHomeTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def page(self,count=1000):
        with patch('app.ui.artwork.ArtworkLoader.request'):page=LibraryPage()
        page.view_mode='grid';page._update_toggle_buttons()
        template=db.get_franchise(self.fid)
        records=[dict(template,id=10000+i,display_title=f'Anime {i:04}',anilist_id=None,cover_filename=None,series_member_ids=[10000+i]) for i in range(count)]
        page._library_index.records=records;page._library_index.groups=records;page._library_index.by_id={row['id']:row for row in records}
        page.resize(1280,850);page.show();page.refresh_display();QTest.qWait(100)
        self.addCleanup(page.deleteLater)
        return page

    def test_large_grid_has_bounded_slots_and_reuses_them_across_scroll_and_return(self):
        page=self.page();virtual=page._virtual_posters
        self.assertTrue(virtual.active);self.assertEqual(len(virtual.records),1000)
        self.assertLess(len(virtual.slots),40)
        page.page_scroll.verticalScrollBar().setValue(page.page_scroll.verticalScrollBar().maximum());QTest.qWait(50)
        first_ids={id(card) for card in virtual.slots};selected=page._cards[-1]
        self.assertEqual(selected.franchise_id,10999)
        selected.selection_box.setChecked(True);self.assertIn(10999,page.selected_fids)
        page.hide();page.show();QTest.qWait(20)
        self.assertEqual(first_ids,{id(card) for card in virtual.slots})
        with patch.object(db,'get_all_franchises',side_effect=AssertionError('Scrolling must not query the database')):
            page.page_scroll.verticalScrollBar().setValue(0);QTest.qWait(30)
            page.page_scroll.verticalScrollBar().setValue(page.page_scroll.verticalScrollBar().maximum());QTest.qWait(30)
        self.assertIn(10999,page.selected_fids)
        self.assertTrue(next(card for card in page._cards if card.franchise_id==10999).selection_box.isChecked())
        self.assertLess(len(virtual.slots),40)

    def test_rebound_slot_click_and_keyboard_use_current_identity(self):
        page=self.page(350);bar=page.page_scroll.verticalScrollBar();bar.setValue(bar.maximum());QTest.qWait(30)
        chosen=[];page.card_clicked.connect(chosen.append);card=page._cards[-1]
        card.setFocus();QTest.keyClick(card,Qt.Key_Return);self.assertEqual(chosen,[10349])
        QTest.keyClick(card,Qt.Key_Left)
        self.assertEqual(QApplication.focusWidget().franchise_id,10348)
        page._render_grid(list(reversed(page._display_franchises)));QTest.qWait(30)
        self.assertLess(len(page._virtual_posters.slots),40)
        for slot in page._cards:self.assertEqual(slot.franchise_id,slot.franchise_data['id'])

    def test_release_strip_reuses_unchanged_card(self):
        db.update_franchise_field(self.fid,'has_new_update',True)
        with patch('app.ui.artwork.ArtworkLoader.request'):page=LibraryPage()
        try:
            original=page.release_layout.itemAt(0).widget()
            page.refresh()
            self.assertIs(page.release_layout.itemAt(0).widget(),original)
            db.update_franchise_field(self.fid,'metadata_json','{"averageScore":85}')
            page.refresh()
            self.assertIs(page.release_layout.itemAt(0).widget(),original)
            self.assertIn('85',original.franchise_data['metadata_json'])
        finally:page.deleteLater()

    def test_large_list_is_delegate_painted_and_checkbox_and_details_keep_identity(self):
        page=self.page(1000);before=len(page.findChildren(QWidget))
        page.view_mode='compact';page.refresh_display();QTest.qWait(30)
        view=page.virtual_list
        self.assertEqual(view.model().rowCount(),1000);self.assertLess(len(page.findChildren(QWidget))-before,20)
        page.set_selection_mode(True)
        view.scrollTo(view.model().index(800,0));QTest.qWait(20)
        index=view.model().index(800,0)
        QTest.mouseClick(view.viewport(),Qt.LeftButton,pos=view.visualRect(index).center())
        self.assertIn(10800,page.selected_fids)
        chosen=[];page.card_clicked.connect(chosen.append)
        view.activate(view.model().index(800,6));self.assertEqual(chosen,[10800])
        page._sort_order='DESC';page.refresh_display()
        self.assertEqual(view.model().index(0,2).data(Qt.UserRole)['id'],10999)
        self.assertIn(10800,page.selected_fids)

    def test_visible_images_are_decoded_in_workers_and_stale_result_cannot_rebind(self):
        import threading
        from PyQt5.QtGui import QImage
        from app.ui.components.virtual_posters import _Read
        page=self.page(350);virtual=page._virtual_posters;seen=[]
        def image(path):
            seen.append(threading.get_ident());result=QImage(20,30,QImage.Format_RGB32);result.fill(0);return result
        for record in virtual.records:record['cover_filename']=f"fixture-{record['id']}.jpg"
        with patch('app.ui.refresh.cached_refresh_image',side_effect=image):
            virtual.revision+=1;virtual.sync()
            end=time.monotonic()+3
            while virtual.pending and time.monotonic()<end:QTest.qWait(10)
        self.assertTrue(seen);self.assertNotIn(threading.get_ident(),seen)
        slot=page._cards[0];before=slot.franchise_id
        virtual.image_ready(('old-unrelated-cover.jpg',None),QImage())
        self.assertEqual(slot.franchise_id,before)

    def test_unified_combo_and_menu_preserve_actions_and_keyboard_selection(self):
        install_dropdown_style(self.app)
        combo=QComboBox();combo.addItems(['All release states','Aired','Upcoming']);combo.resize(280,44);combo.show();self.app.processEvents()
        try:
            self.assertIsInstance(combo.itemDelegate(),DropdownDelegate)
            combo.setCurrentIndex(1);combo.showPopup();QTest.qWait(20)
            self.assertIn('unified_dropdown_popup',combo.view().window().styleSheet())
            combo.hidePopup();self.assertEqual(combo.currentText(),'Aired')
            menu=QMenu();menu.addAction('Local refresh');menu.addAction('Sync with internet');menu.popup(combo.mapToGlobal(QPoint(0,44)));QTest.qWait(20)
            self.assertEqual(len(menu.actions()),2);self.assertIn('border-radius:12px',menu.styleSheet())
            menu.close();menu.deleteLater()
        finally:combo.close();combo.deleteLater()

    def test_episode_finder_opens_release_search_for_same_anime(self):
        from app.ui.pages.episode_page import EpisodePage,EpisodeWorker
        with patch.object(EpisodeWorker,'start'):page=EpisodePage(self.fid)
        try:
            with patch('app.ui.pages.release_search_page.open_release_search') as open_page:
                # The callback imports the destination at construction time.
                with patch.object(EpisodeWorker,'start'):other=EpisodePage(self.fid)
                other.find_button.click();open_page.assert_called_once_with(other,self.fid)
                other.reject();other.deleteLater()
        finally:page.reject();page.deleteLater()
