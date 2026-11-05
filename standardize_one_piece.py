"""Preview or apply explicitly requested One Piece episode filename standardization."""
import argparse
import csv
import json
import os
import re
import sqlite3
import stat as stat_module
from datetime import datetime
from pathlib import Path
from app.startup import prepare_windowed_logging

prepare_windowed_logging()

EXTENSIONS = {'.mkv', '.mp4', '.avi', '.webm', '.ts'}


def rename_preserving_readonly(source, target):
    if os.name != 'nt':
        os.link(source, target)
        source.unlink()
        return
    try:
        os.rename(source, target)
    except PermissionError:
        attributes = source.stat().st_file_attributes
        if not attributes & stat_module.FILE_ATTRIBUTE_READONLY:
            raise
        os.chmod(source, stat_module.S_IWRITE)
        try:
            os.rename(source, target)
        finally:
            restore = target if target.exists() and not source.exists() else source
            os.chmod(restore, stat_module.S_IREAD)


def identify(filename):
    cleaned = re.sub(r'\[[^]]*\]', '', filename)
    number_only = bool(re.fullmatch(r'\s*-?\s*\d{1,4}(?:v\d+)?\.(?:mkv|mp4|avi|webm|ts)', cleaned, re.I))
    if not number_only and not re.search(r'One[ ._-]*Piece|^EP[ ._-]*\d', cleaned, re.I):
        return None
    if re.search(r'\b(?:movies?|films?|SP\d+)\b|\d+SP\b|Fan[ ._-]+Letter', cleaned, re.I):
        return None
    match = re.search(r'\bEP[ ._-]*(\d{1,4})\b|\s-\s*(\d{1,4})(?:v\d+)?(?=\D|$)|\bEpisode\s+(\d{1,4})\b|^\s*-?\s*(\d{1,4})(?=\.)', cleaned, re.I)
    if not match:
        return None
    episode = int(next(value for value in match.groups() if value))
    if episode < 1:
        return None
    quality = re.search(r'(?<!\d)(480|720|1080|2160)p\b', filename, re.I)
    version = re.search(r'\[v(\d+)\]|\d\s*v(\d+)\b', filename, re.I)
    reedit = bool(re.search(r'One Piece Log|Re-edit', cleaned, re.I))
    title = f"One Piece - {'Re-edit ' if reedit else ''}Episode {episode:04}"
    if quality:
        title += f' [{quality[1]}p]'
    if version:
        title += f' [v{next(value for value in version.groups() if value)}]'
    return {'episode': episode, 'quality': quality[1] if quality else None, 'reedit': reedit, 'title': title}


def build_plan(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('One Piece directory is unavailable')
    moves, untouched, reserved = [], [], set()
    for source in sorted(root.rglob('*')):
        if not source.is_file() or source.is_symlink() or source.suffix.lower() not in EXTENSIONS:
            continue
        info = identify(source.name)
        if info is None or 'Movies' in source.relative_to(root).parts:
            untouched.append(str(source))
            continue
        folder = root / 'Re-edits' if info['reedit'] else source.parent
        # These numbered episode titles were previously mistaken for specials
        # because their prose happened to contain the word "Special".
        if source.parent.name == 'Specials' and info['episode'] in (918, 920):
            folder = root / 'Season 20'
        target = folder / (info['title'] + source.suffix.lower())
        original = target
        copy = 1
        while os.path.normcase(str(target)) in reserved or (target.exists() and target != source):
            copy += 1
            target = original.with_name(f'{original.stem} [Copy {copy:02}]{original.suffix}')
        reserved.add(os.path.normcase(str(target)))
        if target == source:
            continue
        stat = source.stat()
        moves.append({'source': str(source), 'target': str(target), 'bytes': stat.st_size,
                      'mtime_ns': stat.st_mtime_ns, **info})
    return {'root': str(root), 'moves': moves, 'untouched': untouched}


def execute(plan, journal_path):
    root = Path(plan['root']).resolve()
    sources, targets = set(), set()
    for entry in plan['moves']:
        source, target = Path(entry['source']), Path(entry['target'])
        source.resolve().relative_to(root)
        target.resolve().relative_to(root)
        if source.is_symlink() or source.suffix.lower() not in EXTENSIONS:
            raise ValueError('Invalid source file')
        stat = source.stat()
        if (stat.st_size, stat.st_mtime_ns) != (entry['bytes'], entry['mtime_ns']) or target.exists():
            raise ValueError(f'File changed or destination exists: {source}')
        key = os.path.normcase(str(target))
        if key in targets or str(source) in sources:
            raise ValueError('Duplicate move in plan')
        targets.add(key)
        sources.add(str(source))
    moved = []
    from app.core.identity import sync_inventory
    from app.core.file_operations import move_file
    sync_inventory()
    with Path(journal_path).open('x', encoding='utf-8', buffering=1) as journal:
        for entry in plan['moves']:
            source, target = Path(entry['source']), Path(entry['target'])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.resolve().relative_to(root)
            stat = source.stat()
            if (stat.st_size, stat.st_mtime_ns) != (entry['bytes'], entry['mtime_ns']) or target.exists():
                raise ValueError(f'File changed during rename: {source}')
            journal.write(json.dumps({'event': 'planned', **entry}) + '\n')
            journal.flush()
            os.fsync(journal.fileno())
            move_file(source, target, (entry['bytes'], entry['mtime_ns']), rename=rename_preserving_readonly)
            moved.append(entry)
            journal.write(json.dumps({'event': 'renamed', **entry}) + '\n')
            journal.flush()
            os.fsync(journal.fileno())
    return moved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=r'E:\Anime Library\One Piece')
    parser.add_argument('--apply', type=Path)
    args = parser.parse_args()
    output = Path(__file__).resolve().parent / 'data' / 'exports' / ('one-piece-names-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    output.mkdir(parents=True)
    if not args.apply:
        plan = build_plan(args.root)
        (output / 'plan.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
        with (output / 'names.csv').open('w', newline='', encoding='utf-8-sig') as stream:
            writer = csv.DictWriter(stream, fieldnames=['source', 'target', 'episode', 'quality', 'reedit'], extrasaction='ignore')
            writer.writeheader()
            writer.writerows(plan['moves'])
        print(f"Preview: {len(plan['moves'])} renames; {len(plan['untouched'])} unchanged.\n{output}")
        return
    plan = json.loads(args.apply.read_text(encoding='utf-8'))
    from app import db
    db.init_db()
    source = db.get_connection()
    backup = sqlite3.connect(str(output / 'before-renames.db'))
    try:
        source.backup(backup)
    finally:
        source.close()
        backup.close()
    moved = execute(plan, output / 'rename-journal.jsonl')
    from app.core.scanner import index_local_folder
    index_local_folder(plan['root'], 'ONE PIECE')
    print(f"Renamed and reindexed {len(moved)} files.\nJournal: {output}")


if __name__ == '__main__':
    main()
