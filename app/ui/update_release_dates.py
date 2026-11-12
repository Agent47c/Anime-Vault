"""Release-date labels from cached metadata; never fetch during UI painting."""
import json,calendar

def dated_changes(franchise):
    try:media=json.loads(franchise.get('metadata_json') or '{}')
    except (TypeError,ValueError):media={}
    nodes=[edge.get('node') or {} for edge in (media.get('relations') or {}).get('edges',[])] if isinstance(media,dict) else []
    by_title={title.casefold():node for node in nodes for title in (node.get('title') or {}).values() if title}
    changes=[]
    for change in (franchise.get('update_details') or '').split(' | '):
        change=change.strip()
        if not change:continue
        from app.core.episode_updates import display_episode_change
        episode_label=display_episode_change(change,media,franchise.get('_release_schedule',())) if isinstance(media,dict) and (media.get('nextAiringEpisode') or franchise.get('_release_schedule')) else None
        if episode_label:
            changes.append(episode_label);continue
        title,sep,status=change.partition(' — ')
        if sep:
            node=by_title.get(title.casefold(),{});date=node.get('startDate') or {};year=date.get('year') or node.get('seasonYear');month=date.get('month')
            value=(calendar.month_name[month]+' ' if isinstance(month,int) and 1<=month<=12 else '')+str(year) if year else 'Date unavailable'
            label='Expected release' if 'Announced' in status else 'Started' if 'Currently Airing' in status else 'Released'
            change+=f' · {label}: {value}'
        changes.append(change)
    return changes
