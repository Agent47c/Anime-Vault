import unittest
from PyQt5.QtWidgets import QApplication, QCheckBox, QLineEdit, QMainWindow, QPushButton, QStackedWidget, QWidget
import test_ui_regressions as support
from app import db
from app.ui.components.close_button import CloseButton
from app.ui.components.settings_switch import SettingsSwitch
from app.ui.navigation import navigate
from app.ui.theme import apply_theme


class EntryImportSakuraUITests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def test_custom_entry_keeps_all_existing_fields_and_omits_unapproved_mockup_items(self):
        from app.ui.dialogs.custom_entry import CustomEntryDialog

        dlg = CustomEntryDialog()
        self.assertTrue(dlg.centered_workflow)
        self.assertEqual(dlg.workflow_width, 900)
        self.assertEqual(dlg.watch_status_combo.count(), 4)
        self.assertEqual(dlg.watch_status_combo.findData("ON_HOLD"), -1)
        for attr in (
            "display_title_input",
            "title_en_input",
            "title_romaji_input",
            "title_native_input",
            "genres_input",
            "synopsis_input",
            "folder_input",
            "notes_input",
            "cover_preview",
        ):
            self.assertTrue(hasattr(dlg, attr), f"Missing attribute: {attr}")
        dlg.rating_choices.button(9).click()
        self.assertIn("9 / 10", dlg._rating_readout.text())
        dlg.rating_choices.button(9).click()
        self.assertEqual(dlg._rating_readout.text(), "Not rated")
        dlg.show()
        self.app.processEvents()
        close_btn = dlg.findChild(CloseButton)
        self.assertGreaterEqual(close_btn.width(), 36)
        self.assertGreaterEqual(close_btn.height(), 36)
        self.assertFalse(any("Supports Markdown" in w.text() for w in dlg.findChildren(QWidget) if hasattr(w, "text")))
        dlg.deleteLater()

    def test_custom_entry_edit_mode_keeps_rating_combo_and_populates_values(self):
        from app.ui.dialogs.custom_entry import CustomEntryDialog

        dlg = CustomEntryDialog(db.get_franchise(self.fid))
        self.assertTrue(dlg.is_edit)
        self.assertTrue(hasattr(dlg, "rating_combo"))
        self.assertEqual(dlg.rating_combo.count(), 11)
        self.assertEqual(dlg.display_title_input.text(), db.get_franchise(self.fid)["display_title"])
        dlg.deleteLater()

    def test_watched_importer_preserves_features_and_omits_unapproved_controls(self):
        from app.ui.dialogs.watched_import_dialog import WatchedImportDialog

        dlg = WatchedImportDialog()
        self.assertTrue(dlg.centered_workflow)
        self.assertEqual(dlg.workflow_width, 980)
        self.assertIsInstance(dlg.rematch_existing, SettingsSwitch)
        self.assertEqual(
            [dlg.result_filter.itemText(i) for i in range(dlg.result_filter.count())],
            ["All titles", "Already in library", "New / needs match", "Duplicate lines"],
        )
        self.assertFalse(any("Filter imported" in e.placeholderText() for e in dlg.findChildren(QLineEdit)))
        self.assertFalse(any("Select all" in cb.text() for cb in dlg.findChildren(QCheckBox)))

        dlg._add_item_row({"raw_title": "Duplicate Show", "matched_title": "Duplicate line", "status": "DUPLICATE", "confidence": 100, "existing_id": None, "anilist_media": None})
        dlg._add_item_row({"raw_title": "Missing Show", "matched_title": "Not found", "status": "NOT_FOUND", "confidence": 0, "existing_id": None, "anilist_media": None})
        self.assertEqual(dlg._count_labels["unmatched"].text(), "1")
        row_buttons = [b.text() for b in dlg.items_layout.itemAt(1).widget().findChildren(QPushButton)]
        self.assertIn("Choose match", row_buttons)
        self.assertIn("Add custom", row_buttons)
        dlg.result_filter.setCurrentIndex(3)
        self.assertFalse(dlg.items_layout.itemAt(0).widget().isHidden())
        self.assertTrue(dlg.items_layout.itemAt(1).widget().isHidden())
        dlg.deleteLater()

    def test_theme_and_scale_refresh_in_embedded_navigation(self):
        from app import preferences as prefs
        from app.ui.dialogs.custom_entry import CustomEntryDialog
        from app.ui.dialogs.watched_import_dialog import WatchedImportDialog

        host = QMainWindow()
        host.stacked_widget = QStackedWidget(host)
        host.setCentralWidget(host.stacked_widget)
        host.stacked_widget.addWidget(QWidget())
        host.resize(1280, 900)
        host.show()

        for factory in (CustomEntryDialog, WatchedImportDialog):
            dlg = factory(parent=host)
            navigate(dlg)
            panel = host.stacked_widget.currentWidget().findChild(QWidget, "workflow_panel")
            self.assertEqual(panel.maximumWidth(), dlg.workflow_width)
            for theme, scale, hc in (("light", 1.0, False), ("dark", 1.3, False), ("dark", 1.0, True)):
                db.set_state("text_scale", str(scale))
                prefs.save("high_contrast", hc)
                apply_theme(self.app, theme)
                self.app.processEvents()
                close_btn = dlg.findChild(CloseButton)
                self.assertGreaterEqual(close_btn.width(), round(36 * scale))
                self.assertGreaterEqual(close_btn.height(), round(36 * scale))
            dlg.reject()
            dlg.deleteLater()

        db.set_state("text_scale", "1.0")
        prefs.save("high_contrast", False)
        apply_theme(self.app, "dark")
        host.deleteLater()
