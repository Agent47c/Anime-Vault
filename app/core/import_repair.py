"""Conservative repair of list-generated titles; never delete records or media."""
import json
from contextlib import closing
from pathlib import Path
from app import db
from app.core.parser import parse_txt_line, clean_title
from app.core.text_import import ImportIndex, read_text_list


def plan(source_paths=()):
    originals=db.get_all_franchises()
    rows=[dict(row) for row in originals]
    recovered={}
    for path in source_paths:
        path=Path(path)
        # Older imports decoded Windows ANSI as UTF-8 with replacement. Recover
        # only an exact original-line correspondence, never a guessed title.
        lines=read_text_list(path)
        legacy=path.read_bytes().decode('utf-8',errors='replace').splitlines()
        if len(lines)==len(legacy):
            for before,after in zip(legacy,lines):recovered.setdefault(before.strip(),set()).add(after.strip())
    updates=[]
    for row in rows:
        raw=row.get('raw_import_name') or ''
        if not raw or row.get('anilist_id') or row.get('display_title') not in (raw.strip(),clean_title(raw)):continue
        choices=recovered.get(raw.strip(),set())
        source=next(iter(choices)) if len(choices)==1 else raw
        parsed=parse_txt_line(source)
        if not parsed or '\ufffd' in parsed['title']:continue
        changes={}
        for field in ('display_title','title_en','title_romaji','title_native'):
            if row.get(field) and row[field] in (raw.strip(),clean_title(raw)) and row[field]!=parsed['title']:
                changes[field]=parsed['title']
        if source!=raw:changes['raw_import_name']=source
        if changes:
            updates.append(dict(id=row['id'],before={key:row.get(key) for key in changes},changes=changes))
            row.update(changes)
    index=ImportIndex(rows,collapse_groups=False)
    overrides=json.loads(db.get_state('series_overrides','{}'))
    parents={row['id']:row['id'] for row in rows}
    def root(fid):
        while parents[fid]!=fid:fid=parents[fid]
        return fid
    ambiguous=[]
    for row in rows:
        if not row.get('raw_import_name'):continue
        matches=index.matches(row['display_title'])
        if len(matches)<2:continue
        if len({r['anilist_id'] for r in matches if r.get('anilist_id')})>1:
            ambiguous.append(row['id']);continue
        # A previous explicit grouping decision has priority over this repair.
        if any(str(r['id']) in overrides or r['id'] in overrides.values() for r in matches):continue
        for match in matches:parents[root(match['id'])]=root(row['id'])
    buckets={}
    byid={row['id']:row for row in rows}
    for fid in parents:buckets.setdefault(root(fid),[]).append(fid)
    groups=[]
    for ids in buckets.values():
        if len(ids)<2:continue
        if len({byid[fid]['anilist_id'] for fid in ids if byid[fid].get('anilist_id')})>1:
            ambiguous.extend(ids);continue
        # Provider/on-disk entry is the visible representative. All other IDs,
        # paths, notes, ratings and watch history continue to exist unchanged.
        target=min(ids,key=lambda fid:(not bool(byid[fid].get('anilist_id')),not bool(byid[fid].get('root_folder_path')),fid))
        members=[fid for fid in ids if fid!=target]
        groups.append(dict(target=target,members=members,title=byid[target]['display_title']))
    return dict(updates=updates,groups=groups,ambiguous=sorted(set(ambiguous)),snapshot=originals,overrides=overrides)


def apply_repair(preview):
    if not preview['updates'] and not preview['groups']:return dict(renamed=0,grouped=0,backup=None)
    backup=db.backup_database()
    with closing(db.get_connection()) as conn,conn:
        conn.execute('BEGIN IMMEDIATE')
        current=[dict(row) for row in conn.execute('SELECT * FROM franchises ORDER BY id')]
        expected=sorted(preview['snapshot'],key=lambda row:row['id'])
        saved=conn.execute("SELECT value FROM app_state WHERE key='series_overrides'").fetchone()
        overrides=json.loads(saved[0]) if saved else {}
        if current!=expected or overrides!=preview['overrides']:
            raise ValueError('Library changed after preview. Generate a fresh repair plan.')
        for update in preview['updates']:
            changes=update['changes']
            conn.execute('UPDATE franchises SET '+','.join(key+'=?' for key in changes)+' WHERE id=?',(*changes.values(),update['id']))
        for group in preview['groups']:
            for fid in group['members']:overrides[str(fid)]=group['target']
        conn.execute("INSERT INTO app_state(key,value) VALUES('series_overrides',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(json.dumps(overrides),))
    return dict(renamed=len(preview['updates']),grouped=sum(len(g['members']) for g in preview['groups']),backup=backup)
