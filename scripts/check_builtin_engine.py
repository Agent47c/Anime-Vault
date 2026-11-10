"""Real native transfer and resume check, without Qt DLLs or public peers."""
import hashlib
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import db
from app.core.builtin_torrents import Engine,library,listen_port


def main():
    lt=library()
    with tempfile.TemporaryDirectory(prefix='animevault-native-') as temporary:
        root=Path(temporary);db.DATA_DIR=root
        source=root/'source';folder=source/'Release';folder.mkdir(parents=True)
        (folder/'Episode 01.mkv').write_bytes(b'first-episode-'*65536)
        (folder/'Episode 02.mkv').write_bytes(b'second-episode-'*65536)
        paths=sorted(folder.iterdir());content=b''.join(p.read_bytes() for p in paths)
        info={b'name':b'Release',b'piece length':16384,
              b'files':[{b'length':p.stat().st_size,b'path':[p.name.encode()]} for p in paths],
              b'pieces':b''.join(hashlib.sha1(content[i:i+16384]).digest() for i in range(0,len(content),16384))}
        path=root/'release.torrent';path.write_bytes(lt.bencode({b'info':info}))
        config={'download_limit_kib':64,'upload_limit_kib':0,'seed_completed':False}
        adapter=Engine(config,network=False)
        seed=lt.session({'listen_interfaces':f'127.0.0.1:{listen_port()}','enable_dht':False,'enable_lsd':False,'enable_upnp':False,'enable_natpmp':False})
        try:
            params=lt.add_torrent_params();params.ti=lt.torrent_info(str(path));params.save_path=str(source)
            params.flags |= lt.torrent_flags.seed_mode
            params.flags &= ~lt.torrent_flags.paused
            params.flags &= ~lt.torrent_flags.auto_managed
            seed_handle=seed.add_torrent(params)
            item={'id':'loopback','destination':str(root/'output'),'selection_confirmed':True,'selected_files':[0],'desired':'running'}
            adapter.attach(item,adapter.prepare(item,str(path)))
            end=time.monotonic()+8
            while time.monotonic()<end:
                partial=adapter.snapshot(item)
                if 0<partial['progress']<1: break
                adapter.handles[item['id']].connect_peer(('127.0.0.1',seed.listen_port()))
                time.sleep(.05)
            assert 0<partial['progress']<1,str(partial)
            item['desired']='paused'
            adapter.snapshot(item);adapter.close()
            assert (adapter.folder/'loopback.resume').exists()
            config['download_limit_kib']=0
            adapter=Engine(config,network=False)
            item['desired']='running'
            end=time.monotonic()+15;result={}
            while time.monotonic()<end:
                result=adapter.snapshot(item)
                if result.get('complete'): break
                adapter.handles[item['id']].connect_peer(('127.0.0.1',seed.listen_port()))
                time.sleep(.05)
            if not result.get('complete'):
                handle=adapter.handles[item['id']]
                print('Seed:',seed.listen_port(),seed_handle.status().is_seeding,seed_handle.status().flags,seed_handle.status().errc)
                print('Download:',handle.status().flags,handle.status().num_peers)
                print('Seed alerts:',[a.message() for a in seed.pop_alerts()][-12:])
                print('Download alerts:',[a.message() for a in adapter.session.pop_alerts()][-12:])
            assert result.get('complete'),str(result)
            assert (Path(item['destination'])/'Release'/'Episode 01.mkv').read_bytes()==(source/'Release'/'Episode 01.mkv').read_bytes()
            assert result['files'][1]['priority']==0
            item['desired']='paused'
            adapter.snapshot(item);adapter.close()
            assert (adapter.folder/'loopback.resume').exists()
            adapter=Engine(config,network=False)
            restored=adapter.snapshot(item)
            assert restored['files'][0]['priority']==4
            assert restored['files'][1]['priority']==0
            print('Partial transfer restart, loopback download, selected-file hashes and saved-state recovery passed.')
        finally:
            adapter.close();seed.pause();seed=None
    return 0


if __name__=='__main__': raise SystemExit(main())
