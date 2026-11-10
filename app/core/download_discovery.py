"""Conservative source results, local coverage and reviewed download plans."""
import json
import re
from pathlib import Path
from app import db
from app.core import downloads
from app.core.parser import extract_episode_numbers,normalize_for_matching
from app.core.match_evidence import base_title
from app.core.consolidation import explicit_season
from app.core.library_health import aired_boundary


def sources():
    try: saved=json.loads(db.get_state('downloads.sources','[]'))
    except (TypeError,ValueError): saved=[]
    current=downloads.settings()['source']
    if not any(row.get('url')==current for row in saved):
        from urllib.parse import urlsplit
        host=urlsplit(current).hostname or 'Selected source'
        saved.append(dict(name='Nyaa' if host=='nyaa.si' else host,url=current))
    return saved


def save_sources(rows):
    from app.core.chrome_bridge import origin
    values=[];seen=set()
    for row in rows:
        name=str(row.get('name','')).strip()[:80];url=str(row.get('url','')).strip()
        downloads.search_url(url,'test');origin(url)
        if not name or url in seen: raise ValueError('Each source needs a name and a unique search URL.')
        seen.add(url);values.append(dict(name=name,url=url))
    if not values or len(values)>20: raise ValueError('Keep between one and twenty sources.')
    db.set_state('downloads.sources',json.dumps(values))


def episode_key(continuous,season,episode,kind='EPISODE'):
    return f'{kind}:{"ABS" if continuous else "S"+str(season)}:{episode}'


def episode_label(key):
    try:kind,scope,number=key.split(':')
    except ValueError:return key
    label={'EPISODE':'Episode','MOVIE':'Movie','SPECIAL':'Special'}.get(kind,kind.title())+' '+number
    return label if scope=='ABS' else scope+' · '+label


def coverage_label(keys):
    if not keys:return 'Unknown'
    groups={}
    for key in keys:
        prefix,number=key.rsplit(':',1);groups.setdefault(prefix,[]).append(int(number))
    labels=[]
    for prefix,numbers in groups.items():
        values=sorted(set(numbers))
        if values==list(range(values[0],values[-1]+1)):
            labels.append(episode_label(prefix+':'+str(values[0]))+('–'+str(values[-1]) if len(values)>1 else ''))
        else:labels.extend(episode_label(prefix+':'+str(number)) for number in values[:12])
    return ', '.join(labels)


