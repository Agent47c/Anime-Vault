"""Conservative episode coverage and released-movie matching."""
import json
import re
from pathlib import Path
from difflib import SequenceMatcher
from app.core.parser import analyze_season_health, extract_episode_numbers, extract_episode_range


def season_health(season):
    from app.core.identity import mapped_inventory_files
    files = mapped_inventory_files(season)
    # Provider counts describe a matched release, not arbitrary local arc folders.
    expected = season.get("episodes_total") if not season.get("local_scan_key") or season.get("numbering_source") == "metadata" else None
    boundary = aired_boundary(season)
    # Total episodes on an airing release includes future installments.
    if season.get('airing_status') not in ('FINISHED', None):
        expected = None
    result = analyze_season_health(
        files, expected, season.get("episode_start"), season.get("episode_end"),
        season.get("title_display") or Path(season.get("season_folder_path") or "").name,
        season.get("relation_type", "SEASON"), season.get("airing_status"),
    )
    result['file_count'] = len(json.loads(season.get('video_files_json') or '[]'))
    if boundary is not None:
        result['missing_episodes'] = [ep for ep in result['missing_episodes'] if ep <= boundary]
    if season.get('airing_status') == 'RELEASING' and boundary is None:
        # Without a release timestamp use only observed internal gaps, not folder
        # boundaries which may include announced episodes.
        observed = sorted({n for name in files for n in extract_episode_numbers(name)})
        result['missing_episodes'] = [ep for ep in result['missing_episodes'] if observed and min(observed) < ep < max(observed)]
        result['range_note'] = 'Release boundary unverified; only internal gaps are checked'
    if not result['missing_episodes'] and result['health_status'] == 'Missing Episodes':
        result['health_status'] = 'Boundaries unverified' if boundary is None else 'Healthy'
    return result


def aired_boundary(season, now=None):
    import time
    now = time.time() if now is None else now
    if season.get('airing_status') == 'NOT_YET_RELEASED':
        return 0
    episode, stamp = season.get('next_airing_ep'), season.get('next_airing_at')
    if isinstance(episode, int) and episode > 0 and isinstance(stamp, (int, float)):
        return episode - 1 if stamp > now else episode
    return None


def episode_inventory(seasons, continuous=False):
    """Root files may fill gaps in an arc; re-edits and movies never fill TV gaps."""
    all_episodes = set()
    paths = set()
    main = [s for s in seasons if s.get("relation_type") == "SEASON" and s.get("storage_state") == "ON_DISK"]
    absolute = continuous or any(
        (s.get("episode_start") or 0) > 1
        or (extract_episode_range(s.get("title_display") or "") or (0, 0))[0] > 1
        for s in main
    )
    unique_count = 0
    relative_keys = set()
    relative_seasons = set()
    folder_ranges = {}
    for season in main:
        local_episodes = set()
        for filename in json.loads(season.get("video_files_json") or "[]"):
            path = str((Path(season.get("season_folder_path") or "") / filename).resolve())
            if path in paths:
                continue
            paths.add(path)
            numbers = extract_episode_numbers(filename)
            token = re.search(r'\bS(\d{1,2})[ ._-]*E\d+', Path(filename).name, re.I)
            if continuous and token:
                relative_keys.update((int(token[1]), number) for number in numbers)
                relative_seasons.add(season['id'])
            else:
                local_episodes.update(numbers)
        if local_episodes:
            folder_ranges[season["id"]] = (min(local_episodes), max(local_episodes))
        all_episodes.update(local_episodes)
        unique_count += len(local_episodes)
    health = {}
    for season in main:
        result = season_health(season)
        if absolute and season['id'] not in relative_seasons:
            result["missing_episodes"] = [ep for ep in result["missing_episodes"] if ep not in all_episodes]
        health[season["id"]] = result
    missing = sorted(set(range(min(all_episodes), max(all_episodes) + 1)) - all_episodes) if continuous and all_episodes else []
    bounds = [aired_boundary(season) for season in main]
    known = [bound for bound in bounds if bound is not None]
    if continuous and known:
        missing = [ep for ep in missing if ep <= max(known)]
    return {"folder_ranges": folder_ranges, "missing_episodes": missing, "unique_episode_count": len(all_episodes) + len(relative_keys) if absolute else unique_count, "numbering": "absolute with unverified season-relative files" if relative_keys else "absolute" if absolute else "per-season or unverified", "episodes": sorted(all_episodes), "seasons": health}


