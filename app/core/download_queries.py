"""Visible, editable source queries with explicit language/title choices."""
import json
from app import db
from app.core import downloads
from app.core.season_numbering import explicit_number


def title_options(fid,season=None):
    series=db.get_series(fid)
    if not series:return []
    options=[];seen=set()
    def add(label,value):
        if value and value.casefold() not in seen:
            seen.add(value.casefold());options.append((label,value))
    def media_options(record,media,prefix=''):
        titles=media.get('title') or {}
        add(prefix+'English',record.get('title_en') or titles.get('english'))
        add(prefix+'Romaji',record.get('title_romaji') or titles.get('romaji'))
        add(prefix+'Japanese',record.get('title_native') or titles.get('native'))
    try:media=json.loads(series.get('metadata_json') or '{}')
    except (TypeError,ValueError):media={}
    if not isinstance(media,dict):media={}
    if season:
        cache=json.loads(db.get_state('series_relation_cache','{}'))
        for release in db.get_series_seasons(fid):
            if release.get('relation_type')=='SEASON' and release.get('season_number')==season:
                media_options(release,cache.get(str(release.get('anilist_id')),{ }),'Release · ')
                add('Release title',release.get('title_display'))
    media_options(series,media)
    add('Display title',series.get('display_title'))
    for value in (media.get('synonyms') or [])[:12]:add('Alternative title',value)
    return options


def default_query(fid,title,season=None,series=None,config=None):
    series=(db.get_series(fid) or {}) if series is None else series
    config=downloads.settings() if config is None else config
    token=f'S{season:02}' if season and season>1 and not db.uses_continuous_episodes(series) and explicit_number(title) is None else ''
    return downloads.make_query(title,token,config['group'],config['quality'])
