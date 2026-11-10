"""Preview/confirm manual grouping without changing file or record ownership."""
import json
import hashlib
from contextlib import closing
from app import db


def fingerprint(conn):
    rows=[tuple(row) for row in conn.execute('SELECT id,anilist_id,display_title,metadata_json FROM franchises ORDER BY id')]
    links=conn.execute("SELECT value FROM app_state WHERE key='series_overrides'").fetchone()
    return hashlib.sha256(json.dumps([rows,links[0] if links else '{}'],ensure_ascii=False).encode()).hexdigest()


def preview(source_id,target_id,additional=()):
    groups=db.get_series_library()
    def locate(fid):
        found=next((g for g in groups if fid in g['series_member_ids']),None)
        if not found:raise ValueError('A selected entry changed or was removed. Search again.')
        return found
    source=locate(source_id);target=locate(target_id)
    if source['id']==target['id']:raise ValueError('Choose a different series as the main card.')
    selected={group['id']:group for group in [source,target,*[locate(fid) for fid in additional]]}
    ids=sorted({fid for group in selected.values() for fid in group['series_member_ids']})
    records=[db.get_franchise(fid) for fid in ids]
    with closing(db.get_connection()) as conn:version=fingerprint(conn)
    return dict(source=source_id,target=target['id'],additional=list(additional),ids=ids,records=records,
                title=target['display_title'],fingerprint=version)


def apply(previewed):
    current=preview(previewed['source'],previewed['target'],previewed['additional'])
    if current['ids']!=previewed['ids'] or current['fingerprint']!=previewed['fingerprint']:
        raise ValueError('The library changed after review. Review the grouping again.')
    with closing(db.get_connection()) as conn,conn:
        conn.execute('BEGIN IMMEDIATE')
        if fingerprint(conn)!=previewed['fingerprint']:raise ValueError('The library changed. Review again.')
        row=conn.execute("SELECT value FROM app_state WHERE key='series_overrides'").fetchone()
        links=json.loads(row[0]) if row else {}
        target=previewed['target'];links.pop(str(target),None)
        for fid in previewed['ids']:
            if fid!=target:links[str(fid)]=target
            record=conn.execute('SELECT anilist_id,metadata_json FROM franchises WHERE id=?',(fid,)).fetchone()
            try:media=json.loads(record['metadata_json'] or '{}')
            except (TypeError,ValueError):media={}
            if (record['anilist_id'] and isinstance(media,dict) and media.get('status')=='NOT_YET_RELEASED'
                    and not conn.execute('SELECT id FROM seasons WHERE franchise_id=? OR anilist_id=? LIMIT 1',(fid,record['anilist_id'])).fetchone()):
                # A future metadata-only member needs a visible catalogue row,
                # never an invented local inventory or missing-download count.
                from app.core.season_numbering import infer
                title=(media.get('title') or {}).get('english') or (media.get('title') or {}).get('romaji') or 'Announced release'
                kind='MOVIE' if media.get('format')=='MOVIE' else 'SPECIAL' if media.get('format') in ('SPECIAL','OVA') else 'SEASON'
                parent=conn.execute('SELECT anilist_id FROM franchises WHERE id=?',(target,)).fetchone()
                number=infer(media,{'id':parent[0]}) or 0 if kind=='SEASON' else 0
                conn.execute("INSERT INTO seasons(franchise_id,anilist_id,season_number,relation_type,title_display,airing_status,episodes_total,storage_state) VALUES(?,?,?,?,?,'NOT_YET_RELEASED',?,'NOT_DOWNLOADED')",
                    (fid,record['anilist_id'],number,kind,title,media.get('episodes')))
        conn.execute("INSERT INTO app_state(key,value) VALUES('series_overrides',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(json.dumps(links),))
    return target


def release_status(value):
    return {'NOT_YET_RELEASED':'Announced · Not released','RELEASING':'Airing',
            'FINISHED':'Finished','CANCELLED':'Cancelled','HIATUS':'On hiatus'}.get(value,'Release status unknown')
