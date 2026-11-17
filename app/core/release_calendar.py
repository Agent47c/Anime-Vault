"""Persistent, dated library release calendar (never infer weekly air dates)."""
import json
from datetime import datetime, time, timedelta
from contextlib import closing
from app import db

KEY = 'release_calendar.v1'


def library_owners():
    """Include official cached sequels without requiring a downloaded season row."""
    owners={};related={}
    for record in db.get_all_franchises():
        fid=record['id'];title=record['display_title']
        if record.get('anilist_id'):owners[record['anilist_id']]=(fid,title,None)
        try:media=json.loads(record.get('metadata_json') or '{}') or {}
        except (ValueError,TypeError):continue
        if not isinstance(media,dict):continue
        for edge in (media.get('relations') or {}).get('edges',[]):
            if edge.get('relationType') not in ('SEQUEL','SIDE_STORY','SPIN_OFF'):continue
            node=edge.get('node') or {};mid=node.get('id')
            if mid:
                names=node.get('title') or {};name=names.get('english') or names.get('romaji') or title
                related.setdefault(mid,{})[fid]=(fid,name,None)
    with closing(db.get_connection()) as conn:
        for row in conn.execute('SELECT anilist_id,franchise_id,title_display,id FROM seasons WHERE anilist_id IS NOT NULL'):
            owners[row[0]]=(row[1],row[2],row[3])
    for mid,candidates in related.items():
        if mid not in owners and len(candidates)==1:owners[mid]=next(iter(candidates.values()))
    return owners


def saved():
    try:
        value = json.loads(db.get_state(KEY, '[]'))
        return value if isinstance(value, list) else []
    except (TypeError, ValueError):
        return []


def remember(entries):
    cutoff = int((datetime.now() - timedelta(weeks=12)).timestamp())
    rows = {}
    for entry in saved() + entries:
        try:
            key = (int(entry['mediaId']), int(entry['episode']))
            if int(entry['airingAt']) >= cutoff:
                rows[key] = dict(entry)
        except (KeyError, TypeError, ValueError):
            continue
    db.set_state(KEY, json.dumps(list(rows.values())))


def remember_metadata(media):
    """Keep the previous next episode even when newer metadata replaces it."""
    entries=[media]+[edge.get('node') or {} for edge in (media.get('relations') or {}).get('edges',[]) if edge.get('relationType') in ('SEQUEL','SIDE_STORY','SPIN_OFF')]
    rows=[]
    for entry in entries:
        episode=entry.get('nextAiringEpisode') or {}
        if entry.get('id') and episode.get('airingAt') and episode.get('episode'):rows.append(dict(episode,mediaId=entry['id']))
    if rows:remember(rows)


def refresh(cancelled=lambda: False):
    """Called only by the existing internet updater, never by page navigation."""
    from app.core import anilist_client as client
    ids = set(library_owners())
    with closing(db.get_connection()) as conn:
        ids.update(row[0] for row in conn.execute(
            'SELECT DISTINCT anilist_id FROM seasons WHERE anilist_id IS NOT NULL'))
    if not ids:
        return
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    start = int(datetime.combine(monday - timedelta(days=7), time.min).timestamp())
    end = int(datetime.combine(monday + timedelta(days=14), time.min).timestamp())
    query = '''query ($ids: [Int], $start: Int, $end: Int, $page: Int) {
      Page(page: $page, perPage: 50) {
        pageInfo { hasNextPage }
        airingSchedules(mediaId_in: $ids, airingAt_greater: $start,
                        airingAt_lesser: $end, sort: TIME) {
          mediaId episode airingAt
        }
      }
    }'''
    with client.cancellable(cancelled):
        for page in range(1, 201):
            if cancelled():
                return
            data = client._graphql_request(query, dict(ids=sorted(ids), start=start-1, end=end, page=page))
            if not data or not data.get('Page'):
                return  # Failed fetch must not erase saved releases.
            result = data['Page']
            remember(result.get('airingSchedules') or [])
            if not (result.get('pageInfo') or {}).get('hasNextPage'):
                return
