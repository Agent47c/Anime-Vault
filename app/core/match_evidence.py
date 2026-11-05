"""Explainable matching. Strong conflicts veto automatic selection."""
import re
from pathlib import Path
from difflib import SequenceMatcher
from app.core.parser import clean_title,normalize_for_matching,extract_base_anime_name,extract_season_number


def base_title(value):
    title=extract_base_anime_name(value)
    title=re.sub(r'(?i)\b(?:part|cour)\s*(?:\d+|IV|III|II)\b','',title)
    return re.sub(r'\b(?:19|20)\d{2}\b','',title).strip(' -')


def context(filename='',folder='',series='',season=None,kind=None):
    raw = ' '.join((filename,folder,series))
    meaningful = [value for value in (Path(filename).stem,Path(folder).name,series)
                  if value and not re.fullmatch(r'(?i)(?:season\s*\d+|episodes?|movies?|specials?|unassigned episodes)',value)]
    titles = []
    filename_title = None
    for value in meaningful:
        if re.fullmatch(r'(?i)(?:(?:episode|ep|e)\s*)?\d+(?:[-_. ]\d+)?',value.strip()):
            continue
        title = base_title(value)
        if normalize_for_matching(title) and not re.fullmatch(r'(?i)(?:episode\s*\d*|ep\s*\d*|\d+)',title):
            titles.append(title)
            if value == Path(filename).stem:
                filename_title = title
    explicit = extract_season_number(filename,None) if filename else None
    year = re.search(r'\b((?:19|20)\d{2})\b',raw)
    part = re.search(r'(?i)\b(?:part|cour)\s*(\d+|II|III|IV)\b',raw)
    roman={'II':2,'III':3,'IV':4}
    part_number = (int(part[1]) if part[1].isdigit() else roman[part[1].upper()]) if part else None
    movie = bool(re.search(r'(?i)\b(?:movie|film)\b',filename+' '+folder))
    return {'titles':titles,'season':explicit or season,'part':part_number,'year':int(year[1]) if year else None,
            'format': 'MOVIE' if movie or kind=='MOVIE' else 'SPECIAL' if kind in ('SPECIAL','OVA') else 'TV',
            'filename':filename,'folder':folder,'filename_title':filename_title}


def rank(candidates,evidence):
    ranked=[]
    for media in {m['id']:m for m in candidates}.values():
        aliases=[v for v in (media.get('title') or {}).values() if v]+(media.get('synonyms') or [])
        normalized=[normalize_for_matching(base_title(v)) for v in aliases]
        title_scores=[]
        for index,value in enumerate(evidence['titles']):
            clean=normalize_for_matching(value)
            title_scores.append(max((1.0 if clean==alias else SequenceMatcher(None,clean,alias).ratio() for alias in normalized),default=0))
        similarity=max(title_scores,default=0)
        score=similarity*75
        reasons=[f'Title similarity {similarity:.0%}']
        conflict=False
        if len(title_scores)>1 and title_scores[0]<.65 and max(title_scores[1:])>=.98:
            conflict=True;reasons.append('Filename conflicts with its broader folder title')
        seasons={extract_season_number(title,None) for title in aliases}
        seasons.discard(None)
        expected=evidence.get('season')
        if expected and seasons:
            if expected not in seasons:
                conflict=True;reasons.append('Season conflict')
            else:
                score+=10;reasons.append('Season agrees')
        elif expected and expected>1:
            conflict=True;reasons.append('Later season not verified')
        parts={int(m[1]) for title in aliases for m in [re.search(r'(?i)\b(?:part|cour)\s*(\d+)\b',title)] if m}
        if evidence.get('part'):
            if evidence['part'] not in parts:
                conflict=True;reasons.append('Part/cour not verified')
            else:
                score+=5;reasons.append('Part agrees')
        year=media.get('seasonYear') or (media.get('startDate') or {}).get('year')
        if evidence.get('year') and year:
            if evidence['year']!=year:
                conflict=True;reasons.append('Year conflict')
            else:
                score+=5;reasons.append('Year agrees')
        elif evidence.get('year'):
            conflict=True;reasons.append('Year not verified')
        formats={'TV','TV_SHORT','ONA'} if evidence['format']=='TV' else {'SPECIAL','OVA'} if evidence['format']=='SPECIAL' else {'MOVIE'}
        if media.get('format') not in formats:
            conflict=True;reasons.append('Format conflict')
        else:
            score+=5;reasons.append('Format agrees')
        ranked.append({'id':media['id'],'score':round(min(score,100),1),'conflict':conflict,
                       'strong_title':similarity>=.98,'reasons':reasons,'media':media})
    return sorted(ranked,key=lambda row:row['score'],reverse=True)


def choose(candidates,evidence):
    ranked=rank(candidates,evidence)
    eligible=[r for r in ranked if not r['conflict'] and r['strong_title'] and r['score']>=80]
    # A close alternative always requires human review, even if it has a conflict.
    if len(eligible)==1 and (len(ranked)==1 or eligible[0]['score']-max(r['score'] for r in ranked if r['id']!=eligible[0]['id'])>=10):
        return eligible[0]['media'],ranked
    return None,ranked