def library_context(fid,season=None):
    series=db.get_series(fid)
    if not series: raise ValueError('This anime is no longer in the library.')
    seasons=db.get_series_seasons(fid)
    continuous=db.uses_continuous_episodes(series) or series.get('anilist_id')==21
    main=[s for s in seasons if s.get('relation_type')=='SEASON']
    numbers={s.get('season_number') for s in main if s.get('season_number')}
    if not continuous and season is None and len(numbers)==1: season=next(iter(numbers))
    selected=[s for s in main if continuous or season is None or s.get('season_number')==season]
    aliases=[]
    for record in [series,*selected]:
        for key in ('display_title','title_en','title_romaji','title_native','title_display'):
            if record.get(key) and record[key] not in aliases: aliases.append(record[key])
        try:
            media=json.loads(record.get('metadata_json') or '{}')
            for value in list((media.get('title') or {}).values())+(media.get('synonyms') or []):
                if value and value not in aliases: aliases.append(value)
        except (TypeError,ValueError): pass
    jobs=downloads.jobs()
    from app.core.download_queue import status as queue_status
    owners={series['id'],fid,*[s['franchise_id'] for s in seasons]}
    active_roots=[Path(job['destination']).resolve() for job in jobs if job['fid'] in owners and
                  queue_status(job) in ('Queued','Downloading','Paused') and not job.get('indexed')]
    available={};observed=set();expected=set();unavailable=0;boundaries={}
    for s in selected:
        for name in json.loads(s.get('video_files_json') or '[]'):
            path=Path(s.get('season_folder_path') or '')/name
            ep_numbers=extract_episode_numbers(name)
            file_season=explicit_season(Path(name).stem) or s.get('season_number')
            if continuous and explicit_season(Path(name).stem) is not None:
                # Season-relative files in an absolute show need verified offsets.
                if s.get('episode_start') and s.get('numbering_source') in ('metadata','manual'):
                    ep_numbers=[s['episode_start']+ep-1 for ep in ep_numbers]
                else: continue
            if not continuous and season is not None and file_season!=season: continue
            for ep in ep_numbers:
                key=episode_key(continuous,file_season,ep)
                observed.add(key)
                if path.is_file() and not any(path.resolve().is_relative_to(root) for root in active_roots): available[key]=str(path)
                else: unavailable+=1
        boundary=aired_boundary(s)
        if boundary is not None:
            boundaries['ABS' if continuous else 'S'+str(s.get('season_number'))]=boundary
            start=s.get('episode_start') or 1
            expected.update(episode_key(continuous,s.get('season_number'),ep) for ep in range(start,min(boundary,9999)+1))
        elif s.get('anilist_id') and s.get('airing_status')=='FINISHED' and s.get('episodes_total') and not continuous:
            boundaries['S'+str(s.get('season_number'))]=s['episodes_total']
            expected.update(episode_key(False,s.get('season_number'),ep) for ep in range(1,min(s['episodes_total'],9999)+1))
    # No invented boundaries for unverified folders: only detected internal gaps.
    groups={}
    for key in observed:
        prefix,number=key.rsplit(':',1);groups.setdefault(prefix,set()).add(int(number))
    for prefix,values in groups.items():
        if values: expected.update(f'{prefix}:{ep}' for ep in range(min(values),max(values)+1))
    pending=set()
    for job in jobs:
        if job['fid'] not in {series['id'],fid,*[s['franchise_id'] for s in seasons]}: continue
        if queue_status(job) in ('Stopped','Failed','Completed','Incomplete or missing files'): continue
        if job.get('indexed') or job.get('status')=='Indexed': continue
        keys=job.get('episode_keys') or []
        if not keys and job.get('source_ref','').lower().startswith('magnet:?'):
            from app.core.magnet_capture import validate
            try:
                name=validate(job['source_ref'])['name'];numbers=extract_episode_numbers(name)
                chosen=explicit_season(name) or job.get('season')
                if continuous and explicit_season(name) is None:
                    keys=[episode_key(True,0,number) for number in numbers]
                elif not continuous and chosen:
                    keys=[episode_key(False,chosen,number) for number in numbers]
            except ValueError:pass
        pending.update(keys)
    return dict(fid=fid,title=series['display_title'],aliases=aliases,continuous=continuous,season=season,
                local=available,expected=sorted(expected),pending=sorted(pending),missing=sorted(expected-set(available)-pending),
                unavailable=unavailable,seasons=selected,boundaries=boundaries)


def classify(entry,context):
    title=entry['title']
    import unicodedata
    def title_key(value):
        value=re.sub(r'\.(?:mkv|mp4|avi|webm|m4v|ts|mov)$','',value,flags=re.I)
        return ''.join(c.casefold() for c in unicodedata.normalize('NFKC',base_title(value)) if c.isalnum())
    clean=title_key(title)
    aliases=[title_key(alias) for alias in context['aliases']]
    title_ok=bool(clean) and clean in aliases
    season=explicit_season(title)
    numbers=extract_episode_numbers(title)
    if not numbers:
        match=re.search(r'\[(\d{1,4})\s*[-–]\s*(\d{1,4})\]',title)
        if match and 0<int(match[1])<=int(match[2])<10000:
            numbers=list(range(int(match[1]),int(match[2])+1))
    special=bool(re.search(r'\b(?:movie|film|ova|special|SP\d+)\b',title,re.I))
    reasons=[]
    if not title_ok: reasons.append('Title needs confirmation')
    if special: reasons.append('Movie/special mapping needs confirmation')
    if not numbers: reasons.append('Episode coverage is not explicit')
    if context['continuous'] and season is not None: reasons.append('Season-relative numbering in an absolute series')
    if not context['continuous']:
        if context['season'] is None: reasons.append('Choose the release/season first')
        elif season is not None and season!=context['season']: reasons.append('Season differs from the selected release')
        elif season is None and (context['season'] or 1)>1: reasons.append('Later season is not explicit')
    boundary=context.get('boundaries',{}).get('ABS' if context['continuous'] else 'S'+str(season or context['season']))
    if boundary is not None and any(n>boundary for n in numbers): reasons.append('Episode is beyond the verified aired boundary; confirm its release')
    keys=[episode_key(context['continuous'],season or context['season'],ep) for ep in numbers] if not reasons else []
    local=set(context['local']);queued=set(context['pending'])
    if reasons: status='Match Uncertain'
    elif set(keys)<=local: status='In Library'
    elif set(keys)<=local|queued: status='Downloading or Queued'
    else: status='Missing — Release Found'
    return {**entry,'episode_keys':keys,'episodes':numbers,'season':season or context['season'],
            'status':status,'reason':'; '.join(reasons),'in_library':sorted(set(keys)&local),
            'already_queued':sorted(set(keys)&queued),'match_confirmed':False}


