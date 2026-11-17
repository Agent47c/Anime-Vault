"""Cached local broadcast view shared by the approved full-calendar screen."""
import json
from contextlib import closing
from datetime import datetime
from app import db
from app.core.release_calendar import saved,library_owners


def entries(first,last):
    records=db.get_all_franchises();visible={r['id']:r for r in records};owners=library_owners();result={}
    def add(fid,title,stamp,episode,release_id=None,season_id=None):
        if fid not in visible or not stamp:return
        try:airing=datetime.fromtimestamp(int(stamp))
        except (ValueError,TypeError,OverflowError,OSError):return
        if first<=airing.date()<=last:
            result[(fid,release_id,episode,int(stamp))]=dict(fid=fid,title=title,episode=episode,airing_at=int(stamp),time=airing.strftime('%H:%M'),release_id=release_id,season_id=season_id,cover=visible[fid].get('cover_filename'))
    for record in records:
        mid=record.get('anilist_id')
        if mid:owners[mid]=(record['id'],record['display_title'],None)
        try:media=json.loads(record.get('metadata_json') or '{}') or {};next_ep=media.get('nextAiringEpisode') or {}
        except (ValueError,TypeError,AttributeError):continue
        add(record['id'],record['display_title'],next_ep.get('airingAt'),next_ep.get('episode'),mid)
        for edge in (media.get('relations') or {}).get('edges',[]):
            node=edge.get('node') or {};related_id=node.get('id');owner=owners.get(related_id)
            if edge.get('relationType') in ('SEQUEL','SIDE_STORY','SPIN_OFF') and owner and owner[0]==record['id']:
                upcoming=node.get('nextAiringEpisode') or {}
                add(owner[0],owner[1],upcoming.get('airingAt'),upcoming.get('episode'),related_id,owner[2])
    with closing(db.get_connection()) as conn:
        for row in conn.execute('SELECT franchise_id,title_display,next_airing_at,next_airing_ep,anilist_id,id FROM seasons'):
            fid,title,stamp,episode,mid,sid=tuple(row)
            if fid not in visible:continue
            if mid:owners[mid]=(fid,title,sid)
            add(fid,title,stamp,episode,mid,sid)
    for release in saved():
        owner=owners.get(release.get('mediaId'))
        if owner:add(owner[0],owner[1],release.get('airingAt'),release.get('episode'),release.get('mediaId'),owner[2])
    return sorted(result.values(),key=lambda e:(e['airing_at'],e['title']))
