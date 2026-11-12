import unittest
import test_ui_regressions as support
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton,QLabel
from app import db

class ThreeReferenceTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_list_keeps_details_and_opt_in_selection_with_reference_rows(self):
        from app.ui.pages.library_page import LibraryPage
        page=LibraryPage();page._set_view_mode('compact');page.resize(1280,900);page.show();self.app.processEvents()
        table=page.compact_table;self.assertEqual(table.objectName(),'library_list');self.assertTrue(table.isColumnHidden(0));self.assertGreaterEqual(table.rowHeight(0),78)
        button=table.cellWidget(0,6).findChild(QPushButton);chosen=[];page.card_clicked.connect(chosen.append);button.click();self.assertEqual(chosen,[self.fid])
        page.set_selection_mode(True);self.assertFalse(table.isColumnHidden(0));page.close();page.deleteLater()
    def test_group_confirmation_is_centered_and_requires_explicit_review(self):
        from app.ui.pages.group_series_page import GroupReview
        page=GroupReview({'title':'Test','target':1,'records':[{'id':1,'display_title':'Test'}]})
        self.assertTrue(page.centered_workflow);self.assertEqual(page.workflow_width,720);self.assertFalse(page.confirm.isEnabled())
        self.assertTrue(any(label.text()=='★ Primary container' for label in page.findChildren(QLabel)))
        page.reviewed.setChecked(True);self.assertTrue(page.confirm.isEnabled());page.deleteLater()
    def test_duplicate_summary_and_existing_safeguards_are_preserved(self):
        from app.ui.pages.duplicate_page import DuplicatePage
        page=DuplicatePage();files=[dict(path=f'episode{i}.mkv',title='Test',episodes=[1],signature=[1024,0,0]) for i in range(3)]
        page._results(([{'files':files}],[]));self.assertEqual([label.text() for label in page.summary_labels],['1 anime','2 copies','2,048 B'])
        branch=page.tree.topLevelItem(0).child(0);self.assertFalse(branch.child(0).flags() & Qt.ItemIsUserCheckable)
        branch.child(1).setCheckState(0,Qt.Checked);self.assertTrue(page.delete.isEnabled());self.assertIn('1 selected',page.delete.text())
        self.assertEqual(len(page.scan.menu().actions()),2);self.assertFalse(any('Select all' in b.text() for b in page.findChildren(QPushButton)));page.deleteLater()
