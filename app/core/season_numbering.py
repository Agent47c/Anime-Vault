"""Release numbering from explicit evidence, never selection/network order."""
import json
import re
from contextlib import closing
from app import db


def explicit_number(title):
    found=[]
    for pattern in (r'\bseason\s*(\d{1,3})\b',r'\b(\d{1,3})(?:st|nd|rd|th)\s+season\b',r'\bS(\d{1,3})(?!\d|E\d)',r'第?(\d{1,3})期'):
        found.extend(int(m) for m in re.findall(pattern,title or '',re.I))
    return found[0] if found and len(set(found))==1 and 0<found[0]<1000 else None


def infer(media,root=None,catalog=()):
    aliases=list((media.get('title') or {}).values())
    values={number for name in aliases if (number:=explicit_number(name)) is not None}
    if len(values)==1:return next(iter(values))
    if len(values)>1:return None
    if root and media.get('id')==root.get('id'):return 1
    graph={m['id']:m for m in [*(catalog or []),*( [root] if root else []),media] if m and m.get('id')}
    cursor=media;distance=0;seen=set()
    while cursor.get('id') not in seen and distance<30:
        seen.add(cursor.get('id'))
        # A later cour/part can share a season; don't invent a new S-number.
        if any(re.search(r'\b(?:part|cour)\s*(?:\d+|II|III)\b',t or '',re.I) for t in (cursor.get('title') or {}).values()):return None
        parents=[e.get('node') or {} for e in (cursor.get('relations') or {}).get('edges',[]) if e.get('relationType')=='PREQUEL' and (e.get('node') or {}).get('format') in ('TV','TV_SHORT','ONA')]
        if len(parents)!=1 or parents[0].get('id') not in graph:return None
        cursor=graph[parents[0]['id']];distance+=1
        numbers={n for t in (cursor.get('title') or {}).values() if (n:=explicit_number(t)) is not None}
        if len(numbers)==1:return next(iter(numbers))+distance
        if root and cursor['id']==root['id']:return 1+distance
    return None


def repair_metadata_numbers(fid):
    """Fix only unowned catalogue labels. Local files and manual choices win."""
    series=db.get_series(fid)
    if not series:return 0
    seasons=db.get_series_seasons(fid)
    root={'id':series.get('anilist_id'),'title':{'english':series['display_title']}}
    try:cache=list(json.loads(db.get_state('series_relation_cache','{}')).values())
    except (ValueError,TypeError):cache=[]
    changed=0
    with closing(db.get_connection()) as conn,conn:
        conn.execute('BEGIN IMMEDIATE')
        for previous in seasons:
            current=conn.execute('SELECT * FROM seasons WHERE id=?',(previous['id'],)).fetchone()
            if not current:continue
            season=dict(current)
            if season.get('relation_type')!='SEASON' or season.get('season_folder_path') or json.loads(season.get('video_files_json') or '[]') or season.get('storage_state')=='ON_DISK':continue
            override=conn.execute('SELECT value FROM app_state WHERE key=?',('season_number_override:'+str(season['id']),)).fetchone()
            if override:continue
            media=next((m for m in cache if m.get('id')==season.get('anilist_id')),dict(id=season.get('anilist_id'),title={'english':season['title_display']}))
            media={**media,'title':{**(media.get('title') or {}),'library_release':season['title_display']}}
            number=infer(media,root,cache)
            if number and number!=season.get('season_number'):
                conn.execute('UPDATE seasons SET season_number=? WHERE id=?',(number,season['id']));changed+=1
    return changed


def save_manual(fid,assignments,expected=None):
    rows={s['id']:s for s in db.get_series_seasons(fid) if s.get('relation_type')=='SEASON'}
    if set(assignments)!=set(rows):raise ValueError('The season list changed. Reopen season numbering.')
    if any(type(n) is not int or not 1<=n<=999 for n in assignments.values()):raise ValueError('Choose season numbers from 1 to 999.')
    with closing(db.get_connection()) as conn,conn:
        conn.execute('BEGIN IMMEDIATE')
        if expected is not None:
            current=[tuple(conn.execute('SELECT id,franchise_id,anilist_id,title_display,season_number FROM seasons WHERE id=?',(sid,)).fetchone() or ()) for sid in sorted(rows)]
            if current!=expected:raise ValueError('A release changed while editing. Reopen season numbering.')
        for sid,number in assignments.items():
            conn.execute('UPDATE seasons SET season_number=? WHERE id=?',(number,sid))
            conn.execute('INSERT INTO app_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('season_number_override:'+str(sid),str(number)))
