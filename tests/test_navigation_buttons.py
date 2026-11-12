import unittest
from unittest.mock import patch
from PyQt5.QtCore import QEvent,QAbstractAnimation
from PyQt5.QtWidgets import QWidget
from PyQt5.QtTest import QTest
import test_ui_regressions as support
from app.ui.components.navigation_button import NavigationButton


class NavigationButtonTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_updates_badge_grows_for_large_counts_and_clears_at_zero(self):
        for title in ('Updates','Downloads'):
            with self.subTest(title=title):
                button=NavigationButton(title);plain=button.sizeHint().width()
                button.setText(title+'  21');self.assertEqual(button.count,21);small=button.sizeHint().width()
                self.assertGreater(small,plain);button.setText(title+'  1200');self.assertGreater(button.sizeHint().width(),small)
                self.assertIn('1200',button.accessibleName());self.assertEqual(button.height(),44)
                button.setText(title);self.assertIsNone(button.count);self.assertEqual(button.sizeHint().width(),plain);button.deleteLater()
    def test_hover_animates_without_disk_reads_and_respects_reduced_motion(self):
        button=NavigationButton('Library');self.app.setProperty('animevaultReducedMotion',False)
        with patch('app.db.get_state',side_effect=AssertionError('No disk read on hover')):button._animate(1)
        self.assertEqual(button.hover_animation.state(),QAbstractAnimation.Running)
        QTest.qWait(220);self.assertAlmostEqual(button.hoverAmount,1)
        self.app.setProperty('animevaultReducedMotion',True);button._animate(0)
        self.assertEqual(button.hoverAmount,0);self.assertEqual(button.hover_animation.state(),QAbstractAnimation.Stopped)
        button.deleteLater();self.app.setProperty('animevaultReducedMotion',False)
    def test_standard_button_activation_still_works(self):
        from PyQt5.QtCore import Qt
        button=NavigationButton('Updates');button.resize(button.sizeHint());button.show();chosen=[];button.clicked.connect(lambda:chosen.append(True))
        button.setText('Updates  5');QTest.mouseClick(button,Qt.LeftButton);self.assertEqual(chosen,[True]);button.hide();button.deleteLater()
