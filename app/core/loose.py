"""Conservative grouping of loose episodes; no filesystem changes during inspection."""
import re
from pathlib import Path
from app.config import VIDEO_EXTENSIONS
from app.core.parser import extract_episode_number, extract_base_anime_name, extract_season_number, normalize_for_matching


def inspect_loose_episodes(root_path):
    root = Path(root_path).resolve()
    files = [p for p in root.iterdir() if p.is_file() and not p.is_symlink()]
    groups, unclassified = {}, []
    for file in files:
        if file.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        episode = extract_episode_number(file.name)
        title = extract_base_anime_name(file.stem)
        title = re.sub(r'[<>:"/\\|?*]', ' ', title).strip(' .-')
        if episode is None or not re.search(r'[a-zA-Z\u3040-\u9fff]', title):
            unclassified.append(str(file))
            continue
        if title.upper() in {'CON', 'PRN', 'AUX', 'NUL'} or re.fullmatch(r'(COM|LPT)\d', title, re.I):
            unclassified.append(str(file))
            continue
        season = extract_season_number(file.stem, 1)
        if season < 1:
            unclassified.append(str(file))
            continue
        key = normalize_for_matching(title) + ':' + str(season)
        group = groups.setdefault(key, {'anime_name': title, 'season_number': season, 'files': [], 'key': key})
        group['files'].append(file)
    items = []
    for group in groups.values():
        destination = root / group['anime_name'] / f"Season {group['season_number']}"
        sources = list(group['files'])
        for file in files:
            if file.suffix.lower() in {'.ass', '.srt', '.vtt', '.sub', '.idx'} and any(file.stem == video.stem or file.stem.startswith(video.stem + '.') for video in group['files']):
                sources.append(file)
        items.append({
            'folder_path': str(root), 'anime_name': group['anime_name'],
            'destination_root': str(destination.parent), 'season_number': group['season_number'],
            'loose_key': group['key'], 'is_loose_group': True,
            'source_files': [str(p) for p in group['files']],
            'video_count': len(group['files']), 'total_size_bytes': sum(p.stat().st_size for p in group['files']),
            'is_organized': False, 'status_badge': f"Season {group['season_number']}",
            'status_reason': f"Loose episodes → {destination.relative_to(root)}",
            'moves': [{'source': str(p), 'target': str(destination / p.name), 'size': p.stat().st_size, 'already_in_place': False} for p in sources],
        })
    return items, unclassified
