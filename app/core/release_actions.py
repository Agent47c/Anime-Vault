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
    """Find the next learned source episode; returning results never queues it."""
    from app.core import download_discovery as discovery,download_assignment
    assignment=download_assignment.next_search(fid,media_id)
    from app.core import downloads
    sources=discovery.sources();configured=downloads.settings()['source']
    source=next((s for s in sources if s.get('name')==assignment.get('source_name')),None) or next((s for s in sources if s.get('url')==configured),sources[0])
    result=discovery.search(fid,assignment['season'],source,assignment['query'],cancelled)
    if cancelled():raise InterruptedError('Search stopped. No download was started.')
    result['context'].update(assignment)
    result['context'].update(discovery.library_context(fid,assignment['season'],continuous=assignment['continuous']))
    result['context'].update(assignment)
    # Suggestions retain their original source episode. The confirmation form
    # proposes the learned logical number without treating that as user approval.
    for entry in result['results']:
        entry['continuous']=assignment['continuous'];entry['season']=assignment['season']
    result['assignment_context']=assignment
    return result
