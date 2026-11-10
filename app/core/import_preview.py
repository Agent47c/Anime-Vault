"""Read-only import preview, including existing entries rather than hiding them."""
from app import preferences as prefs
from app.core.parser import parse_txt_line
from app.core.text_import import ImportIndex, title_key, clean_import_name


def preview_lines(lines,online=False,rematch_existing=False,cancelled=lambda:False):
    from app.core import anilist_client as client,import_matching
    index=ImportIndex();seen={};providers={};cache={}
    ignore=prefs.enabled('import_ignore_duplicates')
    for line in lines:
        if cancelled():break
        parsed=parse_txt_line(line)
        if not parsed:continue
        title=clean_import_name(parsed['title']);key=title_key(title)
        item=dict(raw_line=line,original_title=parsed['title'],raw_title=title,notes=parsed['notes'],
                  matched_title=title,status='NOT_FOUND',confidence=0,anilist_media=None,existing_id=None,enabled=False)
        if ignore and key in seen:
            item.update(status='DUPLICATE',duplicate_of=seen[key]);yield item;continue
        seen[key]=title
        matches=index.matches(title)
        if len(matches)>1:
            item.update(status='AMBIGUOUS',error='Several existing entries match. Choose the correct match for review.');yield item;continue
        existing=matches[0] if matches else None
        if existing:
            item.update(status='MERGED',existing_id=existing['id'],matched_title=existing['display_title'],
                        confidence=100,enabled=not ignore,existing_provider=existing.get('anilist_id'))
            if existing.get('anilist_id') or not rematch_existing:yield item;continue
        if online:
            try:
                if key not in cache:cache[key]=import_matching.search(title,cancelled)
                media,ranked=cache[key]
                suggestion=media or (ranked[0]['media'] if ranked else None)
                if suggestion:
                    item.update(anilist_media=suggestion,matched_title=client.resolve_display_title(suggestion),
                                confidence=100 if media else int(ranked[0]['score']),
                                status='EXISTING_MATCHED' if existing and media else 'MATCHED' if media else 'REVIEW',
                                safe_match=bool(media),update_metadata=bool(existing and media),
                                enabled=bool(media and prefs.enabled('import_auto')))
                    if not media:item['error']='Suggested match needs confirmation: '+'; '.join(ranked[0]['reasons'])
                    linked=index.matches(provider=suggestion['id']) if media else []
                    if media and not existing and len(linked)==1:
                        item.update(existing_id=linked[0]['id'],existing_provider=linked[0].get('anilist_id'),
                                    status='MERGED',update_metadata=False,enabled=not ignore)
                    elif media and ignore and suggestion['id'] in providers and not existing:
                        item.update(status='DUPLICATE',duplicate_of=providers[suggestion['id']],enabled=False)
                    if media:providers[suggestion['id']]=title
                    if item['status']!='DUPLICATE':
                        item['anilist_media']=dict(suggestion)
                        item['anilist_media']['_preview_cover']=client.download_cover(suggestion,'preview-'+str(suggestion['id']))
            except InterruptedError:break
            except Exception as error:
                item['error']='Metadata lookup failed: '+str(error)
                if not existing:item['status']='ERROR'
        yield item
