"""Paint-only motion preserves hit boxes, actions, accessibility and reuse."""
import unittest
from unittest.mock import patch
from PyQt5.QtCore import QEvent,Qt,QPoint
from PyQt5.QtGui import QImage,QPainter
from PyQt5.QtTest import QTest,QSignalSpy
from PyQt5.QtWidgets import QPushButton
import test_ui_regressions as support
from app.ui.theme import apply_theme
from app.ui.components.neumorphic import install,tile


class TactileTests(unittest.TestCase):
    def setUp(self):
        support.Regressions.setUp(self)
        for name in ('reduced_motion','system_high_contrast'):
            setting=patch('app.preferences.'+name,return_value=False);setting.start();self.addCleanup(setting.stop)
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def tearDown(self):
        self.app.setProperty('animevaultReducedMotion',False)
        apply_theme(self.app,'dark');support.Regressions.tearDown(self)

    def button(self):
        apply_theme(self.app,'manga_light');button=QPushButton('Resume episode')
        button.setProperty('accent',True);button.resize(240,52);install(button)
        button.show();self.addCleanup(button.deleteLater);return button

    def test_hover_and_press_transform_without_moving_geometry_or_duplicating_action(self):
        button=self.button();effect=button.graphicsEffect();motion=effect.motion
        geometry=button.geometry();motion.eventFilter(button,QEvent(QEvent.Enter))
        for _ in range(20):
            QTest.qWait(50)
            if motion.animation.state()==motion.animation.Stopped:break
        self.assertAlmostEqual(motion.hover,1.,places=2)
        image=QImage(300,100,QImage.Format_ARGB32);painter=QPainter(image)
        motion.transform(painter);hover_transform=painter.transform();painter.end()
        self.assertTrue(hover_transform.isIdentity()) # Hover shading must not resample the button face.
        spy=QSignalSpy(button.clicked);QTest.mousePress(button,Qt.LeftButton,pos=QPoint(100,20))
        self.assertTrue(motion.pressed)
        painter=QPainter(image);motion.transform(painter);self.assertAlmostEqual(painter.transform().m11(),.97);painter.end()
        QTest.mouseRelease(button,Qt.LeftButton,pos=QPoint(100,20))
        self.assertFalse(motion.pressed);self.assertEqual(len(spy),1);self.assertEqual(button.geometry(),geometry)

    def test_reduced_motion_removes_translation_and_cached_glow_is_reused(self):
        button=self.button();motion=button.graphicsEffect().motion
        self.app.setProperty('animevaultReducedMotion',True);motion.target(1.)
        self.assertEqual(motion.hover,0.)
        image=QImage(300,100,QImage.Format_ARGB32);painter=QPainter(image);motion.transform(painter)
        self.assertTrue(painter.transform().isIdentity());painter.end()
        self.assertIs(tile('glow'),tile('glow'));self.assertIsNot(tile('glow'),tile(True))

    def test_reinstall_reuses_effect_and_hiding_clears_press(self):
        button=self.button();effect=button.graphicsEffect();install(button)
        self.assertIs(button.graphicsEffect(),effect)
        effect.motion.pressed=True;button.hide();self.assertFalse(effect.motion.pressed)
        install(button,enabled=False);self.assertIsNone(button.graphicsEffect())

    def test_light_hover_has_no_dark_fill_and_hero_has_no_nested_effect(self):
        from app.ui.manga_style import controls_qss,library_qss
        from app.ui.components.manga_hero import MangaHero
        apply_theme(self.app,'manga_light')
        self.assertNotIn('#424858',controls_qss()+library_qss())
        hero=MangaHero();self.addCleanup(hero.deleteLater)
        self.assertIsNone(hero.graphicsEffect())
        for button in (hero.resume_btn,hero.details_btn,hero.folder_btn):
            self.assertIsNotNone(button.graphicsEffect())
        self.assertTrue(hero.resume_btn.text());self.assertTrue(hero.details_btn.text())
