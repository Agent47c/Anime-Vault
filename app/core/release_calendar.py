"""Persistent, dated library release calendar (never infer weekly air dates)."""
import json
from datetime import datetime, time, timedelta
from contextlib import closing
from app import db

KEY = 'release_calendar.v1'


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
    episode = media.get('nextAiringEpisode') or {}
    if media.get('id') and episode.get('airingAt') and episode.get('episode'):
        remember([dict(episode, mediaId=media['id'])])


def refresh(cancelled=lambda: False):
    """Called only by the existing internet updater, never by page navigation."""
    from app.core import anilist_client as client
    ids = {f['anilist_id'] for f in db.get_all_franchises() if f.get('anilist_id')}
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
