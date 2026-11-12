"""Timestamp-based aired/upcoming episode labels; never guess episode - 1."""
import re,time
from datetime import datetime


def episode_events(media,history=(),now=None):
    now=time.time() if now is None else now
    mid=media.get('id');next_episode=media.get('nextAiringEpisode') or {};rows={}
    for entry in history:
        if entry.get('mediaId')!=mid:continue
        ep,stamp=entry.get('episode'),entry.get('airingAt')
        if isinstance(ep,int) and ep>0 and isinstance(stamp,(int,float)) and stamp>0:rows[ep]=stamp
    ep,stamp=next_episode.get('episode'),next_episode.get('airingAt')
    if isinstance(ep,int) and ep>0 and isinstance(stamp,(int,float)) and stamp>0:rows[ep]=stamp
    aired=[(n,t) for n,t in rows.items() if t<=now and media.get('status')!='NOT_YET_RELEASED']
    latest=max(aired,key=lambda item:(item[1],item[0])) if aired else None
    future=[(n,t) for n,t in rows.items() if t>now and (latest is None or n>latest[0])]
    upcoming=min(future,key=lambda item:(item[1],item[0])) if future else None
    result=[]
    if latest:result.append((latest[0],'aired',latest[1]))
    if upcoming:result.append((upcoming[0],'scheduled',upcoming[1]))
    elif isinstance(ep,int) and ep>0 and ep not in rows and (latest is None or ep>latest[0]):result.append((ep,'unverified',None))
    return result


def episode_notifications(media,history=(),now=None):
    # Retain the existing stable scheduled token for dismissal compatibility.
    return [f'Episode {ep} '+('aired' if state=='aired' else 'airing soon' if state=='scheduled' else 'broadcast time unverified')
            for ep,state,_ in episode_events(media,history,now)]


def is_episode_change(change):
    return bool(re.match(r'^Episode\s+\d+\b',change.strip(),re.I))


def display_episode_change(change,media,history=(),now=None):
    match=re.fullmatch(r'Episode (\d+) (airing soon|aired|broadcast time unverified)',change.strip(),re.I)
    if not match:return None
    ep=int(match[1]);event=next((item for item in episode_events(media,history,now) if item[0]==ep),None)
    if event is None:return f'Episode {ep} · Broadcast time unverified'
    _,state,stamp=event
    if stamp is None:return f'Episode {ep} · Broadcast time unverified'
    date=datetime.fromtimestamp(stamp).strftime('%d %b %Y at %H:%M')
    return f'Episode {ep} '+('aired' if state=='aired' else 'scheduled')+f' · {date} local time'
