"""
Unfiltered AniList GraphQL client.
Queries AniList without filtering out adult/mature titles.
Supports Romaji folder matching, English title resolution,
poster download, and sequel-tree traversal for franchise grouping.
"""

import json
import time
import html
import threading
from contextlib import contextmanager
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List

from app.config import ANILIST_GRAPHQL_URL, COVERS_DIR

# ---------------------------------------------------------------------------
# Rate-limit: AniList allows ~90 req/min; we pace ourselves
# ---------------------------------------------------------------------------
_request_lock = threading.Lock()
_last_request_time = 0.0
_MIN_INTERVAL = 0.7  # seconds between requests
_cancellation = threading.local()


def _check_cancelled():
    if getattr(_cancellation, 'check', lambda: False)():
        raise InterruptedError('Search cancelled')


@contextmanager
def cancellable(check):
    previous = getattr(_cancellation, 'check', lambda: False)
    _cancellation.check = check
    try:
        _check_cancelled()
        yield
    finally:
        _cancellation.check = previous


def _wait(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        _check_cancelled()
        time.sleep(max(0, min(0.05, end - time.monotonic())))


def _rate_limit():
    global _last_request_time
    with _request_lock:
        now = time.monotonic()
        delay = _MIN_INTERVAL - (now - _last_request_time)
        if delay > 0:
            _wait(delay)
        _check_cancelled()
        _last_request_time = time.monotonic()


# ---------------------------------------------------------------------------
# GraphQL query templates
# ---------------------------------------------------------------------------
_SEARCH_QUERY = """
query ($search: String, $page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    media(search: $search, type: ANIME, sort: SEARCH_MATCH) {
      id
      idMal
      title {
        english
        romaji
        native
      }
      bannerImage
    averageScore
    description(asHtml: false)
      genres
      isAdult
      format
      seasonYear
      status
      episodes
      coverImage {
        large
        medium
      }
      nextAiringEpisode {
        episode
        airingAt
      }
      relations {
        edges {
          relationType
          node {
            id
            title {
              english
              romaji
              native
            }
            format
            synonyms
            status
            episodes
            isAdult
            coverImage {
              large
              medium
            }
            nextAiringEpisode {
              episode
              airingAt
            }
          }
        }
      }
    }
  }
}
"""

_BY_ID_QUERY = """
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    id
    idMal
    title {
      english
      romaji
      native
    }
    bannerImage
    averageScore
    description(asHtml: false)
    genres
    isAdult
    format
    status
    episodes
    coverImage {
      large
      medium
    }
    nextAiringEpisode {
      episode
      airingAt
    }
    relations {
      edges {
        relationType
        node {
          id
          title {
            english
            romaji
            native
          }
          format
          synonyms
          status
          episodes
          isAdult
          coverImage {
            large
            medium
          }
          nextAiringEpisode {
            episode
            airingAt
          }
        }
      }
    }
  }
}
"""


# ---------------------------------------------------------------------------
# Core API functions
# ---------------------------------------------------------------------------
def _graphql_request(query: str, variables: Dict) -> Optional[Dict]:
    """Execute a GraphQL request against AniList. Returns JSON data or None."""
    _rate_limit()
    try:
        resp = requests.post(
            ANILIST_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            timeout=10,
        )
        _check_cancelled()
        if resp.status_code == 429:
            # A later explicit refresh may retry; never recurse indefinitely.
            return None
        resp.raise_for_status()
        return resp.json().get("data")
    except requests.RequestException:
        return None


def search_anime(query: str, page: int = 1, per_page: int = 5) -> List[Dict[str, Any]]:
    """Search AniList for anime matching the query (unfiltered — includes adult)."""
    data = _graphql_request(_SEARCH_QUERY, {
        "search": query, "page": page, "perPage": per_page,
    })
    if not data or "Page" not in data:
        return []
    from app.preferences import enabled
    return [media for media in data["Page"]["media"] if enabled("allow_mature") or not media.get("isAdult")]


def get_anime_by_id(anilist_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single anime by AniList ID."""
    data = _graphql_request(_BY_ID_QUERY, {"id": anilist_id})
    if not data:
        return None
    return data.get("Media")


# ---------------------------------------------------------------------------
# Title resolution helpers
# ---------------------------------------------------------------------------
def resolve_display_title(media: Dict) -> str:
    """Apply the display rule: English → Romaji → 'Unknown'."""
    title = media.get("title", {})
    from app.preferences import enabled
    order = ("english", "romaji", "native") if enabled("prefer_english") else ("romaji", "english", "native")
    return next((title[key] for key in order if title.get(key)), "Unknown")


def extract_franchise_data(media: Dict) -> Dict[str, Any]:
    """Convert raw AniList media JSON into a dict suitable for db.upsert_franchise."""
    title = media.get("title", {})
    desc = media.get("description", "") or ""
    # Clean HTML entities from description
    desc = desc.replace("<br>", "\n").replace("<br/>", "\n")
    import re
    desc = html.unescape(re.sub(r"<[^>]+>", "", desc))

    return {
        "anilist_id": media["id"],
        "mal_id": media.get("idMal"),
        "display_title": resolve_display_title(media),
        "title_en": title.get("english"),
        "title_romaji": title.get("romaji"),
        "title_native": title.get("native"),
        "synopsis": desc,
        "metadata_json": json.dumps(media),
        "genres": json.dumps(media.get("genres", [])),
        "is_adult": 1 if media.get("isAdult") else 0,
    }


def extract_season_data(media: Dict, franchise_id: int,
                         season_number: int = 1,
                         relation_type: str = "SEASON") -> Dict[str, Any]:
    """Convert raw AniList media JSON into a dict suitable for db.upsert_season."""
    title = media.get("title", {})
    airing = media.get("nextAiringEpisode")

    # Map AniList status to our status
    status_map = {
        "FINISHED": "FINISHED",
        "RELEASING": "RELEASING",
        "NOT_YET_RELEASED": "NOT_YET_RELEASED",
        "CANCELLED": "FINISHED",
        "HIATUS": "RELEASING",
    }

    return {
        "franchise_id": franchise_id,
        "anilist_id": media["id"],
        "season_number": season_number,
        "relation_type": relation_type,
        "title_display": title.get("english") or title.get("romaji") or "Unknown",
        "title_romaji": title.get("romaji"),
        "episodes_total": media.get("episodes"),
        "airing_status": status_map.get(media.get("status"), "FINISHED"),
        "next_airing_ep": airing.get("episode") if airing else None,
        "next_airing_at": airing.get("airingAt") if airing else None,
        "storage_state": "NOT_DOWNLOADED",
    }


# ---------------------------------------------------------------------------
# Poster / Cover download
# ---------------------------------------------------------------------------
def download_cover(media: Dict, franchise_id: int) -> Optional[str]:
    """Return a validated, provider/version-cached cover (legacy ID fallback)."""
    cover = media.get("coverImage") or {}
    url = cover.get("extraLarge") or cover.get("large") or cover.get("medium")
    return _cached_artwork(media, 'cover', url, f"{franchise_id}.jpg")


def download_banner(media: Dict, franchise_id: int) -> Optional[str]:
    return _cached_artwork(media, 'banner', media.get("bannerImage"), f"{franchise_id}-banner.jpg")


_artwork_locks_guard = threading.Lock()
_artwork_locks = {}


def _cached_artwork(media, kind, url, legacy_filename):
    """Provider + URL version cache; missing artwork persists until URL changes."""
    if not media.get('id'):
        return _download_artwork(url, legacy_filename)
    import hashlib
    from contextlib import closing
    from app import db
    provider = 'anilist:' + str(media['id'])
    version = hashlib.sha256((url or 'absent').encode()).hexdigest()[:24]
    cache_key = (provider, kind, version)
    with _artwork_locks_guard:
        lock = _artwork_locks.setdefault(cache_key, threading.Lock())
    while not lock.acquire(timeout=0.05):
        _check_cancelled()
    try:
        _check_cancelled()
        with closing(db.get_connection()) as conn:
            row = conn.execute('SELECT * FROM artwork_assets WHERE provider_id=? AND kind=? AND version=?',cache_key).fetchone()
        if row:
            if row['state'] == 'ABSENT' or (row['state'] == 'FAILED' and row['retry_at'] > time.time()):
                return None
            if row['state'] == 'READY' and (COVERS_DIR / row['filename']).is_file():
                from PyQt5.QtGui import QImage
                if not QImage(str(COVERS_DIR / row['filename'])).isNull():
                    return row['filename']
        filename = f"anilist-{media['id']}-{kind}-{version}.jpg"
        result = _download_artwork(url, filename) if url else None
        with closing(db.get_connection()) as conn, conn:
            conn.execute('INSERT OR REPLACE INTO artwork_assets VALUES (?,?,?,?,?,?)',
                         (*cache_key,result,'READY' if result else ('FAILED' if url else 'ABSENT'),0 if result or not url else time.time()+3600))
        return result
    finally:
        lock.release()


def _download_artwork(url, filename):
    if not url:
        return None
    from PyQt5.QtGui import QImage
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        _check_cancelled()
        resp = requests.get(url, timeout=15)
        _check_cancelled()
        resp.raise_for_status()
        if QImage.fromData(resp.content).isNull():
            return None
        destination = COVERS_DIR / filename
        import uuid
        temporary = destination.with_suffix('.' + uuid.uuid4().hex + '.download')
        temporary.write_bytes(resp.content)
        temporary.replace(destination)
        return filename
    except (requests.RequestException, OSError):
        return None
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Franchise tree traversal — gather sequels, movies, OVAs
# ---------------------------------------------------------------------------
_ALLOWED_FORMATS = {"TV", "TV_SHORT", "MOVIE", "OVA", "ONA", "SPECIAL"}
_RELATION_TO_TYPE = {
    "SEQUEL": "SEASON",
    "PREQUEL": "SEASON",
    "SIDE_STORY": "SPECIAL",
    "ALTERNATIVE": "SPECIAL",
    "SPIN_OFF": "SPECIAL",
}


def traverse_franchise_tree(root_media: Dict) -> List[Dict[str, Any]]:
    """Walk the relations tree from a root anime and return all related entries
    that should be grouped under the same franchise.
    Returns list of dicts: {media, relation_type, season_number}."""
    visited = {root_media["id"]}
    results = []
    queue = [(root_media, "SEASON", 1)]
    season_counter = 1

    while queue:
        media, rel_type, season_num = queue.pop(0)
        results.append({
            "media": media,
            "relation_type": rel_type,
            "season_number": season_num,
        })

        edges = media.get("relations", {}).get("edges", [])
        for edge in edges:
            node = edge.get("node", {})
            nid = node.get("id")
            if nid in visited:
                continue
            node_format = node.get("format", "")
            if node_format not in _ALLOWED_FORMATS:
                continue

            visited.add(nid)
            edge_type = edge.get("relationType", "")
            mapped_type = _RELATION_TO_TYPE.get(edge_type)

            if not mapped_type:
                continue

            if edge_type == "SEQUEL":
                season_counter += 1
                sn = season_counter
            elif node_format in ("MOVIE", "OVA", "ONA", "SPECIAL"):
                mapped_type = node_format
                sn = 0
            else:
                sn = season_counter

            queue.append((node, mapped_type, sn))

    return results
