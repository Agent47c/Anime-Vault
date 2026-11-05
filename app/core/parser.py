"""
Romaji / English folder name parser and .txt line cleaner.
Cleans anime folder names, .txt import lines, and extracts
season / episode info from filenames.
"""

import re
from typing import Optional, Tuple, Dict


# ---------------------------------------------------------------------------
# Season number extraction patterns (ordered by specificity)
# ---------------------------------------------------------------------------
_SEASON_PATTERNS = [
    # "S02", "s01"
    re.compile(r"[Ss](\d{1,2})"),
    # "Season 2", "Season 02"
    re.compile(r"[Ss]eason\s*(\d{1,2})", re.IGNORECASE),
    # "2nd Season", "3rd Season"
    re.compile(r"(\d{1,2})(?:st|nd|rd|th)\s+[Ss]eason", re.IGNORECASE),
    # "Part 2", "Part II"
    re.compile(r"[Pp]art\s*(\d{1,2})"),
    # Roman numerals at end: "... II", "... III"
    re.compile(r"\b(II|III|IV|V|VI|VII|VIII|IX|X)\b"),
]

_ROMAN_MAP = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
}

# Episode patterns for filenames
_EPISODE_PATTERNS = [
    # "E01", "E12", "EP01", "Ep 12"
    re.compile(r"[Ee][Pp]?\s*(\d{1,4})"),
    # "- 01", " - 12v2"
    re.compile(r"\s-\s+(\d{1,4})(?:v\d)?"),
    # "S02E05"
    re.compile(r"[Ss]\d{1,2}[Ee](\d{1,4})"),
    # Just a number at the end after spaces
    re.compile(r"\s(\d{2,4})(?:\s|$|\[|\()"),
]

# Junk tokens to strip from folder/file names
_JUNK_PATTERNS = [
    re.compile(r"\[.*?\]"),                  # [SubGroup], [1080p], etc.
    re.compile(r"\(.*?\)"),                  # (BD), (TV), etc.
    re.compile(r"\b(?:720|1080|2160)[pP]\b"),
    re.compile(r"\b(?:HEVC|x264|x265|AAC|FLAC|BD|BluRay|WEB-?DL|WEBRip)\b", re.IGNORECASE),
    re.compile(r"\b(?:Dual Audio|Multi Sub|BATCH)\b", re.IGNORECASE),
    re.compile(r"[_.]"),                     # Replace underscores/dots with spaces
]


def clean_title(raw: str) -> str:
    """Strip encoding tags, sub-group brackets, resolution markers, etc.
    Returns a cleaned, human-readable anime title."""
    text = raw.strip()
    for pat in _JUNK_PATTERNS:
        if pat.pattern == r"[_.]":
            text = pat.sub(" ", text)
        else:
            text = pat.sub("", text)
    # Collapse whitespace
    text = re.sub(r"\s{2,}", " ", text).strip()
    # Strip leading/trailing dashes
    text = text.strip("- ")
    return text


def extract_season_number(text: str, default: int = 1) -> int:
    """Try to extract a season number from a string.
    Returns 0 for Movies/OVAs/Specials, -1 for Sample/Proof directories,
    or the matched season number (defaulting to `default`).
    """
    # Check for sample / non-media directories
    if re.search(r"\b(?:sample|samples|proof|screens|screenshots)\b", text, re.IGNORECASE):
        return -1

    # Check for specials / movies / OVAs / extra sagas
    if re.search(r"\b(?:movies?|films?|ovas?|onas?|specials?|sp|extras?|bonus|shorts?)\b", text, re.IGNORECASE):
        return 0

    for pat in _SEASON_PATTERNS:
        m = pat.search(text)
        if m:
            val = m.group(1)
            if val in _ROMAN_MAP:
                return _ROMAN_MAP[val]
            try:
                return int(val)
            except ValueError:
                continue
    return default



def _filename_only(filename: str) -> str:
    return str(filename).replace("\\", "/").rsplit("/", 1)[-1]


def classification_filename(filename: str) -> str:
    """Ignore an episode's prose title when testing movie/special markers."""
    return re.split(r"\s-\s*\d{1,4}(?:v\d+)?\s+-\s", _filename_only(filename), maxsplit=1)[0]


def extract_episode_numbers(filename: str) -> list:
    """Read episode identifiers, never resolution, CRC, movie or special numbers."""
    name = _filename_only(filename)
    if re.search(r"\b(?:movies?|films?|specials?|extras?|bonus|samples?|proof|NCOP|NCED|OP|ED)\b|\bSP\d+\b|\d+SP\b", classification_filename(name), re.I):
        return []
    name = re.sub(r"\[[^]]*\]", " ", name)
    name = re.sub(r"\.(?:mkv|mp4|avi|webm|m4v|ts|mov)$", "", name, flags=re.I)
    patterns = [
        r"\b\d{1,2}x(\d{1,4})(?:\s*-\s*(?:\d{1,2}x)?(\d{1,4}))?",
        r"\bS\d{1,2}[ ._-]*E(?:P)?[ ._-]*(\d{1,4})(?:v\d+)?(?:[ ._]*-[ ._]*(?:E(?:P)?)?[ ._]*(\d{1,4})(?:v\d+)?)?",
        r"\bE(?:P(?:ISODE)?)?[ ._-]*(\d{1,4})(?:v\d+)?(?:[ ._]*-[ ._]*(?:E(?:P)?)?[ ._]*(\d{1,4})(?:v\d+)?)?",
        r"\s-\s*(\d{1,4})(?:[ ._]*v\d+)?(?:[ ._]*-[ ._]*(\d{1,4})(?:v\d+)?)?(?!\d)",
        r"^\s*(\d{1,4})(?:v\d+)?(?:[ ._]*-[ ._]*(\d{1,4}))?(?:\s|$|[.(])",
        r"[ ._](\d{1,4})(?:v\d+)?(?=\s*$|[ ._(])",
    ]
    for pattern in patterns:
        match = re.search(pattern, name, re.I)
        if not match:
            continue
        start = int(match.group(1))
        end = int(match.group(2)) if match.lastindex and match.lastindex > 1 and match.group(2) else start
        if start in (480, 720, 1080, 2160) and re.search(str(start) + r"p\b", name, re.I):
            continue
        if 0 < start <= end < 10000 and end - start < 1000:
            return list(range(start, end + 1))
    return []


