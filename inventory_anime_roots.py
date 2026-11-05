r"""Read-only filesystem inventory. No database access, network calls or media changes.

Run: python inventory_anime_roots.py
Or:  python inventory_anime_roots.py "E:\New Anime Seasons" "E:\Seen Anime"
"""
import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from app.core.parser import extract_episode_numbers, extract_base_anime_name, extract_season_number

VIDEOS = {'.mkv', '.mp4', '.avi', '.webm', '.ts', '.m4v', '.mov'}
DEFAULT_ROOTS = [r'E:\New Anime Seasons', r'E:\Seen Anime']


def scan_root(root):
    root = Path(root).resolve()
    report = {'root': str(root), 'files': [], 'folders': [], 'errors': [], 'skipped_links': []}
    if not root.is_dir():
        report['errors'].append('Directory is missing or unavailable')
        return report
    def onerror(error):
        report['errors'].append(str(error))
    for current, directories, filenames in os.walk(root, followlinks=False, onerror=onerror):
        parent = Path(current)
        for directory in list(directories):
            if (parent / directory).is_symlink() or (hasattr(os.path, 'isjunction') and os.path.isjunction(parent / directory)):
                directories.remove(directory)
                report['skipped_links'].append(str(parent / directory))
        report['folders'].append(parent.relative_to(root).as_posix())
        for filename in sorted(filenames):
            path = parent / filename
            if path.is_symlink():
                report['skipped_links'].append(str(path))
                continue
            try:
                size = path.stat().st_size
                video = path.suffix.lower() in VIDEOS
                relative = path.relative_to(root)
                episodes = extract_episode_numbers(filename) if video else []
                report['files'].append({
                    'path': str(path), 'relative_path': relative.as_posix(),
                    'folder': parent.relative_to(root).as_posix(), 'name': filename,
                    'extension': path.suffix.lower(), 'bytes': size, 'is_video': video,
                    'loose_at_root': parent == root,
                    'top_folder': relative.parts[0] if len(relative.parts) > 1 else '',
                    'candidate_title': extract_base_anime_name(path.stem) if video and episodes else '',
                    'season_hint': extract_season_number(path.stem) if video else None,
                    'episode_numbers': episodes,
                })
            except OSError as error:
                report['errors'].append(f'{path}: {error}')
    videos = [file for file in report['files'] if file['is_video']]
    report['summary'] = {
        'files': len(report['files']), 'folders': len(report['folders']),
        'video_files': len(videos), 'video_bytes': sum(file['bytes'] for file in videos),
        'loose_videos': sum(file['loose_at_root'] for file in videos),
        'videos_with_episode_numbers': sum(bool(file['episode_numbers']) for file in videos),
        'video_extensions': dict(Counter(file['extension'] for file in videos)),
    }
    return report


def write_reports(roots, output):
    output = Path(output).resolve()
    for root in roots:
        try:
            output.relative_to(Path(root).resolve())
        except ValueError:
            continue
        raise ValueError('Choose an output directory outside the anime roots.')
    results = []
    for root in roots:
        print(f'Inspecting {root} (file names and sizes only)…', flush=True)
        result = scan_root(root)
        results.append(result)
        print(result.get('summary', result['errors']), flush=True)
    # Compare overlapping selected roots without counting their files twice.
    videos = {os.path.normcase(file['path']): file for result in results for file in result['files'] if file['is_video']}
    candidates, duplicates = defaultdict(list), defaultdict(list)
    for file in videos.values():
        if file['candidate_title']:
            key = re.sub(r'[^a-z0-9]', '', file['candidate_title'].lower())
            candidates[key].append(file['path'])
        duplicates[(file['name'].casefold(), file['bytes'])].append(file['path'])
    report = {
        'generated_at': datetime.now().astimezone().isoformat(),
        'read_only': True,
        'limitations': [
            'Candidate titles are filename guesses, not verified anime or series counts.',
            'Matching filenames and sizes indicate possible duplicates, not identical contents.',
            'No missing-episode or unreleased-movie claims are made from this inventory.',
            'Reports contain full local file paths. Review before sharing publicly.',
        ],
        'unique_video_paths': len(videos),
        'unique_video_bytes': sum(file['bytes'] for file in videos.values()),
        'candidate_groups': dict(candidates),
        'possible_duplicates': [paths for paths in duplicates.values() if len(paths) > 1],
        'roots': results,
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / 'inventory.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    columns = ['root', 'relative_path', 'folder', 'name', 'extension', 'bytes', 'is_video', 'loose_at_root', 'top_folder', 'candidate_title', 'season_hint', 'episode_numbers']
    with (output / 'files.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for result in results:
            for file in result['files']:
                row = {key: file.get(key, '') for key in columns}
                row['root'] = result['root']
                row['episode_numbers'] = ','.join(map(str, file['episode_numbers']))
                writer.writerow(row)
    text = ['# Anime directory inventory', '', 'Read-only inspection; no media or app database changes.', '']
    for result in results:
        text += [f"## {result['root']}", '']
        summary = result.get('summary', {})
        text += [f"- Video files: {summary.get('video_files', 0):,}", f"- Video size: {summary.get('video_bytes', 0) / 1024**3:.2f} GiB", f"- Loose videos: {summary.get('loose_videos', 0):,}", f"- Read errors: {len(result['errors'])}", '']
        by_folder = defaultdict(list)
        for file in result['files']:
            if file['is_video']:
                by_folder[file['folder']].append(file)
        for folder, files in sorted(by_folder.items()):
            text.append(f"- `{folder}`: {len(files)} videos, {sum(f['bytes'] for f in files) / 1024**3:.2f} GiB")
        text += ['', 'Errors:', *result['errors'], ''] if result['errors'] else ['']
    text += ['## Interpretation', '', *report['limitations'], '', f"Possible duplicate groups: {len(report['possible_duplicates'])}", 'Full filenames and numbering hints are in files.csv and inventory.json.']
    (output / 'summary.md').write_text('\n'.join(text), encoding='utf-8')
    print(f'Reports saved to {output}', flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('roots', nargs='*', help='Anime directories; defaults to your two known roots')
    parser.add_argument('--output', type=Path, help='New report folder outside the anime roots')
    args = parser.parse_args()
    output = args.output or Path(__file__).resolve().parent / 'data' / 'exports' / ('root-inventory-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    write_reports(args.roots or DEFAULT_ROOTS, output)


if __name__ == '__main__':
    main()
