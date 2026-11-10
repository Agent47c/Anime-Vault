"""Compare source watch lists with the app, optionally add only absent names."""
from app import db
from app.core.parser import parse_txt_line
from app.core.text_import import read_text_list,clean_import_name,title_key,ImportIndex


def audit(paths):
    rows=[];index=ImportIndex()
    for path in paths:
        seen=set()
        for number,line in enumerate(read_text_list(path),1):
            parsed=parse_txt_line(line)
            if not parsed:continue
            title=clean_import_name(parsed['title']);key=title_key(title)
            matches=index.matches(title)
            rows.append(dict(file=str(path),line=number,original=line,title=title,notes=parsed['notes'],
                duplicate=key in seen,status='Already in library' if len(matches)==1 else 'Present — review match' if matches else 'Not in library',
                ids=[row['id'] for row in matches],provider_linked=any(row.get('anilist_id') for row in matches)))
            seen.add(key)
    return rows


def add_missing(rows,online=False):
    from app.core.import_preview import preview_lines
    from app.core.entry_service import apply_import
    seen=set();missing=[]
    for row in rows:
        key=title_key(row['title'])
        if not row['ids'] and key not in seen:seen.add(key);missing.append(row)
    if not missing:return dict(added=0,merged=0,backup=None)
    backup=db.backup_database()
    items=[]
    for row in missing:
        preview=next(preview_lines([row['title']],online=online),None)
        if preview is None:continue
        if preview.get('status') not in ('MATCHED','MERGED'):
            # Ensure the list is represented, without binding an uncertain guess.
            preview.update(anilist_media=None,matched_title=row['title'])
        preview.update(raw_line=row['original'],notes=row['notes'],enabled=True)
        items.append(preview)
    added,merged=apply_import(items,'WATCHED')
    return dict(added=added,merged=merged,backup=backup)
