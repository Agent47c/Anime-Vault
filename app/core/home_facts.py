"""Read-only Home presentation facts, prepared in refresh/background workers."""
import json
from contextlib import closing
from app import db
from app.core.library_health import episode_inventory,aired_boundary


def download_badges(groups,jobs):
    result={}
    for group in groups:
        members=set(group.get('series_member_ids',[group['id']]))
        active=[job for job in jobs if job.get('fid') in members and not job.get('indexed') and job.get('desired') not in ('cancelled','stopped') and job.get('status')!='Indexed']
        if not active:continue
        progress=sum(max(0,min(1,float(job.get('progress') or 0))) for job in active)/len(active)
        failed=any(any(word in job.get('status','').lower() for word in ('error','failed','review')) for job in active)
        paused=all(job.get('desired')=='paused' for job in active)
        label='Needs review' if failed else 'Paused' if paused else f'DL {round(progress*100)}%'
        result[group['id']]=dict(label=label,progress=progress,jobs=active)
    return result


def build_facts(index):
    with closing(db.get_connection()) as conn:
        seasons=[dict(row) for row in conn.execute('SELECT * FROM seasons')]
    by_owner={}
    for season in seasons:by_owner.setdefault(season['franchise_id'],[]).append(season)
    result={}
    for group in index.groups:
        owned=[s for member in group['series_member_ids'] for s in by_owner.get(member,[])]
        continuous=db.uses_continuous_episodes(group)
        coverage=episode_inventory(owned,continuous=continuous)
        totals=[]
        for season in owned:
            if season.get('relation_type')!='SEASON' or season.get('airing_status')=='NOT_YET_RELEASED':continue
            boundary=aired_boundary(season)
            if boundary is None and season.get('airing_status')=='FINISHED':boundary=season.get('episodes_total')
            if boundary is not None:totals.append(boundary)
        total=max(totals,default=0) if continuous else sum(totals)
        found=coverage['unique_episode_count']
        result[group['id']]=dict(found=found,total=max(found,total),verified_total=bool(totals),coverage=coverage)
    return result
