import unittest
from PyQt5.QtWidgets import QFrame,QPushButton
import test_ui_regressions as support
from app.ui.pages.settings_page import SettingsPage


class SettingsReferenceTests(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        support.Regressions.setUp(self);self.icons_patch=patch.object(SettingsPage,'_load_player_icons');self.icons_patch.start()
    def tearDown(self):
        self.icons_patch.stop();support.Regressions.tearDown(self)
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_sections_keep_existing_routes_and_controls(self):
        page=SettingsPage();page.resize(1280,900);page.show();self.app.processEvents()
        self.assertEqual(len(page.section_targets),8);self.assertTrue(page.tabs.tabBar().isHidden())
        panels=[p.property('settings_section') for p in page.findChildren(QFrame)]
        for name in ('Application behavior','About','Library roots and scanning','Sources','Backup location and maintenance','Watchers and automatic imports'):self.assertIn(name,panels)
        page.tabs.setCurrentIndex(4);self.app.processEvents();self.assertTrue(page.section_buttons[4].isChecked());self.assertTrue(page.section_targets[4].isVisible());self.assertFalse(page.section_targets[0].isVisible())
        page.section_buttons[0].click();self.app.processEvents();self.assertEqual(page.tabs.currentIndex(),0);self.assertTrue(page.section_targets[0].isVisible());self.assertFalse(page.section_targets[4].isVisible())
        for index in range(8):
            page.section_buttons[index].click();self.app.processEvents()
            self.assertEqual([i for i,target in enumerate(page.section_targets) if target.isVisible()],[index])
        page.close();page.deleteLater()
    def test_about_displays_application_version_and_opens_repository(self):
        from unittest.mock import patch
        from PyQt5.QtWidgets import QLabel
        from app import __version__

        page=SettingsPage();self.addCleanup(page.deleteLater)
        about=next(panel for panel in page.findChildren(QFrame) if panel.property('settings_section')=='About')
        self.assertIn(f'Version {__version__}',[label.text() for label in about.findChildren(QLabel)])
        button=about.findChild(QPushButton,'settings_project_github')
        with patch('app.ui.pages.settings_page.QDesktopServices.openUrl') as open_url:
            button.click()
            self.assertEqual(open_url.call_args.args[0].toString(),'https://github.com/Agent47c/Anime-Vault')

    def test_choice_cards_mirror_real_controls(self):
        page=SettingsPage();light=next(card for card in page.theme_cards if card.value=='light')
        light.click();self.assertEqual(page.theme_combo.currentData(),'light');self.assertTrue(light.isChecked())
        light.click();self.assertTrue(light.isChecked())
        value,button=next((v,b) for v,b in page.player_cards if v=='mpc-hc');button.click();self.assertEqual(page.player_combo.currentData(),'mpc-hc');self.assertTrue(button.isChecked())
        page.deleteLater()
    def test_library_selection_control_is_local_and_synchronized(self):
        from app.ui.pages.library_page import LibraryPage
        page=LibraryPage();page.select_multiple_button.click();self.assertTrue(page._selection_mode)
        page.set_selection_mode(False);self.assertFalse(page.select_multiple_button.isChecked());page.deleteLater()
    def test_new_reference_keeps_naming_and_metadata_in_their_own_categories(self):
        page=SettingsPage()
        sections=lambda index:{p.property('settings_section') for p in page.section_targets[index].findChildren(QFrame) if p.property('settings_section')}
        self.assertEqual(sections(6),{'Naming and organization rules'});self.assertEqual(sections(7),{'Metadata and AniList'})
        self.assertEqual(sections(1),{'Library roots and scanning','Scanning and organization'})
        self.assertEqual(page.tabs.widget(4).widget(),page.section_targets[4]);page.deleteLater()
    def test_download_reference_pairs_group_quality_and_transfer_limits(self):
        page=SettingsPage();config=page.download_config
        self.assertIs(config.controls['group'].parentWidget().parentWidget(),config.controls['quality'].parentWidget().parentWidget())
        self.assertIs(config.download_limit.parentWidget().parentWidget(),config.upload_limit.parentWidget().parentWidget());page.deleteLater()
