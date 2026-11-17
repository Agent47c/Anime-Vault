"""Future downloads: confirmed library identity is independent of source names.

No migration: only jobs with assignment_version=1 use these bindings.
"""
import json
from contextlib import closing
from pathlib import Path
from app import db
from app.core import identity
from app.core.season_paths import season_folder_name


def release_context(fid, provider_id=None, title=None):
    seasons=[s for s in db.get_series_seasons(fid) if not (s.get('local_scan_key') or '').startswith('download:')]
    if provider_id is not None:seasons=[s for s in seasons if s.get('anilist_id')==provider_id]
    elif title:seasons=[s for s in seasons if title in (s.get('title_display'),s.get('title_romaji'))]
    if len(seasons)!=1:return {}
    season=seasons[0]
    return dict(local_season_id=season['id'],season=season.get('season_number'),kind='EPISODE' if season.get('relation_type')=='SEASON' else season.get('relation_type'))


def destination(fid, season,folder_override=None,canonical=True):
    from app.core import downloads
    from app.core.consolidation import explicit_season
    root = downloads.library_root()
    if not root or not Path(root).is_absolute():
        raise ValueError('Choose your main library destination in Organizer first.')
    root = Path(root).absolute()
    canonical_root=root.resolve()
    series = db.get_series(fid)
    if not series:
        raise ValueError('This anime is no longer in the library.')
    import re
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', series['display_title']).strip(' .')[:100] or 'Anime'
    staging = [Path(downloads.settings()['destination']).resolve()]
    staging += [Path(j['root']).resolve() for j in downloads.jobs() if j.get('root')]
    def valid(path):
        path=path.resolve()
        return path != canonical_root and path.is_relative_to(canonical_root) and not any(path == p or path.is_relative_to(p) for p in staging if p != canonical_root)
    existing = Path(series.get('root_folder_path') or root).absolute()
    anime = existing if valid(existing) else root / title
    folder = anime / (season_folder_name(season) if season else 'Episodes')
    candidates = [p for p in anime.iterdir() if p.is_dir() and explicit_season(p.name) == season] if season and anime.is_dir() else []
    explicit_candidates=bool(candidates)
    for s in db.get_series_seasons(fid):
        p = Path(s.get('season_folder_path') or root).absolute()
        if not explicit_candidates and s.get('season_number') == season and explicit_season(p.name) in (None,season) and p.resolve()!=anime.resolve() and p.resolve().is_relative_to(anime.resolve()) and valid(p) and p.is_dir():
            candidates.append(p)
    candidates = list({identity.path_key(p): p for p in candidates}.values())
    if len(candidates) > 1 and not folder_override and not canonical:
        raise ValueError(f'Multiple folders match season {season}. Review them in Organizer first.')
    if candidates and not canonical:
        folder = candidates[0]
    if folder_override:
        folder=Path(folder_override).absolute()
        if folder.resolve()==anime.resolve() or not folder.resolve().is_relative_to(anime.resolve()) or not valid(folder) or explicit_season(folder.name) not in (None,season):raise ValueError('Choose a folder for this season inside the anime’s library folder.')
        if canonical and season and explicit_season(folder.name)==season:
            folder=folder.with_name(season_folder_name(season))
    from app.core.download_library import _safe
    _safe(folder)
    return dict(root=str(root), anime=str(anime), folder=str(folder), create=not folder.is_dir())