def _movie_title(value):
    text = str(value).replace("\\", "/").rsplit("/", 1)[-1]
    text = re.sub(r"\.(?:mkv|mp4|avi|webm)$", "", text, flags=re.I)
    text = re.sub(r"\[[^]]*\]|\([^)]*\)", " ", text)
    text = text.replace("_", " ").lower()
    text = re.sub(r"^op\b", "one piece", text)
    text = re.sub(r"\bmovies?\s*\d+\b", " ", text)
    text = re.sub(r"\b(?:480p|720p|1080p|2160p|bd|hevc|x26[45]|dubbed|dual|audio|eng|sub|multi|10bit|aac|katmoviehd|info)\b", " ", text)
    return re.sub(r"[^a-z0-9]", "", text)


def movie_inventory(seasons, media):
    files = []
    for season in seasons:
        if season.get("relation_type") == "MOVIE" and season.get("storage_state") == "ON_DISK":
            files.extend(json.loads(season.get("video_files_json") or "[]"))
    released, upcoming, unknown = {}, {}, {}
    candidates = [media] if media and media.get("format") == "MOVIE" else []
    candidates += [edge.get("node") or {} for edge in (media or {}).get("relations", {}).get("edges", [])]
    for node in candidates:
        if node.get("format") != "MOVIE" or not node.get("id"):
            continue
        title = node.get("title") or {}
        entry = {"id": node["id"], "title": title.get("english") or title.get("romaji") or "Unknown movie", "aliases": [v for v in title.values() if v] + (node.get("synonyms") or [])}
        if node.get("status") == "NOT_YET_RELEASED":
            upcoming[node["id"]] = entry
        elif node.get("status") in ("FINISHED", "RELEASING"):
            released[node["id"]] = entry
        else:
            unknown[node["id"]] = entry
    scores = []
    for mid, entry in released.items():
        for index, filename in enumerate(files):
            local = _movie_title(filename)
            for alias in entry["aliases"]:
                expected = _movie_title(alias)
                if not local or not expected:
                    continue
                score = SequenceMatcher(None, local, expected).ratio()
                if local == expected or (len(expected) >= 12 and expected in local):
                    score = 1.0
                if score >= .88:
                    scores.append((score, mid, index))
    matched, used = {}, set()
    for score, mid, index in sorted(scores, reverse=True):
        if mid not in matched and index not in used:
            matched[mid] = files[index]
            used.add(index)
    return {
        "released_count": len(released), "matched_count": len(matched),
        "not_matched": [entry for mid, entry in released.items() if mid not in matched],
        "upcoming": list(upcoming.values()), "unknown_release": list(unknown.values()),
        "unmatched_local_files": [name for index, name in enumerate(files) if index not in used],
        "catalog_available": bool(media),
    }


def missing_episodes_through(files, latest):
    """Extend the observed interval through the latest known release."""
    if not isinstance(latest, int) or not 0 < latest < 10000:
        return []
    found = {episode for filename in files for episode in extract_episode_numbers(filename)}
    start = min(found, default=1)
    return [episode for episode in range(start, latest + 1) if episode not in found]


def missing_episode_notice(missing, root):
    from itertools import groupby

    labels = []
    for _, group in groupby(enumerate(missing), lambda item: item[1] - item[0]):
        numbers = [item[1] for item in group]
        if len(numbers) <= 2:
            labels.extend(map(str, numbers))
        else:
            labels.append(f"{numbers[0]}\u2013{numbers[-1]}")
    noun = "Episode" if len(missing) == 1 else "Episodes"
    verb = "is" if len(missing) == 1 else "are"
    return (f"{noun} {', '.join(labels)} {verb} not available locally. "
            f"Download the missing episodes and put them in {root}, then Refresh the library.")


def release_availability_notice(files, episode, root, airing_at=None, warnings=False, now=None):
    """Separate scheduled episodes from gaps in the local released interval."""
    import time
    from datetime import datetime
    now = time.time() if now is None else now
    found = {number for filename in files for number in extract_episode_numbers(filename)}
    try:
        stamp = float(airing_at) if airing_at is not None else None
    except (ValueError, TypeError):
        stamp = None
    if not isinstance(episode, int) or not 0 < episode < 10000:
        return "Episode release information is unavailable."
    upcoming = bool(stamp and stamp > now)
    if stamp is None:
        latest = max(found, default=0)
        prefix = f"Episode {episode}'s release date is unverified. Only gaps between local episodes are checked."
    elif upcoming:
        latest = episode - 1
        date = datetime.fromtimestamp(stamp).strftime("%d %b %Y")
        prefix = f"Episode {episode} is scheduled for {date}; it is excluded from missing episodes."
    else:
        latest = episode
        prefix = ""
    if warnings:
        return (prefix + " Some folders could not be read; missing episodes cannot be fully checked.").strip()
    missing = missing_episodes_through(files, latest)
    if missing:
        return (prefix + " " + missing_episode_notice(missing, root)).strip()
    suffix = f"No missing episodes found in the checked range through {latest}." if latest else "No local episode range could be checked."
    return (prefix + " " + suffix).strip()
