import unittest
from pathlib import Path
from unittest.mock import patch
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QColor,QPalette
from PyQt5.QtWidgets import QMainWindow,QWidget,QVBoxLayout,QLabel
from PyQt5.QtTest import QTest
from app.ui.theme import apply_theme
import test_ui_regressions as support

class Scope(QWidget):
    def __init__(self,parent):
        super().__init__(parent);self.refreshes=0;self.setProperty('animevaultThemeScope',True)
    def refresh_home_style(self):self.refreshes+=1

class ThemeFamilyTransitionTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def tearDown(self):apply_theme(self.app,'dark');support.Regressions.tearDown(self)

    def test_sakura_startup_registers_bundled_manga_fonts_before_live_switch(self):
        from PyQt5.QtGui import QFontDatabase
        from app.ui import manga_style

        with patch.object(manga_style,'_fonts_loaded',False),patch.object(QFontDatabase,'addApplicationFont',return_value=0) as register:
            apply_theme(self.app,'dark')
            self.assertEqual([Path(call.args[0]).name for call in register.call_args_list],
                             ['Inter.ttf','NotoSerif.ttf'])
            register.reset_mock()
            apply_theme(self.app,'manga_dark')
            register.assert_not_called()

    def test_repainting_settings_after_sakura_switch_matches_manga_startup(self):
        from app.ui.pages.settings_page import SettingsPage

        def settings():
            page=SettingsPage();page.resize(1440,960);page.show()
            self.addCleanup(page.deleteLater)
            QTest.qWait(20)
            return page

        def samples(page):
            hints=[w for w in page.findChildren(QLabel,'settings_hint') if 'compact list' in w.text() or 'Move focus and scroll' in w.text()]
            self.assertEqual(len(hints),2)
            combo=page.release_position
            return [(hint.text(),hint.grab().toImage()) for hint in hints]+[(combo.currentText(),combo.grab().toImage())]

        apply_theme(self.app,'manga_dark')
        cold=settings();expected=samples(cold);cold.hide()
        apply_theme(self.app,'dark')
        page=settings()
        page.theme_changed.connect(lambda theme:apply_theme(self.app,theme))
        next(card for card in page.theme_cards if card.value=='manga_dark').click()
        QTest.qWait(30)
        self.assertTrue(page.updatesEnabled())
        self.assertEqual(self.app.property('animevaultRequestedTheme'),'manga_dark')
        self.assertEqual(samples(page),expected)
        page.hide()

    def test_same_base_palette_still_restyles_when_family_changes(self):
        host=QMainWindow();host.setProperty('animevaultScopedWindow',True)
        scope=Scope(host);host.setCentralWidget(scope);self.addCleanup(host.deleteLater)
        box=QVBoxLayout(scope);label=QLabel('Library — Watching · 日本語',scope);box.addWidget(label)
        host.show();QTest.qWait(10)
        for theme in ('light','manga_light','dark','manga_light','light'):
            before=scope.refreshes;apply_theme(self.app,theme);QTest.qWait(10)
            self.assertGreater(scope.refreshes,before)
            self.assertEqual(label.text(),'Library — Watching · 日本語')

    def test_live_switch_repaints_library_and_settings_surfaces(self):
        from app.ui.main_window import MainWindow
        from app.ui.pages.downloads_page import DownloadsPage
        from app.ui.pages.library_page import LibraryPage
        from app.ui.manga_style import COLORS,DARK_COLORS

        apply_theme(self.app,'manga_dark')
        with patch.object(LibraryPage,'_request_home_facts'),patch.object(DownloadsPage,'refresh'):
            window=MainWindow.__new__(MainWindow);QMainWindow.__init__(window)
            window.setProperty('animevaultScopedWindow',True)
            window._dirty_pages=set();window._setup_ui()
        self.addCleanup(window.deleteLater)
        window._task_timer.stop();window.downloads_page.timer.stop()
        window.resize(1440,900);window.show()
        settings=window.settings_page;library=window.library_page
        settings.theme_changed.connect(window._on_theme_changed)

        def canvas_at(widget):
            point=widget.mapTo(window,QPoint(1,1))
            return window.grab().toImage().pixelColor(point).name()

        for theme,palette in (('manga_light',COLORS),('manga_dark',DARK_COLORS)):
            with self.subTest(theme=theme):
                window.stacked_widget.setCurrentWidget(settings)
                self.app.processEvents()
                next(card for card in settings.theme_cards if card.value==theme).click()
                QTest.qWait(30)
                self.assertEqual(self.app.property('animevaultRequestedTheme'),theme)
                canvas=QColor(palette['bg'])
                self.assertEqual(canvas_at(settings.settings_scroll),canvas.name())
                self.assertEqual(window.manga_header.search.palette().color(QPalette.PlaceholderText),QColor(palette['muted']))

                window.stacked_widget.setCurrentWidget(library)
                library.release_heading_widget.show()
                self.app.processEvents()
                self.assertEqual(canvas_at(library.release_heading_widget),canvas.name())
                self.assertEqual(canvas_at(library.hero_card),canvas.name())
        window.hide()

    def test_poster_episode_bar_keeps_its_height_when_switching_themes(self):
        from app.ui.components.home_poster import HomePosterCard
        from app.ui.home_style import qss

        apply_theme(self.app,'dark')
        page=Scope(None);page.setObjectName('home_library')
        layout=QVBoxLayout(page)
        card=HomePosterCard({'id':self.fid,'display_title':'Example anime'})
        layout.addWidget(card)
        card.update_facts({'found':4,'total':12,'verified_total':True})
        self.addCleanup(page.deleteLater)
        page.show()
        for theme in ('dark','manga_dark','manga_light','light','manga_dark'):
            with self.subTest(theme=theme):
                apply_theme(self.app,theme);page.setStyleSheet(qss());card.restyle()
                QTest.qWait(10)
                self.assertEqual(card.coverage_bar.height(),3)
                self.assertEqual(card.coverage_bar.value(),333)
