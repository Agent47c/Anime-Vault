"""Complete release titles, evidence-based S numbers and visible website queries."""
import json
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget,QStackedWidget,QVBoxLayout,QLabel
import test_ui_regressions as support
from app import db
from app.core import season_numbering as numbering,anilist_client,matching,download_discovery


class SeasonNumbersAndQueriesTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def media(self,aid,title,root=None):
        data=dict(id=aid,title={'english':title},format='TV',status='FINISHED')
        if root:data['relations']={'edges':[dict(relationType='PREQUEL',node=dict(id=root['id'],format='TV'))]}
        return data

    def test_explicit_numbers_and_unknown_parts_are_not_selection_order(self):
        for title,number in [('Example Season 4',4),('Example 2nd Season',2),('Example S03',3),('魔法 第2期',2)]:self.assertEqual(numbering.explicit_number(title),number)
        root=self.media(100,'Root')
        part=self.media(200,'Root Part 2',root)
        self.assertIsNone(numbering.infer(part,root,[root]))
        self.assertIsNone(numbering.infer(self.media(300,'Different name'),root))

    def test_multi_rematch_saves_release_numbers_even_if_selected_out_of_order(self):
        db.set_continuous_episodes(self.fid,False)
        root=self.media(100,'Series');two=self.media(200,'Series Season 2',root);three=self.media(300,'Series Season 3',root);four=self.media(400,'Series Season 4',root)
        with patch.object(matching.client,'get_anime_by_id',return_value=root),patch.object(matching.client,'download_cover',return_value=None),patch.object(matching.client,'download_banner',return_value=None):
            fid=matching.apply_release_match(self.fid,three,None,[(four,None),(two,None),(root,None)],use_local=False)
        self.assertEqual([(s['season_number'],s['anilist_id']) for s in db.get_series_seasons(fid)],[(1,100),(2,200),(3,300),(4,400)])

    def test_catalogue_repair_does_not_relabel_local_folders_or_manual_overrides(self):
        root=db.upsert_season(dict(franchise_id=self.fid,anilist_id=21,season_number=2,title_display='One Piece',storage_state='NOT_DOWNLOADED'))
        two=db.upsert_season(dict(franchise_id=self.fid,anilist_id=200,season_number=1,title_display='One Piece Season 2',storage_state='NOT_DOWNLOADED'))
        local=db.upsert_season(dict(franchise_id=self.fid,anilist_id=300,season_number=4,title_display='One Piece Season 3',storage_state='ON_DISK',season_folder_path=self.temp.name))
        self.assertEqual(numbering.repair_metadata_numbers(self.fid),2)
        self.assertEqual(db.get_season(root)['season_number'],1);self.assertEqual(db.get_season(two)['season_number'],2)
        self.assertEqual(db.get_season(local)['season_number'],4)
        numbering.save_manual(self.fid,{root:1,two:7,local:3})
        numbering.repair_metadata_numbers(self.fid)
        db.upsert_season(dict(franchise_id=self.fid,anilist_id=200,season_number=2,title_display='One Piece Season 2'))
        self.assertEqual(db.get_season(two)['season_number'],7)
        self.assertEqual(db.get_season(local)['season_folder_path'],self.temp.name)

    def test_manual_editor_has_full_names_and_requires_review(self):
        from app.ui.dialogs.season_numbers import SeasonNumbers
        sid=db.upsert_season(dict(franchise_id=self.fid,season_number=2,title_display='Long named arc Season 3'))
        dialog=SeasonNumbers(self.fid)
        self.assertFalse(dialog.save_button.isEnabled());self.assertIn(sid,dialog.controls)
        self.assertTrue(any(label.text()=='Long named arc Season 3' for label in dialog.findChildren(QLabel)))
        dialog.reviewed.setChecked(True);self.assertTrue(dialog.save_button.isEnabled());dialog.reject();dialog.deleteLater()

    def test_traversal_ignores_relation_response_order_and_movie_season_counter(self):
        root=self.media(100,'Series')
        root['relations']={'edges':[dict(relationType='SEQUEL',node=self.media(300,'Series Season 3')),
            dict(relationType='SEQUEL',node=dict(id=500,title={'english':'Series Movie'},format='MOVIE')),
            dict(relationType='SEQUEL',node=self.media(200,'Series Season 2'))]}
        rows=anilist_client.traverse_franchise_tree(root);byid={r['media']['id']:r for r in rows}
        self.assertEqual(byid[200]['season_number'],2);self.assertEqual(byid[300]['season_number'],3)
        self.assertEqual(byid[500]['relation_type'],'MOVIE');self.assertEqual(byid[500]['season_number'],0)

    def test_rematch_page_is_full_width_and_keeps_complete_season_suffix(self):
        from app.ui.dialogs.rematch_dialog import RematchDialog
        from app.ui.navigation import navigate
        host=QWidget();host.stacked_widget=QStackedWidget(host);QVBoxLayout(host).addWidget(host.stacked_widget)
        original=QWidget();host.stacked_widget.addWidget(original);host.resize(1400,900);host.show()
        with patch.object(RematchDialog,'_start_search'):dialog=RematchDialog(self.fid,host)
        title='A very long anime release title with important edition and arc information '*3+'Season 3'
        result=dialog._create_result_card(self.media(200,title),'anime')
        labels=[label for label in result.findChildren(QLabel) if label.text()==title]
        self.assertEqual(len(labels),1);self.assertTrue(labels[0].wordWrap())
        navigate(dialog);self.app.processEvents();self.assertGreater(dialog.width(),1000)
        dialog.reject();host.hide();host.deleteLater()

    def query_page(self):
        from app.ui.pages.release_search_page import ReleaseSearchPage
        db.update_franchise_field(self.fid,'title_en','A Returner Magic Should Be Special')
        db.update_franchise_field(self.fid,'title_romaji','Kikansha no Mahou wa Tokubetsu desu')
        db.update_franchise_field(self.fid,'title_native','帰還者の魔法は特別です')
        return ReleaseSearchPage(None,self.fid)

    def test_language_query_is_visible_editable_and_same_in_browser_url(self):
        page=self.query_page();self.assertIn('A Returner',page.query.text())
        index=next(i for i in range(page.title_choice.count()) if 'Romaji' in page.title_choice.itemText(i))
        page.title_choice.setCurrentIndex(index);self.assertIn('Kikansha',page.query.text())
        custom='[My group] Kikansha no Mahou 720p 12';page.query.setText(custom)
        self.assertEqual(parse_qs(urlsplit(page.source_url.text()).query)['q'],[custom])
        with patch('PyQt5.QtGui.QDesktopServices.openUrl',return_value=True) as open_url:page.open_browser()
        self.assertEqual(parse_qs(urlsplit(open_url.call_args.args[0].toString()).query)['q'],[custom])
        page.deleteLater()

    def test_empty_query_does_not_start_hidden_automatic_search(self):
        page=self.query_page();page.query.clear()
        with patch('app.ui.pages.release_search_page.IOTask') as worker:page.search()
        worker.assert_not_called();self.assertIn('Enter a search query',page.status.text());page.deleteLater()

    def test_exact_primary_query_is_not_rewritten_and_alternatives_are_explicit(self):
        source=dict(name='Test',url='https://example.test/?q={query}')
        query='日本語 title exact custom words'
        with patch('app.core.source_bridge.enqueue',return_value='token') as enqueue,patch('app.core.source_bridge.wait',return_value=[]):
            result=download_discovery.search(self.fid,None,source,query)
        self.assertEqual(enqueue.call_count,1)
        self.assertEqual(parse_qs(urlsplit(enqueue.call_args.args[0]).query)['q'],[query])
        self.assertEqual(result['query_used'],query)
