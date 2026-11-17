"""Calendar has one shadowed surface with the badge outside its content."""
import unittest
from datetime import date
from PyQt5.QtTest import QTest
from app.ui.theme import apply_theme
from app.ui.components.home_day import HomeDay
from app.ui.components.neumorphic import NeumorphicEffect,PAD
import test_ui_regressions as support

class CalendarSurfaceTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def tearDown(self):apply_theme(self.app,'dark');support.Regressions.tearDown(self)

    def test_badge_straddles_card_and_shadow_has_room(self):
        apply_theme(self.app,'manga_light');day=HomeDay(date.today(),True,'',[])
        self.addCleanup(day.deleteLater);day.resize(240,day.height());day.show();QTest.qWait(30)
        self.assertIs(day.today_badge.parentWidget(),day)
        self.assertLess(day.today_badge.y(),day.surface.y())
        self.assertGreater(day.today_badge.geometry().bottom(),day.surface.y())
        self.assertGreaterEqual(day.surface.x(),PAD)
        self.assertGreaterEqual(day.height()-day.surface.geometry().bottom(),PAD)
        self.assertIsInstance(day.surface.graphicsEffect(),NeumorphicEffect)
        self.assertIn('background:transparent',day.release_button.styleSheet())
        self.assertIn('border:none',day.release_button.styleSheet())
        self.assertIsNone(day.release_button.graphicsEffect())

    def test_only_real_progress_shows_a_transfer_track(self):
        apply_theme(self.app,'manga_light');day=HomeDay(date.today(),False,'',[])
        self.addCleanup(day.deleteLater);self.assertTrue(day.availability_bar.isHidden())
        day.download_state('Downloading',.5);self.assertFalse(day.availability_bar.isHidden())
        self.assertEqual(day.availability_bar.value(),500)
        day.download_state('Series Paused',None);self.assertTrue(day.availability_bar.isHidden())

    def test_high_contrast_does_not_require_a_decorative_effect(self):
        apply_theme(self.app,'manga_light');self.app.setProperty('animevaultHighContrast',True)
        day=HomeDay(date.today(),True,'',[]);self.addCleanup(day.deleteLater)
        self.assertIsNone(day.surface.graphicsEffect())
