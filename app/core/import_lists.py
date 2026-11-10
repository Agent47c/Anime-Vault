"""Opt-in local TXT list subscriptions; never silently choose an API match."""
import hashlib
import json
from contextlib import closing
from pathlib import Path
from app import db
from app.core.parser import parse_txt_line
from app.core.text_import import read_text_list, ImportIndex


def lists(): return json.loads(db.get_state('import_lists','[]'))


def save(rows):
    if len(rows)>50: raise ValueError('Keep at most 50 import lists.')
    for row in rows:
        if not Path(row['path']).is_absolute() or Path(row['path']).suffix.lower()!='.txt':
            raise ValueError('Choose an absolute .txt file path.')
        if row.get('status','WATCHED') not in ('WATCHED','WATCHING','PLAN_TO_WATCH','DROPPED'): raise ValueError('Choose a valid watch status.')
    db.set_state('import_lists',json.dumps(rows))


def refresh(cancelled=lambda:False,force=False):
    rows=lists();added=0
    for row in rows:
        if cancelled(): break
        if not row.get('enabled'): continue
        path=Path(row['path'])
        try:
            if path.stat().st_size>4*1024*1024: raise ValueError('List exceeds 4 MB.')
            raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
            if digest==row.get('digest') and not force: continue
            row['error']=''
            index=ImportIndex()
            for line in read_text_list(path):
                if cancelled(): return added
                parsed=parse_txt_line(line)
                if not parsed: continue
                links=row.setdefault('links',{})
                link=links.get(parsed['title'].casefold())
                found=None
                if link:
                    with closing(db.get_connection()) as conn:
                        owner=conn.execute('SELECT franchise_id FROM library_series WHERE id=?',(link['series_id'],)).fetchone()
                    if not owner or owner[0]!=link['fid']:
                        row['error']='A linked title was removed or replaced. Review this list before reimporting it.'
                        continue
                    found=db.get_franchise(link['fid'])
                if found is None:
                    matches=index.matches(parsed['title'])
                    if len(matches)>1:
                        row['error']='Ambiguous titles need manual import review.';continue
                    if matches:found=matches[0]
                if found:
                    # Existing notes/corrections stay intact; only the chosen list status applies.
                    if found.get('watch_status')!=row.get('status','WATCHED'):
                        db.update_franchise_field(found['id'],'watch_status',row.get('status','WATCHED'));added+=1
                else:
                    fid=db.upsert_franchise(dict(display_title=parsed['title'],title_romaji=parsed['title'],
                        raw_import_name=parsed['title'],user_notes=parsed.get('notes',''),needs_review=1,
                        is_custom=1,storage_state='NOT_DOWNLOADED',watch_status=row.get('status','WATCHED')))
                    added+=1
                    found=db.get_franchise(fid)
                    index.add(found)
                with closing(db.get_connection()) as conn,conn:
                    conn.execute('INSERT OR IGNORE INTO library_series(franchise_id) VALUES (?)',(found['id'],))
                    series_id=conn.execute('SELECT id FROM library_series WHERE franchise_id=?',(found['id'],)).fetchone()[0]
                links[parsed['title'].casefold()]=dict(fid=found['id'],series_id=series_id)
            row.update(digest=digest,result='Imported safely; new unmatched names need review.')
        except (OSError,ValueError) as error: row['error']=str(error)
    current=lists()
    processed={row['path']:row for row in rows}
    for row in current:
        result=processed.get(row['path'])
        if result and row.get('enabled')==result.get('enabled') and row.get('status')==result.get('status'):
            for key in ('digest','error','result','links'):
                if key in result:row[key]=result[key]
    save(current)
    return added
