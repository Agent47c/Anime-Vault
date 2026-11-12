"""Roomier header and Library-owned status without duplicate disk text."""
import unittest
from unittest.mock import Mock,patch
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QMainWindow,QLineEdit,QLabel
import test_ui_regressions as support


class ShellSpaceAndStatusTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)

    def test_header_is_centered_roomier_and_menu_uses_three_lines(self):
        from app.ui.components.home_header import HomeHeader
        from app.ui.home_style import colors
        from app.ui.icons import icon
        host=QMainWindow();self.addCleanup(host.deleteLater)
        host.top_search_input=QLineEdit();host.coll_counts={}
        for name in ('_on_nav_clicked','_on_collection_clicked','_request_refresh','_open_custom_entry_dialog','_open_watched_import_dialog'):
            setattr(host,name,Mock())
        header=HomeHeader(host);host.setCentralWidget(header)
        host.resize(1920,150);host.show();self.app.processEvents()
        self.assertGreater(header.search.width(),170)
        self.assertLessEqual(abs(header.capsule.geometry().center().x()-header.rect().center().x()),1)
        self.assertEqual(header.options.icon().cacheKey(),icon('list',colors()['muted']).cacheKey())
        self.assertIn('::menu-indicator {image:none;',header.styleSheet())
        for width in (1100,1280,1920):
            host.resize(width,180);self.app.processEvents()
            for child in (header.capsule,header.search,header.options,header.drive):
                point=child.mapTo(header,QPoint(child.width(),0))
                self.assertLessEqual(point.x(),header.width())
        host.hide()

    def test_library_status_is_below_anime_count_without_disk_usage(self):
        from app.ui.pages.library_page import LibraryPage
        with patch.object(LibraryPage,'_request_home_facts'),patch.object(LibraryPage,'_refresh_airing_week'):
            page=LibraryPage();self.addCleanup(page.deleteLater)
            connectivity=QLabel('AniList & Jikan · Online');connectivity.setObjectName('library_connectivity')
            indexed=QLabel('1 anime indexed');indexed.setObjectName('home_meta')
            page.service_status_row.addWidget(connectivity);page.service_status_row.addWidget(indexed)
            page.resize(1280,900);page.show();self.app.processEvents()
            self.assertEqual(page.stats_subtitle.text(),'1 anime')
            self.assertNotIn('on disk',page.stats_subtitle.text())
            self.assertGreater(connectivity.mapTo(page,QPoint()).y(),page.stats_subtitle.mapTo(page,QPoint()).y())
            self.assertEqual(connectivity.parentWidget(),page.stats_subtitle.parentWidget())
            page.close()
