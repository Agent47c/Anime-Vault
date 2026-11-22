"""Conservative byte-identical duplicate review within one release."""
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

from app import db
from app.config import VIDEO_EXTENSIONS
from app.core.consolidation import explicit_season
from app.core.parser import extract_episode_numbers
from app.core.recycle_bin import send2trash


def signature(path):
    stat = path.stat()
    return (stat.st_size, stat.st_mtime_ns, stat.st_ino)


def digest(path, cancelled):
    before = signature(path)
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            if cancelled():
                raise InterruptedError("Cancelled")
            block = stream.read(1024 * 1024)
            if not block:
                break
            hasher.update(block)
    if signature(path) != before:
        raise ValueError(f"File changed while checking: {path}")
    return hasher.hexdigest(), before


def find_duplicates(cancelled=lambda: False, progress=lambda text: None):
    # Drive scans discover current files. Saved reviews have their own path in
    # load_review; an empty/stale inventory must not turn a drive scan into a no-op.
    buckets = defaultdict(list)
    seen = set()
    errors = []
    from app.core import downloads,download_queue
    pending_roots=[Path(job['destination']).resolve() for job in downloads.jobs()
                   if job.get('destination') and download_queue.status(job) not in ('Completed','Seeding')
                   and not job.get('library_moved')]
    for record in db.get_all_franchises():
        if cancelled():
            raise InterruptedError("Cancelled")
        seasons=db.get_seasons_for_franchise(record['id'])
        seasons.sort(key=lambda row:len(Path(row.get('season_folder_path') or '').parts),reverse=True)
        for season in seasons:
            folder = season.get("season_folder_path")
            if not folder:
                continue
            if Path(folder).is_symlink():continue
            root = Path(folder).resolve()
            progress(f'Scanning directory: {root}')
            if not root.is_dir():
                errors.append(f'Missing directory: {root}');continue
            def files_on_drive():
                for directory,dirs,names in os.walk(root,onerror=lambda error:errors.append(str(error)),followlinks=False):
                    if cancelled():raise InterruptedError('Cancelled')
                    dirs[:]=[name for name in dirs if not (Path(directory)/name).is_symlink()]
                    for name in names:
                        if cancelled():raise InterruptedError('Cancelled')
                        yield Path(directory)/name
            for path in files_on_drive():
                if cancelled():
                    raise InterruptedError("Cancelled")
                try:
                    resolved = path.resolve()
                    if root not in resolved.parents or path.is_symlink() or path.suffix.lower() not in VIDEO_EXTENSIONS:
                        continue
                    if any(resolved==pending or pending in resolved.parents for pending in pending_roots):
                        continue  # Torrent chunks are not completed duplicate candidates.
                    identity = os.path.normcase(str(resolved))
                    if identity in seen or not path.is_file():
                        continue
                    seen.add(identity)
                    # Nested explicit seasons override a broad parent inventory.
                    number = next((explicit_season(parent.name) for parent in path.parents
                                   if (parent == root or root in parent.parents) and explicit_season(parent.name) is not None),
                                  season.get("season_number"))
                    episodes = tuple(extract_episode_numbers(path.name))
                    if not episodes:
                        continue
                    release = season.get("anilist_id") or number
                    scope = (record["id"], season.get("relation_type"), release, number, episodes)
                    stat = signature(path)
                    if stat[0]==0:continue
                    buckets[(scope, stat[0])].append((resolved, record["display_title"], episodes))
                except OSError as error:
                    errors.append(str(error))
    groups = []
    for candidates in buckets.values():
        if len(candidates) < 2:
            continue
        hashes = defaultdict(list)
        for path, title, episodes in candidates:
            progress(f"Checking {title} / {path.name}")
            try:
                checksum, stat = digest(path, cancelled)
                hashes[checksum].append({"path": str(path), "signature": stat, "title": title, "episodes": episodes})
            except (OSError, ValueError) as error:
                errors.append(str(error))
        for checksum, files in hashes.items():
            if len(files) > 1:
                files.sort(key=lambda file: file["path"].casefold())
                groups.append({"hash": checksum, "files": files})
    progress(f'Finished checking {len(seen)} files: {len(groups)} exact duplicate groups; {len(errors)} location errors.')
    return groups, errors