def duplicate_files(fid, keys):
    """Resolve real copies, not just an episode count, before asking to replace."""
    from app.core.download_discovery import library_context
    result = {}
    for key in keys:
        _, scope, _ = key.split(':')
        context = library_context(fid, int(scope[1:]) if scope.startswith('S') else 0, continuous=scope == 'ABS')
        for candidate, path in context['local'].items():
            if candidate == key and Path(path).is_file():
                with closing(db.get_connection()) as conn:
                    linked=conn.execute('SELECT e.original_number,e.release_number,e.mapping_verified,r.release_key,r.kind,s.season_number FROM file_episodes fe JOIN file_locations l ON l.file_id=fe.file_id JOIN physical_files f ON f.id=l.file_id JOIN seasons s ON s.id=f.season_id JOIN episodes e ON e.id=fe.episode_id JOIN releases r ON r.id=e.release_id WHERE l.path_key=?',(identity.path_key(path),)).fetchall()
                from app.core.download_discovery import episode_key
                actual={episode_key(r['release_key']=='continuous',r['season_number'],r['release_number'] if r['mapping_verified'] else r['original_number'],'EPISODE' if r['kind']=='SEASON' else r['kind']) for r in linked}
                if actual-set(keys):
                    raise ValueError('The old file also contains other episodes. Choose Download another copy to keep those episodes safe.')
                result[identity.path_key(path)] = dict(path=path, signature=list(identity.signature(path)))
    return list(result.values())


