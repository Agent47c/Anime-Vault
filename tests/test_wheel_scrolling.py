"""Mouse-wheel routing over rematch controls and nested scrolling lists."""
import unittest
from unittest.mock import patch
from PyQt5.QtCore import Qt,QPoint,QPointF
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QComboBox,QSpinBox,QScrollArea,QListWidget,QAbstractItemView
from PyQt5.QtTest import QTest
import test_ui_regressions as support
from app.ui.components.smooth_scroll import SmoothScrollArea


class WheelScrollingTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def wheel(self,widget,angle=-120,pixels=0):
        point=widget.rect().center()
        event=QWheelEvent(QPointF(point),QPointF(widget.mapToGlobal(point)),QPoint(0,pixels),QPoint(0,angle),Qt.NoButton,Qt.NoModifier,Qt.NoScrollPhase,False)
        self.app.sendEvent(widget,event)

    def area(self):
        scroll=SmoothScrollArea();scroll.setWidgetResizable(True);scroll.resize(500,350)
        body=QWidget();box=QVBoxLayout(body)
        combo=QComboBox();combo.addItems(['Metadata only','Season 1','Season 2']);box.addWidget(combo)
        spin=QSpinBox();spin.setValue(2);box.addWidget(spin)
        filler=QWidget();filler.setMinimumHeight(1800);box.addWidget(filler)
        scroll.setWidget(body);scroll.show();self.app.processEvents()
        self.addCleanup(scroll.deleteLater)
        return scroll,combo,spin,box

    def test_closed_dropdown_and_spin_wheels_scroll_page_without_changing_values(self):
        scroll,combo,spin,_=self.area();bar=scroll.verticalScrollBar()
        self.wheel(combo);QTest.qWait(200)
        self.assertGreater(bar.value(),0);self.assertEqual(combo.currentIndex(),0)
        before=bar.value();self.wheel(spin);QTest.qWait(200)
        self.assertGreater(bar.value(),before);self.assertEqual(spin.value(),2)
        bar.setValue(bar.maximum());self.wheel(combo);self.assertEqual(combo.currentIndex(),0)
        self.wheel(combo,120);QTest.qWait(200);self.assertLess(bar.value(),bar.maximum())

    def test_wheel_reversal_does_not_wait_for_previous_scroll_target(self):
        scroll,_,_,_=self.area();bar=scroll.verticalScrollBar();bar.setValue(500)
        self.wheel(scroll.viewport());self.wheel(scroll.viewport());QTest.qWait(25)
        before=bar.value();self.assertGreater(before,500)
        self.wheel(scroll.viewport(),120)
        self.assertLess(scroll._animation.endValue(),before)
        QTest.qWait(200);self.assertLess(bar.value(),before)

    def test_reduced_motion_and_touchpad_remain_responsive(self):
        scroll,_,_,_=self.area();bar=scroll.verticalScrollBar()
        with patch('app.ui.components.smooth_scroll.motion_duration',return_value=0):
            self.wheel(scroll.viewport());self.assertGreater(bar.value(),0)
        before=bar.value();self.wheel(scroll.viewport(),angle=-120,pixels=-30)
        self.assertGreater(bar.value(),before)

    def test_nested_list_scrolls_itself_then_bubbles_at_its_boundary(self):
        scroll,_,_,box=self.area()
        listing=QListWidget();listing.addItems([f'Episode {n}' for n in range(80)]);listing.setFixedHeight(150);box.insertWidget(0,listing)
        self.app.processEvents();self.assertEqual(listing.verticalScrollMode(),QAbstractItemView.ScrollPerPixel)
        self.wheel(listing.viewport());self.assertGreater(listing.verticalScrollBar().value(),0)
        self.assertEqual(scroll.verticalScrollBar().value(),0)
        listing.verticalScrollBar().setValue(listing.verticalScrollBar().maximum())
        self.wheel(listing.viewport());QTest.qWait(200)
        self.assertGreater(scroll.verticalScrollBar().value(),0)

    def test_rematch_shared_body_scrolls_over_local_season_selectors(self):
        from app.ui.dialogs.rematch_dialog import RematchDialog
        from app import db
        db.set_continuous_episodes(self.fid,False)
        with patch.object(RematchDialog,'_start_search'):dialog=RematchDialog(self.fid)
        dialog.full_page=True
        for n in range(8):
            media=dict(id=200+n,title={'english':f'A long release title Season {n+1}'},format='TV')
            dialog.results_layout.addWidget(dialog._create_result_card(media,'anime'))
        dialog.resize(1000,700);dialog.show();self.app.processEvents()
        scroll=dialog.findChild(QScrollArea);self.assertIsInstance(scroll,SmoothScrollArea)
        combo=dialog.results_container.findChild(QComboBox)
        self.wheel(combo);QTest.qWait(200)
        self.assertGreater(scroll.verticalScrollBar().value(),0);self.assertEqual(combo.currentIndex(),0)
        self.wheel(combo,120);QTest.qWait(200);self.assertEqual(scroll.verticalScrollBar().value(),0)
        dialog.reject();dialog.deleteLater()

    def test_open_dropdown_scrolls_its_popup_not_the_page(self):
        scroll,combo,_,_=self.area();combo.addItems([f'Season {n}' for n in range(50)])
        combo.showPopup();self.app.processEvents()
        view=combo.view();self.wheel(view.viewport());self.app.processEvents()
        self.assertEqual(scroll.verticalScrollBar().value(),0)
        self.assertTrue(view.isVisible());combo.hidePopup()
