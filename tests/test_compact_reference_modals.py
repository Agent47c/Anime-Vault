"""Requested compact overlays: real blur, clean dismissal and retained actions."""
import unittest
from unittest.mock import patch,Mock
from PyQt5.QtCore import Qt,QCoreApplication,QEvent,QPoint,QRect,QTimer
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QLabel,QDialog,QStackedWidget,QLineEdit,QPushButton
from PyQt5.QtGui import QPixmap,QPainter
from PyQt5.QtTest import QTest
from app.ui.theme import apply_theme
import test_ui_regressions as support


class CompactReferenceTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def tearDown(self):apply_theme(self.app,'dark');support.Regressions.tearDown(self)

    def host(self):
        host=QWidget();host.resize(1440,1000);box=QVBoxLayout(host)
        label=QLabel('Library / Example Anime\n\nBroadcast schedule\n\nVault Archive');label.setStyleSheet('background:#eef0f5;color:#111217;font-size:32px;');box.addWidget(label)
        host.show();QTest.qWait(10);self.addCleanup(host.deleteLater);return host

    def test_blur_is_a_single_bounded_raster_and_softens_edges(self):
        from app.ui.components.compact_modal import blur_snapshot
        source=QPixmap(160,80);source.fill(Qt.white);p=QPainter(source);p.fillRect(0,0,80,80,Qt.black);p.end()
        result=blur_snapshot(source).toImage()
        self.assertEqual(result.width(),160)
        self.assertGreater(result.pixelColor(79,40).red(),0)
        self.assertLess(result.pixelColor(80,40).red(),255)
        huge=QPixmap(2000,1200);huge.fill(Qt.white);bounded=blur_snapshot(huge)
        self.assertLessEqual(bounded.width(),1280);self.assertLessEqual(bounded.height(),800)

    def test_password_modes_are_bounded_and_backdrop_clears_on_reject(self):
        from app.ui.dialogs.adult_password_dialog import AdultPasswordDialog
        apply_theme(self.app,'manga_light');host=self.host()
        for mode in ('change','unlock'):
            page=AdultPasswordDialog(host,mode=mode);page.show();QTest.qWait(30)
            self.assertEqual(page._compact_modal.content.width(),480)
            self.assertLess(page.height(),600)
            self.assertIsNotNone(page._compact_modal.backdrop)
            self.assertIsNone(host.graphicsEffect())
            self.assertTrue(all(edit.echoMode()==QLineEdit.Password for edit in page.findChildren(QLineEdit)))
            controller=page._compact_modal;page.reject();self.assertIsNone(controller.backdrop)
            QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)

    def test_quit_is_compact_and_remember_stays_after_choices(self):
        from app.ui.main_window import QuitConfirmDialog
        apply_theme(self.app,'manga_light');host=self.host()
        page=QuitConfirmDialog(host);self.addCleanup(page.deleteLater);page.show();QTest.qWait(20)
        self.assertEqual(page._compact_modal.content.width(),580);self.assertLess(page.height(),700)
        self.assertGreater(page.remember_cb.mapTo(page,page.remember_cb.rect().topLeft()).y(),page.exit_radio.mapTo(page,page.exit_radio.rect().topLeft()).y())
        page.cancel_button.click();self.assertIsNone(page.choice);self.assertIsNone(page._compact_modal.backdrop)

    def test_exit_background_is_captured_hidden_and_repaints_after_geometry_changes(self):
        from app.ui.main_window import QuitConfirmDialog
        apply_theme(self.app,'manga_light');host=self.host();captures=[]
        host._running_threads=lambda:[object()]
        original=host.grab
        def grab(*args):
            captures.append([child.isVisible() for child in host.findChildren(QuitConfirmDialog)])
            return original(*args)
        with patch.object(host,'grab',side_effect=grab),patch('app.core.builtin_torrents.active',return_value=True):
            page=QuitConfirmDialog(host);self.addCleanup(page.deleteLater)
            page.show();QTest.qWait(50)
            self.assertTrue(captures);self.assertFalse(any(any(states) for states in captures))
            controller=page._compact_modal
            self.assertLessEqual(controller.background.width(),1280)
            self.assertLessEqual(controller.background.height(),800)
            page.resize(page.width(),page.height()+48);page.move(page.pos()+QPoint(0,-10));QTest.qWait(30)
            self.assertEqual(controller.backplate.size(),page.size())
            image=page.grab().toImage()
            for point in (QPoint(0,0),QPoint(image.width()-1,image.height()-1)):
                pixel=image.pixelColor(point)
                self.assertGreater(max(pixel.red(),pixel.green(),pixel.blue()),30)
            page.reject()

    def test_quit_shadow_margin_blends_into_backdrop_in_both_manga_themes(self):
        from app.ui.main_window import QuitConfirmDialog
        for theme in ('manga_dark','manga_light'):
            with self.subTest(theme=theme):
                apply_theme(self.app,theme)
                host=self.host();page=QuitConfirmDialog(host)
                self.addCleanup(page.deleteLater);page.show();QTest.qWait(30)
                try:
                    backdrop=page._compact_modal.backdrop
                    origin=backdrop.mapFromGlobal(page.mapToGlobal(QPoint()))
                    behind=backdrop.grab(QRect(origin,page.size())).toImage()
                    dialog=page.grab().toImage()
                    for point in (QPoint(),QPoint(dialog.width()-1,0),QPoint(0,dialog.height()-1)):
                        self.assertEqual(dialog.pixelColor(point),behind.pixelColor(point))
                finally:
                    page.reject()

    def test_grouping_overlay_preserves_underlying_navigation_and_review_gate(self):
        from app.ui.pages.group_series_page import GroupReview
        from app.ui.navigation import navigate
        apply_theme(self.app,'manga_light');host=self.host()
        host.stacked_widget=QStackedWidget(host);original=QWidget();host.stacked_widget.addWidget(original)
        page=GroupReview(dict(title='Example',target=1,records=[dict(id=1,display_title='Example')]),host)
        self.addCleanup(page.deleteLater);callback=Mock();navigate(page,callback);QTest.qWait(20)
        self.assertIs(host.stacked_widget.currentWidget(),original)
        self.assertTrue(page.isModal());self.assertEqual(page._compact_modal.content.width(),650)
        self.assertFalse(page.confirm.isEnabled());page.reviewed.setChecked(True);self.assertTrue(page.confirm.isEnabled())
        page.reject();callback.assert_called_once_with(QDialog.Rejected);self.assertIsNone(page._compact_modal.backdrop)

    def test_discovery_actions_have_equal_sizes_including_owned_titles(self):
        from app.ui.pages.release_news_page import ReleaseNewsPage
        apply_theme(self.app,'manga_light')
        with patch.object(ReleaseNewsPage,'load'),patch('app.ui.pages.release_news_page.NewsArtwork.start'):
            page=ReleaseNewsPage();self.addCleanup(page.deleteLater)
            page._cache_info={'library_owners':{21:1}}
            long_title='Love Live! Nijigasaki Gakuen School Idol Doukoukai: Kanketsu-hen'
            page.render(([dict(id=i,title={'english':long_title}) for i in (21,22)],False))
            from app.ui.components.design import TwoLineElidedLabel
            title=page._discovery_cards[0].findChild(TwoLineElidedLabel)
            title.ensurePolished()
            title.resize(155,title.height())
            title._elide()
            self.assertEqual(len(title.text().splitlines()),2)
            self.assertTrue(title.text().endswith('…'))
            self.assertEqual(title.toolTip(),long_title)
            owned=next(button for button in page._discovery_cards[0].findChildren(QPushButton) if button.text()=='Added')
            self.assertFalse(owned.isEnabled())
            for card in page._discovery_cards:
                buttons=card.findChildren(QPushButton)
                self.assertEqual(len(buttons),2)
                self.assertEqual(buttons[0].size(),buttons[1].size())
                buttons[1].setText('Added to Watching');page.equal_discovery_actions(*buttons)
                self.assertEqual(buttons[0].size(),buttons[1].size())

    def test_discovery_next_scrolls_to_top_and_previous_keeps_position(self):
        from app.ui.pages.release_news_page import ReleaseNewsPage
        apply_theme(self.app,'manga_light')
        items=[dict(id=i,title={'english':f'Release {i}'}) for i in range(18)]
        with patch('app.ui.pages.release_news_page.NewsArtwork.start'):
            page=ReleaseNewsPage()
            self.addCleanup(page.deleteLater)
            with patch.object(page,'run',side_effect=lambda operation,ready: ready(((items,True),{}))):
                page.resize(850,640)
                page.show()
                self.app.processEvents()
                bar=page.scroll.verticalScrollBar()
                self.assertGreater(bar.maximum(),100)
                bar.setValue(bar.maximum())
                page.next.click()
                self.app.processEvents()
                self.assertEqual(page.page,2)
                self.assertEqual(bar.value(),0)
                bar.setValue(100)
                page.previous.click()
                self.app.processEvents()
                self.assertEqual(page.page,1)
                self.assertEqual(bar.value(),100)
                page.close()

    def mouse_click(self,page,control,point=None):
        # Deliver through QWindow/Qt's child hit testing, never button.click().
        point=control.mapTo(page,point or control.rect().center())
        handle=page.windowHandle()
        QTest.mouseMove(handle,point);QTest.qWait(25)
        QTest.mousePress(handle,Qt.LeftButton,pos=point);QTest.qWait(25)
        QTest.mouseRelease(handle,Qt.LeftButton,pos=point);QTest.qWait(25)

    def quit_page(self):
        from app.ui.main_window import QuitConfirmDialog
        apply_theme(self.app,'manga_light');page=QuitConfirmDialog(self.host())
        self.addCleanup(page.deleteLater);page.show();QTest.qWait(40)
        self.assertFalse(page.testAttribute(Qt.WA_TranslucentBackground))
        self.assertTrue(page._compact_modal.backdrop.testAttribute(Qt.WA_TransparentForMouseEvents))
        return page

    def test_exit_card_and_remember_then_confirm_accept_real_mouse_input(self):
        from app import db
        page=self.quit_page()
        self.mouse_click(page,page.exit_radio.parentWidget())
        self.assertTrue(page.exit_radio.isChecked());self.assertEqual(page.confirm_button.text(),'Exit completely')
        self.mouse_click(page,page.remember_cb,QPoint(9,page.remember_cb.height()//2))
        self.assertTrue(page.remember_cb.isChecked())
        self.mouse_click(page,page.confirm_button)
        self.assertEqual(page.choice,'exit');self.assertEqual(page.result(),QDialog.Accepted)
        self.assertEqual(db.get_state('quit_preference'),'exit');self.assertIsNone(page._compact_modal.backdrop)

    def test_both_choice_cards_and_cancel_accept_real_mouse_input(self):
        from app import db
        page=self.quit_page()
        self.mouse_click(page,page.exit_radio.parentWidget());self.assertTrue(page.exit_radio.isChecked())
        self.mouse_click(page,page.tray_radio.parentWidget());self.assertTrue(page.tray_radio.isChecked())
        self.mouse_click(page,page.remember_cb,QPoint(9,page.remember_cb.height()//2));self.assertTrue(page.remember_cb.isChecked())
        self.mouse_click(page,page.cancel_button)
        self.assertIsNone(page.choice);self.assertEqual(page.result(),QDialog.Rejected)
        self.assertIsNone(db.get_state('quit_preference'));self.assertIsNone(page._compact_modal.backdrop)

    def test_tray_confirmation_and_radio_indicators_accept_real_mouse_input(self):
        page=self.quit_page()
        self.mouse_click(page,page.exit_radio);self.assertTrue(page.exit_radio.isChecked())
        self.mouse_click(page,page.tray_radio);self.assertTrue(page.tray_radio.isChecked())
        self.mouse_click(page,page.confirm_button)
        self.assertEqual(page.choice,'tray');self.assertEqual(page.result(),QDialog.Accepted)

    def test_close_event_exec_loop_accepts_mouse_selection_and_remember(self):
        from app import db
        from app.ui.main_window import QuitConfirmDialog
        apply_theme(self.app,'manga_light');page=QuitConfirmDialog(self.host())
        self.addCleanup(page.deleteLater)
        observed=[]
        def choose():
            self.mouse_click(page,page.exit_radio.parentWidget())
            self.mouse_click(page,page.remember_cb,QPoint(9,page.remember_cb.height()//2))
            observed.append((page.exit_radio.isChecked(),page.remember_cb.isChecked()))
            self.mouse_click(page,page.confirm_button)
        QTimer.singleShot(80,choose)
        # Prevent a failed hit test from hanging the test process indefinitely.
        timeout=QTimer(page);timeout.setSingleShot(True);timeout.timeout.connect(page.reject);timeout.start(3000)
        result=page.exec_();timeout.stop()
        self.assertEqual(observed,[(True,True)])
        self.assertEqual(result,QDialog.Accepted);self.assertEqual(page.choice,'exit')
        self.assertEqual(db.get_state('quit_preference'),'exit')
