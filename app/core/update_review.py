"""Read current saved changes; contact AniList only on an explicit refresh."""
from app import db
from app.ui.update_release_dates import dated_changes


def read_changes(identifiers, refresh=False, cancelled=lambda:False):
    warnings=[];refreshed=False
    import json
    from app.core.release_calendar import saved
    from app.config import is_offline
    from app.core import anilist_client as api
    from app.core.updater import UpdaterThread
    offline=refresh and is_offline()
    if offline:warnings.append('Offline mode: showing saved updates. Connect to the internet, then refresh again.')
    records=[]
    with api.cancellable(cancelled):
        for fid in sorted(set(identifiers)):
            if cancelled():raise InterruptedError('Update check cancelled')
            record=db.get_franchise(fid)
            if not record:continue
            if not refresh:
                try:media=json.loads(record.get('metadata_json') or '{}') or {}
                except (ValueError,TypeError):media={}
                if media.get('id')==record.get('anilist_id') and media.get('nextAiringEpisode'):
                    current=UpdaterThread._check_for_updates(None,record,media)
                    if current!=record.get('update_details'):
                        before=record.get('update_details');db.publish_updates(fid,current)
                        record=db.get_franchise(fid) or record
                        refreshed=refreshed or before!=record.get('update_details')
            if refresh and not record.get('anilist_id'):
                warnings.append(record['display_title']+': no AniList link. Rematch this anime before checking online.')
            if refresh and not offline and record.get('anilist_id'):
                try:
                    media=api.get_anime_by_id(record['anilist_id'])
                    if not media:raise ValueError(api.last_error() or 'AniList did not return metadata. Try again later.')
                    if cancelled():raise InterruptedError('Update check cancelled')
                    # Reuse the existing updater comparison and dismissal rules.
                    changes=UpdaterThread._check_for_updates(None,record,media)
                    db.cache_media(fid,media);db.publish_updates(fid,changes)
                    refreshed=True;record=db.get_franchise(fid) or record
                except InterruptedError:raise
                except Exception as error:warnings.append(record['display_title']+': '+str(error))
            records.append(record)
    history=saved()
    for record in records:record['_release_schedule']=history
    entries=[]
    for record in records:
        raw=[p.strip() for p in (record.get('update_details') or '').split(' | ') if p.strip()]
        try:media=json.loads(record.get('metadata_json') or '{}') or {}
        except (ValueError,TypeError):media={}
        nodes=[media]+[(edge.get('node') or {}) for edge in (media.get('relations') or {}).get('edges',[])]
        for original,label in zip(raw,dated_changes(record)):
            title=original.partition(' — ')[2] if original.startswith('Episode ') else original.partition(' — ')[0]
            node=next((node for node in nodes if title in (node.get('title') or {}).values()),{})
            date=node.get('startDate') or {}
            from app.core.download_assignment import release_context
            context=release_context(record['id'],node.get('id'),title)
            entries.append(dict(fid=record['id'],raw=original,text=label,title=title,date=(date.get('year') or 0,date.get('month') or 0,date.get('day') or 0),assignment_context=context))
    return dict(changes=list(dict.fromkeys(change for record in records for change in dated_changes(record))),entries=entries,
                warnings=warnings,refreshed=refreshed)


def ignore_entry(fid,raw):
    """Dismiss this exact pending event, preserving every other event and choice."""
    import json
    from contextlib import closing
    with closing(db.get_connection()) as conn,conn:
        row=conn.execute('SELECT update_details FROM franchises WHERE id=?',(fid,)).fetchone()
        if not row:return
        pending=[p.strip() for p in (row['update_details'] or '').split(' | ') if p.strip()]
        if raw not in pending:return
        key=f'dismissed_updates:{fid}';saved=conn.execute('SELECT value FROM app_state WHERE key=?',(key,)).fetchone()
        dismissed=set(json.loads(saved['value'])) if saved else set();dismissed.add(raw)
        conn.execute('INSERT OR REPLACE INTO app_state(key,value) VALUES (?,?)',(key,json.dumps(sorted(dismissed))))
        remaining=' | '.join(p for p in pending if p!=raw) or None
        muted=conn.execute('SELECT value FROM app_state WHERE key=?',(f'muted_updates:{fid}',)).fetchone()
        conn.execute('UPDATE franchises SET update_details=?,has_new_update=? WHERE id=?',(remaining,bool(remaining) and not bool(muted and muted['value']=='1'),fid))
