import unittest,json
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
import test_ui_regressions as support
from app import db
from app.core import identity,download_assignment,season_file_moves,download_discovery


class FolderReconciliation(unittest.TestCase):
    setUp=support.Regressions.setUp
    tearDown=support.Regressions.tearDown
    @classmethod
    def setUpClass(cls):support.Regressions.setUpClass.__func__(cls)
    def fixture(self):
        db.set_continuous_episodes(self.fid,False)
        root=Path(self.temp.name)/'library';anime=root/'Black Clover';season=anime/'Season 01';season.mkdir(parents=True)
        db.add_watched_directory(str(root));db.update_franchise_field(self.fid,'root_folder_path',str(anime))
        paths=[]
        for n in range(172,176):p=anime/f'ASW - {n}.mkv';p.write_bytes(bytes(n));paths.append(p)
        db.upsert_season(dict(franchise_id=self.fid,season_number=1,relation_type='SEASON',title_display='Old root',season_folder_path=str(anime),video_files_json=json.dumps([p.name for p in paths]),storage_state='ON_DISK'))
        for n in range(5,8):p=season/f'Judas S02E{n:02}.mkv';p.write_bytes(bytes(n));paths.append(p)
        db.upsert_season(dict(franchise_id=self.fid,season_number=2,relation_type='SEASON',title_display='Old season',season_folder_path=str(season),video_files_json=json.dumps([p.name for p in paths[4:]]),storage_state='ON_DISK'))
        db.upsert_season(dict(franchise_id=self.fid,season_number=2,anilist_id=123,title_display='Metadata season 2'))
        return anime,season,paths
    def test_anime_root_is_not_a_second_season_folder(self):
        anime,season,_=self.fixture()
        self.assertEqual(identity.path_key(download_assignment.destination(self.fid,1)['folder']),identity.path_key(season))
        self.assertEqual(Path(download_assignment.destination(self.fid,2)['folder']).name,'Season 02')
    def test_user_numbered_files_move_to_season_two_with_filenames_kept(self):
        anime,season,paths=self.fixture();rows=season_file_moves.files(self.fid)
        numbers={r['id']:[int(Path(r['path']).stem.split(' - ')[1])-171] if 'ASW' in r['path'] else [int(Path(r['path']).stem[-2:])] for r in rows}
        plan=season_file_moves.preview(self.fid,[r['id'] for r in rows],2,numbers,True)
        season_file_moves.apply(plan)
        self.assertFalse(season.exists());self.assertEqual(sorted(p.name for p in (anime/'Season 02').iterdir()),sorted(p.name for p in paths))
        self.assertEqual(set(download_discovery.library_context(self.fid,2,continuous=False)['local']),{f'EPISODE:S2:{n}' for n in range(1,8)})
        with closing(db.get_connection()) as conn:self.assertEqual({r[0] for r in conn.execute('SELECT s.season_number FROM physical_files f JOIN seasons s ON s.id=f.season_id')},{2})
    def test_same_season_edit_moves_legacy_folder_into_padded_folder(self):
        root=Path(self.temp.name)/'library';anime=root/'Demo';old=anime/'Season 1';old.mkdir(parents=True)
        canonical=anime/'Season 01';canonical.mkdir()
        first=old/'Demo - 01.mkv';second=canonical/'Demo - 02.mkv'
        first.write_bytes(b'first');second.write_bytes(b'second')
        db.add_watched_directory(str(root));db.update_franchise_field(self.fid,'root_folder_path',str(anime))
        for folder,file in ((old,first),(canonical,second)):
            db.upsert_season(dict(franchise_id=self.fid,season_number=1,relation_type='SEASON',title_display=folder.name,season_folder_path=str(folder),video_files_json=json.dumps([file.name]),storage_state='ON_DISK'))
        rows=season_file_moves.files(self.fid)
        plan=season_file_moves.preview(self.fid,[r['id'] for r in rows],1,remove_empty=True)
        self.assertEqual(Path(plan['destination']['folder']),canonical)
        self.assertTrue(first.exists()) # Preview never moves files.
        season_file_moves.apply(plan)
        self.assertFalse(old.exists());self.assertEqual((canonical/first.name).read_bytes(),b'first')
        self.assertEqual(second.read_bytes(),b'second')
        with closing(db.get_connection()) as conn:
            paths=[r[0] for r in conn.execute('SELECT path FROM file_locations')]
        self.assertEqual({Path(p).parent for p in paths},{canonical})
    def test_strong_file_identity_repairs_externally_moved_location(self):
        anime,season,paths=self.fixture();old=paths[-1];new=anime/old.name
        with closing(db.get_connection()) as conn:before=conn.execute('SELECT file_id FROM file_locations WHERE path_key=?',(identity.path_key(old),)).fetchone()[0]
        old.rename(new);rows=season_file_moves.files(self.fid)
        self.assertTrue(any(r['id']==before and identity.path_key(r['path'])==identity.path_key(new) for r in rows))
    def test_new_inode_is_indexed_separately_without_false_relink(self):
        anime,season,paths=self.fixture();old=paths[-1];new=anime/old.name
        with closing(db.get_connection()) as conn,conn:
            before=conn.execute('SELECT file_id FROM file_locations WHERE path_key=?',(identity.path_key(old),)).fetchone()[0]
            conn.execute("UPDATE physical_files SET inode='different-old-file' WHERE id=?",(before,))
        old.rename(new);rows=season_file_moves.files(self.fid)
        self.assertEqual(len(rows),7)
        self.assertTrue(any(r['id']!=before and identity.path_key(r['path'])==identity.path_key(new) for r in rows))
    def test_new_episode_returns_after_dismiss_or_watched_ignore(self):
        for action in (db.dismiss_updates,db.mark_watched_and_ignore_updates):
            db.set_state(f'dismissed_updates:{self.fid}','[]')
            db.publish_updates(self.fid,'Episode 7 airing soon');action(self.fid)
            self.assertEqual(db.publish_updates(self.fid,'Episode 7 airing soon | Episode 8 airing soon'),'Episode 8 airing soon')
        for disposition in ('later','not_interested'):
            db.set_update_disposition(self.fid,disposition);db.publish_updates(self.fid,'Episode 9 airing soon')
            self.assertEqual(db.get_state(f'update_disposition:{self.fid}'),disposition)