def save_review(result):
    """Keep the last three completed reviews; cancelled scans never replace them."""
    import time
    previous=json.loads(db.get_state('duplicates.review_history','[]'))
    previous.insert(0,{'time':time.time(),'result':result})
    db.set_state('duplicates.review_history',json.dumps(previous[:3]))

def load_review(cancelled=lambda:False,progress=lambda text:None):
    history=json.loads(db.get_state('duplicates.review_history','[]'))
    if not history:return [],['No saved duplicate review. Check the drive first.']
    groups,errors=history[0]['result'];valid=[];errors=list(errors)
    for group in groups:
        unchanged=True
        for file in group['files']:
            if cancelled():raise InterruptedError('Stopped')
            progress('Checking saved location: '+file['path'])
            try:
                if signature(Path(file['path']))!=tuple(file['signature']):raise ValueError('File changed')
            except (OSError,ValueError):
                errors.append('Missing, moved or changed — check the drive: '+file['path']);unchanged=False
        if unchanged:valid.append(group)
    return valid,errors


def delete_duplicate(group, candidate, cancelled=lambda: False, *, verified_keepers=None):
    """Recheck both files, retain the keeper, and remove only the reviewed copy."""
    keeper = group["files"][0]
    if candidate not in group["files"][1:] or candidate["path"] == keeper["path"]:
        raise ValueError("A verified retained copy is required.")
    def keeper_token():
        path=Path(keeper['path'])
        if path.is_symlink():raise ValueError('The retained file changed.')
        stat=path.stat()
        return (str(path.absolute()),stat.st_size,stat.st_mtime_ns,stat.st_ino,stat.st_dev,stat.st_ctime_ns,group['hash'])
    token=keeper_token()
    for entry in (keeper, candidate):
        path = Path(entry["path"])
        if entry is keeper and verified_keepers is not None and token in verified_keepers:
            if signature(path)!=tuple(entry['signature']):raise ValueError('The retained file changed.')
            continue
        checksum, stat = digest(path, cancelled)
        if checksum != group["hash"] or tuple(entry["signature"]) != stat:
            raise ValueError("Files changed since the scan. Scan again before deleting.")
        if entry is keeper and verified_keepers is not None:
            if keeper_token()!=token:raise ValueError('The retained file changed.')
            verified_keepers[token]=True
    if cancelled():
        raise InterruptedError("Cancelled")
    path = Path(candidate["path"])
    if path.is_symlink() or signature(path) != tuple(candidate["signature"]):
        raise ValueError("The selected file changed.")
    if keeper_token()!=token:raise ValueError('The retained file changed.')
    # Record the intent before the filesystem action so a failed DB write can
    # be reconciled from this log without guessing which file was removed.
    journal = db.DATA_DIR / "exports" / "duplicate-deletions.jsonl"
    journal.parent.mkdir(parents=True, exist_ok=True)
    with journal.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"event": "planned", "path": str(path), "kept": keeper["path"], "sha256": group["hash"]}) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
        from app.core.file_operations import recycle_file
        current = path.stat()
        expected = (candidate['signature'][0], candidate['signature'][1], str(current.st_dev), str(candidate['signature'][2]))
        recycle_file(path, expected, recycle=send2trash)
        if path.exists():
            raise OSError('Recycle Bin operation did not remove the selected copy')
        stream.write(json.dumps({"event": "recycled", "path": str(path), "kept": keeper["path"], "sha256": group["hash"]}) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    # recycle_file already updates inventories and size/state in its durable
    # operation transaction; repeating that library-wide pass adds only IO.
