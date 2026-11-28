"""Approved light master, isolated Sakura family, bounded pagination and calendar."""
import json,unittest
from datetime import datetime,date
from unittest.mock import patch,Mock
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtTest import QTest
import test_ui_regressions as support
from app import db
from app.ui.theme import apply_theme
from app.ui.theme_catalog import is_manga
from app.ui.pages.library_page import LibraryPage


class MangaLightTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def tearDown(self):
        db.set_state('text_scale','1.0');apply_theme(self.app,'dark');support.Regressions.tearDown(self)
    def library(self):
        with patch.object(LibraryPage,'_request_home_facts'):
            page=LibraryPage()
        self.addCleanup(page.deleteLater);return page

    def test_existing_modes_keep_palette_and_manga_is_distinct_saved_selection(self):
        from app.ui.home_style import qss
        from app.config import set_theme,get_theme
        apply_theme(self.app,'light');sakura=qss();self.assertFalse(is_manga())
        set_theme('manga_light');apply_theme(self.app,get_theme())
        self.assertTrue(is_manga());self.assertEqual(self.app.property('animevaultTheme'),'light');self.assertNotEqual(qss(),sakura)
        self.assertEqual(self.app.property('animevaultRequestedTheme'),'manga_light')
        apply_theme(self.app,'light');self.assertEqual(qss(),sakura)
        self.assertEqual(db.get_state('theme'),'manga_light')

    def test_pagination_reuses_six_slots_and_search_resets_page(self):
        for i in range(100):db.upsert_franchise({'display_title':f'Title {i:03}'})
        apply_theme(self.app,'manga_light');page=self.library();page.resize(1500,1000);page.show();self.app.processEvents()
        self.assertEqual(len(page._cards),6);slots={id(card) for card in page._cards};self.assertFalse(page._virtual_posters.active)
        page.pagination.go(2);self.assertEqual(page.pagination.page,2);self.assertEqual({id(c) for c in page._cards},slots)
        self.assertLessEqual(len(page._card_pool),6)
        page.set_search_query('Title 099');self.assertEqual(page.pagination.page,1);self.assertEqual(len(page._cards),1)
        self.assertEqual(page._cards[0].franchise_data['display_title'],'Title 099')
        page.hide()

    def test_runtime_theme_switch_restores_sakura_hero_and_continuous_grid(self):
        for i in range(12):db.upsert_franchise({'display_title':f'Series {i}'})
        apply_theme(self.app,'dark');page=self.library();hero=page.hero_card;original=page._card_pool
        apply_theme(self.app,'manga_light');page.refresh_home_style();page.refresh_display()
        self.assertIsNot(page.hero_card,hero);self.assertFalse(page.pagination.isHidden());self.assertEqual(len(page._cards),6)
        apply_theme(self.app,'dark');page.refresh_home_style();page.refresh_display()
        self.assertIs(page.hero_card,hero);self.assertIs(page._card_pool,original);self.assertTrue(page.pagination.isHidden());self.assertEqual(len(page._cards),13)

    def test_return_from_manga_detaches_paged_cards_before_showing_virtual_cards(self):
        from app.ui.components.home_poster import HomePosterCard

        for i in range(72):db.upsert_franchise({'display_title':f'Series {i:03}'})
        apply_theme(self.app,'dark');page=self.library();page.resize(1440,900);page.show()
        page.refresh_display();self.app.processEvents()
        self.assertTrue(page._virtual_posters.active)
        original_slots=set(page._virtual_posters.slots)
        for theme in ('manga_light','manga_dark'):
            apply_theme(self.app,theme);page.refresh_home_style();page.refresh_display();self.app.processEvents()
            apply_theme(self.app,'dark');page.refresh_home_style();page.refresh_display();self.app.processEvents()
            visible={card for card in page.grid_container.findChildren(HomePosterCard, options=Qt.FindDirectChildrenOnly) if not card.isHidden()}
            self.assertTrue(page._virtual_posters.active)
            self.assertEqual(len(visible),len(page._cards))
            self.assertEqual(visible,set(page._cards))
            self.assertTrue(original_slots.intersection(visible))
        page.hide()

    def test_release_strip_and_heading_match_the_library_canvas_across_themes(self):
        from app.ui.home_style import colors

        apply_theme(self.app,'manga_dark');page=self.library();page.resize(1440,1250);page.show()
        page.release_heading_widget.show();page.release_scroll.show()
        for theme in ('manga_dark','dark','manga_light','light'):
            with self.subTest(theme=theme):
                apply_theme(self.app,theme);page.refresh_home_style();self.app.processEvents()
                for widget in (page.release_heading_widget,page.release_scroll.viewport(),page.release_scroll.widget()):
                    self.assertEqual(widget.grab().toImage().pixelColor(2,2).name(),colors()['bg'])
        page.hide()

    def test_shell_routes_search_and_keeps_old_family_shell(self):
        from app.ui.main_window import MainWindow
        from app.ui.pages.downloads_page import DownloadsPage
        with patch.object(LibraryPage,'_request_home_facts'),patch.object(DownloadsPage,'refresh'):
            window=MainWindow.__new__(MainWindow);QMainWindow.__init__(window);window._dirty_pages=set();window._setup_ui()
        window._task_timer.stop();window.downloads_page.timer.stop();self.addCleanup(window.deleteLater)
        window.resize(1280,800);window.show()
        window._on_theme_changed('manga_light');self.app.processEvents()
        self.assertTrue(window.manga_rail.isVisible());self.assertIs(window.header_stack.currentWidget(),window.manga_header)
        before=window.stacked_widget.geometry();cards_before=window.library_page.page_scroll.viewport().width()
        window.manga_rail._set_rail_width(240);self.app.processEvents()
        self.assertEqual(window.stacked_widget.geometry(),before);self.assertEqual(window.library_page.page_scroll.viewport().width(),cards_before)
        self.assertEqual(window.manga_rail_slot.width(),94);window.manga_rail._set_rail_width(94)
        window.manga_header.search.setText('One Piece');self.assertEqual(window.top_search_input.text(),'One Piece');self.assertEqual(window.library_page._search_query,'One Piece')
        window._focus_library_search();self.assertTrue(window.manga_header.search.hasFocus())
        db.set_state('text_scale','1.3');window._on_theme_changed('manga_light');self.app.processEvents();QTest.qWait(100)
        self.assertTrue(window.library_page._calendar_controls_wrapped)
        self.assertEqual(window.header_stack.height(),91)
        self.assertLessEqual(window.library_page.calendar_panel.width(),window.library_page.page_scroll.viewport().width())
        window._on_theme_changed('dark');self.assertFalse(window.manga_rail.isVisible());self.assertIs(window.header_stack.currentWidget(),window.home_header)
        window.hide()

    def test_calendar_collects_owned_cached_history_without_guessing_other_titles(self):
        from app.core.calendar_view import entries
        stamp=int(datetime(2026,11,14,20,30).timestamp())
        db.update_franchise_field(self.fid,'anilist_id',901)
        db.update_franchise_field(self.fid,'metadata_json',json.dumps({'nextAiringEpisode':{'airingAt':stamp,'episode':20}}))
        db.set_state('release_calendar.v1',json.dumps([{'mediaId':901,'episode':19,'airingAt':stamp-86400},{'mediaId':999999,'episode':1,'airingAt':stamp}]))
        rows=entries(date(2026,11,1),date(2026,11,30))
        self.assertEqual({r['episode'] for r in rows},{19,20});self.assertTrue(all(r['fid']==self.fid for r in rows))

    def test_full_calendar_loads_and_navigates_months_from_cache(self):
        from app.ui.pages.full_calendar_page import FullCalendarPage
        from PyQt5.QtTest import QSignalSpy
        from app.ui.components.airing_count import AiringDay
        apply_theme(self.app,'manga_light');page=FullCalendarPage();self.addCleanup(page.deleteLater)
        worker=page.worker
        if worker:self.assertTrue(QSignalSpy(worker.finished).wait(3000))
        self.assertTrue(page.title.text());self.assertIn('saved broadcasts',page.status.text());self.assertGreaterEqual(len(page.findChildren(AiringDay)),28)
        previous=page.month;page.change(1);worker=page.worker
        if worker:self.assertTrue(QSignalSpy(worker.finished).wait(3000))
        self.assertGreater(page.month,previous);page.change(-1);worker=page.worker
        if worker:self.assertTrue(QSignalSpy(worker.finished).wait(3000))
        self.assertEqual(page.month,previous);page.stop()

    def test_wide_library_seven_cards_and_narrow_six_reuses_slots(self):
        for i in range(20):db.upsert_franchise({'display_title':f'Wide title {i}'})
        apply_theme(self.app,'manga_light');page=self.library();page.resize(2000,1000);page.show();QTest.qWait(200)
        self.assertEqual(page.pagination.size,7);self.assertEqual(len(page._cards),7)
        page.resize(1280,900);QTest.qWait(200)
        self.assertEqual(page.pagination.size,6);self.assertEqual(len(page._cards),6);self.assertLessEqual(len(page._card_pool),7)
        page.hide()

    def test_navigation_distance_blur_and_reduced_motion(self):
        from app.ui.components.manga_shell import MangaRail
        from PyQt5.QtCore import QEvent
        host=Mock();apply_theme(self.app,'manga_light');self.app.setProperty('animevaultReducedMotion',False)
        rail=MangaRail(host);self.addCleanup(rail.deleteLater)
        def finish_blur():
            for animation in rail._motions:
                animation.setCurrentTime(animation.duration())
        group=rail.motion_groups[0];rail._hovered=None;rail._blur_group(group,1);finish_blur()
        radii=[rail._blur_effects[b].blurRadius() for b in group]
        from app.ui.components.manga_navigation import opacity_for_blur
        self.assertEqual(radii[1],0);self.assertAlmostEqual(radii[0],radii[2])
        self.assertTrue(all(.3<=opacity_for_blur(radius)<=1 for radius in radii))
        self.assertLess(opacity_for_blur(radii[3]),opacity_for_blur(radii[2]))
        rail._expanded=True;rail.activate(2);finish_blur()
        self.assertEqual(rail._blur_effects[rail.buttons[2]].blurRadius(),0)
        self.assertAlmostEqual(opacity_for_blur(rail._blur_effects[rail.buttons[0]].blurRadius()),.5)
        self.assertAlmostEqual(opacity_for_blur(rail._blur_effects[rail.buttons[5]].blurRadius()),.5)
        target=rail.buttons[4];rail.eventFilter(target,QEvent(QEvent.Enter));finish_blur()
        self.assertEqual(rail._blur_effects[target].blurRadius(),0)
        rail.eventFilter(target,QEvent(QEvent.Leave));finish_blur()
        self.assertGreater(rail._blur_effects[target].blurRadius(),0)
        self.app.setProperty('animevaultReducedMotion',True);rail._blur_group(group,1)
        self.assertTrue(all(e.blurRadius()==0 for e in rail._blur_effects.values()))
        rail.enterEvent(QEvent(QEvent.Enter));self.assertEqual(rail.width(),240)
        self.assertTrue(all(b.text() for b in rail.collection_buttons));rail.leaveEvent(QEvent(QEvent.Leave));self.assertEqual(rail.width(),94);rail.hide()

    def test_entry_choice_adapter_preserves_fields_and_sakura_layout(self):
        from app.ui.dialogs.custom_entry import CustomEntryDialog
        apply_theme(self.app,'manga_light');dialog=CustomEntryDialog(db.get_franchise(self.fid));self.addCleanup(dialog.deleteLater)
        self.assertTrue(dialog._manga_form);self.assertTrue(dialog.full_page)
        combo,panel=dialog._manga_choices[0];buttons=panel.findChildren(__import__('PyQt5.QtWidgets',fromlist=['QPushButton']).QPushButton)
        buttons[1].click();self.assertEqual(combo.currentData(),'WATCHING')
        rating=dialog.rating_combo;rating.setCurrentIndex(6)
        self.assertEqual(dialog._manga_choices[1][1].findChildren(__import__('PyQt5.QtWidgets',fromlist=['QPushButton']).QPushButton)[6].isChecked(),True)
        apply_theme(self.app,'light');dialog.refresh_home_style();self.assertFalse(dialog._manga_form);self.assertFalse(combo.isHidden());self.assertEqual(combo.currentData(),'WATCHING');self.assertEqual(rating.currentData(),6)
