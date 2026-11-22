import unittest
from unittest.mock import patch
from PyQt5.QtWidgets import QFrame,QMainWindow,QStackedWidget,QWidget
import test_ui_regressions as support
from app import db
from app.ui.pages.organizer_page import OrganizerPage,ScannerWorker
from app.ui.theme import apply_theme


class OrganizerReferenceTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_reference_keeps_manual_scan_merge_and_duplicate_entry(self):
        with patch.object(ScannerWorker,'start') as scanner:
            page=OrganizerPage();page.resize(1200,900);page.show();self.app.processEvents();scanner.assert_not_called()
            self.assertEqual(page.organizer_tabs.count(),3);self.assertIs(page.organizer_tabs.widget(1),page.merge_page)
            self.assertEqual(page.organizer_tabs.tabText(2),'Review duplicate files');self.assertFalse(page.duplicates_btn.isVisible())
            self.assertEqual(len(page.rule_switches),5);self.assertGreater(page.preview_card.width(),page.width()*.8)
            page.scan_btn.click();scanner.assert_called_once();page.close();page.deleteLater()
    def test_theme_refresh_does_not_rebuild_or_change_rules(self):
        page=OrganizerPage();before=dict(page._rules);merge=page.merge_page
        self.app.setProperty('animevaultTheme','light');page.refresh_home_style()
        self.assertIn('#f7f3f6',page.season_tab.styleSheet());self.assertIs(page.merge_page,merge);self.assertEqual(page._rules,before)
        self.app.setProperty('animevaultTheme','dark');page.deleteLater()

    def test_hidden_organizer_drops_old_dark_surfaces_when_opened_in_sakura_light(self):
        db.add_watched_directory(self.temp.name)
        apply_theme(self.app,'manga_dark')
        window=QMainWindow();window.setProperty('animevaultScopedWindow',True)
        stack=QStackedWidget();stack.addWidget(QWidget());window.setCentralWidget(stack)
        page=OrganizerPage();page.setProperty('animevaultThemeScope',True);stack.addWidget(page)
        window.resize(1440,960);window.show();self.app.processEvents()
        try:
            apply_theme(self.app,'light');stack.setCurrentWidget(page);self.app.processEvents()
            cards=page.season_tab.findChildren(QFrame,'organizer_card')
            self.assertEqual(len(cards),3)
            for card in cards:
                self.assertEqual(card.grab().toImage().pixelColor(8,30).name(),'#ffffff')
            self.assertEqual(page.table.viewport().grab().toImage().pixelColor(2,2).name(),'#ffffff')
            roots=page.season_tab.findChildren(QFrame,'organizer_row')
            self.assertEqual(len(roots),1)
            self.assertEqual(roots[0].grab().toImage().pixelColor(5,16).name(),'#eee6ee')
            for index in (1,2):
                page.organizer_tabs.setCurrentIndex(index);self.app.processEvents()
                self.assertIn('#f7f3f6',page.organizer_tabs.widget(index).styleSheet())
        finally:
            window.hide();window.deleteLater();apply_theme(self.app,'dark')

    def test_manga_dark_organizer_tabs_share_the_same_face_color(self):
        from app.ui.manga_style import DARK_COLORS

        apply_theme(self.app,'manga_dark')
        page=OrganizerPage();self.addCleanup(page.deleteLater)
        page.resize(1440,960);page.show();self.app.processEvents()
        try:
            tabs=page.organizer_tabs
            bar=tabs.tabBar()
            for current in range(tabs.count()):
                tabs.setCurrentIndex(current);self.app.processEvents()
                image=bar.grab().toImage()
                for index in range(tabs.count()):
                    rect=bar.tabRect(index)
                    self.assertEqual(image.pixelColor(rect.center().x(),rect.top()+18).name(),DARK_COLORS['panel'])
        finally:
            page.hide();apply_theme(self.app,'dark')

    def test_saved_preview_badge_uses_active_theme_tokens(self):
        from PyQt5.QtGui import QPalette
        from app.ui.home_style import colors

        apply_theme(self.app,'manga_dark')
        page=OrganizerPage();self.addCleanup(page.deleteLater)
        page.resize(1200,900);page.show()
        try:
            page._on_scan_finished({'unorganized':[],'organized':[],'all':[]},cached=True)
            badge=page.top_status_badge
            for theme in ('manga_dark','light','manga_light','dark'):
                with self.subTest(theme=theme):
                    apply_theme(self.app,theme);self.app.processEvents()
                    self.assertEqual(badge.text(),'Saved preview · 0 need organization · 0 organized')
                    self.assertEqual(badge.styleSheet(),'')
                    self.assertEqual(badge.palette().color(QPalette.WindowText).name(),colors()['ok'])
                    self.assertEqual(badge.grab().toImage().pixelColor(6,badge.height()//2).name(),colors()['raised'])
            page._mark_preview_stale('Preview needs updating')
            self.assertEqual(badge.palette().color(QPalette.WindowText).name(),colors()['amber'])
        finally:
            page.hide();apply_theme(self.app,'dark')

    def test_rules_match_settings_rows_and_root_remove_has_trash_icon(self):
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QPalette
        from PyQt5.QtTest import QTest
        from PyQt5.QtWidgets import QLabel,QPushButton
        from app.ui.components.settings_switch import SettingsSwitch
        from app.ui.icons import icon
        from app.ui.pages.settings_page import SettingsPage

        db.add_watched_directory(self.temp.name)
        apply_theme(self.app,'manga_dark')
        page=OrganizerPage();settings=SettingsPage()
        self.addCleanup(page.deleteLater);self.addCleanup(settings.deleteLater)
        page.resize(1440,960);settings.resize(1440,960);settings.show();page.show()
        try:
            self.app.processEvents()
            switch=page.rule_switches['detect_episode_numbers']
            self.assertIsInstance(switch,SettingsSwitch)
            other=next(w for w in settings.findChildren(SettingsSwitch) if w.accessibleName()=='Compact library')
            self.assertEqual(switch.size(),other.size())
            for name in ('settings_label','settings_hint'):
                label=switch.parentWidget().findChild(QLabel,name)
                reference=other.parentWidget().findChild(QLabel,name)
                self.assertEqual(label.font().pixelSize(),reference.font().pixelSize())
                self.assertEqual(label.palette().color(QPalette.WindowText),reference.palette().color(QPalette.WindowText))
            original=switch.isChecked()
            QTest.keyClick(switch,Qt.Key_Space)
            self.assertEqual(page._rules['detect_episode_numbers'],not original)
            remove=page.findChild(QPushButton,'remove_library_root')
            self.assertEqual(remove.text(),'')
            self.assertEqual(remove.icon().cacheKey(),icon('trash','#df2545').cacheKey())
            with patch.object(page,'_remove_library_root') as remove_root:
                remove.click();remove_root.assert_called_once_with(db.get_watched_directories()[0]['id'])
        finally:
            page.hide();settings.hide();apply_theme(self.app,'dark')

    def test_duplicate_tab_is_manual_and_only_extra_copy_can_be_selected(self):
        from PyQt5.QtCore import Qt
        from app.ui.pages.duplicate_page import DuplicateWorker
        with patch.object(DuplicateWorker,'start') as start:
            page=OrganizerPage();page.organizer_tabs.setCurrentIndex(2);page.show();self.app.processEvents();start.assert_not_called()
            dup=page._duplicate_page;files=[dict(title='Example',path='a.mkv',episodes=[6]),dict(title='Example',path='b.mkv',episodes=[6])]
            dup._results(([dict(files=files)],[]));branch=dup.tree.topLevelItem(0).child(0)
            self.assertFalse(branch.child(0).flags() & Qt.ItemIsUserCheckable);self.assertFalse(dup._selected())
            branch.child(1).setCheckState(0,Qt.Checked);self.assertEqual(len(dup._selected()),1);self.assertTrue(dup.delete.isEnabled());page.close();page.deleteLater()
    def test_duplicate_scan_waits_for_merge(self):
        from app.ui.pages.duplicate_page import DuplicateWorker
        page=OrganizerPage()
        with patch.object(page.merge_page,'busy',return_value=True),patch.object(DuplicateWorker,'start') as start:page._duplicate_page._scan();start.assert_not_called()
        self.assertIn('Wait',page._duplicate_page.status.text());page.deleteLater()
