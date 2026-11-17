import unittest
from contextlib import closing
import test_ui_regressions as support
from app import db


class WatchedPathTests(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def test_slash_case_and_trailing_separator_return_one_root_and_stable_id(self):
        first=db.add_watched_directory('E:/Anime Library')
        self.assertEqual(db.add_watched_directory('e:\\anime library\\'),first)
        self.assertEqual(db.add_watched_directory('E:/Anime Library/.'),first)
        roots=db.get_watched_directories();self.assertEqual(len(roots),1)
        self.assertEqual(roots[0]['folder_path'],'E:\\Anime Library')
    def test_legacy_aliases_display_once_without_deleting_their_scan_records(self):
        with closing(db.get_connection()) as conn,conn:
            first=conn.execute('INSERT INTO watched_directories(folder_path) VALUES (?)',('E:/Anime Library',)).lastrowid
            second=conn.execute('INSERT INTO watched_directories(folder_path,last_scanned_at) VALUES (?,?)',('E:\\Anime Library','2026-11-16 01:00:00')).lastrowid
            conn.execute('INSERT INTO scan_roots(root_id,state,checked_at) VALUES (?,?,?)',(second,'ONLINE',1))
        root=db.get_watched_directories()[0]
        self.assertEqual(len(db.get_watched_directories()),1);self.assertEqual(root['id'],first);self.assertEqual(root['availability'],'ONLINE')
        self.assertEqual(db.add_watched_directory('E:\\Anime Library'),first)
        with closing(db.get_connection()) as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM watched_directories').fetchone()[0],2)
        db.remove_watched_directory(first);self.assertFalse(db.get_watched_directories())
        self.assertIsNotNone(db.get_franchise(self.fid))
    def test_different_and_nested_folders_remain_distinct(self):
        for path in ('E:/Anime Library','E:/Anime Library/Black Clover','F:/Anime Library'):db.add_watched_directory(path)
        self.assertEqual(len(db.get_watched_directories()),3)
    def test_blank_path_cannot_accidentally_watch_working_directory(self):
        with self.assertRaises(ValueError):db.add_watched_directory(' ')