def availability_rows(context,results):
    found={key for entry in results for key in entry.get('episode_keys',[])}
    return [dict(episode=key,status='In Library' if key in context['local'] else
                 'Downloading or Queued' if key in context['pending'] else
                 'Missing — Release Found' if key in found else 'Missing — No Release Found')
            for key in sorted(set(context['expected'])|set(context['local'])|found|set(context['pending']))]


def search(fid,season,source,query,cancelled=lambda:False,alternative_queries=()):
    from app.core import source_bridge
    context=library_context(fid,season)
    queries=list(dict.fromkeys([query,*alternative_queries]))[:4]
    # Alternative titles are fallback queries, with the same saved group/quality.
    if not query.strip():
        config=downloads.settings()
        queries=[downloads.make_query(alias,f'S{season:02}' if season and season>1 and not context['continuous'] else '',config['group'],config['quality']) for alias in context['aliases'][:3]]
    results=[];tried=[]
    for candidate in queries:
        if cancelled():raise InterruptedError('Search cancelled.')
        tried.append(candidate)
        request=source_bridge.enqueue(downloads.search_url(source['url'],candidate),source['name'])
        results=source_bridge.wait(request,cancelled)
        if results: break
    return dict(context=context,results=[classify(entry,context) for entry in results],query_used=tried[-1] if tried else '',queries_tried=tried)


def missing_plan(context,results):
    remaining=set(context['missing']);chosen=[]
    for entry in sorted(results,key=lambda row:row.get('seeders') or -1,reverse=True):
        keys=set(entry.get('episode_keys',[]))
        if entry['status']=='Match Uncertain' or not keys or keys&set(context['local']) or keys&set(context['pending']): continue
        if keys&remaining:
            chosen.append(entry);remaining-=keys
    return chosen,sorted(remaining)


def submit(fid,entries):
    """Revalidate coverage immediately before the existing durable submission."""
    added=[];coverage=set();identities=set()
    from app.core.magnet_capture import validate
    for entry in entries:
        keys=set(entry.get('episode_keys') or [])
        identity=validate(entry['magnet'])['identity']
        if coverage&keys or identity in identities: raise ValueError('Selected releases overlap. Choose one release per episode before adding them.')
        coverage.update(keys);identities.add(identity)
        context=library_context(fid,entry.get('season'))
        if keys&set(context['pending']): raise ValueError('Some selected episodes are already queued. Refresh the search before adding them.')
    for entry in entries:
        if not entry.get('episode_keys'): raise ValueError('Confirm episode/season coverage before adding this release.')
        context=library_context(fid,entry.get('season'))
        duplicates=set(entry['episode_keys'])&set(context['pending'])
        if duplicates: raise ValueError('Episodes are already queued: '+', '.join(sorted(duplicates)))
        if set(entry['episode_keys'])<=set(context['local']): raise ValueError('All selected episodes are already in the library.')
        destination=downloads.add_download(fid,entry['magnet'],entry.get('season') or 0,
            context={key:entry.get(key) for key in ('title','episode_keys','source','quality','group','season')})
        added.append(destination)
    return added
