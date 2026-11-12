"""On-demand, cached release discovery; no startup network requests."""
import json
import time
from datetime import datetime, timedelta
from app import db
from app.core import anilist_client as api

FIELDS = '''id idMal title { english romaji native } description(asHtml:false)
genres isAdult format status episodes seasonYear startDate { year month day }
coverImage { large medium } bannerImage nextAiringEpisode { episode airingAt }'''

GENRES = ('Action', 'Adventure', 'Comedy', 'Drama', 'Ecchi', 'Fantasy', 'Hentai',
          'Horror', 'Mahou Shoujo', 'Mecha', 'Music', 'Mystery', 'Psychological',
          'Romance', 'Sci-Fi', 'Slice of Life', 'Sports', 'Supernatural', 'Thriller')
THEMES = ('Isekai', 'Reincarnation', 'Time Manipulation', 'School', 'Vampire', 'Military')
FORMATS = ('TV', 'TV_SHORT', 'MOVIE', 'SPECIAL', 'OVA', 'ONA', 'MUSIC')

class CacheMiss(ValueError):
    """This release query has not been saved yet; no request was made."""


def _saved(key):
    try:
        value=json.loads(db.get_state('release_news:'+key,'null'))
        if isinstance(value,dict) and isinstance(value.get('data'),dict) and isinstance(value.get('time'),(int,float)):
            return value
    except (ValueError,TypeError):
        pass
    return None


def cached(key, query, variables, force=False, *, cache_only=False, info=None, fallback=False):
    # Issue: Corrupted cache JSON could crash before querying, and failed calls
    # masked the underlying AniList/HTTP error with a fixed generic message.
    # Fix: Tolerate invalid cached payloads and surface api.last_error() (or
    # offline mode) while keeping valid cached entries untouched on failure.
    saved=_saved(key)
    if saved and not force:
        if info is not None:info.update(source='cache',saved_at=saved['time'])
        return saved['data']
    if cache_only and not force:
        raise CacheMiss('No saved results for these filters yet. Click Check updates to fetch and save them.')
    data=api._graphql_request(query,variables)
    if not data:
        reason=api.last_error() if hasattr(api,'last_error') else None
        if not reason:
            from app import config
            if getattr(config,'OFFLINE_MODE',False):reason='Offline Mode is enabled'
        detail=f' ({reason})' if reason else ''
        message=f'Could not check AniList{detail}.'
        if saved and fallback:
            if info is not None:info.update(source='cache',saved_at=saved['time'],warning=message+' Showing your saved results.')
            return saved['data']
        raise ValueError(message+(' Saved results are kept.' if saved else ' No saved results are available yet.')+' Try Check updates again later.')
    stamp=time.time()
    db.set_state('release_news:'+key,json.dumps({'time':stamp,'data':data}))
    if info is not None:info.update(source='network',saved_at=stamp)
    return data


def _migrate_discovery_cache(key,upcoming,page,announced,sort,filters):
    """Keep pre-existing date-keyed results usable after a restart/day change."""
    if _saved(key):return
    from contextlib import closing
    suffix=f':{upcoming}:{page}:{announced}:{sort}:{filters}'
    legacy_suffix=f':{upcoming}:{page}:{announced}:{sort}'
    unfiltered=json.loads(filters)[:3]==[None,None,None]
    with closing(db.get_connection()) as connection:
        rows=connection.execute("SELECT key,value FROM app_state WHERE key LIKE 'release_news:discover:%'").fetchall()
    matches=[]
    for row in rows:
        if row['key'].endswith(suffix) or (unfiltered and row['key'].endswith(legacy_suffix)):
            try:
                saved=json.loads(row['value'])
                if isinstance(saved.get('data'),dict) and isinstance(saved.get('time'),(int,float)):matches.append(saved)
            except (ValueError,TypeError,AttributeError):pass
    if matches:db.set_state('release_news:'+key,json.dumps(max(matches,key=lambda value:value['time'])))

