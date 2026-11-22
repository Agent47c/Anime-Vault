import unittest

from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtWidgets import QFrame
from app import db
from app.ui.components.neumorphic import tile
from app.ui.manga_style import set_material
from app.ui.pages.settings_page import SettingsPage
from app.ui.theme import apply_theme
from app.ui.theme_catalog import THEME_CHOICES, is_manga_dark
import test_ui_regressions as support


class MangaDarkTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def test_settings_saves_distinct_dark_theme_and_preserves_other_choices(self):
        page = SettingsPage()
        try:
            self.assertEqual(page.theme_combo.currentData(),'dark')
            for variant in ('light', 'manga_light', 'manga_dark', 'dark'):
                card = next(card for card in page.theme_cards if card.value == variant)
                card.click()
                self.assertEqual(db.get_state('theme'),variant)
                self.assertTrue(card.isChecked())
            self.assertEqual([page.theme_combo.itemData(i) for i in range(page.theme_combo.count())],
                             [value for _,value in THEME_CHOICES])
            self.assertEqual([card.label for card in page.theme_cards],
                             ['Sakura Dark','Sakura Light','Manga Brutalism Light','Manga Brutalism Dark'])
        finally:
            page.deleteLater()

    def test_visible_material_and_shadow_cache_round_trip(self):
        widget = QFrame()
        try:
            apply_theme(self.app,'manga_light')
            widget.show()
            source = 'QFrame{background:white;color:#111217;border:1px solid white;}'
            set_material(widget,source)
            light_tile = tile()
            apply_theme(self.app,'manga_dark')
            self.assertTrue(is_manga_dark())
            self.assertIn('background:#16171a',widget.styleSheet())
            self.assertIn('color:#e5e2e1',widget.styleSheet())
            self.assertIn('solid #2c2e33',widget.styleSheet())
            self.assertIsNot(tile(),light_tile)
            apply_theme(self.app,'manga_light')
            self.assertEqual(widget.styleSheet(),source)
            self.assertIs(tile(),light_tile)
        finally:
            widget.hide()
            widget.deleteLater()
            apply_theme(self.app,'dark')

    def test_theme_previews_mark_center_and_left_navigation(self):
        from app.ui.settings_style import ThemeCard

        for label,value in THEME_CHOICES:
            with self.subTest(theme=value):
                card=ThemeCard(label,'',value)
                image=QImage(160,64,QImage.Format_RGB32)
                painter=QPainter(image)
                card.paint_preview(painter,QRectF(0,0,160,64))
                painter.end()
                x=18 if value.startswith('manga_') else 80
                self.assertEqual(image.pixelColor(x,15).name(),card.PREVIEWS[value][2])
                card.deleteLater()