def extract_episode_number(filename: str) -> Optional[int]:
    numbers = extract_episode_numbers(filename)
    return numbers[0] if numbers else None


def extract_episode_range(text: str) -> Optional[Tuple[int, int]]:
    """Only trust explicit episode labels, not arbitrary years or movie ranges."""
    match = re.search(r"\bEP?(?:ISODES?)?[ ._-]*(\d{1,4})\s*[-–]\s*(\d{1,4})(?!\d)", text, re.I)
    if match:
        start, end = map(int, match.groups())
        if 0 < start <= end < 10000:
            return start, end
    return None


def extract_base_anime_name(text: str) -> str:
    """Extract the base anime name, stripping season/episode markers."""
    cleaned = clean_title(text)
    # Remove season markers
    for pat in _SEASON_PATTERNS:
        cleaned = pat.sub("", cleaned)
    # Remove episode markers
    for pat in _EPISODE_PATTERNS:
        cleaned = pat.sub("", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip("- ")
    return cleaned if cleaned else text.strip()


def parse_txt_line(line: str) -> Optional[Dict[str, str]]:
    """Parse a single line from a .txt import file.
    Returns dict with 'title' and optional 'notes', or None for blank/comment lines.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    # Check for inline notes after |, //, or --
    notes = ""
    for sep in [" // ", " -- ", " | "]:
        if sep in line:
            parts = line.split(sep, 1)
            line = parts[0].strip()
            notes = parts[1].strip()
            break

    title = clean_title(line)
    if not title:
        return None

    return {"title": title, "notes": notes}


def parse_filename(filename: str) -> Dict[str, any]:
    """Parse a video filename into components.
    Returns dict with 'base_name', 'season', 'episode', 'clean_name'."""
    name_no_ext = re.sub(r"\.\w{2,4}$", "", filename)
    return {
        "base_name": extract_base_anime_name(name_no_ext),
        "season": extract_season_number(name_no_ext),
        "episode": extract_episode_number(name_no_ext),
        "clean_name": clean_title(name_no_ext),
    }


def normalize_for_matching(title: str) -> str:
    """Normalize a title for fuzzy matching: lowercase, strip non-alphanumeric."""
    return re.sub(r"[^a-z0-9]", "", title.lower())


def analyze_season_health(video_files: list, expected_total: Optional[int] = None,
                          episode_start=None, episode_end=None, folder_name="",
                          relation_type="SEASON", airing_status=None) -> Dict[str, any]:
    """Check coverage inside verified boundaries, otherwise only observed internal gaps."""
    from collections import Counter
    counts = Counter()
    unrecognized, excluded = [], []
    if relation_type in ("MOVIE", "SPECIAL", "OVA", "EXTRAS"):
        return {"health_status": "Not episode-numbered", "found_count": len(video_files), "file_count": len(video_files), "expected_total": None, "missing_episodes": [], "duplicate_episodes": [], "unrecognized_files": [], "excluded_files": [], "range_verified": False, "range_note": "Movies and specials are checked separately", "episode_start": None, "episode_end": None}
    for filename in video_files:
        numbers = extract_episode_numbers(filename)
        if numbers:
            counts.update(numbers)
        elif re.search(r"\b(?:movies?|films?|specials?|extras?|bonus|NCOP|NCED|OP|ED)\b|\bSP\d+\b|\d+SP\b", _filename_only(filename), re.I):
            excluded.append(filename)
        else:
            unrecognized.append(filename)
    found = sorted(counts)
    declared = (episode_start, episode_end) if episode_start and episode_end else extract_episode_range(folder_name)
    verified = bool(declared)
    note = "Folder episode range" if verified else "Boundaries unverified; only internal gaps are checked"
    if declared and found and (min(found) < declared[0] or max(found) > declared[1]):
        # A mislabeled folder must not create an invented season boundary.
        declared = None
        verified = False
        note = "Folder range conflicts with files; boundaries unverified"
    if declared:
        start, end = declared
    elif expected_total and expected_total > 0 and (not found or max(found) <= expected_total):
        start, end = 1, expected_total
        verified = True
        note = "Expected count from matched season metadata"
    elif found:
        start, end = min(found), max(found)
    else:
        start, end = None, None
    if airing_status == "NOT_YET_RELEASED":
        start, end = None, None
        note = "Unreleased; not counted as missing"
    missing = [ep for ep in range(start, end + 1) if ep not in counts] if start and end else []
    duplicates = [ep for ep, count in counts.items() if count > 1]
    status = "Missing Episodes" if missing else "Duplicate Episodes" if duplicates else "Needs Metadata Review" if unrecognized else "Healthy" if verified else "Boundaries unverified"
    return {"health_status": status, "found_count": len(found), "file_count": len(video_files), "expected_total": end - start + 1 if verified and start and end else None, "missing_episodes": missing, "duplicate_episodes": sorted(duplicates), "unrecognized_files": unrecognized, "excluded_files": excluded, "range_verified": verified, "range_note": note, "episode_start": start, "episode_end": end}
