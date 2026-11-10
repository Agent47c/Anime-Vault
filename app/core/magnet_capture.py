"""Bounded, durable inbox for selected-site Chrome native messages."""
import hashlib
import re
import sqlite3
import time
import uuid
from contextlib import closing
from urllib.parse import parse_qsl,urlsplit
from app import db

def validate(uri):
    if not isinstance(uri,str) or len(uri)>16000 or any(c in uri for c in '\r\n\x00"'):
        raise ValueError('The magnet link is malformed or too long.')
    parsed=urlsplit(uri)
    if parsed.scheme.lower()!='magnet' or parsed.netloc or parsed.path or parsed.fragment:
        raise ValueError('Expected a magnet link.')
    values=parse_qsl(parsed.query,keep_blank_values=True,max_num_fields=100)
    identities=[]
    for key,value in values:
        if key=='xt' and (re.fullmatch(r'urn:btih:(?:[0-9a-f]{40}|[a-z2-7]{32})',value,re.I) or re.fullmatch(r'urn:btmh:1220[0-9a-f]{64}',value,re.I)):
            identities.append(value.lower())
    if not identities:
        raise ValueError('The magnet link has no supported BitTorrent identity.')
    import base64
    identities=[('urn:btih:'+base64.b32decode(v.rsplit(':',1)[-1].upper()).hex())
                if v.startswith('urn:btih:') and len(v.rsplit(':',1)[-1])==32 else v for v in identities]
    name=next((v for k,v in values if k=='dn'),'Unnamed torrent')
    name=' '.join(name.split())[:300]
    identity=hashlib.sha256('\n'.join(sorted(set(identities))).encode()).hexdigest()
    return {'uri':uri,'name':name,'identity':identity}


def _connection():
    db.DATA_DIR.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(str(db.DATA_DIR/'magnet-inbox.sqlite'),timeout=5)
    conn.row_factory=sqlite3.Row
    conn.execute('''CREATE TABLE IF NOT EXISTS inbox (
        id TEXT PRIMARY KEY, identity TEXT NOT NULL, uri TEXT NOT NULL,
        name TEXT NOT NULL, state TEXT NOT NULL, updated REAL NOT NULL)''')
    return conn


def enqueue(uri):
    value=validate(uri)
    with closing(_connection()) as conn,conn:
        conn.execute('BEGIN IMMEDIATE')
        found=conn.execute("SELECT id FROM inbox WHERE identity=? AND (state IN ('NEW','OPEN') OR updated>?) ORDER BY updated DESC LIMIT 1",(value['identity'],time.time()-60)).fetchone()
        if found: return found[0]
        count=conn.execute("SELECT COUNT(*) FROM inbox WHERE state IN ('NEW','OPEN')").fetchone()[0]
        if count>=32:
            raise ValueError('The browser magnet inbox is full. Review pending links in Anime Vault first.')
        identifier=uuid.uuid4().hex
        conn.execute('INSERT INTO inbox VALUES (?,?,?,?,?,?)',(identifier,value['identity'],uri,value['name'],'NEW',time.time()))
        # Retain a bounded recent audit; never remove pending links.
        conn.execute("DELETE FROM inbox WHERE state NOT IN ('NEW','OPEN','SUBMITTING') AND id NOT IN (SELECT id FROM inbox ORDER BY updated DESC LIMIT 100)")
        return identifier


def next_link(reset_open=False):
    with closing(_connection()) as conn,conn:
        conn.execute('BEGIN IMMEDIATE')
        if reset_open:
            conn.execute("UPDATE inbox SET state='NEW' WHERE state='OPEN'")
            from app.core.downloads import jobs
            origins={job.get('origin') for job in jobs()}
            for pending in conn.execute("SELECT id FROM inbox WHERE state='SUBMITTING'").fetchall():
                state='REVIEW' if 'browser:'+pending['id'] in origins else 'NEW'
                conn.execute('UPDATE inbox SET state=? WHERE id=?',(state,pending['id']))
        row=conn.execute("SELECT * FROM inbox WHERE state='NEW' ORDER BY updated LIMIT 1").fetchone()
        if not row: return None
        conn.execute("UPDATE inbox SET state='OPEN',updated=? WHERE id=?",(time.time(),row['id']))
        return dict(row)


def mark(identifier,state):
    if state not in ('NEW','DISMISSED','SUBMITTING','ACCEPTED','REVIEW'):
        raise ValueError('Unknown browser magnet state.')
    with closing(_connection()) as conn,conn:
        conn.execute('UPDATE inbox SET state=?,updated=? WHERE id=?',(state,time.time(),identifier))


def submit(item,fid,season):
    from app.core import downloads
    mark(item['id'],'SUBMITTING')
    try:
        result=downloads.add_download(fid,item['uri'],season,origin='browser:'+item['id'])
        mark(item['id'],'ACCEPTED')
        return result
    except Exception:
        mark(item['id'],'REVIEW')
        raise


def suggestion(name,records):
    from pathlib import Path
    from app.config import VIDEO_EXTENSIONS
    from app.core.match_evidence import base_title
    from app.core.parser import normalize_for_matching
    name=Path(name).stem if Path(name).suffix.lower() in VIDEO_EXTENSIONS else name
    title=normalize_for_matching(base_title(name))
    matches=[row['id'] for row in records if title and title in {
        normalize_for_matching(base_title(row.get(key) or ''))
        for key in ('display_title','title_en','title_romaji','title_native')}]
    return matches[0] if len(matches)==1 else None
