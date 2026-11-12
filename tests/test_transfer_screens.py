"""Approved Downloads bulk controls and Updates sorting/selection contracts."""
import time,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest,QSignalSpy
from PyQt5.QtWidgets import QWidget,QPushButton
import test_ui_regressions as support
from app import db
from app.core import download_queue
from app.ui.pages.downloads_page import DownloadsPage
from app.ui.pages.updates_page import UpdatesPage,UpdateCard,UpdateActionWorker


class TransferScreenTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def job(self,identifier,status='Downloading',**values):
        return dict(id=identifier,title='Example anime',release_title='Example S01E02',engine='builtin',status=status,desired='running',destination=str(Path(self.temp.name)),root=str(Path(self.temp.name)),progress=.5,downloaded=50,total=100,download_rate=20,**values)
    def test_bulk_pause_targets_active_native_jobs_and_keeps_failures_visible(self):
        items=[self.job('a'),self.job('b','Paused',indexed=False),self.job('c','Seeding',indexed=True,upload_rate=20),self.job('d','Queued')]
        calls=[]
        def command(identifier,action):
            calls.append((identifier,action))
            if identifier=='a':raise ValueError('permission failure')
        with patch.object(download_queue.service,'jobs',return_value=items),patch.object(download_queue,'action',side_effect=command):
            result=download_queue.bulk_action('pause',['a','b','c','d'])
        self.assertEqual(calls,[('a','pause'),('c','pause'),('d','pause')]);self.assertIn('permission failure',result);self.assertIn('2 queue entries',result)
    def test_clear_completed_revalidates_state_and_never_deletes_files(self):
        file=Path(self.temp.name)/'keep.mkv';file.write_bytes(b'keep this file')
        items=[self.job('complete','Seeding',indexed=True),self.job('running'),self.job('missing','Seeding',indexed=True,integrity_missing=True)]
        state=list(items)
        def save(rows):state[:]=rows
        with patch.object(download_queue.service,'jobs',side_effect=lambda:list(state)),patch.object(download_queue.service,'_save_jobs',side_effect=save),patch.object(download_queue.service,'settings',return_value={'enabled':False}),patch.object(download_queue.service,'control_builtin') as control:
            result=download_queue.bulk_action('clear_completed',['complete','running','missing'])
        self.assertEqual([r['id'] for r in state],['running','missing']);self.assertEqual(file.read_bytes(),b'keep this file');self.assertIn('all files kept',result);control.assert_not_called()
    def test_bulk_cancel_stops_before_any_new_operation(self):
        with patch.object(download_queue,'action') as action,patch.object(download_queue.service,'jobs') as jobs:
            result=download_queue.bulk_action('clear_completed',['complete'],cancelled=lambda:True)
        action.assert_not_called();jobs.assert_not_called();self.assertIn('remaining entries kept',result)
    def test_download_filter_cards_retain_selection_and_virtualization(self):
        with patch.object(DownloadsPage,'refresh'):
            page=DownloadsPage();page.loaded([self.job(str(n),'Paused' if n%2 else 'Downloading') for n in range(2000)])
            page.resize(1200,850);page.show();self.app.processEvents()
            self.assertEqual(page.model.rowCount(),2000);self.assertLess(len(page.findChildren(QWidget)),200)
            page.table.selectRow(2);self.assertEqual(page.selected()['id'],'2')
            page.filter.setCurrentIndex(1);self.assertEqual(page.model.rowCount(),1000);self.assertEqual(page.selected()['id'],'2')
            self.assertEqual(page.model.index(0,0).data(Qt.UserRole)['id'],'0')
            from app.ui.components.transfer_row import action_rects
            with patch.object(page,'action') as action:
                point=action_rects(page.table.visualRect(page.model.index(0,0)).adjusted(0,4,-2,-4))[0].center()
                QTest.mouseClick(page.table.viewport(),Qt.LeftButton,pos=point)
                action.assert_called_once_with('pause')
            labels={b.text() for b in page.findChildren(QPushButton)}
            for label in ('Pause all','Clear completed','Choose files','Stop','Retry','More','Refresh'):self.assertIn(label,labels)
            page.hide();page.timer.stop();page.deleteLater()
    def test_updates_sort_and_batch_choices_keep_notes_and_per_anime_restore(self):
        second=db.upsert_franchise({'display_title':'A second anime','user_notes':'Keep me'})
        db.publish_updates(self.fid,'Season 2 announced | Movie announced');db.publish_updates(second,'Episode 2 airing soon')
        page=UpdatesPage();page.resize(1200,900);page.show();self.app.processEvents()
        page.sort.setCurrentIndex(3)
        cards=[page.list_layout.itemAt(i).widget() for i in range(page.list_layout.count()) if isinstance(page.list_layout.itemAt(i).widget(),UpdateCard)]
        self.assertEqual([c.franchise_id for c in cards],[second,self.fid]);self.assertTrue(all(c.checkbox.isHidden() for c in cards))
        page.set_selection_mode(True)
        for card in cards:QTest.mouseClick(card.checkbox,Qt.LeftButton)
        self.assertEqual(page.selected_fids,{second,self.fid})
        finished=QSignalSpy(page.action_finished);page.batch_action('later');self.assertTrue(finished.wait(5000))
        self.assertEqual(db.update_disposition(second),'later');self.assertEqual(db.get_franchise(second)['user_notes'],'Keep me')
        page._select_filter('Later');self.assertEqual(len(page._saved_updates),2)
        self.assertFalse(page._selection_mode);self.assertEqual(page.selected_fids,set());page.hide();page.deleteLater()
    def test_partial_update_failure_names_anime_and_does_not_stop_other_choices(self):
        other=db.upsert_franchise({'display_title':'Second title'});db.publish_updates(other,'Season 2 announced')
        original=UpdateActionWorker.perform
        def perform(fid,action):
            if fid==self.fid:raise ValueError('Cannot save')
            original(fid,action)
        worker=UpdateActionWorker([self.fid,other],'later')
        with patch.object(UpdateActionWorker,'perform',side_effect=perform):worker.run()
        self.assertIn('One Piece',worker.error);self.assertEqual(db.update_disposition(other),'later')

    def test_choice_moves_only_affected_card_without_refreshing_page(self):
        other=db.upsert_franchise({'display_title':'Unaffected anime'})
        db.publish_updates(self.fid,'Season 2 announced');db.publish_updates(other,'Episode 2 airing soon')
        page=UpdatesPage();page.resize(1200,900);page.show();self.app.processEvents()
        untouched=page._update_card_pool[other][1]
        changed=QSignalSpy(page.choices_changed);full_refresh=QSignalSpy(page.data_changed)
        with patch.object(page,'refresh') as refresh:
            finished=QSignalSpy(page.action_finished);page._start_update_action(self.fid,'not_interested')
            self.assertTrue(page.isEnabled());self.assertTrue(untouched.isEnabled())
            self.assertTrue(finished.wait(5000));refresh.assert_not_called()
        self.assertEqual(len(changed),1);self.assertEqual(len(full_refresh),0)
        self.assertIs(page._update_card_pool[other][1],untouched)
        self.assertGreaterEqual(page.list_layout.indexOf(untouched),0)
        self.assertEqual([r['id'] for r in page._updates],[other])
        self.assertEqual(page._saved_updates[0]['_update_disposition'],'not_interested')
        page._select_filter('Not interested')
        finished=QSignalSpy(page.action_finished);page._start_update_action(self.fid,'new');self.assertTrue(finished.wait(5000))
        self.assertEqual(len(page._updates),2)
        page.hide();page.deleteLater()

    def test_failed_choice_keeps_card_enabled_and_retryable(self):
        db.publish_updates(self.fid,'Season 2 announced');page=UpdatesPage()
        card=page._update_card_pool[self.fid][1]
        with patch.object(UpdateActionWorker,'perform',side_effect=ValueError('Disk unavailable')),patch('app.ui.pages.updates_page.QMessageBox.warning'):
            finished=QSignalSpy(page.action_finished);page._start_update_action(self.fid,'later');self.assertTrue(finished.wait(5000))
        self.assertIs(page._update_card_pool[self.fid][1],card);self.assertTrue(card.isEnabled())
        self.assertEqual(len(page._updates),1);page.deleteLater()

    def test_choice_shell_updates_counts_without_starting_global_refresh(self):
        from types import SimpleNamespace
        from PyQt5.QtWidgets import QLabel
        from app.ui.main_window import MainWindow
        library=QWidget();storage=QWidget();badge=QLabel();tab=QPushButton()
        host=SimpleNamespace(library_page=library,storage_page=storage,_dirty_pages=set(),
                             updates_page=SimpleNamespace(_updates=[{'id':3}]),
                             findChild=lambda *args:badge,home_header=SimpleNamespace(tabs={2:tab}),
                             coll_counts={'WATCHED':QLabel('2'),'WATCHING':QLabel('3')},_start_refresh=Mock())
        MainWindow._on_update_choices_changed(host,{4:{'watch_status':'WATCHED','_previous_watch_status':'WATCHING'}})
        host._start_refresh.assert_not_called();self.assertEqual(host._dirty_pages,{library,storage})
        self.assertEqual(badge.text(),'1');self.assertEqual(host.coll_counts['WATCHED'].text(),'3')
        self.assertEqual(host.coll_counts['WATCHING'].text(),'2');self.assertEqual(tab.text(),'Updates  1')

    def test_rapid_choices_are_queued_instead_of_ignored(self):
        other=db.upsert_franchise({'display_title':'Second anime'})
        db.publish_updates(self.fid,'Season 2 announced');db.publish_updates(other,'Season 2 announced')
        page=UpdatesPage();finished=QSignalSpy(page.action_finished)
        original=UpdateActionWorker.perform
        def slow(fid,action):time.sleep(.03);original(fid,action)
        with patch.object(UpdateActionWorker,'perform',side_effect=slow):
            page._start_update_action(self.fid,'later');page._start_update_action(other,'not_interested')
            deadline=time.monotonic()+5
            while len(finished)<2 and time.monotonic()<deadline:QTest.qWait(10)
        self.assertEqual(len(finished),2);self.assertEqual(db.update_disposition(other),'not_interested')
        self.assertEqual(db.update_disposition(self.fid),'later');page.deleteLater()
    def test_health_sort_reuses_prepared_cards(self):
        page=UpdatesPage();record=page._health_records[0];page._health=[(record,3,1)]
        page._select_filter('Health');original=page._health_card_pool[record['id']][1]
        page.sort.setCurrentIndex(3)
        self.assertIs(page._health_card_pool[record['id']][1],original)
        self.assertIsNone(page._health_worker);page.deleteLater()
    def test_large_text_pages_do_not_force_a_wider_window(self):
        from app.ui.theme import apply_theme
        db.set_state('text_scale','1.3');apply_theme(self.app,'dark')
        try:
            with patch.object(DownloadsPage,'refresh'):
                pages=[DownloadsPage(),UpdatesPage()]
                for page in pages:
                    page.resize(1100,900);page.show();self.app.processEvents()
                    self.assertLessEqual(page.minimumSizeHint().width(),1100)
                    page.hide();page.deleteLater()
        finally:db.set_state('text_scale','1.0');apply_theme(self.app,'dark')
