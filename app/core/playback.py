"""App-owned VLC/MPV control and progress stored by stable episode identity."""
import json,math,os,secrets,socket,sys,threading,time,uuid
from contextlib import closing
from pathlib import Path
from app import db
from app.core.identity import path_key

_lock=threading.Lock()
_session=None
_revision=0
_retired=[]

class MediaChanged(ValueError):pass

def episode_ids(path):
    with closing(db.get_connection()) as conn:
        return [row[0] for row in conn.execute('SELECT fe.episode_id FROM file_locations l JOIN file_episodes fe ON fe.file_id=l.file_id WHERE l.path_key=? ORDER BY fe.episode_id',(path_key(path),))]

def saved_progress(ids):
    for eid in ids:
        try:value=json.loads(db.get_state('playback.episode:'+str(eid),'null'))
        except (TypeError,ValueError):continue
        if isinstance(value,dict):
            try:position=float(value.get('position',0));duration=float(value.get('duration',0))
            except (TypeError,ValueError):continue
            if duration>0 and math.isfinite(position) and math.isfinite(duration):return {**value,'position':max(0,min(position,duration)),'duration':duration,'episode_id':eid}
    return {}

def last_progress():
    eid=db.get_state('last_episode_id')
    if not eid or not str(eid).isdigit():return {}
    value=saved_progress([int(eid)])
    with closing(db.get_connection()) as conn:
        row=conn.execute('SELECT ls.franchise_id,l.path FROM episodes e JOIN releases r ON r.id=e.release_id JOIN library_series ls ON ls.id=r.series_id LEFT JOIN file_episodes fe ON fe.episode_id=e.id LEFT JOIN file_locations l ON l.file_id=fe.file_id WHERE e.id=? LIMIT 1',(int(eid),)).fetchone()
    return {**value,'fid':row[0],'path':row[1]} if row else value

