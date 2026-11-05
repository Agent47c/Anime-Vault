"""Explicit qBittorrent handoff and tracked, completed-only local indexing."""
import base64
import json
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlencode, parse_qsl, urlunsplit
import requests
from app import db

_lock = threading.RLock()
DEFAULTS = {'url':'http://127.0.0.1:8080','username':'admin','secret':'',
            'source':'https://nyaa.si/?q={query}&f=0&c=0_0','group':'ASW','quality':'1080p',
            'destination':str(Path.home()/'Downloads'/'AnimeVault'),'enabled':False,'start_paused':True}


def settings():
    return {**DEFAULTS, **json.loads(db.get_state('downloads.settings','{}'))}


def protect(password):
    import win32crypt
    return base64.b64encode(win32crypt.CryptProtectData(password.encode(),'Anime Vault qBittorrent',None,None,None,0)).decode()


def password(config):
    if not config.get('secret'):
        return ''
    import win32crypt
    return win32crypt.CryptUnprotectData(base64.b64decode(config['secret']),None,None,None,0)[1].decode()


def validate_url(value, local=False):
    parsed=urlsplit(value)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Use an http/https URL without credentials in the address.')
    if local and parsed.hostname not in ('localhost','127.0.0.1','::1'):
        raise ValueError('This integration connects to qBittorrent on this computer. Use localhost or 127.0.0.1.')
    if local and (parsed.query or parsed.fragment):
        raise ValueError('Use the qBittorrent base URL without a query or fragment.')
    return value.rstrip('/')


def save_settings(config,new_password=None):
    with _lock:
        config={**settings(),**config}
        config['url']=validate_url(config['url'],True)
        search_url(config['source'],'test')
        if not Path(config['destination']).is_absolute():
            raise ValueError('Choose an absolute download destination.')
        if new_password is not None:
            config['secret']=protect(new_password)
        db.set_state('downloads.settings',json.dumps(config))


def search_url(template,query):
    validate_url(template)
    if template.count('{query}') != 1:
        raise ValueError('Search URL must contain {query} once, in a query parameter.')
    parsed=urlsplit(template)
    if '{query}' in parsed.netloc or '{query}' in parsed.path or '{query}' in parsed.fragment:
        raise ValueError('Place {query} in the search query parameter.')
    values=[(key,value.replace('{query}',query)) for key,value in parse_qsl(parsed.query,keep_blank_values=True)]
    return urlunsplit((parsed.scheme,parsed.netloc,parsed.path,urlencode(values),parsed.fragment))


def make_query(title,episode='',group='',quality=''):
    group=group.strip().strip('[]')
    return ' '.join(value for value in (f'[{group}]' if group else '',title.strip(),str(episode).strip(),quality.strip()) if value)


class Client:
    def __init__(self,config):
        self.base=validate_url(config['url'],True)
        self.session=requests.Session()
        self.session.trust_env=False
        self.session.headers.update({'Referer':self.base+'/','Origin':self.base})
        try:
            response=self.call('auth/login',data={'username':config['username'],'password':password(config)})
            if response.text.strip() != 'Ok.':
                raise ValueError('qBittorrent login failed. Check the Web UI username and password.')
        except Exception:
            self.session.close()
            raise

    def call(self,route,**kwargs):
        response=self.session.request('POST' if 'data' in kwargs or 'files' in kwargs else 'GET',
                                      self.base+'/api/v2/'+route,timeout=(3,10),allow_redirects=False,**kwargs)
        if 300 <= response.status_code < 400:
            raise ValueError('qBittorrent redirected the request. Check its Web UI URL.')
        response.raise_for_status()
        return response

    def close(self):
        self.session.close()


def test_connection(config,new_password=None):
    config={**settings(),**config}
    if new_password is not None:
        config['secret']=protect(new_password)
    client=Client(config)
    try:
        return 'Connected to qBittorrent '+client.call('app/version').text.strip()
    finally:
        client.close()


def jobs():
    return json.loads(db.get_state('downloads.jobs','[]'))


def _save_jobs(items):
    db.set_state('downloads.jobs',json.dumps(items))


