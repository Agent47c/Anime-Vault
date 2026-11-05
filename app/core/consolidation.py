"""Plan and explicitly apply a cross-root, non-overwriting media consolidation."""
import csv
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from app.core.parser import clean_title, extract_season_number, extract_episode_range, extract_episode_numbers

VIDEOS = {'.mkv', '.mp4', '.avi', '.webm', '.ts', '.mov', '.m4v'}
SIDECARS = {'.ass', '.srt', '.sub', '.idx', '.vtt', '.ttf', '.otf', '.jpg', '.jpeg', '.png', '.webp', '.nfo', '.xml'}


def safe_name(value):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', ' ', value)
    value = re.sub(r'\s+', ' ', value).strip(' .-')[:140].rstrip(' .')
    if not value or re.fullmatch(r'CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]', value, re.I):
        raise ValueError('Unsafe or empty folder name')
    return value


def approve_release_group(plan, title, release):
    """Approve only the highlighted anime's uncertain files for an explicit folder."""
    parts = re.split(r'[/\\]', release.strip())
    if not parts or any(part in ('', '.', '..') or safe_name(part) != part for part in parts):
        raise ValueError('Enter a folder such as Unassigned episodes, Season 21, or Arcs/Egghead. Do not enter a drive or parent path.')
    release = '/'.join(parts)
    entries = [entry for entry in plan['moves'] if entry['series'] == title and entry.get('review_reason')]
    reserved = {os.path.normcase(str(Path(entry['target']))) for entry in plan['moves'] if entry not in entries}
    updated = []
    for entry in entries:
        target = Path(plan['destination']) / title / release / Path(entry['target']).name
        target.resolve().relative_to(Path(plan['destination']).resolve())
        original = target
        counter = 0
        while os.path.normcase(str(target)) in reserved:
            counter += 1
            token = hashlib.sha256(entry['source'].encode()).hexdigest()[:8]
            target = original.with_name(f'{original.stem}__{token}_{counter}{original.suffix}')
        reserved.add(os.path.normcase(str(target)))
        updated.append({**entry, 'target': str(target), 'release': release,
                        'review_reason': None, 'review_approved': entry['review_reason'],
                        'collision_preserved': entry.get('collision_preserved', False) or counter > 0})
    replacements = {entry['source']: entry for entry in updated}
    return {**plan, 'moves': [replacements.get(entry['source'], entry) for entry in plan['moves']]}


def series_name(raw):
    text = re.sub(r'^(?:ASW|Anime Time)\]\s*', '', raw, flags=re.I)
    text = clean_title(text)
    text = re.split(r'\b(?:S\d{1,2}\b|Seasons?\s+\d|\d+(?:st|nd|rd|th)\s+Season|1080p|720p|2160p|WEBRip|Dual Audio)', text, flags=re.I)[0]
    text = re.sub(r'\bR1\s*\+\s*R2\b|\bComplete(?: Series)?(?:\s*&.*)?$', '', text, flags=re.I)
    return safe_name(text)


def explicit_season(text):
    match = re.search(r'\b(?:S(\d{1,2})(?:E\d+)?|R(\d{1,2})\b|(\d{1,2})x\d{1,4})', text, re.I)
    if match:
        return int(next(v for v in match.groups() if v))
    if re.search(r'\bseason\s*\d|\d+(?:st|nd|rd|th)\s+season', text, re.I):
        return extract_season_number(text, None)
    return None


