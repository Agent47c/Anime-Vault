"""Portable application-state backups, with optional caches and guarded restore.

Media, executable files, .env tokens and machine-specific Chrome registration
are deliberately excluded. SQLite backup captures all committed database tables.
"""
import json
import os
import shutil
import sqlite3
import stat
import tempfile
import uuid
import zipfile
from contextlib import closing
from datetime import datetime
from pathlib import Path,PurePosixPath
from app import db

CACHE_DIRS=('covers','episode-thumbnails','player-icons')
STATE_DIR='builtin-downloads'
MAX_BYTES=64*1024**3


def safe_target(root,name):
    parts=PurePosixPath(name).parts
    reserved={'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}
    if not parts or str(PurePosixPath(name))!=name or any(p in ('.','..') or p.split('.')[0].upper() in reserved or any(c in p for c in ':\\\x00<>"|?*') or p.endswith((' ','.')) for p in parts) or name.startswith('/'):
        raise ValueError('Unsafe backup path.')
    path=Path(root).joinpath(*parts)
    for parent in (path,*path.parents):
        if parent.is_symlink() or (hasattr(parent,'is_junction') and parent.is_junction()):raise ValueError('Linked backup paths require manual review.')
    return path


def state_files(include_caches):
    directories=(STATE_DIR,)+(CACHE_DIRS if include_caches else ())
    for directory in directories:
        folder=safe_target(db.DATA_DIR,directory)
        if not folder.is_dir():continue
        for path in folder.rglob('*'):
            relative=path.relative_to(db.DATA_DIR).as_posix();safe_target(db.DATA_DIR,relative)
            if not path.is_file():continue
            if directory==STATE_DIR and path.suffix.lower() not in ('.resume','.torrent','.json'):continue
            if directory in CACHE_DIRS and path.suffix.lower() not in ('.png','.jpg','.jpeg','.webp','.gif','.ico','.json'):continue
            yield relative,path


def create_backup(include_caches=False,directory=None):
    destination=Path(directory or db.get_state('backup_directory',str(db.DATA_DIR/'backups')))
    if not destination.is_absolute():raise ValueError('Choose an absolute backup directory.')
    destination.mkdir(parents=True,exist_ok=True)
    target=destination/f"AnimeVault-profile-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}.zip"
    temporary=target.with_suffix('.partial')
    try:
        with tempfile.TemporaryDirectory(prefix='AnimeVault-backup-') as stage:
            from app.core import downloads,builtin_torrents
            with downloads._lock:
                if builtin_torrents.active():builtin_torrents._engine.save()
                snapshot=db.backup_database(stage)
                state=Path(stage)/STATE_DIR;state.mkdir()
                for name,path in state_files(False):
                    copy=Path(stage)/name;copy.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,copy)
            with zipfile.ZipFile(temporary,'x',compression=zipfile.ZIP_DEFLATED,allowZip64=True) as archive:
                archive.writestr('manifest.json',json.dumps({'format':'AnimeVault-profile','version':1,'caches':bool(include_caches),'media_files':False,'created':datetime.now().astimezone().isoformat()}))
                archive.write(snapshot,'library.db')
                for path in state.rglob('*'):
                    if path.is_file():archive.write(path,path.relative_to(stage).as_posix())
                if include_caches:
                    for name,path in state_files(True):
                        if not name.startswith(STATE_DIR+'/'):archive.write(path,name)
        os.replace(temporary,target)
        return str(target)
    finally:
        temporary.unlink(missing_ok=True)


def _allowed(name):
    parts=PurePosixPath(name).parts
    if name in ('manifest.json','library.db'):return True
    if len(parts)<2:return False
    suffix=PurePosixPath(name).suffix.lower()
    return ((parts[0] in CACHE_DIRS and suffix in ('.png','.jpg','.jpeg','.webp','.gif','.ico','.json')) or
            (parts[0]==STATE_DIR and suffix in ('.resume','.torrent','.json')))


def restore_backup(filename):
    """Validate/extract before writes; keep a persistent full safety archive."""
    from app.core import builtin_torrents
    if builtin_torrents.active():raise ValueError('Stop the download engine before restoring an application backup.')
    with tempfile.TemporaryDirectory(prefix='AnimeVault-restore-') as temporary:
        stage=Path(temporary);payload=stage/'incoming';payload.mkdir()
        with zipfile.ZipFile(filename) as archive:
            infos=archive.infolist()
            if len(infos)>100000 or sum(i.file_size for i in infos)>MAX_BYTES:raise ValueError('Backup exceeds the supported 64 GB / 100,000-file safety limit.')
            seen=set()
            for info in infos:
                if info.is_dir():continue
                key=info.filename.casefold()
                if key in seen or not _allowed(info.filename) or stat.S_ISLNK(info.external_attr>>16) or info.flag_bits&1:raise ValueError('Invalid, linked or duplicate backup entry.')
                seen.add(key);target=safe_target(payload,info.filename);target.parent.mkdir(parents=True,exist_ok=True)
                with archive.open(info) as source,target.open('xb') as output:shutil.copyfileobj(source,output,1024*1024)
        manifest=json.loads((payload/'manifest.json').read_text(encoding='utf-8'))
        if manifest.get('format')!='AnimeVault-profile' or manifest.get('version')!=1:raise ValueError('Unsupported application backup.')
        incoming=payload/'library.db'
        with closing(sqlite3.connect(incoming.resolve().as_uri()+'?mode=ro',uri=True)) as check:
            if check.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Backup database is damaged.')
            check.execute('SELECT COUNT(*) FROM franchises').fetchone()
        planned=[]
        for path in payload.rglob('*'):
            if path.is_file() and path.relative_to(payload).as_posix() not in ('library.db','manifest.json'):
                relative=path.relative_to(payload).as_posix();planned.append((relative,path,safe_target(db.DATA_DIR,relative)))
        safety=create_backup(True,directory=db.DATA_DIR/'backups')
        previous_db=db.backup_database(stage/'previous-db')
        applied=[]
        try:
            db.restore_database(str(incoming))
            for relative,source,target in planned:
                old=stage/'previous-files'/relative
                if target.exists():old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,old)
                applied.append((target,old));target.parent.mkdir(parents=True,exist_ok=True)
                pending=target.with_name(target.name+'.restore-'+uuid.uuid4().hex)
                try:shutil.copy2(source,pending);os.replace(pending,target)
                finally:pending.unlink(missing_ok=True)
        except Exception:
            for target,old in reversed(applied):
                if old.exists():shutil.copy2(old,target)
                else:target.unlink(missing_ok=True)
            db.restore_database(previous_db)
            raise
        return safety