def add_download(fid,source,season=0):
    """Only explicitly submitted torrents are tracked; no unrelated client jobs."""
    with _lock:
        config=settings()
        if not config['enabled']:
            raise ValueError('Save and enable the qBittorrent connection first.')
        series=db.get_franchise(fid)
        if not series:
            raise ValueError('Choose an anime from the library first.')
        from contextlib import closing
        with closing(db.get_connection()) as conn,conn:
            conn.execute('INSERT OR IGNORE INTO library_series(franchise_id) VALUES (?)',(fid,))
            series_id=conn.execute('SELECT id FROM library_series WHERE franchise_id=?',(fid,)).fetchone()[0]
        is_magnet=source.startswith('magnet:?')
        torrent=Path(source) if not is_magnet else None
        if is_magnet:
            if not any(key=='xt' and value.startswith(('urn:btih:','urn:btmh:')) for key,value in parse_qsl(urlsplit(source).query)):
                raise ValueError('The magnet link has no BitTorrent identity.')
        elif torrent.suffix.lower()!='.torrent' or not torrent.is_file():
            raise ValueError('Paste a magnet link or choose a local .torrent file.')
        identifier=uuid.uuid4().hex
        import re
        title=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',series['display_title']).strip(' .')[:100] or 'Anime'
        root=Path(config['destination']).resolve()/(title+'-'+identifier[:10])
        target=root/(f'Season {season:02}' if season else 'Episodes')
        item={'id':identifier,'tag':'AnimeVault-'+identifier,'fid':fid,'series_id':series_id,'title':series['display_title'],
              'root':str(root),'destination':str(target),'status':'Submitting','progress':0,'created':time.time()}
        items=jobs();items.append(item);_save_jobs(items)
        client=None
        try:
            client=Client(config)
            paused='true' if config.get('start_paused',True) else 'false'
            data={'savepath':str(target),'tags':item['tag'],'autoTMM':'false','paused':paused,'stopped':paused}
            if is_magnet:
                response=client.call('torrents/add',data={**data,'urls':source})
            else:
                with torrent.open('rb') as handle:
                    response=client.call('torrents/add',data=data,files={'torrents':(torrent.name,handle,'application/x-bittorrent')})
            if response.text.strip()!='Ok.':
                raise ValueError('qBittorrent did not accept the torrent.')
            item['status']='Waiting for torrent metadata'
        except Exception:
            item['status']='Submission unconfirmed — check qBittorrent; do not resubmit blindly'
            raise
        finally:
            _save_jobs(items)
            if client: client.close()
        return item['destination']


def _completed_files(item,info,entries):
    target=Path(item['destination']).resolve()
    if Path(info['save_path']).resolve()!=target:
        raise ValueError('The client save path differs from the reviewed destination. Review in qBittorrent.')
    if not entries:
        raise ValueError('The torrent has no file inventory yet.')
    from app.config import VIDEO_EXTENSIONS
    files=[]
    for entry in entries:
        if entry.get('priority',1)==0:
            continue
        path=(target/entry['name']).resolve()
        if path==target or target not in path.parents:
            raise ValueError('A torrent file is outside the download destination.')
        if entry.get('progress',0)<1:
            raise ValueError('Some selected files are still downloading.')
        if path.suffix.lower() in VIDEO_EXTENSIONS:
            stat=path.stat()
            if stat.st_size!=entry['size']:
                raise ValueError('A completed file is missing or has an unexpected size.')
            files.append(path)
    if not files:
        raise ValueError('No completed video files found. Archives require manual extraction and review.')
    return files


def poll(cancelled=lambda:False):
    """Worker-only polling; completed jobs are idempotent across restarts."""
    with _lock:
        config=settings();items=jobs();changed=False
        pending=sorted((item for item in items if item['status']!='Indexed'),key=lambda item:item.get('checked',0))[:8]
        if not config['enabled'] or not pending:
            return items,False
        client=Client(config)
        try:
            for item in pending:
                if cancelled(): break
                item['checked']=time.time()
                matches=client.call('torrents/info',params={'tag':item['tag']}).json()
                if len(matches)!=1:
                    item['status']='Waiting for torrent metadata' if time.time()-item['created']<600 else 'Review in qBittorrent: tracked torrent not found'
                    continue
                info=matches[0]
                item['progress']=info.get('progress',0)
                item['status']=info.get('state','Downloading')
                if item['progress']<1 or info.get('state') in ('checkingUP','checkingDL','checkingResumeData','moving','error','missingFiles'):
                    continue
                try:
                    if cancelled(): break
                    entries=client.call('torrents/files',params={'hash':info['hash']}).json()
                    files=_completed_files(item,info,entries)
                    if not db.get_franchise(item['fid']):
                        raise ValueError('The linked anime was removed from the library. Keep the completed files and review them manually.')
                    from contextlib import closing
                    with closing(db.get_connection()) as conn:
                        identity=conn.execute('SELECT franchise_id FROM library_series WHERE id=?',(item.get('series_id'),)).fetchone()
                    if not identity or identity[0]!=item['fid']:
                        raise ValueError('The original series identity changed. Review this download before linking it.')
                    from app.core.scanner import _update_on_disk_info
                    # Only this torrent's verified files enter the inventory.
                    inventory={str(path):(s.st_size,s.st_mtime_ns,str(s.st_dev),str(s.st_ino)) for path in files for s in [path.stat()]}
                    _update_on_disk_info(item['fid'],item['root'],inventory=inventory)
                    db.set_state('organizer_preview_stale','1')
                    item['status']='Indexed';changed=True
                except (OSError,ValueError) as error:
                    item['status']='Needs review: '+str(error)
            _save_jobs(items)
            return items,changed
        finally:
            client.close()