def release_folder(relative, release_title=None, absolute=False):
    """Filename identifiers outrank generic folders; original arc names are retained."""
    name = relative.name
    directories = list(relative.parts[:-1])
    combined = ' '.join(directories + [name])
    if re.search(r'\b(?:movies?|films?)\b', name.replace('_', ' '), re.I):
        return 'Movies', None
    if re.search(r'\b(?:specials?|OVAs?|NCOP|NCED|extras?|bonus|SP\d+)\b|\d+SP\b|Fan[ ._-]+Letter', name, re.I):
        return 'Specials', None
    if any(re.search(r'\b(?:movies?|films?)\b', d, re.I) for d in directories):
        return 'Movies', None
    if any(re.search(r'\b(?:specials?|OVAs?|extras?|bonus)\b', d, re.I) for d in directories):
        return 'Specials', None
    if any('log -' in d.lower() or 're-edit' in d.lower() for d in directories):
        return 'Alternate editions/' + safe_name(clean_title(directories[-1])), None
    number = explicit_season(name)
    # Prefer meaningful outer arc folders to accidental nested Season 1 folders.
    arc = next((d for d in directories if extract_episode_range(d)), None)
    if arc and (number is None or number == explicit_season(arc)):
        span = extract_episode_range(arc)
        numbers = extract_episode_numbers(name)
        if numbers and not all(span[0] <= ep <= span[1] for ep in numbers):
            return 'Unassigned episodes', 'File episode conflicts with the folder episode range'
        return safe_name(re.sub(r'\[[^]]*\]', '', arc)), None
    if number is None and release_title and re.search(r'\bArc\b|hen\b', release_title, re.I):
        return 'Arcs/' + safe_name(release_title), None
    if number is None:
        for directory in directories:
            number = explicit_season(directory)
            if number:
                break
    if number:
        episodes = extract_episode_numbers(name)
        if absolute and number == 1 and episodes and min(episodes) > 62 and not explicit_season(name):
            return 'Unassigned episodes', 'Absolute episode numbering; arc needs review'
        return f'Season {number:02}', None
    if release_title and re.search(r'\bArc\b|hen\b', release_title, re.I):
        return 'Arcs/' + safe_name(release_title), None
    return 'Unassigned episodes', 'No reliable season or arc identifier'


def make_plan(roots, destination, overrides=None):
    from app import db
    roots = [Path(root).resolve() for root in roots]
    destination = Path(destination).resolve()
    if any(destination == root or root in destination.parents or destination in root.parents for root in roots):
        raise ValueError('Destination must be separate from each source root')
    overrides = overrides or {}
    records = db.get_all_franchises()
    groups = db.get_series_library()
    by_member = {fid: group for group in groups for fid in group['series_member_ids']}
    owners = []
    absolute_ids = set()
    for record in records:
        group = by_member[record['id']]
        for season in db.get_seasons_for_franchise(record['id']):
            if season.get('episode_start') and season['episode_start'] > 1:
                absolute_ids.add(group['id'])
            observed = {ep for name in json.loads(season.get('video_files_json') or '[]') for ep in extract_episode_numbers(name)}
            if (season.get('season_number') or 0) > 1 and observed and min(observed) > 1 and max(observed) > max(30, len(observed)):
                absolute_ids.add(group['id'])
            if season.get('season_folder_path'):
                owners.append((Path(season['season_folder_path']).resolve(), record, group))
        if record.get('root_folder_path'):
            owners.append((Path(record['root_folder_path']).resolve(), record, group))
    owners.sort(key=lambda item: len(item[0].parts), reverse=True)
    moves, review, errors = [], [], []
    visited, targets = set(), set()
    for root in roots:
        if not root.is_dir():
            errors.append(f'Unavailable root: {root}')
            continue
        def onerror(error):
            errors.append(str(error))
        for current, dirs, filenames in os.walk(root, followlinks=False, onerror=onerror):
            dirs[:] = [d for d in dirs if not (Path(current) / d).is_symlink() and not (hasattr(os.path, 'isjunction') and os.path.isjunction(Path(current) / d))]
            for filename in sorted(filenames):
                source = Path(current) / filename
                if source.is_symlink() or source.suffix.lower() not in VIDEOS | SIDECARS:
                    continue
                source_key = os.path.normcase(str(source))
                if source_key in visited:
                    continue
                visited.add(source_key)
                relative = source.relative_to(root)
                if len(relative.parts) < 2:
                    review.append({'source': str(source), 'reason': 'Loose root file requires an explicit anime assignment'})
                    continue
                top = root / relative.parts[0]
                override = overrides.get(str(top))
                owner = next(((record, group) for folder, record, group in owners if folder != root and folder in [source.parent, *source.parent.parents] and root in folder.parents), None)
                try:
                    title = safe_name(override['series']) if override else series_name(owner[1]['display_title'] if owner else top.name)
                    if title.isupper():
                        title = title.title()
                    release, reason = release_folder(relative, owner[0]['display_title'] if owner else None, bool(owner and owner[1]['id'] in absolute_ids))
                    if override and override.get('release'):
                        release, reason = safe_name(override['release']), None
                    if source.suffix.lower() not in VIDEOS and not any(source.stem == Path(f).stem or source.stem.startswith(Path(f).stem + '.') for f in filenames if Path(f).suffix.lower() in VIDEOS):
                        release = 'Extras/' + safe_name(top.name) + '/' + source.parent.relative_to(top).as_posix()
                    target = destination / title / release / filename
                    target.resolve().relative_to(destination)
                    collision = False
                    counter = 0
                    original = target
                    while os.path.normcase(str(target)) in targets or target.exists():
                        collision = True
                        counter += 1
                        token = hashlib.sha256(str(source).encode()).hexdigest()[:8]
                        target = original.with_name(f'{original.stem}__{token}_{counter}{original.suffix}')
                    targets.add(os.path.normcase(str(target)))
                    stat = source.stat()
                    entry = {'source': str(source), 'target': str(target), 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns, 'series': title, 'release': release, 'collision_preserved': collision, 'review_reason': reason}
                    moves.append(entry)
                except (ValueError, OSError) as error:
                    errors.append(f'{source}: {error}')
    return {'version': 1, 'generated_at': datetime.now().astimezone().isoformat(), 'roots': list(map(str, roots)), 'destination': str(destination), 'moves': moves, 'unassigned': review, 'errors': errors}


