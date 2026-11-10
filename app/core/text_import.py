"""Shared watch-list decoding and conservative duplicate identity."""
from pathlib import Path
import unicodedata
import re
import json
from contextlib import closing
from app import db
from app.core.parser import parse_txt_line, clean_title


def clean_import_name(value):
    """Remove packaging text without erasing remake years or season identity."""
    text=value.strip()
    text=re.sub(r'\.(?:mkv|mp4|avi)$','',text,flags=re.I)
    text=re.sub(r'^\[(?:ASW|EMBER|Judas|AnimeRG|Anime Time|AnimeTime|Kayoanime|SubsPlease|Erai-raws)\]\s*','',text,flags=re.I)
    technical=r'(?:(?:480|720|1080|1440|2160)p|HEVC|x26[45]|AAC|FLAC|10[- ]?bits?|8[- ]?bits?|Dual[- ]Audio|Multi[- ]Sub|WEBRip|WEB-DL|BDRip)'
    def bracket(match):
        body=match.group(1)
        tag=r'(?:'+technical+r'|480|720|1080|1440|2160|Batch|pseudo)'
        return '' if re.search(r'(?i)\b'+tag+r'\b',body) else match.group(0)
    text=re.sub(r'\[([^\]]+)\]',bracket,text)
    text=re.sub(r'\((?:Complete(?: Series)?|Batch)\)','',text,flags=re.I)
    text=re.sub(r'\b(?:Complete Series|All Seasons)\b','',text,flags=re.I)
    text=re.sub(r'\bEP(?:ISODES?)?\s*\d{1,4}\s*[-–]\s*\d{1,4}\b','',text,flags=re.I)
    text=re.sub(r'\b'+technical+r'\b','',text,flags=re.I)
    if re.search(r'(?i)\b(?:x26[45]|\d{3,4}p|BDRip|WEBRip)\b',value):text=re.sub(r'\bDD\b','',text)
    text=re.sub(r'\s*-\s*(?:EMBER|ASW|Judas)\s*$','',text,flags=re.I)
    # A release's episode suffix is not part of a watch-list series title.
    text=re.sub(r'\s+-\s+\d{1,4}(?:v\d+)?\s*$','',text,flags=re.I)
    text=re.sub(r'\s+',' ',text).strip(' -–')
    return text or value.strip()


def read_text_list(path):
    path=Path(path)
    if path.stat().st_size>4*1024*1024:raise ValueError('Text list exceeds 4 MB.')
    raw=path.read_bytes()
    if raw.startswith((b'\xff\xfe',b'\xfe\xff')):return raw.decode('utf-16').splitlines()
    try:return raw.decode('utf-8-sig').splitlines()
    except UnicodeDecodeError:
        try:return raw.decode('cp1252').splitlines()
        except UnicodeDecodeError as error:raise ValueError('Save this text file as UTF-8 or UTF-16 and import it again.') from error


def title_key(value):
    """Ignore case/punctuation/spacing, but retain Unicode and season numbers."""
    import re
    normalized=unicodedata.normalize('NFKC',value or '').casefold()
    # Seasons 1–2 and 1 & 2 can be equivalent; neither is Season 12.
    normalized=re.sub(r'(?<=\d)[\W_]+(?=\d)', '|', normalized)
    return ''.join(c for c in normalized if c.isalnum() or c=='|')


class ImportIndex:
    def __init__(self,records=None,collapse_groups=True):
        import json
        self.records={};self.titles={};self.providers={}
        self.overrides=json.loads(db.get_state('series_overrides','{}')) if collapse_groups else {}
        for row in records if records is not None else db.get_all_franchises():self.add(row)
        saved=json.loads(db.get_state('import_aliases','{}'))
        with closing(db.get_connection()) as conn:
            owners={row['id']:row['franchise_id'] for row in conn.execute('SELECT id,franchise_id FROM library_series')}
        for key,link in saved.items():
            row=self.records.get(link['fid'])
            if row and owners.get(link['series_id'])==row['id'] and row.get('anilist_id')==link.get('provider'):
                self.titles.setdefault(key,set()).add(row['id'])

    def add_alias(self,title,fid):
        key=title_key(clean_import_name(title))
        if key:self.titles.setdefault(key,set()).add(fid)

    def add(self,row):
        self.records[row['id']]=row
        aliases=[row.get(k) for k in ('display_title','title_en','title_romaji','title_native')]
        import json
        try:
            media=json.loads(row.get('metadata_json') or '{}')
            if not isinstance(media,dict):media={}
            aliases.extend((media.get('title') or {}).values());aliases.extend(media.get('synonyms') or [])
        except (ValueError,TypeError):pass
        raw=row.get('raw_import_name')
        if raw and row.get('display_title') in (raw.strip(),clean_title(raw)):
            parsed=parse_txt_line(raw)
            if parsed:aliases.append(parsed['title'])
        for alias in aliases:
            for candidate in (alias,clean_import_name(alias) if alias else None):
                key=title_key(candidate)
                if key:self.titles.setdefault(key,set()).add(row['id'])
        if row.get('anilist_id'):self.providers.setdefault(row['anilist_id'],set()).add(row['id'])

    def matches(self,*titles,provider=None):
        ids=self.providers.get(provider,set()) if provider else set()
        if not ids:
            ids=set().union(*(self.titles.get(title_key(clean_import_name(title) if title else ''),set()) for title in titles))
        def root(fid):
            seen=set()
            while str(fid) in self.overrides and fid not in seen:
                seen.add(fid);fid=int(self.overrides[str(fid)])
            return fid
        roots={root(fid) for fid in ids}
        if len(ids)>1 and len(roots)==1:
            representative=next(iter(roots))
            if representative in self.records:return [self.records[representative]]
        return [self.records[fid] for fid in sorted(ids)]


def remember_import_alias(fid,title):
    """Keep a confirmed source name after the provider changes its display title."""
    key=title_key(clean_import_name(title))
    if not key:return
    with closing(db.get_connection()) as conn,conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT anilist_id FROM franchises WHERE id=?',(fid,)).fetchone()
        if not row:raise ValueError('Imported entry was removed. Reopen the list.')
        conn.execute('INSERT OR IGNORE INTO library_series(franchise_id) VALUES (?)',(fid,))
        series=conn.execute('SELECT id FROM library_series WHERE franchise_id=?',(fid,)).fetchone()[0]
        saved=conn.execute("SELECT value FROM app_state WHERE key='import_aliases'").fetchone()
        aliases=json.loads(saved[0]) if saved else {}
        aliases[key]=dict(fid=fid,series_id=series,provider=row[0])
        conn.execute("INSERT INTO app_state(key,value) VALUES('import_aliases',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(json.dumps(aliases),))