def save_progress(ids,position,duration):
    if not all(math.isfinite(n) for n in (position,duration)) or duration<=0:return
    position=max(0,min(position,duration));now=int(time.time())
    with closing(db.get_connection()) as conn,conn:
        for eid in ids:
            if not conn.execute('SELECT 1 FROM episodes WHERE id=?',(eid,)).fetchone():continue
            value=json.dumps(dict(position=position,duration=duration,updated_at=now))
            conn.execute('INSERT INTO app_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('playback.episode:'+str(eid),value))
            row=conn.execute("SELECT id FROM episode_history WHERE episode_id=? AND event='PROGRESS' ORDER BY id DESC LIMIT 1",(eid,)).fetchone()
            if row:conn.execute('UPDATE episode_history SET position_seconds=?,played_at=? WHERE id=?',(position,now,row[0]))
            else:conn.execute("INSERT INTO episode_history(episode_id,played_at,position_seconds,event) VALUES(?,?,?,'PROGRESS')",(eid,now,position))

def _pipe_command(endpoint,command):
    payload=(json.dumps({'command':command,'request_id':1})+'\n').encode()
    if sys.platform=='win32':
        import win32file,win32pipe
        handle=win32file.CreateFile(endpoint,0xC0000000,0,None,3,0,None)
        try:
            win32file.WriteFile(handle,payload);end=time.monotonic()+.6;buffer=b''
            while time.monotonic()<end:
                available=win32pipe.PeekNamedPipe(handle,0)[1]
                if available:
                    buffer+=win32file.ReadFile(handle,min(available,65536))[1]
                    for line in buffer.split(b'\n')[:-1]:
                        reply=json.loads(line)
                        if reply.get('request_id')==1:return reply.get('data')
                time.sleep(.01)
            raise TimeoutError('Player IPC timeout')
        finally:win32file.CloseHandle(handle)
    else:
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
            client.settimeout(.6);client.connect(endpoint);client.sendall(payload)
            buffer=b''
            while len(buffer)<65536:
                data=client.recv(4096)
                if not data:break
                buffer+=data
                for line in buffer.split(b'\n')[:-1]:
                    reply=json.loads(line)
                    if reply.get('request_id')==1:return reply.get('data')
            raise ValueError('No player response')

class Session:
    def __init__(self,player,path,resume=True):
        self.player=player;self.path=str(path);self.ids=episode_ids(path);self.process=None
        self.fid=None
        if self.ids:
            with closing(db.get_connection()) as conn:
                row=conn.execute('SELECT ls.franchise_id FROM episodes e JOIN releases r ON r.id=e.release_id JOIN library_series ls ON ls.id=r.series_id WHERE e.id=?',(self.ids[0],)).fetchone()
                if row:self.fid=row[0]
        self.previous=saved_progress(self.ids);self.last_save=0;self.started=time.monotonic();self.state={};self.error=''
        self.playlist_id=None
        saved=self.previous.get('position',0);duration=self.previous.get('duration',0)
        start=saved if resume and duration and saved<duration*.95 else 0
        if player=='vlc':
            with socket.socket() as listener:listener.bind(('127.0.0.1',0));self.port=listener.getsockname()[1]
            self.password=secrets.token_urlsafe(24)
            self.arguments=['--no-one-instance','--extraintf=http','--http-host=127.0.0.1',f'--http-port={self.port}','--http-password='+self.password]
            if start:self.arguments.append('--start-time='+str(round(start,2)))
        elif player=='mpv':
            import tempfile
            self._ipc_directory=None if sys.platform=='win32' else tempfile.TemporaryDirectory(prefix='animevault-ipc-')
            self.endpoint=r'\\.\pipe\animevault-'+uuid.uuid4().hex if sys.platform=='win32' else str(Path(self._ipc_directory.name)/'player.sock')
            self.arguments=['--input-ipc-server='+self.endpoint]
            if start:self.arguments.append('--start='+str(round(start,2)))
        else:raise ValueError('This player does not expose supported playback controls')
    def _vlc(self,command=None):
        import requests
        with requests.Session() as client:
            client.trust_env=False
            response=client.get(f'http://127.0.0.1:{self.port}/requests/status.json',params={'command':command} if command else None,auth=('',self.password),timeout=.6)
            response.raise_for_status();return response.json()
    def poll(self):
        if self.process is None or self.process.poll() is not None:return {**self.state,'active':False}
        if self.player=='vlc':
            data=self._vlc();position=float(data.get('time') or 0);duration=float(data.get('length') or 0);paused=data.get('state')=='paused'
            current=data.get('currentplid')
            if self.playlist_id is not None and current is not None and current!=self.playlist_id:raise MediaChanged('Player changed media')
            if duration>0 and current is not None:self.playlist_id=current
        else:
            current=_pipe_command(self.endpoint,['get_property','path'])
            if current and path_key(current)!=path_key(self.path):raise MediaChanged('Player changed media')
            position=float(_pipe_command(self.endpoint,['get_property','time-pos']) or 0)
            duration=float(_pipe_command(self.endpoint,['get_property','duration']) or 0)
            paused=bool(_pipe_command(self.endpoint,['get_property','pause']))
        if not all(math.isfinite(v) for v in (position,duration)):raise ValueError('Invalid playback time')
        self.state=dict(position=max(0,position),duration=max(0,duration),paused=paused,active=duration>0,path=self.path,fid=self.fid,episode_ids=self.ids,player=self.player)
        if duration>0 and time.monotonic()-self.last_save>=5:
            save_progress(self.ids,position,duration);self.last_save=time.monotonic()
        return self.state
    def toggle(self):
        if self.process is None or self.process.poll() is not None:raise ValueError('No active app-launched player')
        if self.player=='vlc':self._vlc('pl_pause')
        else:_pipe_command(self.endpoint,['cycle','pause'])

def launch_session(player,path,resume=True):
    return Session(player,path,resume) if player in ('vlc','mpv') else None

def attach(session,process=None):
    global _session,_revision
    with _lock:
        if _session is not None and _session is not session:_retired.append(_session)
        _session=session
        _revision+=1
        if session:session.process=process

def poll():
    global _session
    with _lock:
        retired=list(_retired);_retired.clear()
    for previous in retired:
        try:
            state=previous.poll()  # Verify media ownership before stopping it.
            if state.get('duration'):save_progress(previous.ids,state['position'],state['duration'])
            if previous.process and previous.process.poll() is None:previous.process.terminate()
        except Exception:pass  # Independently changed media is left alone.
    session=_session
    if session is None:return {**last_progress(),'active':False}
    try:
        state=session.poll()
        if not state.get('active') and session.process.poll() is not None:
            if state.get('duration'):save_progress(session.ids,state['position'],state['duration'])
            with _lock:
                if _session is session:_session=None
        return state
    except Exception as error:
        if isinstance(error,MediaChanged) or time.monotonic()-session.started>15:
            with _lock:
                if _session is session:_session=None
        return {**last_progress(),'active':False,'notice':'Live playback is unavailable. Use app-launched VLC or MPV.'}

def toggle():
    session=_session
    if session is None:raise ValueError('Open an episode in VLC or MPV to use playback controls.')
    session.toggle()

def active():
    return _session is not None or bool(_retired)

def revision():return _revision