def discover(upcoming=False,page=1,force=False,announced=False,sort='START_DATE',
             genre=None,theme=None,media_format=None,include_adult=None,cache_info=None):
    from app.preferences import enabled
    allow_adult = enabled('allow_mature') and include_adult is not False
    def choices(value,allowed):
        if isinstance(value,str):return value if value in allowed else None
        if isinstance(value,(tuple,list)):
            values=tuple(item for item in allowed if item in value)
            return values[0] if len(values)==1 else values or None
        return None
    genre=choices(genre,GENRES);theme=choices(theme,THEMES);media_format=choices(media_format,FORMATS)
    today=datetime.now().date()
    lower=today if upcoming else today-timedelta(days=30)
    upper=today+timedelta(days=90) if upcoming else today+timedelta(days=1)
    # Issue: AniList Page.media startDate_greater / startDate_lesser require the
    # FuzzyDateInt scalar, not Int, causing HTTP 400 Bad Request on every live
    # check; additionally int(strftime('%Y%m%d')) - 1 produced invalid day 00 on
    # the 1st of a month.
    # Fix: Declare $from/$to as FuzzyDateInt and compute (lower - 1 day) properly.
    query='''query($from:FuzzyDateInt,$to:FuzzyDateInt,$page:Int){Page(page:$page,perPage:20){pageInfo{hasNextPage}
    media(type:ANIME,startDate_greater:$from,startDate_lesser:$to,sort:START_DATE){'''+FIELDS+'''}}}'''
    previous_day=lower-timedelta(days=1)
    sort=sort if sort in ('START_DATE','START_DATE_DESC','TITLE_ENGLISH','POPULARITY_DESC') else 'START_DATE'
    query=query.replace('sort:START_DATE','sort:'+sort)
    variables={'from':int(previous_day.strftime('%Y%m%d')),'to':int(upper.strftime('%Y%m%d')),'page':page}
    if announced:
        query='''query($page:Int){Page(page:$page,perPage:20){pageInfo{hasNextPage} media(type:ANIME,status:NOT_YET_RELEASED,sort:'''+sort+'''){'''+FIELDS+'''}}}'''
        variables={'page':page}
    # Filter at AniList, before pagination, rather than hiding most of a page.
    declarations='$genre:String,$tag:String,$format:MediaFormat,$adult:Boolean'
    query=query.replace('query(', 'query('+declarations+',', 1)
    query=query.replace('media(type:ANIME,', 'media(type:ANIME,genre:$genre,tag:$tag,format:$format,isAdult:$adult,', 1)
    variables.update(genre=genre,tag=theme,format=media_format,adult=None if allow_adult else False)
    for variable,value,scalar,argument in (('genre',genre,'String','genre'),('tag',theme,'String','tag'),('format',media_format,'MediaFormat','format')):
        if value is None:
            # AniList interprets format:null as an active filter, which can
            # return zero recent releases. Unselected filters must be absent.
            query=query.replace(f'${variable}:{scalar},','').replace(f'{argument}:${variable},','')
            variables.pop(variable,None)
            continue
        if isinstance(value,tuple):
            query=query.replace(f'${variable}:{scalar}',f'${variable}:[{scalar}]').replace(f'{argument}:${variable}',f'{argument}_in:${variable}')
            variables[variable]=list(value)
    if allow_adult:
        query=query.replace('$adult:Boolean,','').replace('isAdult:$adult,','');variables.pop('adult',None)
    filters=json.dumps([genre,theme,media_format,allow_adult],separators=(',',':'))
    key=f'discover:v2:{upcoming}:{page}:{announced}:{sort}:{filters}'
    _migrate_discovery_cache(key,upcoming,page,announced,sort,filters)
    data=cached(key,query,variables,force,cache_only=not force,info=cache_info,fallback=True)
    result=(data.get('Page') or {}) if isinstance(data,dict) else {}
    media=result.get('media') or []
    has_next=bool((result.get('pageInfo') or {}).get('hasNextPage'))
    return [m for m in media if isinstance(m,dict) and (allow_adult or not m.get('isAdult'))],has_next

def timeline(media_id,page=1,force=False,cache_info=None):
    query='''query($id:Int,$page:Int){Media(id:$id,type:ANIME){'''+FIELDS+'''
    relations{edges{relationType node{id type title{english romaji native} status startDate{year month day}}}}}
    Page(page:$page,perPage:50){pageInfo{hasNextPage} airingSchedules(mediaId:$id,sort:EPISODE){episode airingAt}}}'''
    # Opening a specific release is an explicit request for that anime's details.
    # Fetch a missing timeline once; reuse it on later visits until refreshed.
    return cached(f'timeline:{media_id}:{page}',query,{'id':media_id,'page':page},force,info=cache_info,fallback=True)

def import_watching(media):
    # Existing library data and manually matched releases must remain intact.
    existing=db.get_franchise_by_anilist_id(media['id'])
    if existing:return existing['id'],False
    data=api.extract_franchise_data(media);data.update(watch_status='WATCHING',storage_state='NOT_DOWNLOADED')
    fid=db.upsert_franchise(data)
    db.upsert_season(api.extract_season_data(media,fid))
    db.publish_updates(fid,'Added to Watching — '+('Announced (Not Yet Released)' if media.get('status')=='NOT_YET_RELEASED' else 'Release available (Not in Library)'))
    return fid,True

def date_label(value):
    value=value or {}
    return '-'.join(str(value[k]).zfill(4 if k=='year' else 2) if value.get(k) else ('????' if k=='year' else '??') for k in ('year','month','day'))
