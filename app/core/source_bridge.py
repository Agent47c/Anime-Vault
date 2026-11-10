"""Durable commands/results for the selected-site Chrome native connection."""
import json
import time
import uuid
from contextlib import closing
from app import db

PREFIX='source_request:'


def connection():
    try: state=json.loads(db.get_state('source_bridge.connection','{}'))
    except (ValueError,TypeError): state={}
    state['connected']=bool(time.time()-state.get('seen',0)<15)
    return state


def heartbeat(site,enabled):
    db.set_state('source_bridge.connection',json.dumps(dict(site=site,enabled=bool(enabled),seen=time.time())))


def enqueue(url,source_name='Source'):
    from app.core.chrome_bridge import origin
    if not connection()['connected']:
        raise ValueError('Chrome extension is disconnected. Open Chrome, reload the Anime Vault extension and enable your selected website, then retry.')
    if not connection().get('enabled') or connection().get('site')!=origin(url):
        raise ValueError('Enable this source website in the Chrome extension popup, then retry.')
    identifier=uuid.uuid4().hex
    value=dict(id=identifier,url=url,source=source_name,state='PENDING',created=time.time())
    db.set_state(PREFIX+identifier,json.dumps(value))
    return identifier


def claim(site):
    from app.core.chrome_bridge import origin
    with closing(db.get_connection()) as conn,conn:
        conn.execute('BEGIN IMMEDIATE')
        rows=conn.execute("SELECT key,value FROM app_state WHERE key LIKE ? ORDER BY key",(PREFIX+'%',)).fetchall()
        for row in rows:
            value=json.loads(row['value'])
            if time.time()-value['created']>180:
                conn.execute('DELETE FROM app_state WHERE key=?',(row['key'],));continue
            if value['state']!='PENDING': continue
            if origin(value['url'])!=site:
                value.update(state='ERROR',error='The extension source differs from this search. Enable the selected website and retry.')
            else:
                value['state']='DISPATCHED'
            conn.execute('UPDATE app_state SET value=? WHERE key=?',(json.dumps(value),row['key']))
            if value['state']=='DISPATCHED': return value
    return None


def finish(identifier,site,entries=None,error=None):
    from app.core.chrome_bridge import origin
    from app.core.magnet_capture import validate
    if not isinstance(identifier,str) or len(identifier)!=32: raise ValueError('Invalid search identity.')
    with closing(db.get_connection()) as conn,conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT value FROM app_state WHERE key=?',(PREFIX+identifier,)).fetchone()
        if not row: raise ValueError('Search expired.')
        value=json.loads(row['value'])
        if value['state']!='DISPATCHED' or origin(value['url'])!=site: raise ValueError('Search was cancelled or source changed.')
        if error:
            value.update(state='ERROR',error=str(error)[:500])
        else:
            cleaned=[];seen=set()
            for entry in (entries or [])[:100]:
                if not isinstance(entry,dict): continue
                try: identity=validate(entry.get('magnet'))['identity']
                except (TypeError,ValueError): continue
                if identity in seen: continue
                seen.add(identity)
                item={key:str(entry.get(key) or '')[:500] for key in ('title','size','quality','group')}
                item.update(magnet=entry['magnet'],identity=identity,source=value['source'],
                            seeders=max(0,int(entry['seeders'])) if str(entry.get('seeders','')).isdigit() else None)
                if item['title']: cleaned.append(item)
            value.update(state='COMPLETE',results=cleaned)
        conn.execute('UPDATE app_state SET value=? WHERE key=?',(json.dumps(value),PREFIX+identifier))


def wait(identifier,cancelled=lambda:False,timeout=65):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        value=json.loads(db.get_state(PREFIX+identifier,'{}'))
        if value.get('state')=='COMPLETE': return value['results']
        if value.get('state')=='ERROR': raise ValueError(value['error'])
        if cancelled():
            value['state']='CANCELLED';db.set_state(PREFIX+identifier,json.dumps(value))
            raise InterruptedError('Search cancelled.')
        time.sleep(.15)
    value['state']='CANCELLED';db.set_state(PREFIX+identifier,json.dumps(value))
    raise ValueError('Chrome/source did not answer in time. Open the website to complete any browser verification, check the extension, then retry.')
