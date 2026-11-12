import json,unittest
from unittest.mock import patch
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton
import test_ui_regressions as support
from app import db
from app.ui.update_release_dates import dated_changes

class UpdateDatesButtonsTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_dates_are_per_release_and_unknown_dates_are_not_invented(self):
        value={'update_details':'Older season — Released (Not in Library) | Future season — Announced (Not Yet Released) | Unknown — Released (Not in Library)', 'metadata_json':json.dumps({'relations':{'edges':[{'node':{'title':{'english':'Older season'},'startDate':{'year':2020,'month':4}}},{'node':{'title':{'english':'Future season'},'startDate':{'year':2027,'month':1}}}]}})}
        changes=dated_changes(value);self.assertIn('Released: April 2020',changes[0]);self.assertIn('Expected release: January 2027',changes[1]);self.assertIn('Date unavailable',changes[2])
    def test_date_display_does_not_change_persisted_update_or_dismissal(self):
        original='Old title — Released (Not in Library)';db.publish_updates(self.fid,original);db.dismiss_updates(self.fid)
        record=db.get_franchise(self.fid);record['update_details']=original;dated_changes(record)
        self.assertIsNone(db.publish_updates(self.fid,original))
    def test_update_actions_are_equal_width_horizontal_and_unclipped(self):
        from app.ui.pages.updates_page import UpdateCard
        record=db.get_franchise(self.fid);record['update_details']='Season 2 — Released (Not in Library)'
        card=UpdateCard(record);card.resize(1600,260);card.show();self.app.processEvents()
        buttons={b.text():b for b in card.findChildren(QPushButton)};actions=[buttons[name] for name in ('View changes','Later','Not interested','Mute anime','Watched and ignore','Dismiss')]
        self.assertEqual(len({b.y() for b in actions}),1);self.assertEqual(len({b.width() for b in actions}),1)
        self.assertEqual(len({actions[i+1].x()-actions[i].geometry().right()-1 for i in range(len(actions)-1)}),1);self.assertNotIn('More',buttons)
        for button in actions:self.assertGreater(button.width(),button.fontMetrics().horizontalAdvance(button.text())+20)
        from PyQt5.QtCore import QPoint
        center=actions[0].mapTo(card,actions[0].rect().center())
        self.assertGreater(center.y(),card.rect().center().y())
        self.assertEqual(card.layout().count(),2)
        last=buttons['Remove anime'];right=last.mapTo(card,last.rect().topRight()).x()
        self.assertLess(card.width()-right,25)
        card.close();card.deleteLater()
    def test_folder_button_opens_full_path_with_native_folder_action(self):
        from app.ui.components.folder_button import FolderButton
        button=FolderButton(self.temp.name)
        with patch('app.ui.components.folder_button.QDesktopServices.openUrl',return_value=True) as open_url:button.click()
        from pathlib import Path
        self.assertEqual(Path(open_url.call_args.args[0].toLocalFile()),Path(self.temp.name));self.assertEqual(button.toolTip(),self.temp.name);self.assertEqual(button.property('role'),'folder');button.deleteLater()
