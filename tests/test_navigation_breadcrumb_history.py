"""Keep full workflow context through nested pages and tab changes."""
import unittest
from PyQt5.QtCore import QCoreApplication,QEvent
from PyQt5.QtWidgets import QDialog,QVBoxLayout,QLabel
import test_ui_regressions as support
import test_tab_navigation_memory as nav_support
from app.ui.navigation import navigate,switch_tab,set_navigation_title


class BreadcrumbHistoryTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    host=nav_support.TabNavigationMemoryTests.host
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def workflow(self,host,title,parent=None):
        dialog=QDialog(parent or host);dialog.setWindowTitle(title);dialog.dispose_on_leave=True
        QVBoxLayout(dialog).addWidget(QLabel('Content'))
        navigate(dialog)
        return dialog

    def path(self,dialog):return dialog._navigation_header.breadcrumb.text()

    def test_nested_path_and_back_survive_switching_to_downloads(self):
        host=self.host()
        title='The Exiled Heavy Knight Knows How to Game the System'
        details=self.workflow(host,'Anime Details');set_navigation_title(details,title)
        episodes=self.workflow(host,'Choose episode',details)
        search=self.workflow(host,'Find Download Files',episodes)
        expected='Library / '+title+' / Choose episode / Find Download Files'
        self.assertEqual(self.path(search),expected)
        wrapper=host.stacked_widget.currentWidget()
        switch_tab(host,5);switch_tab(host,0)
        self.assertIs(host.stacked_widget.currentWidget(),wrapper)
        self.assertEqual(self.path(search),expected)
        search._navigation_header.back.click()
        self.assertIs(host.stacked_widget.currentWidget().workflow,episodes)
        self.assertEqual(self.path(episodes),'Library / '+title+' / Choose episode')
        episodes._navigation_header.back.click()
        self.assertIs(host.stacked_widget.currentWidget().workflow,details)
        self.assertEqual(self.path(details),'Library / '+title)
        details.reject()

    def test_all_details_actions_inherit_anime_name(self):
        host=self.host();details=self.workflow(host,'Anime Details');set_navigation_title(details,'Overgeared')
        for title in ('Edit Anime Entry','Rematch Anime Metadata','Find Download Files','Broadcast & Release Updates','View API JSON','Group seasons and arcs'):
            with self.subTest(action=title):
                child=self.workflow(host,title,details)
                self.assertEqual(self.path(child),'Library / Overgeared / '+title)
                child.reject()
        details.reject()

    def test_async_parent_title_updates_live_and_retained_descendants(self):
        host=self.host();details=self.workflow(host,'Loading anime details')
        episodes=self.workflow(host,'Choose episode',details)
        switch_tab(host,4)
        set_navigation_title(details,'Fate/stay night')
        self.assertEqual(self.path(episodes),'Library / Fate/stay night / Choose episode')
        switch_tab(host,0)
        self.assertEqual(self.path(episodes),'Library / Fate/stay night / Choose episode')
        episodes.reject();details.reject()

    def test_edit_drawer_shows_context_and_back_returns_to_details(self):
        from app.ui.dialogs.drawer import DrawerDialog
        host=self.host();details=self.workflow(host,'Anime Details');set_navigation_title(details,'Overgeared')
        drawer=DrawerDialog(details);drawer.setWindowTitle('Edit Anime Entry');QVBoxLayout(drawer).addWidget(QLabel('Edit fields'))
        navigate(drawer);self.app.processEvents()
        self.assertTrue(drawer._navigation_header.isVisible())
        self.assertEqual(self.path(drawer),'Library / Overgeared / Edit Anime Entry')
        drawer._navigation_header.back.click()
        self.assertIs(host.stacked_widget.currentWidget().workflow,details)
        details.reject()

    def test_explicit_main_screen_resets_context_for_the_next_anime(self):
        host=self.host();details=self.workflow(host,'Anime Details');set_navigation_title(details,'First anime')
        self.workflow(host,'Choose episode',details)
        switch_tab(host,0,restore=False)
        QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
        switch_tab(host,5);switch_tab(host,0)
        self.assertIs(host.stacked_widget.currentWidget(),host.stacked_widget.widget(0))
        next_details=self.workflow(host,'Anime Details');set_navigation_title(next_details,'Second anime')
        child=self.workflow(host,'Choose episode',next_details)
        self.assertEqual(self.path(child),'Library / Second anime / Choose episode')
        child.reject();next_details.reject()

    def test_api_viewer_uses_parent_context_without_repeating_the_title(self):
        from app.ui.pages.detail_modal import DetailModal
        from app import db
        host=self.host();details=self.workflow(host,'Anime Details');set_navigation_title(details,'One Piece')
        details.franchise_id=self.fid;details.franchise=db.get_franchise(self.fid)
        DetailModal._show_api_json(details)
        viewer=host.stacked_widget.currentWidget().workflow
        self.assertEqual(self.path(viewer),'Library / One Piece / View API JSON')
        viewer.accept();details.reject()