def register(item, files):
    """Insert only new physical content using explicit logical episode mappings."""
    files=[Path(p).resolve() for p in files]
    base=Path(item['destination']).resolve()
    keys = item.get('episode_keys') or []
    # A single video can contain several episodes. Packs require explicit per-file
    # assignments; never infer a 177 -> 7 offset for unseen files.
    bindings = item.get('file_bindings') or {}
    if len(files)>1 and not bindings:
        from app.core.parser import extract_episode_numbers
        source=item.get('source_episodes') or []
        if len(source)==len(keys) and len(set(source))==len(source):
            confirmed=dict(zip(source,keys))
            for file in files:
                numbers=extract_episode_numbers(file.name)
                if numbers and all(n in confirmed for n in numbers):
                    bindings[str(file.relative_to(base))]=[confirmed[n] for n in numbers]
    if len(files) != 1 and not bindings:
        raise ValueError('This torrent contains multiple videos. Confirm each file’s episode assignment before indexing.')
    assignments = [(p, bindings.get(str(p.relative_to(base)))) for p in files] if bindings else [(files[0], keys)]
    if any(not ks for _, ks in assignments):
        raise ValueError('An episode assignment is required for every downloaded video.')
    if {k for _, ks in assignments for k in ks} != set(keys):
        raise ValueError('The file assignments differ from the confirmed episodes.')
    if sum(len(ks) for _,ks in assignments)!=len(keys):
        raise ValueError('Several videos cover the same episode. Review the file assignments.')
    with closing(db.get_connection()) as conn, conn:
        existing = [conn.execute('SELECT file_id FROM file_locations WHERE path_key=?', (identity.path_key(p),)).fetchone() for p, _ in assignments]
        if any(existing):
            if all(existing):
                saved=conn.execute('SELECT value FROM app_state WHERE key=?',('download.registered_files:'+item['id'],)).fetchone()
                if saved and set(json.loads(saved[0]))=={r[0] for r in existing}:return
            raise ValueError('Some downloaded files already have library identities. Review before indexing.')
        series = item['series_id']
        kind = keys[0].split(':')[0]
        number = item.get('season') or 0
        local = item.get('local_season_id')
        owner = conn.execute('SELECT s.*,r.release_key,r.id AS rid FROM seasons s LEFT JOIN season_releases sr ON sr.season_id=s.id LEFT JOIN releases r ON r.id=sr.release_id WHERE s.id=? AND (r.series_id=? OR (r.id IS NULL AND s.franchise_id=?))', (local, series,item['fid'])).fetchone() if local else None
        if owner and (owner['season_number'] != number or owner['relation_type'] != ('SEASON' if kind=='EPISODE' else kind) or (not item.get('continuous') and owner['release_key'] == 'continuous')):
            owner = None
        release_key = 'continuous' if item.get('continuous') and kind=='EPISODE' else f'local:{"SEASON" if kind == "EPISODE" else kind}:{number}'
        if owner:
            rid = owner['rid']
            if rid is None:
                selected_key='continuous' if item.get('continuous') and kind=='EPISODE' else f'provider:{owner["anilist_id"]}' if owner['anilist_id'] else release_key
                conn.execute('INSERT OR IGNORE INTO releases(series_id,release_key,provider_id,kind) VALUES (?,?,?,?)',(series,selected_key,owner['anilist_id'],'SEASON' if kind=='EPISODE' else kind))
                rid=conn.execute('SELECT id FROM releases WHERE series_id=? AND release_key=?',(series,selected_key)).fetchone()[0]
                conn.execute('INSERT INTO season_releases VALUES (?,?)',(owner['id'],rid))
        else:
            conn.execute('INSERT OR IGNORE INTO releases(series_id,release_key,kind) VALUES (?,?,?)', (series, release_key, 'SEASON' if kind == 'EPISODE' else kind))
            rid = conn.execute('SELECT id FROM releases WHERE series_id=? AND release_key=?', (series, release_key)).fetchone()[0]
        # Append future files to their selected logical season. Separate staging
        # folders do not create separate seasons. Legacy folders are never merged.
        canonical=owner or conn.execute("SELECT s.* FROM seasons s JOIN season_releases sr ON sr.season_id=s.id WHERE sr.release_id=? AND s.local_scan_key LIKE 'download:%' ORDER BY s.id LIMIT 1",(rid,)).fetchone()
        if canonical:
            sid=canonical['id'];folder=Path(canonical['season_folder_path'] or str(base))
            names=json.loads(canonical['video_files_json'] or '[]')
            for p in files:
                try:name=str(p.relative_to(folder.resolve()))
                except ValueError:name=str(p)
                names.append(name)
            conn.execute("UPDATE seasons SET season_folder_path=?,video_files_json=?,size_bytes=COALESCE(size_bytes,0)+?,storage_state='ON_DISK' WHERE id=?",(str(folder),json.dumps(names),sum(p.stat().st_size for p in files),sid))
        else:
            names = [str(p.relative_to(base)) for p in files]
            sid = conn.execute('INSERT INTO seasons(franchise_id,season_number,relation_type,title_display,season_folder_path,video_files_json,size_bytes,storage_state,numbering_source,local_scan_key) VALUES (?,?,?,?,?,?,?,?,?,?)',
                (item['fid'], number, 'SEASON' if kind == 'EPISODE' else kind, f'Season {number:02}' if number else 'Episodes', str(base), json.dumps(names), sum(p.stat().st_size for p in files), 'ON_DISK', 'manual', 'download:' + item['id'])).lastrowid
            conn.execute('INSERT INTO season_releases VALUES (?,?)', (sid, rid))
        source_numbers = item.get('source_episodes') or []
        registered=[]
        for path, assigned in assignments:
            sig = identity.signature(path)
            file_id = conn.execute("INSERT INTO physical_files(season_id,original_name,size_bytes,mtime_ns,device,inode,availability) VALUES (?,?,?,?,?,?,'AVAILABLE')", (sid, path.name, *sig)).lastrowid
            registered.append(file_id)
            conn.execute('INSERT INTO file_locations VALUES (?,?,?)', (file_id, str(path), identity.path_key(path)))
            for key in assigned:
                n = int(key.rsplit(':', 1)[1])
                original = source_numbers[keys.index(key)] if len(source_numbers) == len(keys) else n
                keyname=f'number:{n}'
                old=conn.execute('SELECT mapping_verified,release_number,mapping_source FROM episodes WHERE release_id=? AND identity_key=?',(rid,keyname)).fetchone()
                if old and (not old['mapping_verified'] or old['release_number']!=n or old['mapping_source']!='MANUAL'):keyname=f'confirmed:number:{n}'
                conn.execute("INSERT OR IGNORE INTO episodes(release_id,identity_key,original_number,numbering_scheme,release_number,mapping_verified,mapping_source) VALUES (?,?,?,?,?,1,'MANUAL')", (rid, keyname, original, 'ABSOLUTE' if item.get('continuous') else 'SEASON', n))
                eid = conn.execute('SELECT id FROM episodes WHERE release_id=? AND identity_key=?', (rid, keyname)).fetchone()[0]
                conn.execute('INSERT INTO file_episodes VALUES (?,?)', (file_id, eid))
        conn.execute('INSERT OR REPLACE INTO app_state VALUES (?,?)',('download.registered_files:'+item['id'],json.dumps(registered)))
        conn.execute('INSERT OR REPLACE INTO app_state VALUES (?,?)',('download.scoped_inventory:'+str(sid),'1'))
        conn.execute("UPDATE franchises SET storage_state='ON_DISK',total_size_bytes=(SELECT COALESCE(SUM(size_bytes),0) FROM seasons WHERE franchise_id=?) WHERE id=?", (item['fid'], item['fid']))


