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
    return dict(changes=list(dict.fromkeys(change for record in records for change in dated_changes(record))),
                warnings=warnings,refreshed=refreshed)
