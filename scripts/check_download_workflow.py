"""Generated Chrome-result fixture → native download → real library indexing.

All peers are loopback. No public source, user database or anime is accessed.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['OFFLINE_MODE']='true'
from app import db
from app.core import downloads,download_discovery as discovery,builtin_torrents as native,source_bridge


def main():
    lt=native.library()
    with tempfile.TemporaryDirectory(prefix='animevault-workflow-') as directory:
        root=Path(directory)
        db.DATA_DIR=root;db.DB_PATH=root/'library.db';db.COVERS_DIR=root/'covers';db.EXPORTS_DIR=root/'exports'
        db.init_db()
        content=b'Generated download workflow verification\n'*16000
        name='Fixture Anime - 01.mkv';seed_folder=root/'seed';seed_folder.mkdir();(seed_folder/name).write_bytes(content)
        info={b'name':name.encode(),b'length':len(content),b'piece length':16384,
              b'pieces':b''.join(hashlib.sha1(content[i:i+16384]).digest() for i in range(0,len(content),16384))}
        torrent=lt.torrent_info({b'info':info})
        seed=lt.session({'listen_interfaces':f'127.0.0.1:{native.listen_port()}','enable_dht':False,'enable_lsd':False,'enable_upnp':False,'enable_natpmp':False})
        params=lt.add_torrent_params();params.ti=torrent;params.save_path=str(seed_folder)
        params.flags |= lt.torrent_flags.seed_mode
        params.flags &= ~lt.torrent_flags.paused;params.flags &= ~lt.torrent_flags.auto_managed
        seed_handle=seed.add_torrent(params)
        fid=db.upsert_franchise(dict(display_title='Fixture Anime',anilist_id=12345,user_notes='Keep my notes'))
        config={**downloads.DEFAULTS,'enabled':True,'engine':'builtin','start_paused':False,'destination':str(root/'downloads'),'source':'https://example.test/?q={query}'}
        downloads.save_settings(config)
        native._engine=native.EngineClient(config,network=False)
        try:
            end=time.monotonic()+3
            while seed.listen_port()==0 and time.monotonic()<end:time.sleep(.05)
            magnet='magnet:?xt=urn:btih:'+str(torrent.info_hashes().v1)+'&dn=Fixture+Anime+-+01&x.pe=127.0.0.1:'+str(seed.listen_port())
            source_bridge.heartbeat('https://example.test',True)
            identifier=source_bridge.enqueue('https://example.test/?q=Fixture','Fixture source')
            source_bridge.claim('https://example.test')
            source_bridge.finish(identifier,'https://example.test',[dict(title='Fixture Anime - 01',magnet=magnet,seeders=1,size='1 MiB')])
            with patch.object(source_bridge,'enqueue',return_value=identifier):
                result=discovery.search(fid,1,dict(name='Fixture source',url=config['source']),'Fixture Anime')
            entry=result['results'][0]
            assert entry['status']=='Missing — Release Found',str(entry)
            with patch('requests.sessions.Session.request',side_effect=AssertionError('External client must not be contacted')):
                discovery.submit(fid,[entry])
                end=time.monotonic()+16
                while time.monotonic()<end:
                    items,changed=downloads.poll()
                    if items[0].get('indexed'):break
                    time.sleep(.1)
            job=downloads.jobs()[0]
            assert job.get('indexed'),str(job)
            assert (Path(job['destination'])/name).read_bytes()==content
            seasons=db.get_seasons_for_franchise(fid)
            assert any(name in json.loads(s.get('video_files_json') or '[]') for s in seasons),str(seasons)
            assert db.get_franchise(fid)['user_notes']=='Keep my notes'
            try:discovery.submit(fid,[entry])
            except ValueError:pass
            else:raise AssertionError('Duplicate submission was accepted')
            saved_id=job['id'];downloads.shutdown_builtin();db.init_db()
            assert downloads.jobs()[0]['id']==saved_id
            print('Source bridge fixture, native transfer, duplicate guard, real indexing and restart queue passed.')
        finally:
            downloads.shutdown_builtin();seed.pause();seed=None
    return 0


if __name__=='__main__':raise SystemExit(main())
