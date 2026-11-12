"""Bounded, cached episode presentation data. Call only from IO workers."""
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import time
import threading
import uuid
from contextlib import closing
from pathlib import Path
from app import db
from app.core.identity import path_key

_api_lock=threading.Lock()
_last_request=0.0


def _metadata(key,mal,number,cancelled):
    """Serialize visible-row requests and retain negative results across visits."""
    global _last_request
    import requests
    while not _api_lock.acquire(timeout=.1):
        if cancelled():return {}
    try:
        try:cached=json.loads(db.get_state(key,'{}'))
        except (ValueError,TypeError):cached={}
        if not isinstance(cached,dict):cached={}
        if time.time()<cached.get('retry_at',0):return cached
        while time.monotonic()-_last_request<1.1:
            if cancelled():return cached
            time.sleep(.05)
        if cancelled():return cached
        _last_request=time.monotonic()
        try:
            response=requests.get(f'https://api.jikan.moe/v4/anime/{int(mal)}/episodes/{int(number)}',timeout=(2,3))
            response.raise_for_status();payload=response.json()
            data=payload.get('data') or {} if isinstance(payload,dict) else {}
            if not isinstance(data,dict):raise ValueError('Invalid episode metadata')
            cached=dict(title=data.get('title'),description=data.get('synopsis'),retry_at=time.time()+7*86400)
        except (requests.RequestException,ValueError,TypeError):cached['retry_at']=time.time()+6*3600
        db.set_state(key,json.dumps(cached,ensure_ascii=False))
        return cached
    finally:_api_lock.release()


def enrich_rows(rows):
    """Resolve watch dates and provider numbers through stable episode IDs."""
    with closing(db.get_connection()) as conn:
        franchises={f['anilist_id']:dict(f) for f in conn.execute('SELECT * FROM franchises WHERE anilist_id IS NOT NULL')}
        for row in rows:
            linked=[dict(e) for e in conn.execute('''SELECT e.*, l.file_id,
                (SELECT MAX(h.played_at) FROM episode_history h WHERE h.episode_id=e.id) AS last_played
                FROM episodes e JOIN file_episodes fe ON fe.episode_id=e.id
                JOIN file_locations l ON l.file_id=fe.file_id WHERE l.path_key=?''',(path_key(row['path']),))]
            row['last_played']=max((e['last_played'] or 0 for e in linked),default=0)
            row['episode_ids']=[e['id'] for e in linked]
            if linked:row['file_id']=linked[0]['file_id']
            record=franchises.get(row.get('release_id'),{})
            row['mal_id']=record.get('mal_id')
            row['provider_number']=linked[0]['release_number'] if len(linked)==1 and linked[0]['mapping_verified'] else None
            row['description']='Episode description has not been fetched.'
            row['episode_name']=row['title']
    return rows


def load_preview(row,cancelled=lambda:False):
    """A visible row only: local frame and verified-release synopsis, with TTLs."""
    from PyQt5.QtGui import QImage
    from app.config import is_offline
    result={}
    path=Path(row['path'])
    try:
        stat=path.stat()
        fingerprint=f"{row.get('file_id',path_key(path))}:{stat.st_size}:{stat.st_mtime_ns}"
        key=hashlib.sha256(fingerprint.encode()).hexdigest()
        folder=db.DATA_DIR/'episode-thumbnails';target=folder/(key+'.jpg')
        retry_key='episode-frame-retry:'+key
        if not target.is_file() and not cancelled() and time.time()>float(db.get_state(retry_key,'0')):
            executable=shutil.which('ffmpeg')
            if executable:
                folder.mkdir(parents=True,exist_ok=True)
                temporary=target.with_name(key+'.'+uuid.uuid4().hex+'.tmp.jpg')
                try:
                    process=subprocess.run([executable,'-nostdin','-v','error','-y','-ss','30','-i',str(path),'-frames:v','1','-vf','scale=320:180:force_original_aspect_ratio=decrease',str(temporary)],
                        capture_output=True,timeout=6,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    if not process.returncode and temporary.is_file() and not QImage(str(temporary)).isNull():os.replace(temporary,target)
                except (OSError,subprocess.TimeoutExpired):pass
                finally:temporary.unlink(missing_ok=True)
            if not target.is_file():db.set_state(retry_key,str(time.time()+6*3600))
        if target.is_file():result['image']=QImage(str(target))
    except (OSError,ValueError):pass
    if cancelled():return result
    mal,number=row.get('mal_id'),row.get('provider_number')
    if not mal or not number:
        result['description']='Episode description unavailable: a verified episode/release match is required.'
        return result
    cache_key=f'episode-description:jikan:{mal}:{number}'
    try:cached=json.loads(db.get_state(cache_key,'{}'))
    except (ValueError,TypeError):cached={}
    if not isinstance(cached,dict):cached={}
    if time.time()>cached.get('retry_at',0) and not is_offline() and not cancelled():
        cached=_metadata(cache_key,mal,number,cancelled)
    if cached.get('title'):result['episode_name']=html.unescape(cached['title'])
    result['description']=html.unescape(re.sub('<[^>]+>','',cached.get('description') or 'No episode description available.'))
    return result
