"""Add/edit use one rating value and cumulative Manga highlighting."""
import unittest
from PyQt5.QtTest import QTest
from app.ui.theme import apply_theme
from app.ui.dialogs.custom_entry import CustomEntryDialog
from app import db
import test_ui_regressions as support


class EntryRatingTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def tearDown(self):apply_theme(self.app,'dark');support.Regressions.tearDown(self)

    def test_add_and_edit_share_fields_and_cumulative_rating_and_clear(self):
        apply_theme(self.app,'manga_light')
        for record in (None,db.get_franchise(self.fid)):
            dialog=CustomEntryDialog(record);self.addCleanup(dialog.deleteLater)
            dialog.resize(1400,1000);dialog.show();QTest.qWait(30)
            self.assertEqual(dialog.rating_combo.count(),11)
            panel=next(panel for combo,panel in dialog._manga_choices if combo is dialog.rating_combo)
            buttons=panel.findChildren(__import__('PyQt5.QtWidgets',fromlist=['QPushButton']).QPushButton)
            buttons[7].click()
            self.assertEqual(dialog.rating_combo.currentData(),7)
            self.assertEqual([i for i,b in enumerate(buttons) if b.property('ratingFilled')],list(range(1,8)))
            buttons[3].click()
            self.assertEqual([i for i,b in enumerate(buttons) if b.property('ratingFilled')],[1,2,3])
            buttons[0].click();self.assertEqual(dialog.rating_combo.currentData(),0)
            self.assertFalse(any(b.property('ratingFilled') for b in buttons))
            if not record:self.assertTrue(dialog._add_rating_native.isHidden())
            dialog.hide()

    def test_sakura_add_pills_and_manga_rating_stay_in_sync(self):
        apply_theme(self.app,'dark');dialog=CustomEntryDialog();self.addCleanup(dialog.deleteLater)
        dialog.rating_choices.button(7).click();self.assertEqual(dialog.rating_combo.currentData(),7)
        apply_theme(self.app,'manga_light');dialog.refresh_home_style()
        dialog.rating_combo.setCurrentIndex(4)
        self.assertEqual(dialog.rating_choices.checkedId(),4)
        apply_theme(self.app,'dark');dialog.refresh_home_style()
        self.assertFalse(dialog._add_rating_native.isHidden())
