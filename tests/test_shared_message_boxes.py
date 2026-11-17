import unittest
from PyQt5.QtCore import Qt,QTimer,QPoint,QPointF
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QPushButton,QWidget
from app.ui.components.message_boxes import AppMessageBox as QMessageBox
from PyQt5.QtTest import QTest
import test_ui_regressions as support
from app.ui.theme import apply_theme


class MessageBoxTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def tearDown(self):apply_theme(self.app,'dark');support.Regressions.tearDown(self)

    def test_ok_stays_visible_and_clickable_on_hover_press_and_theme_switch(self):
        apply_theme(self.app,'manga_light')
        box=QMessageBox(QMessageBox.Warning,'Could not play episode','Review the pending path repair.',QMessageBox.Ok)
        self.addCleanup(box.deleteLater);box.show();QTest.qWait(20)
        button=box.button(QMessageBox.Ok)
        for theme in ('manga_light','dark','light','manga_light'):
            apply_theme(self.app,theme);QTest.mouseMove(button,button.rect().center());QTest.qWait(15)
            self.assertTrue(button.isVisible());self.assertIsNone(button.graphicsEffect())
            self.assertGreaterEqual(button.width(),96);self.assertIn('color:',button.styleSheet())
        QTest.mousePress(button,Qt.LeftButton);self.assertTrue(button.isVisible());self.assertTrue(button.isDown())
        QTest.mouseRelease(button,Qt.LeftButton);self.assertEqual(box.result(),QMessageBox.Ok)

    def test_static_warning_and_custom_confirmation_keep_original_results(self):
        apply_theme(self.app,'manga_light');seen=[]
        def accept_warning():
            box=self.app.activeModalWidget();button=box.button(QMessageBox.Ok)
            seen.append(button.isVisible() and button.graphicsEffect() is None)
            QTest.mouseClick(button,Qt.LeftButton)
        QTimer.singleShot(20,accept_warning)
        self.assertEqual(QMessageBox.warning(None,'Warning','Example message'),QMessageBox.Ok)
        self.assertEqual(seen,[True])
        box=QMessageBox();self.addCleanup(box.deleteLater)
        danger=box.addButton('Delete files',QMessageBox.DestructiveRole);cancel=box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(cancel);box.show();QTest.qWait(10)
        self.assertIs(box.defaultButton(),cancel);self.assertIn('#b3261e',danger.styleSheet())
        QTest.mouseClick(cancel,Qt.LeftButton);self.assertIs(box.clickedButton(),cancel)
    def test_path_repair_details_remain_readable_without_accepting(self):
        box=QMessageBox();self.addCleanup(box.deleteLater)
        box.setText('Review repairs');box.setDetailedText('Original path\n→ Verified path')
        box.setStandardButtons(QMessageBox.Yes|QMessageBox.No);box.setDefaultButton(QMessageBox.No)
        box.show();QTest.qWait(10);QTest.mouseClick(box.details_button,Qt.LeftButton)
        self.assertTrue(box.details.isVisible());self.assertIn('Verified path',box.detailedText());self.assertIsNone(box.clickedButton())
        QTest.mouseClick(box.button(QMessageBox.No),Qt.LeftButton);self.assertEqual(box.result(),QMessageBox.No)

    def test_home_strip_wheel_moves_horizontally_without_vertical_scroll(self):
        from app.ui.components.smooth_scroll import HorizontalStrip
        strip=HorizontalStrip();self.addCleanup(strip.deleteLater)
        content=QWidget();content.setFixedSize(1200,250);strip.setWidget(content);strip.resize(400,300);strip.show();QTest.qWait(10)
        event=QWheelEvent(QPointF(100,100),QPointF(strip.mapToGlobal(QPoint(100,100))),QPoint(),QPoint(0,-120),Qt.NoButton,Qt.NoModifier,Qt.NoScrollPhase,False)
        self.app.sendEvent(strip.viewport(),event)
        self.assertGreater(strip.horizontalScrollBar().value(),0)
        self.assertEqual(strip.verticalScrollBar().value(),0)