def save_plan(plan, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / 'plan.json').write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding='utf-8')
    with (directory / 'moves.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        fields = ['series', 'release', 'source', 'target', 'bytes', 'collision_preserved', 'review_reason']
        writer = csv.DictWriter(stream, fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(plan['moves'])
    summary = ['# Consolidation preview', '', f"Destination: {plan['destination']}", f"Planned files: {len(plan['moves'])}", f"Files needing release review: {sum(bool(m['review_reason']) for m in plan['moves'])}", f"Unassigned files: {len(plan['unassigned'])}", f"Errors: {len(plan['errors'])}", '', 'No files have been moved. Review moves.csv and plan.json before applying.', 'Unassigned files and files with review_reason are excluded from execution.']
    (directory / 'summary.md').write_text('\n'.join(summary), encoding='utf-8')


def apply_plan(plan, journal_path, progress=None, should_stop=None):
    """Preflight the complete reviewed subset, then journal each non-overwriting move."""
    if plan.get('version') != 1 or plan.get('errors'):
        raise ValueError('Resolve the plan errors and generate a fresh preview first')
    roots = [Path(root).resolve() for root in plan['roots']]
    destination = Path(plan['destination']).resolve()
    if any(destination == root or root in destination.parents or destination in root.parents for root in roots):
        raise ValueError('Source and destination roots must be separate')
    selected = [entry for entry in plan['moves'] if not entry.get('review_reason')]
    targets, sources = set(), set()
    for entry in selected:
        if should_stop and should_stop():
            raise InterruptedError('Cancelled before moving files')
        source, target = Path(entry['source']), Path(entry['target'])
        resolved = source.resolve()
        if source.is_symlink() or not any(root in resolved.parents for root in roots):
            raise ValueError(f'Source outside approved roots: {source}')
        if destination not in target.resolve().parents or source.suffix.lower() not in VIDEOS | SIDECARS:
            raise ValueError(f'Invalid move: {source} → {target}')
        if os.name == 'nt' and source.resolve().drive.casefold() != target.resolve().drive.casefold():
            raise ValueError('This move-only organizer requires sources and destination on the same drive. Choose a destination on the source drive.')
        stat = source.stat()
        if (stat.st_size, stat.st_mtime_ns) != (entry['bytes'], entry['mtime_ns']):
            raise ValueError(f'Source changed since preview; generate a new plan: {source}')
        if target.exists() or os.path.normcase(str(target)) in targets or str(resolved) in sources:
            raise ValueError(f'Conflicting or existing target: {target}')
        targets.add(os.path.normcase(str(target)))
        sources.add(str(resolved))
    moved, errors, cancelled = [], [], False
    from app.core.identity import sync_inventory
    from app.core.file_operations import move_file
    sync_inventory()
    with Path(journal_path).open('x', encoding='utf-8', buffering=1) as journal:
        for entry in selected:
            if should_stop and should_stop():
                cancelled = True
                journal.write(json.dumps({'event': 'cancelled'}) + '\n')
                break
            source, target = Path(entry['source']), Path(entry['target'])
            try:
                # Recheck immediately before moving; no overwrite or copy/delete fallback.
                target.parent.mkdir(parents=True, exist_ok=True)
                target.resolve().relative_to(destination)
                stat = source.stat()
                if (stat.st_size, stat.st_mtime_ns) != (entry['bytes'], entry['mtime_ns']) or target.exists():
                    raise ValueError('Source or destination changed during execution')
                journal.write(json.dumps({'event': 'planned', **entry}) + '\n')
                journal.flush()
                os.fsync(journal.fileno())
                move_file(source, target, (entry['bytes'], entry['mtime_ns']))
                moved.append(entry)
                if progress:
                    progress(len(moved), len(selected), entry['series'])
                journal.write(json.dumps({'event': 'moved', **entry}) + '\n')
                journal.flush()
                os.fsync(journal.fileno())
            except (OSError, ValueError) as error:
                errors.append({'source': str(source), 'error': str(error)})
                journal.write(json.dumps({'event': 'error', 'source': str(source), 'error': str(error)}) + '\n')
                break  # Stop on failure; retain all remaining originals for review.
    return {'moved': moved, 'errors': errors, 'skipped_review': len(plan['moves']) - len(selected), 'cancelled': cancelled}


def sync_moved_inventory(moved, destination):
    """Remove old path references only for successful moves, then index new locations."""
    from app import db
    from app.core.scanner import index_local_folder
    repair_moved_paths(moved)
    paths = {os.path.normcase(str(Path(entry['source']).resolve())) for entry in moved}
    touched = set()
    for record in db.get_all_franchises():
        for season in db.get_seasons_for_franchise(record['id']):
            folder = Path(season.get('season_folder_path') or '')
            files = json.loads(season.get('video_files_json') or '[]')
            remaining = [name for name in files if os.path.normcase(str((folder / name).resolve())) not in paths]
            if len(remaining) == len(files):
                continue
            db.update_season_field(season['id'], 'video_files_json', json.dumps(remaining))
            db.update_season_field(season['id'], 'size_bytes', sum((folder / name).stat().st_size for name in remaining if (folder / name).is_file()))
            if not remaining:
                db.update_season_field(season['id'], 'storage_state', 'NOT_DOWNLOADED')
            touched.add(record['id'])
    for fid in touched:
        db.recalculate_franchise_size(fid)
        db.recalculate_franchise_storage_state(fid)
    for title in sorted({entry['series'] for entry in moved}):
        index_local_folder(str(Path(destination) / title), title)
    if moved:
        db.add_watched_directory(str(Path(destination)))
        repair_moved_paths(moved)


def repair_moved_paths(entries):
    """Relink stale paths using recorded moves and existing destination files."""
    from contextlib import closing
    from app import db
    from app.core.parser import normalize_for_matching

    if not entries:
        return 0, 0

    def key(path):
        from app.core.identity import path_key
        return path_key(path)

    moves = {key(entry['source']): Path(entry['target']) for entry in entries}

    def follow(path):
        seen = set()
        while key(path) in moves and key(path) not in seen and not path.is_file():
            seen.add(key(path))
            path = moves[key(path)]
        return path

    roots = {}
    for entry in entries:
        source = Path(entry['source'])
        if entry.get('series'):
            target = Path(entry['target'])
            release = Path(entry['release'])
            root = target.parents[len(release.parts)]
            for parent in source.parents:
                if parent.parent != parent:
                    roots.setdefault(key(parent), set()).add(root)

    changed_roots, changed_seasons = 0, 0
    aliases = []
    with closing(db.get_connection()) as conn, conn:
        records = conn.execute("SELECT id, display_title, anilist_id, root_folder_path FROM franchises").fetchall()
        for record in records:
            old_root = record['root_folder_path']
            candidates = roots.get(key(old_root), set()) if old_root else set()
            seasons = conn.execute("SELECT * FROM seasons WHERE franchise_id=?", (record['id'],)).fetchall()
            live = set()
            for season in seasons:
                if not season['season_folder_path']:
                    continue
                folder = Path(season['season_folder_path'])
                original = [folder / name for name in json.loads(season['video_files_json'] or '[]')]
                updated = [follow(file) for file in original]
                live.update(file for file in updated if file.is_file())
                if updated == original or not all(file.is_file() for file in updated):
                    continue
                common = Path(os.path.commonpath([str(file.parent) for file in updated]))
                names = [file.relative_to(common).as_posix() for file in updated]
                matching_roots = [root for root in candidates if all(root in file.parents for file in updated)]
                scan_root = matching_roots[0] if len(matching_roots) == 1 else season['scan_root']
                conn.execute(
                    "UPDATE seasons SET season_folder_path=?, video_files_json=?, scan_root=? WHERE id=?",
                    (str(common), json.dumps(names), str(scan_root) if scan_root else None, season['id']),
                )
                changed_seasons += 1
            if not live and len(candidates) == 1:
                candidate = next(iter(candidates))
                matches = [
                    other for other in records
                    if other['id'] != record['id'] and not other['anilist_id']
                    and other['root_folder_path'] and key(other['root_folder_path']) == key(candidate)
                    and normalize_for_matching(other['display_title']) == normalize_for_matching(record['display_title'])
                ]
                if len(matches) == 1:
                    owner = matches[0]['id']
                    indexed = conn.execute(
                        "SELECT season_folder_path, video_files_json FROM seasons WHERE franchise_id=? AND storage_state='ON_DISK'",
                        (owner,),
                    )
                    if any(row['season_folder_path'] and any(
                        (Path(row['season_folder_path']) / file).is_file()
                        for file in json.loads(row['video_files_json'] or '[]')
                    ) for row in indexed):
                        aliases.append((owner, record['id']))
            live_candidates = {candidate for candidate in candidates if any(candidate in file.parents for file in live)}
            if len(live_candidates) == 1 and not any(Path(old_root) in file.parents for file in live):
                target = next(iter(live_candidates))
                if key(target) != key(old_root):
                    conn.execute("UPDATE franchises SET root_folder_path=? WHERE id=?", (str(target), record['id']))
                    changed_roots += 1
        from app.core.identity import relocate
        for entry in entries:
            if not Path(entry['source']).exists() and Path(entry['target']).is_file():
                relocate(conn, entry['source'], entry['target'])
    for owner, original in aliases:
        source, target = db.get_series(owner), db.get_series(original)
        if source["id"] == owner and source["series_member_ids"] == [owner] and target["id"] != owner:
            db.group_with_series(owner, original)
    return changed_roots, changed_seasons


def repair_from_move_journals():
    """Replay completed moves, including renamed files, without touching media."""
    from app import db

    entries = []
    exports = db.DATA_DIR / 'exports'
    for folder in sorted(exports.iterdir()) if exports.is_dir() else ():
        for name in ('move-journal.jsonl', 'rename-journal.jsonl'):
            journal = folder / name
            if not journal.is_file():
                continue
            for line in journal.read_text(encoding='utf-8').splitlines():
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get('event') in ('moved', 'renamed'):
                    entries.append(entry)
    return repair_moved_paths(entries)