def settle_folder(job, folder):
    """Keep one logical season while its future files occupy several locations."""
    import os
    with closing(db.get_connection()) as conn,conn:
        row=conn.execute('SELECT value FROM app_state WHERE key=?',('download.registered_files:'+job['id'],)).fetchone()
        ids=json.loads(row[0]) if row else []
        if not ids:return
        seasons=conn.execute('SELECT DISTINCT season_id FROM physical_files WHERE id IN (%s)' % ','.join('?' for _ in ids),ids).fetchall()
        for record in seasons:
            season=conn.execute('SELECT * FROM seasons WHERE id=?',(record[0],)).fetchone()
            paths=[(Path(season['season_folder_path'])/n).resolve() for n in json.loads(season['video_files_json'] or '[]')]
            names=[]
            for path in paths:
                try:names.append(os.path.relpath(path,folder))
                except ValueError:names.append(str(path))
            conn.execute('UPDATE seasons SET season_folder_path=?,video_files_json=? WHERE id=?',(str(folder),json.dumps(names),record[0]))


def remember(job):
    """Keep learned mappings even when the user clears completed queue entries."""
    if job.get('assignment_version')!=1:return
    key=f'download.confirmed_history:{job["fid"]}'
    records=json.loads(db.get_state(key,'[]'))
    fields=('id','fid','created','assignment_version','season','continuous','episode_keys','source_episodes','local_season_id','release_title','title','group','source_name')
    record={k:job[k] for k in fields if k in job}
    records=[r for r in records if r.get('id')!=job['id']]
    if len({k.rsplit(':',1)[0] for k in job.get('episode_keys',[])})!=1:
        db.set_state(key,json.dumps(records));return
    records.append(record)
    db.set_state(key,json.dumps(records[-100:]))


def next_search(fid, media_id=None):
    from app.core import downloads
    from app.core.match_evidence import base_title
    jobs = [j for j in downloads.jobs() if j.get('fid') == fid and j.get('assignment_version') == 1 and j.get('episode_keys') and len({k.rsplit(':',1)[0] for k in j['episode_keys']})==1 and (j.get('desired') != 'cancelled' or j.get('library_moved'))]
    jobs += json.loads(db.get_state(f'download.confirmed_history:{fid}','[]'))
    if media_id:
        seasons = {s['id'] for s in db.get_series_seasons(fid) if s.get('anilist_id') == media_id}
        jobs = [j for j in jobs if j.get('local_season_id') in seasons]
    if not jobs:
        raise ValueError('Confirm a download for this release first so Auto-Grab can learn its season and numbering. Use Find Download Files.')
    last = max(jobs, key=lambda j: j.get('created', 0))
    if not last.get('source_episodes'):
        raise ValueError('The last confirmed download has no source episode number yet. Wait for its metadata/completion or search manually.')
    logical = max(int(k.rsplit(':', 1)[1]) for k in last['episode_keys']) + 1
    original = max(last.get('source_episodes') or [logical - 1]) + 1
    title = last.get('release_title') or last['title']
    import re
    token = re.search(r'\bS(\d{1,2})[ ._-]*E\d+', title, re.I)
    query = base_title(title)
    query += f' S{int(token[1]):02}E{original:02}' if token else f' {original:02}'
    encoder=re.match(r'^\[([^]]+)\]',title)
    group=last.get('group') or (encoder[1] if encoder else None)
    if group:
        query = f'[{group}] ' + query
    return dict(season=last.get('season'), continuous=last.get('continuous', False), local_season_id=last.get('local_season_id'), target_episode=logical, source_episode=original, query=query, source_name=last.get('source_name'))
