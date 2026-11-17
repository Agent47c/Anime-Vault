"""All Manga workflows inherit the same master control states lazily."""
import unittest
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QPushButton,QComboBox,QLineEdit,QGraphicsDropShadowEffect
from PyQt5.QtTest import QTest
import test_ui_regressions as support
from app.ui.theme import apply_theme
from app.ui.components.neumorphic import NeumorphicEffect


class SharedControlTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def tearDown(self):apply_theme(self.app,'dark');support.Regressions.tearDown(self)

    def surface(self):
        host=QWidget();box=QVBoxLayout(host)
        button=QPushButton('Later');button.setProperty('chip',True)
        combo=QComboBox();combo.addItems(['Name A to Z','Newest first'])
        edit=QLineEdit('Search')
        for control in (button,combo,edit):box.addWidget(control)
        host.show();self.addCleanup(host.deleteLater);QTest.qWait(20)
        return host,button,combo,edit

    def test_lazy_controls_share_material_and_reuse_effect(self):
        apply_theme(self.app,'manga_light');host,button,combo,edit=self.surface()
        for control in (button,edit):self.assertIsInstance(control.graphicsEffect(),NeumorphicEffect)
        self.assertIsNone(combo.graphicsEffect());self.assertTrue(edit.graphicsEffect().inset)
        self.assertIn('QPushButton:checked{background:white',button.styleSheet())
        self.assertNotIn('#424858',button.styleSheet());effect=button.graphicsEffect()
        host.hide();host.show();QTest.qWait(20);self.assertIs(button.graphicsEffect(),effect)

    def test_local_style_and_sakura_are_restored_without_losing_actions(self):
        host,button,combo,edit=self.surface();button.setStyleSheet('padding:3px;')
        apply_theme(self.app,'manga_light');QTest.qWait(20)
        self.assertIn('padding:3px;',button.styleSheet())
        apply_theme(self.app,'dark');QTest.qWait(20)
        self.assertEqual(button.styleSheet(),'padding:3px;');self.assertIsNone(button.graphicsEffect())

    def test_parent_effect_is_not_nested_and_play_action_uses_primary_kind(self):
        apply_theme(self.app,'manga_light')
        host=QWidget();host.setGraphicsEffect(QGraphicsDropShadowEffect(host));box=QVBoxLayout(host)
        button=QPushButton('Preview');box.addWidget(button);host.show();self.addCleanup(host.deleteLater);QTest.qWait(20)
        self.assertIsNone(button.graphicsEffect())
        host.setGraphicsEffect(None);button.setObjectName('detail_play_main')
        self.app._manga_controls.apply(button)
        self.assertEqual(button.graphicsEffect().motion.kind,'primary')

    def test_details_personal_band_keeps_flat_status_and_rating_controls(self):
        from app import db
        from app.ui.pages.detail_modal import DetailModal
        from app.ui.components.neumorphic import NeumorphicTrack
        db.update_franchise_field(self.fid,'user_rating',7)
        apply_theme(self.app,'manga_light');page=DetailModal(self.fid)
        self.addCleanup(page.deleteLater);page.resize(1400,1000);page.show();QTest.qWait(40)
        self.assertIsInstance(page.personal_band,NeumorphicTrack)
        self.assertEqual(page.notes_edit.height(),36)
        watch,rating,notes=page.personal_band.layout().items
        self.assertLess(notes.widget().x(),watch.widget().x())
        self.assertLess(watch.widget().x(),rating.widget().x())
        self.assertGreater(notes.widget().width(),220)
        self.assertLessEqual(page.personal_band.width()-rating.widget().geometry().right(),18)
        self.assertEqual([i for i,b in enumerate(page.rating_buttons,1) if b.property('rated')],list(range(1,8)))
        for button in page.watch_status_buttons.buttons():
            self.assertIn('background:transparent',button.styleSheet());self.assertIsNone(button.graphicsEffect())
        self.assertTrue(all(b.graphicsEffect() is None for b in page.rating_buttons))
        image=page.rating_buttons[0].grab().toImage()
        # Sample the face, rather than a single pixel that a scaled numeral
        # or focus outline may cover under another suite's font settings.
        yellow=0
        for y in range(image.height()):
            for x in range(image.width()):
                color=image.pixelColor(x,y)
                yellow+=color.red()>230 and color.green()>170 and color.blue()<100
        self.assertGreater(yellow,40)
        page.done(0)
        for worker in (page.episode_panel._worker,page.episode_panel._previews):
            if worker is not None:
                from PyQt5 import sip
                if not sip.isdeleted(worker):worker.wait(3000)
        apply_theme(self.app,'dark');page.refresh_home_style();self.assertEqual(page.notes_edit.height(),68)
