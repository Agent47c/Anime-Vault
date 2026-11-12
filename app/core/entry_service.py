"""Entry and import persistence; called from workers, never widget callbacks."""
import json
from pathlib import Path
from contextlib import closing
from app import db
from app.config import COVERS_DIR
from app.core.scan_state import decision


def _apply_import_metadata(fid,media):
    """Metadata-only import correction; retain file/episode and user identities."""
    from app.core import anilist_client as client
    data=client.extract_franchise_data(media)
    current=db.get_franchise(fid)
    if current.get('anilist_id') and current['anilist_id']!=media['id']:
        raise ValueError('This entry has a confirmed provider link. Use its Rematch action to change it.')
    owner=db.get_franchise_by_anilist_id(media['id'])
    if owner and owner['id']!=fid:
        # A provider ID is unique. Group the old local record; never delete it,
        # move its seasons or overwrite the provider owner's notes/storage data.
        db.group_with_series(fid,owner['id'])
        db.update_franchise_field(fid,'needs_review',0)
        return
    data.update(needs_review=0,is_custom=0)
    # Keep the user's chosen display name. Provider aliases/art fill metadata.
    data.pop('display_title',None)
    if media.get('_preview_cover') and not str(current.get('cover_filename') or '').startswith('custom-'):
        data['cover_filename']=media['_preview_cover']
    with closing(db.get_connection()) as conn,conn:
        fields=','.join(key+'=?' for key in data)
        conn.execute('UPDATE franchises SET '+fields+' WHERE id=?',(*data.values(),fid))
        decision(conn,'series',fid,media['id'])


def save_entry(data,previous=None,cover_path=None):
    db.validate_fields(data,db.FRANCHISE_FIELDS)
    data=dict(data)
    folder=data.get('root_folder_path')
    changed=bool(folder and (not previous or folder!=previous.get('root_folder_path')))
    if changed:
        folder=str(Path(folder).resolve(strict=True))
        if not Path(folder).is_dir():
            raise ValueError('Choose an anime folder.')
        data['root_folder_path']=folder
    if previous:
        fid=previous['id']
        with closing(db.get_connection()) as conn,conn:
            fields=','.join(f'{key}=?' for key in data)
            conn.execute(f'UPDATE franchises SET {fields} WHERE id=?',(*data.values(),fid))
    else:
        data['storage_state']='ON_DISK' if folder else 'NOT_DOWNLOADED'
        fid=db.upsert_franchise(data)
    if changed:
        from app.core.scanner import _update_on_disk_info
        _update_on_disk_info(fid,folder)
    if cover_path:
        from PIL import Image
        import uuid
        COVERS_DIR.mkdir(parents=True,exist_ok=True)
        # Custom art is never overwritten by a provider cache entry.
        filename=f'custom-{fid}-{uuid.uuid4().hex}.jpg'
        try:
            with Image.open(cover_path) as image:
                image=image.convert('RGB')
                image.thumbnail((400,600))
                image.save(str(COVERS_DIR/filename),'JPEG',quality=90)
        except OSError:
            import shutil
            shutil.copy2(cover_path,COVERS_DIR/filename)
        db.update_franchise_field(fid,'cover_filename',filename)
    with closing(db.get_connection()) as conn,conn:
        current=conn.execute('SELECT anilist_id FROM franchises WHERE id=?',(fid,)).fetchone()
        decision(conn,'series',fid,current[0])
        conn.execute('DELETE FROM matching_review WHERE local_id=?',(fid,))
    return fid


def apply_import(items,status):
    from app.core import anilist_client as client
    from app.core.text_import import ImportIndex,remember_import_alias
    index=ImportIndex()
    imported=merged=0
    for item in items:
        if not item.get('enabled',True):
            continue
        existing_id=item.get('existing_id')
        media=item.get('anilist_media')
        notes=item.get('notes') or ''
        # Recheck at write time: another list or an earlier row may already have
        # created this anime while the preview was open.
        if not existing_id:
            matches=index.matches(item.get('raw_title'),item.get('matched_title'),provider=(media or {}).get('id'))
            if len(matches)>1:raise ValueError('Multiple library entries match '+item['raw_title']+'. Review their match before importing.')
            if matches:existing_id=matches[0]['id']
        if existing_id:
            existing=db.get_franchise(existing_id)
            if not existing:raise ValueError('The selected library entry was removed. Reopen the importer.')
            if item.get('update_metadata') and media:_apply_import_metadata(existing_id,media)
            if notes:
                old=existing.get('user_notes') or ''
                if notes not in old:
                    db.update_franchise_field(existing_id,'user_notes',f'{old}\n{notes}'.strip())
            db.update_franchise_field(existing_id,'watch_status',status)
            index.add(db.get_franchise(existing_id))
            remember_import_alias(existing_id,item['raw_title']);index.add_alias(item['raw_title'],existing_id)
            merged+=1
            continue
        data={'display_title':item['matched_title'],'title_romaji':item['raw_title'],
              'watch_status':status,'storage_state':'NOT_DOWNLOADED',
              'raw_import_name':item['raw_line'],'user_notes':notes,'is_custom':1,'needs_review':1}
        if media:
            data.update(client.extract_franchise_data(media))
            data['is_custom']=0
            data['needs_review']=0
        fid=db.upsert_franchise(data)
        # Preview artwork was fetched by ParseAndMatchWorker. Saving does not
        # make another API request or download on the GUI thread.
        if media and media.get('_preview_cover'):
            db.update_franchise_field(fid,'cover_filename',media['_preview_cover'])
        with closing(db.get_connection()) as conn,conn:
            decision(conn,'series',fid,media['id'] if media else None)
        index.add(db.get_franchise(fid))
        remember_import_alias(fid,item['raw_title']);index.add_alias(item['raw_title'],fid)
        imported+=1
    return imported,merged


def grab_frame(folder):
    import os
    import subprocess
    import tempfile
    from PyQt5.QtGui import QImage
    from app.config import VIDEO_EXTENSIONS
    video=next((p for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS),None)
    if not video:
        raise ValueError('No video files found in the specified folder.')
    handle,name=tempfile.mkstemp(prefix='animevault-frame-',suffix='.jpg')
    os.close(handle)
    try:
        result=subprocess.run(['ffmpeg','-y','-i',str(video),'-ss','00:02:00','-vframes','1','-q:v','2',name],capture_output=True,timeout=30)
        image=QImage(name)
        if result.returncode or image.isNull():
            raise ValueError('FFmpeg could not extract a frame. Check that FFmpeg is installed and the video is readable.')
        from PyQt5.QtCore import Qt
        return name,image.scaled(140,210,Qt.KeepAspectRatio,Qt.SmoothTransformation)
    except Exception:
        Path(name).unlink(missing_ok=True)
        raise
