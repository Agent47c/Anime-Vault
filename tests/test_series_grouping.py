"""Grouping confirmation, announced seasons and old-card rematch safety."""
import json
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import closing
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage,QColor
from PyQt5.QtWidgets import QLabel,QPushButton
from PyQt5.QtTest import QTest
import test_ui_regressions as support
from app import db
from app.core import series_grouping,matching


class SeriesGroupingTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def wait(self,page):
        end=time.monotonic()+5
        while getattr(page,'_apply_worker',None) is not None and time.monotonic()<end:QTest.qWait(10)
        self.assertIsNone(getattr(page,'_apply_worker',None))

    def release(self,aid,title,status='FINISHED',root=None):
        media=dict(id=aid,title={'english':title},format='TV',status=status)
        if root:media['relations']={'edges':[{'relationType':'PREQUEL','node':{'id':root['id'],'format':'TV'}}]}
        return media

    def test_group_preview_changes_nothing_then_apply_preserves_records_and_seasons(self):
        target=db.upsert_franchise(dict(display_title='Main anime'))
        extra=db.upsert_franchise(dict(display_title='Differently named arc',user_notes='Keep me',user_rating=8))
        sid=db.upsert_season(dict(franchise_id=extra,season_number=2,title_display='Arc 2',storage_state='ON_DISK',video_files_json='["EP01.mkv"]'))
        version=db.get_season(sid)
        p=series_grouping.preview(self.fid,target,[extra])
        self.assertNotEqual(db.get_series(extra)['id'],target)
        self.assertEqual(series_grouping.apply(p),target)
        self.assertEqual(set(db.get_series(target)['series_member_ids']),{self.fid,target,extra})
        self.assertEqual(db.get_season(sid),version)
        self.assertEqual(db.get_franchise(extra)['user_notes'],'Keep me')
        self.assertEqual(db.get_franchise(extra)['user_rating'],8)

    def test_stale_group_review_is_rejected_without_partial_changes(self):
        target=db.upsert_franchise(dict(display_title='Main anime'))
        p=series_grouping.preview(self.fid,target)
        db.update_franchise_field(target,'display_title','New name')
        with self.assertRaisesRegex(ValueError,'changed'):series_grouping.apply(p)
        self.assertNotEqual(db.get_series(self.fid)['id'],target)

    def test_grouped_announced_member_without_local_folder_gets_catalogue_row(self):
        media=self.release(300,'Future arc','NOT_YET_RELEASED')
        future=db.upsert_franchise(dict(anilist_id=300,display_title='Future arc',metadata_json=json.dumps(media),storage_state='NOT_DOWNLOADED'))
        target=db.upsert_franchise(dict(display_title='Main anime'))
        p=series_grouping.preview(self.fid,target,[future]);series_grouping.apply(p)
        seasons=db.get_series_seasons(target)
        self.assertEqual(len(seasons),1)
        self.assertEqual(seasons[0]['airing_status'],'NOT_YET_RELEASED')
        self.assertEqual(seasons[0]['storage_state'],'NOT_DOWNLOADED')
        self.assertFalse(seasons[0]['season_folder_path'])

    def test_grouping_page_searches_aliases_shows_small_images_and_keeps_selection(self):
        from app.ui.pages import group_series_page as ui
        target=db.upsert_franchise(dict(display_title='Main anime',title_romaji='Different Japanese title',cover_filename='poster.png'))
        root=Path(self.temp.name);image=QImage(44,66,QImage.Format_RGB32);image.fill(QColor('red'));image.save(str(root/'poster.png'))
        with patch.object(ui,'COVERS_DIR',root):
            page=ui.GroupSeriesPage(self.fid);self.wait(page)
        page.search.setText('Different Japanese')
        self.assertEqual(page.proxy.rowCount(),1)
        index=page.proxy.index(0,0);self.assertFalse(index.data(Qt.DecorationRole).isNull())
        page.list.setCurrentIndex(index);page.proxy.setData(index,Qt.Checked,Qt.CheckStateRole)
        self.assertEqual(page.target,target);self.assertIn(target,page.model.checked)
        self.assertTrue(page.review.isEnabled())
        page.search.setText('no such title');self.assertEqual(page.proxy.rowCount(),0)
        self.assertIn(target,page.model.checked)
        page.deleteLater()

    def test_group_confirmation_requires_acknowledgement_and_cancel_does_not_write(self):
        from app.ui.pages.group_series_page import GroupReview
        target=db.upsert_franchise(dict(display_title='Main anime'))
        dialog=GroupReview(series_grouping.preview(self.fid,target))
        self.assertFalse(dialog.confirm.isEnabled())
        dialog.reviewed.setChecked(True);self.assertTrue(dialog.confirm.isEnabled())
        dialog.reject();self.assertNotEqual(db.get_series(self.fid)['id'],target)
        dialog.deleteLater()

    def test_group_row_and_checkbox_select_the_same_entry_and_uncheck_clears_target(self):
        from app.ui.pages.group_series_page import GroupSeriesPage
        from PyQt5.QtWidgets import QStyleOptionViewItem,QStyle
        target=db.upsert_franchise(dict(display_title='Main anime'))
        extra=db.upsert_franchise(dict(display_title='Other season'))
        page=GroupSeriesPage(self.fid);self.wait(page)
        page.resize(1100,760);page.show();self.app.processEvents()
        def index_for(fid):
            return next(page.proxy.index(i,0) for i in range(page.proxy.rowCount()) if page.proxy.index(i,0).data(Qt.UserRole)['id']==fid)
        index=index_for(target)
        rect=page.list.visualRect(index)
        # Clicking the title includes the row instead of only highlighting it.
        QTest.mouseClick(page.list.viewport(),Qt.LeftButton,pos=rect.center())
        self.assertIn(target,page.model.checked);self.assertEqual(page.target,target)
        self.assertTrue(page.review.isEnabled())
        def checkbox(index):
            option=QStyleOptionViewItem();option.initFrom(page.list);option.widget=page.list
            option.rect=page.list.visualRect(index)
            page.list.itemDelegate().initStyleOption(option,index)
            return page.list.style().subElementRect(QStyle.SE_ItemViewItemCheckIndicator,option,page.list).center()
        QTest.mouseClick(page.list.viewport(),Qt.LeftButton,pos=checkbox(index))
        self.assertNotIn(target,page.model.checked);self.assertIsNone(page.target)
        self.assertFalse(page.review.isEnabled())
        # A direct checkbox click selects the main card too, exactly once.
        QTest.mouseClick(page.list.viewport(),Qt.LeftButton,pos=checkbox(index))
        self.assertIn(target,page.model.checked);self.assertEqual(page.target,target)
        other=index_for(extra)
        QTest.mouseClick(page.list.viewport(),Qt.LeftButton,pos=checkbox(other))
        self.assertEqual(page.model.checked,{target,extra});self.assertEqual(page.target,extra)
        # Space toggles the same model state; a remaining checked entry becomes main.
        QTest.keyClick(page.list,Qt.Key_Space)
        self.assertEqual(page.model.checked,{target});self.assertEqual(page.target,target)
        page.hide();page.deleteLater()

    def test_rematch_to_existing_series_keeps_old_card_id_and_play_history(self):
        from app.core import identity
        from app.ui.pages.detail_modal import DetailModal
        db.set_continuous_episodes(self.fid,False)
        target=db.upsert_franchise(dict(anilist_id=100,display_title='Main series',user_notes='Target note'))
        folder=Path(self.temp.name)/'Season 2';folder.mkdir();file=folder/'S02E01.mkv';file.write_bytes(b'video')
        sid=db.upsert_season(dict(franchise_id=self.fid,season_number=2,title_display='Arc',season_folder_path=str(folder),video_files_json='["S02E01.mkv"]',storage_state='ON_DISK'))
        identity.sync_inventory(sid);identity.track_play(str(file))
        db.update_franchise_field(self.fid,'user_notes','Original note');db.update_franchise_field(self.fid,'user_rating',9)
        with closing(db.get_connection()) as conn:before=[tuple(r) for r in conn.execute('SELECT * FROM episode_history')]
        root=self.release(100,'Main series');release=self.release(200,'Different arc',root=root)
        with patch.object(matching.client,'get_anime_by_id',return_value=root),patch.object(matching.client,'download_cover',return_value=None),patch.object(matching.client,'download_banner',return_value=None):
            self.assertEqual(matching.apply_release_match(self.fid,release,sid),target)
        old=db.get_franchise(self.fid);self.assertIsNotNone(old)
        self.assertEqual(old['user_notes'],'Original note');self.assertEqual(old['user_rating'],9)
        self.assertEqual(db.get_franchise(target)['user_notes'],'Target note')
        self.assertEqual(db.get_season(sid)['franchise_id'],self.fid)
        with closing(db.get_connection()) as conn:self.assertEqual([tuple(r) for r in conn.execute('SELECT * FROM episode_history')],before)
        modal=DetailModal(self.fid);self.assertEqual(modal.franchise['id'],target)
        self.assertEqual(modal.franchise_id,target)
        self.assertEqual(file.read_bytes(),b'video');modal.deleteLater()

    def test_missing_old_id_is_handled_without_a_details_crash(self):
        from app.ui.pages.detail_modal import DetailModal
        self.assertFalse(db.uses_continuous_episodes(None))
        modal=DetailModal(987654321)
        self.assertTrue(any('changed or was removed' in label.text() for label in modal.findChildren(QLabel)))
        modal.deleteLater()

    def test_stale_library_and_calendar_clicks_request_refresh_without_opening_missing_detail(self):
        from unittest.mock import Mock
        from app.ui.main_window import MainWindow
        host=Mock()
        with patch('app.ui.main_window.DetailModal') as detail:
            MainWindow._open_detail_modal(host,987654321)
            MainWindow._open_airing_detail(host,{'fid':987654321})
        detail.assert_not_called();self.assertEqual(host._on_data_updated.call_count,2)

    def test_announced_season_is_not_shown_as_missing_or_offered_locate(self):
        from app.ui.pages.detail_modal import DetailModal
        db.set_continuous_episodes(self.fid,False)
        sid=db.upsert_season(dict(franchise_id=self.fid,season_number=2,title_display='Future season',airing_status='NOT_YET_RELEASED',episodes_total=12,storage_state='NOT_DOWNLOADED'))
        modal=DetailModal(self.fid);table=modal._create_season_table([db.get_season(sid)])
        labels=' '.join(label.text() for label in table.findChildren(QLabel))
        self.assertIn('Announced',labels);self.assertNotIn('Missing from disk',labels)
        self.assertFalse(any(button.text()=='Locate' for button in table.findChildren(QPushButton)))
        table.deleteLater();modal.deleteLater()

    def test_multi_rematch_prepares_confirmation_before_starting_apply(self):
        from app.ui.dialogs.rematch_dialog import RematchDialog
        db.set_continuous_episodes(self.fid,False)
        with patch.object(RematchDialog,'_start_search'):dialog=RematchDialog(self.fid)
        dialog.selections={100:(self.release(100,'Root'),None),200:(self.release(200,'Arc'),None)}
        with patch('app.ui.io_task.start') as start,patch.object(dialog,'_start_apply') as apply:
            dialog._apply_match();start.assert_called_once();apply.assert_not_called()
        dialog.deleteLater()

    def test_match_confirmation_shows_announced_and_requires_review(self):
        from app.ui.dialogs.match_review import MatchReview
        root=self.release(100,'Root');future=self.release(200,'Future arc','NOT_YET_RELEASED',root)
        with patch.object(matching.client,'get_anime_by_id',return_value=root):prepared=matching.review_selection(self.fid,[(root,None),(future,None)])
        prepared['images']={};dialog=MatchReview(prepared)
        self.assertIn('Announced', ' '.join(label.text() for label in dialog.findChildren(QLabel)))
        self.assertFalse(dialog.apply_button.isEnabled())
        dialog.reviewed.setChecked(True);chosen=[];dialog.confirmed.connect(chosen.append);dialog.apply()
        self.assertEqual(chosen,[prepared['selections']]);self.assertIsNone(db.get_franchise_by_anilist_id(100))
        dialog.deleteLater()

    def test_background_verification_does_not_reopen_drawer_after_navigation_away(self):
        from app.ui.dialogs.rematch_dialog import RematchDialog
        with patch.object(RematchDialog,'_start_search'):dialog=RematchDialog(self.fid)
        dialog._embedded=True;dialog.hide()
        with patch('app.ui.navigation.navigate') as navigate:dialog._show_match_review({})
        navigate.assert_not_called();dialog.deleteLater()

    def test_unrelated_releases_and_duplicate_local_assignments_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'same series'):
            matching.review_selection(self.fid,[(self.release(100,'A'),None),(self.release(200,'B'),None)])
        with self.assertRaisesRegex(ValueError,'different local season'):
            matching.review_selection(self.fid,[(self.release(100,'A'),1),(self.release(200,'B'),1)])

    def test_conflict_names_every_selected_release_under_its_verified_series(self):
        root=self.release(100,'Tokyo Ghoul')
        sequel=self.release(200,'Tokyo Ghoul Season 2',root=root)
        other=self.release(300,'A Different Anime With An Important Season 3 Suffix')
        before=db.get_franchise(self.fid)
        with patch.object(matching.client,'get_anime_by_id',return_value=root):
            with self.assertRaises(ValueError) as error:
                matching.review_selection(self.fid,[(root,None),(sequel,None),(other,None)])
        message=str(error.exception)
        for title in ('Tokyo Ghoul','Tokyo Ghoul Season 2','A Different Anime With An Important Season 3 Suffix'):
            self.assertIn(title,message)
        self.assertEqual(message.count('Series: '),2)
        self.assertIn('Deselect',message);self.assertIn('group existing library entries manually',message)
        self.assertEqual(db.get_franchise(self.fid),before)

    def test_unverified_prequel_error_names_the_selected_anime(self):
        media=self.release(200,'Named Anime Season 2',root=self.release(100,'Named Anime'))
        with patch.object(matching.client,'get_anime_by_id',return_value=None):
            with self.assertRaisesRegex(ValueError,'Named Anime Season 2'):
                matching.review_selection(self.fid,[(media,None)])

    def test_announced_release_cannot_relabel_a_local_folder(self):
        sid=db.upsert_season(dict(franchise_id=self.fid,season_number=2,storage_state='ON_DISK'))
        with self.assertRaisesRegex(ValueError,'announced'):
            matching.apply_release_match(self.fid,self.release(200,'Future','NOT_YET_RELEASED'),sid)
        self.assertIsNone(db.get_season(sid)['anilist_id'])
