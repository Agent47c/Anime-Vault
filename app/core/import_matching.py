"""TXT-specific search cleanup using the scanner's conservative match evidence."""
import re
from app.core.text_import import clean_import_name
from app.core import match_evidence
from app.core.parser import extract_season_number


def queries(title):
    clean=clean_import_name(title)
    base=re.sub(r'(?i)\s*(?:[-–]\s*)?\b(?:seasons?\s*\d+(?:\s*[-–&+]\s*\d+)*|S\d{1,2}(?:\s*[-+&]\s*S?\d{1,2})*)\s*$','',clean).strip()
    return list(dict.fromkeys(q for q in (clean,base) if q))


def choose(title,candidates):
    clean=clean_import_name(title)
    evidence=match_evidence.context(series=clean,season=extract_season_number(clean,None))
    if re.search(r'(?i)\b(?:movie|film)\b',clean):evidence['format']='MOVIE'
    elif re.search(r'(?i)\b(?:OVA|special)\b',clean):evidence['format']='SPECIAL'
    # Ranges describe a collection, not a verified mapping to one release.
    collection=bool(re.search(r'(?i)\b(?:seasons?\s*\d+\s*[-–&+]\s*\d+|S\d+\s*[-+&]\s*S?\d+)',clean))
    selected,ranked=match_evidence.choose(candidates,evidence)
    return (None if collection else selected),ranked


def search(title,cancelled=lambda:False):
    from app.core import anilist_client as client
    candidates={}
    with client.cancellable(cancelled):
        for query in queries(title):
            for media in client.search_anime(query,per_page=5):candidates[media['id']]=media
            selected,ranked=choose(title,list(candidates.values()))
            if selected:return selected,ranked
    return choose(title,list(candidates.values()))
