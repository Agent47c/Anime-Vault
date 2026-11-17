import unittest
from PyQt5.QtCore import Qt,QPoint
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QComboBox,QMenu
from PyQt5.QtTest import QTest,QSignalSpy
from app.ui.theme import apply_theme
import test_ui_regressions as support


class DropdownDepthBehavior(unittest.TestCase):
    setUp=support.Regressions.setUp
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def tearDown(self):
        apply_theme(self.app,'dark');support.Regressions.tearDown(self)

    def test_combo_shadow_keeps_keyboard_selection_and_restores_sakura(self):
        apply_theme(self.app,'manga_light')
        host=QWidget();box=QVBoxLayout(host);box.setContentsMargins(24,24,24,24)
        combo=QComboBox();combo.addItems(['Name A to Z','Newest first','Oldest first']);box.addWidget(combo)
        host.show();self.addCleanup(host.deleteLater);QTest.qWait(20)
        shade=combo._manga_combo_depth
        self.assertIsNone(combo.graphicsEffect())
        self.assertTrue(shade.testAttribute(Qt.WA_TransparentForMouseEvents))
        changes=QSignalSpy(combo.currentIndexChanged)
        combo.showPopup();QTest.qWait(20)
        QTest.keyClick(combo.view(),Qt.Key_Down);QTest.keyClick(combo.view(),Qt.Key_Enter)
        self.assertEqual(combo.currentIndex(),1);self.assertEqual(len(changes),1)
        combo.hide();combo.show();QTest.qWait(10)
        self.assertIs(combo._manga_combo_depth,shade)
        apply_theme(self.app,'dark');self.assertTrue(shade.isHidden())
        host.close()

    def test_manga_short_popup_keeps_last_label_visible_without_scrolling(self):
        apply_theme(self.app,'manga_light')
        host=QWidget();box=QVBoxLayout(host);combo=QComboBox();box.addWidget(combo)
        combo.addItems(['Above hero banner','Above broadcast schedule','Above All anime'])
        host.resize(240,110);host.show();self.addCleanup(host.deleteLater)
        combo.showPopup();QTest.qWait(30)
        from app.ui.components.dropdown_depth import PopupDepth
        shades=combo.view().window().findChildren(PopupDepth)
        self.assertEqual(len(shades),1);self.assertTrue(shades[0].isVisible())
        self.assertEqual(combo.view().verticalScrollBar().maximum(),0)
        self.assertEqual(combo.view().horizontalScrollBar().maximum(),0)
        last=combo.view().visualRect(combo.model().index(2,0))
        self.assertLessEqual(last.bottom(),combo.view().viewport().height())
        combo.hidePopup();combo.showPopup();QTest.qWait(20)
        self.assertEqual(combo.view().window().findChildren(PopupDepth),shades)
        combo.hidePopup();host.close()

    def test_menu_shadow_keeps_actions_and_keyboard_activation(self):
        apply_theme(self.app,'manga_light')
        host=QWidget();host.resize(500,500);host.show();self.addCleanup(host.deleteLater)
        menu=QMenu(host);actions=[menu.addAction(label) for label in ('View API JSON','Group with another series','Combine episode folders')]
        selected=QSignalSpy(actions[-1].triggered)
        menu.popup(host.mapToGlobal(QPoint(30,30)));QTest.qWait(20)
        self.assertTrue(menu.windowFlags()&Qt.FramelessWindowHint)
        self.assertTrue(menu.windowFlags()&Qt.NoDropShadowWindowHint)
        self.assertEqual(menu.windowType(),Qt.Popup)
        QTest.keyClick(menu,Qt.Key_End)
        self.assertIs(menu.activeAction(),actions[-1]);self.assertTrue(menu.rect().contains(menu.actionGeometry(actions[-1])))
        QTest.keyClick(menu,Qt.Key_Enter);self.assertEqual(len(selected),1)
        host.close()

    def test_first_frame_stays_hidden_until_final_popup_layout_is_ready(self):
        apply_theme(self.app,'manga_light')
        host=QWidget();box=QVBoxLayout(host);combo=QComboBox();box.addWidget(combo)
        combo.addItems(['Severity & date','Latest checked','Oldest checked','Title A to Z'])
        host.show();self.addCleanup(host.deleteLater);QTest.qWait(10)
        popup=combo.view().window()
        self.assertTrue(popup.windowFlags()&Qt.FramelessWindowHint)
        self.assertTrue(popup.testAttribute(Qt.WA_TranslucentBackground))
        self.assertFalse(self.app.isEffectEnabled(Qt.UI_AnimateCombo))
        combo.showPopup()
        self.assertTrue(popup.property('mangaPopupPreparing'))
        self.assertEqual(popup.windowOpacity(),0.)
        QTest.qWait(30)
        self.assertFalse(popup.property('mangaPopupPreparing'))
        self.assertEqual(popup.windowOpacity(),1.)
        self.assertEqual(combo.view().verticalScrollBar().maximum(),0)
        self.assertLessEqual(combo.view().visualRect(combo.model().index(3,0)).bottom(),combo.view().viewport().height())
        combo.hidePopup();host.close()

    def test_immediate_close_and_reopen_cannot_present_an_old_popup_pass(self):
        apply_theme(self.app,'manga_light')
        host=QWidget();box=QVBoxLayout(host);combo=QComboBox();box.addWidget(combo);combo.addItems(['One','Two'])
        host.show();self.addCleanup(host.deleteLater);QTest.qWait(10)
        popup=combo.view().window();combo.showPopup();first=popup.property('mangaPopupGeneration')
        combo.hidePopup();self.assertEqual(popup.windowOpacity(),1.)
        combo.addItem('A new longer sort option');combo.showPopup()
        self.assertGreater(popup.property('mangaPopupGeneration'),first)
        self.assertEqual(popup.windowOpacity(),0.)
        QTest.qWait(30)
        self.assertEqual(popup.windowOpacity(),1.);self.assertFalse(popup.property('mangaPopupPreparing'))
        self.assertEqual(combo.currentIndex(),0);combo.hidePopup();host.close()

    def test_theme_install_uses_new_family_with_windows_effects_initially_enabled(self):
        apply_theme(self.app,'dark')
        effects=(Qt.UI_AnimateCombo,Qt.UI_AnimateMenu,Qt.UI_FadeMenu)
        original=self.app._dropdown_native_effects
        general=self.app.isEffectEnabled(Qt.UI_General)
        host=QWidget();box=QVBoxLayout(host);combo=QComboBox();combo.addItems(['One','Two']);box.addWidget(combo)
        menu=QMenu(host);menu.addAction('Example');menu.ensurePolished()
        host.show();self.addCleanup(host.deleteLater);QTest.qWait(10)
        popup=combo.view().window()
        try:
            # Offscreen defaults masked the Windows startup bug: all native
            # effects were already disabled. Exercise the enabled startup case.
            self.app._dropdown_native_effects={effect:True for effect in effects}
            self.app.setEffectEnabled(Qt.UI_General,True)
            for effect in effects:self.app.setEffectEnabled(effect,True)
            apply_theme(self.app,'manga_light')
            self.assertTrue(all(not self.app.isEffectEnabled(effect) for effect in effects))
            self.assertTrue(popup.testAttribute(Qt.WA_TranslucentBackground))
            self.assertTrue(menu.testAttribute(Qt.WA_TranslucentBackground))
            self.assertTrue(popup.windowFlags()&Qt.FramelessWindowHint)
            apply_theme(self.app,'dark')
            self.assertTrue(all(self.app.isEffectEnabled(effect) for effect in effects))
        finally:
            self.app._dropdown_native_effects=original
            self.app.setEffectEnabled(Qt.UI_General,general)
            apply_theme(self.app,'dark');host.close()

    def test_scoped_details_page_keeps_popup_style_without_blue_underpainting(self):
        from PyQt5.QtWidgets import QPushButton
        from PyQt5.QtGui import QFontMetrics
        from app.ui.components.dropdowns import dropdown_font
        apply_theme(self.app,'dark')
        host=QWidget();host.setObjectName('series_details')
        host.setProperty('animevaultScopedWindow',True);host.setProperty('animevaultThemeScope',True)
        host.resize(650,500);button=QPushButton('Play',host);button.setGeometry(30,30,150,44)
        host.show();self.addCleanup(host.deleteLater);QTest.qWait(10)
        apply_theme(self.app,'manga_light')
        menu=QMenu(button);menu.setObjectName('detail_play_menu')
        menu.addAction('Resume episode 6\tSeason 1');play=menu.addAction('Play from episode 1')
        menu.addAction('Choose episode...');menu.addSeparator();player=menu.addAction('Player: PotPlayer\tChange in Settings')
        menu.popup(host.mapToGlobal(QPoint(30,90)));menu.setActiveAction(play);QTest.qWait(30)
        self.assertEqual(menu.styleSheet(),menu.property('unifiedMenuStyle'))
        self.assertNotEqual(menu.styleSheet(),self.app._theme_scopes.stylesheet)
        image=menu.grab().toImage();rect=menu.actionGeometry(play);blue=0
        for y in range(rect.top(),rect.bottom()+1):
            for x in range(rect.left(),rect.right()+1):
                p=image.pixelColor(x,y)
                blue+=p.alpha()>230 and p.blue()>120 and p.blue()>p.red()*1.5 and p.blue()>p.green()*1.5
        self.assertEqual(blue,0)
        metrics=QFontMetrics(dropdown_font())
        self.assertGreaterEqual(menu.actionGeometry(player).width()-8,metrics.horizontalAdvance('Player: PotPlayer')+metrics.horizontalAdvance('Change in Settings')+44)
        menu.hide();host.close()
