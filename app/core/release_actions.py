"""Explicit release actions reuse verified download coverage and queue identity."""
import json,time
from app import db

def remind(media_id,episode,airing_at,title):
    if airing_at<=time.time():raise ValueError('This episode has already aired.')
    rows=json.loads(db.get_state('release.reminders','[]'))
    rows=[r for r in rows if (r['media_id'],r['episode'])!=(media_id,episode)]
    rows.append(dict(media_id=media_id,episode=episode,airing_at=airing_at,title=title))
    db.set_state('release.reminders',json.dumps(rows))

def due_reminders(now=None):
    now=time.time() if now is None else now
    rows=json.loads(db.get_state('release.reminders','[]'));due=[r for r in rows if r['airing_at']<=now]
    if due:db.set_state('release.reminders',json.dumps([r for r in rows if r['airing_at']>now]))
    return due

def auto_grab(fid,media_id,episode,cancelled=lambda:False):
    if not isinstance(episode,int) or episode<1:raise ValueError('Choose a valid episode number.')
    from app.core import download_discovery as discovery,download_queries
    season=next((s for s in db.get_series_seasons(fid) if s.get('anilist_id')==media_id),None)
    if not season:raise ValueError('Match this release to a local season first using Rematch.')
    number=season.get('season_number') or 0
    context=discovery.library_context(fid,number)
    key=discovery.episode_key(context['continuous'],number,episode)
    if key in context['local'] or key in context['pending']:return 'Episode already present or queued.'
    from app.core import downloads
    sources=discovery.sources();configured=downloads.settings()['source']
    source=next((s for s in sources if s.get('url')==configured),sources[0])
    custom=download_queries.custom_query(fid,number)
    query=(custom.get('query') if custom.get('active') else None) or download_queries.default_query(fid,season['title_display'],number)
    result=discovery.search(fid,number,source,query+f' {episode:02}',cancelled)
    entries=[r for r in result['results'] if r.get('status')!='Match Uncertain' and set(r.get('episode_keys') or [])=={key}]
    if not entries:raise ValueError('No verified single-episode release found. Use Find Download Files to review results.')
    chosen=max(entries,key=lambda r:r.get('seeders') or 0)
    if cancelled():raise InterruptedError('Stopped before queueing download.')
    discovery.submit(fid,[chosen])
    return 'Verified episode sent to the built-in download queue.'
