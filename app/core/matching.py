"""Match a local release while keeping the series and season identities separate."""
import json
import time
from contextlib import closing
from app import db
from app.core import anilist_client as client
from app.core.parser import extract_season_number


def _series_conflict(selections,roots):
    """Name all differing provider groups without guessing which one is wrong."""
    groups={}
    for (media,_),root in zip(selections,roots):
        group=groups.setdefault(root['id'],(root,[]))
        group[1].append(media)
    lines=['These releases are not verified seasons of the same series.',
           '', 'Conflicting selections:']
    for root,releases in groups.values():
        lines.append('Series: '+client.resolve_display_title(root))
        for release in releases:
            lines.append('  • '+client.resolve_display_title(release))
    lines.extend(['','Deselect the conflicting release(s) and try again, or group existing library entries manually.'])
    return '\n'.join(lines)


def series_root(media):
    root = cursor = media
    formats = {"ONA"} if media.get("format") == "ONA" else {"TV", "TV_SHORT"}
    visited = {root["id"]}
    for _ in range(12):
        prequels = [edge.get("node") or {} for edge in (cursor.get("relations") or {}).get("edges", []) if edge.get("relationType") == "PREQUEL" and (edge.get("node") or {}).get("format") in formats]
        if len(prequels) != 1 or prequels[0].get("id") in visited:
            break
        earlier = client.get_anime_by_id(prequels[0]["id"])
        if not earlier:
            raise ValueError('Could not verify the earlier season for "'+client.resolve_display_title(media)+'". Retry when AniList is available.')
        cursor = earlier
        if earlier.get("format", "TV") in formats:
            root = earlier
        visited.add(earlier["id"])
    return root


def review_selection(fid,selections):
    if not db.get_franchise(fid):raise ValueError('This entry changed. Return to the Library and select its current card.')
    if len({media['id'] for media,_ in selections})!=len(selections):raise ValueError('Select each release only once.')
    assigned=[sid for _,sid in selections if sid is not None]
    if len(set(assigned))!=len(assigned):raise ValueError('Assign each release to a different local season.')
    seasons={s['id']:s for s in db.get_series_seasons(fid)}
    roots=[series_root(media) for media,_ in selections]
    if len({root['id'] for root in roots})!=1:raise ValueError(_series_conflict(selections,roots))
    for media,sid in selections:
        if sid is not None and (sid not in seasons or seasons[sid].get('storage_state')!='ON_DISK'):
            raise ValueError('A selected local season changed. Select its folder again.')
        if sid is not None and media.get('status')=='NOT_YET_RELEASED':
            raise ValueError('An announced release cannot be assigned to an existing local season. Choose Metadata only for that release.')
    return dict(root=roots[0],selections=selections,seasons=seasons)


def apply_release_match(fid, media, season_id=None, additional=(), use_local=True):
    if additional:review_selection(fid,[(media,season_id),*additional])
    elif season_id is not None and media.get('status')=='NOT_YET_RELEASED':
        raise ValueError('An announced release cannot be assigned to an existing local season. Choose Metadata only.')
    selected = {key: value for key, value in media.items() if key != "_preview_cover"}
    root = series_root(selected)
    for release, _ in additional:
        release_root=series_root(release)
        if release_root["id"] != root["id"]:
            raise ValueError(_series_conflict([(selected,season_id),(release,None)],[root,release_root]))
    source = db.get_franchise(fid)
    if not source:
        raise ValueError("This library entry no longer exists. Refresh the library.")
    continuous = db.uses_continuous_episodes(source)
    if continuous and (season_id is not None or additional):
        raise ValueError("Choose one series match for all continuing episodes.")
    seasons = db.get_series_seasons(fid)
    owned = [s for s in seasons if s.get("storage_state") == "ON_DISK" and s.get("relation_type") == "SEASON"]
    if season_id is not None:
        owned = [s for s in owned if s["id"] == season_id]
        if not owned:
            raise ValueError("The selected local season was not found.")
    # A franchise-wide match must never silently relink several local seasons.
    if not use_local or continuous:
        owned = []
    if len(owned) > 1:
        raise ValueError("This anime contains several local seasons. Open Rematch on the specific season row.")
    cover = client.download_cover(selected, fid)
    banner = client.download_banner(selected, fid)
    data = client.extract_franchise_data(root)
    with closing(db.get_connection()) as conn, conn:
        existing = conn.execute("SELECT id FROM franchises WHERE anilist_id=? AND id<>?", (root["id"], fid)).fetchone()
        destination = existing["id"] if existing else fid
        allowed_owners={fid,destination,*((db.get_series(fid) or {}).get('series_member_ids') or []),*((db.get_series(destination) or {}).get('series_member_ids') or [])}
        if destination != fid:
            # Keep the old card ID, season ownership and all user/history data.
            # Group under the provider owner instead of deleting the source.
            links=json.loads(db.get_state('series_overrides','{}'))
            links[str(fid)]=destination
            conn.execute("INSERT INTO app_state(key,value) VALUES('series_overrides',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(json.dumps(links),))
            selected_titles=selected.get('title') or {}
            conn.execute("UPDATE franchises SET anilist_id=NULL,metadata_json=?,display_title=?,title_en=?,title_romaji=?,title_native=?,needs_review=0 WHERE id=?",
                (json.dumps(selected),client.resolve_display_title(selected),selected_titles.get('english'),selected_titles.get('romaji'),selected_titles.get('native'),fid))
        conn.execute("UPDATE franchises SET anilist_id=?, display_title=?, title_en=?, title_romaji=?, title_native=?, synopsis=?, genres=?, needs_review=0, metadata_json=?, cover_filename=COALESCE(?,cover_filename), banner_filename=COALESCE(?,banner_filename) WHERE id=?", (root["id"], data["display_title"], data.get("title_en"), data.get("title_romaji"), data.get("title_native"), data["synopsis"], data["genres"], json.dumps(root), cover, banner, destination))
        assignments = [] if continuous else [(selected, owned[0]["id"] if owned else None), *additional]
        from app.core.scan_state import decision
        decision(conn,'series',destination,root['id'])
        if destination!=fid:decision(conn,'series',fid,root['id'])
        conn.execute('DELETE FROM matching_review WHERE local_id IN (?,?)',(fid,destination))
        local_ids = [sid for _, sid in assignments if sid is not None]
        if len(set(local_ids)) != len(local_ids):
            raise ValueError("Assign each selected release to a different local season.")
        eligible_ids = {s["id"] for s in seasons if s.get("storage_state") == "ON_DISK" and s.get("relation_type") == "SEASON"}
        if not set(local_ids) <= eligible_ids:
            raise ValueError("A selected local season is no longer available.")
        for release, sid in assignments:
            release_id = release["id"]
            linked = conn.execute("SELECT * FROM seasons WHERE anilist_id=?", (release_id,)).fetchone()
            if linked and linked["franchise_id"] not in allowed_owners:
                raise ValueError("This release is already linked to another library entry.")
            if linked and sid is not None and linked["id"] != sid:
                if linked["season_folder_path"]:
                    raise ValueError("This release is already linked to a different local season.")
                conn.execute("DELETE FROM seasons WHERE id=?", (linked["id"],))
                linked = None
            title = client.resolve_display_title(release)
            if sid is not None or linked:
                conn.execute(
                    "UPDATE seasons SET anilist_id=?, title_display=?, episodes_total=?, airing_status=? WHERE id=?",
                    (release_id, title, release.get("episodes"), release.get("status"), sid if sid is not None else linked["id"]),
                )
            else:
                from app.core.season_numbering import infer
                number=infer(release,root,[selected,*[m for m,_ in additional]]) or 0
                conn.execute(
                    "INSERT INTO seasons (franchise_id, anilist_id, season_number, title_display, episodes_total, airing_status, storage_state) VALUES (?, ?, ?, ?, ?, ?, 'NOT_DOWNLOADED')",
                    (destination, release_id, number, title, release.get("episodes"), release.get("status")),
                )
            if sid is not None:
                decision(conn,'season',sid,release_id)
    db.recalculate_franchise_size(destination)
    db.recalculate_franchise_storage_state(destination)
    from app.core.season_numbering import repair_metadata_numbers
    repair_metadata_numbers(destination)
    from app.core.identity import bind_release
    for release, sid in assignments:
        if sid is not None:
            bind_release(sid, release)
    return destination


def auto_match_indexed_folders(cancelled, progress=None, franchise_ids=None):
    """Match exact series titles and unambiguous numbered TV releases."""
    import re
    from pathlib import Path
    from app.core.parser import clean_title, normalize_for_matching

    tv = {"TV", "TV_SHORT", "ONA"}

    def relatives(media, relation):
        return {
            node["id"]: node
            for edge in (media.get("relations") or {}).get("edges", [])
            for node in [edge.get("node") or {}]
            if edge.get("relationType") == relation and node.get("format") in tv and node.get("id")
            and ((media.get("format") == "ONA") == (node["format"] == "ONA"))
        }

    records = [record for record in db.get_all_franchises() if (franchise_ids is None or record["id"] in franchise_ids) and record.get("root_folder_path")
               and record.get("storage_state") in ("ON_DISK", "PARTIALLY_ON_DISK")]
    errors = []
    for index, record in enumerate(records, 1):
        if cancelled():
            break
        from app.preferences import enabled
        if record.get("needs_review") and not enabled("rematch_low_confidence"):
            continue
        fid = record["id"]
        local = db.get_seasons_for_franchise(fid)
        with closing(db.get_connection()) as conn:
            locked = {row['local_id'] for row in conn.execute("SELECT local_id FROM matching_decisions WHERE kind='season' AND source IN ('MANUAL','LEGACY_CONFIRMED')")}
            custom = conn.execute("SELECT 1 FROM matching_decisions WHERE kind='series' AND local_id=? AND provider_id IS NULL AND source='MANUAL'",(fid,)).fetchone()
        if custom:
            continue
        numbered = [
            season for season in local if season["storage_state"] == "ON_DISK"
            and season["relation_type"] == "SEASON" and not season["anilist_id"]
            and (season.get("local_scan_key") or "").startswith("season:")
            and season['id'] not in locked
        ]
        if db.uses_continuous_episodes(record):
            numbered = []
        if record["anilist_id"] and not numbered:
            continue
        folder = Path(record["root_folder_path"])
        if not folder.is_dir():
            continue
        if progress:
            progress(f"Matching: {record['display_title']}", index, len(records))
        try:
            if record["anilist_id"]:
                media = json.loads(record.get("metadata_json") or "{}")
                if not media.get("id") or "relations" not in media:
                    media = client.get_anime_by_id(record["anilist_id"])
                if not media or relatives(media, "PREQUEL"):
                    continue
            else:
                from app.core.match_evidence import context,choose
                sample = next(((s,name) for s in sorted(local,key=lambda s:s.get('season_number') or 999)
                               for name in json.loads(s.get('video_files_json') or '[]')), (None,''))
                season,name = sample
                evidence = context(name,str(Path(name).parent) if Path(name).parent.name else folder.name,
                                   folder.name,season.get('season_number') if season else None,
                                   season.get('relation_type') if season else None)
                evidence['files'] = [str(Path(s['season_folder_path'])/name)
                                     for s in local if s.get('season_folder_path')
                                     for name in json.loads(s.get('video_files_json') or '[]')]
                query = evidence['titles'][0] if evidence['titles'] else clean_title(folder.name)
                if not normalize_for_matching(query):
                    continue
                candidates = client.search_anime(query,per_page=8)
                if cancelled():
                    break
                media,ranked = choose(candidates,evidence)
                if media:
                    # Do not let one good filename conceal unrelated media in
                    # the same folder. Number-only names add no title evidence.
                    from difflib import SequenceMatcher
                    from app.core.match_evidence import base_title
                    aliases=[normalize_for_matching(base_title(v)) for v in (media.get('title') or {}).values() if v]
                    for path in evidence['files']:
                        title=context(Path(path).name)['filename_title']
                        if title and max((SequenceMatcher(None,normalize_for_matching(title),alias).ratio() for alias in aliases),default=0)<.65:
                            evidence['conflicting_file']=path
                            media=None
                            break
                if media is None or relatives(media,'PREQUEL'):
                    with closing(db.get_connection()) as conn,conn:
                        conn.execute('INSERT OR REPLACE INTO matching_review VALUES (?,?,?,?,?)',
                            (fid,json.dumps(evidence),json.dumps([{k:r[k] for k in ('id','score','reasons','conflict')} for r in ranked]),
                             'No unique, strongly supported release match. Review filenames, season/part and format.',int(time.time())))
                        conn.execute('UPDATE franchises SET needs_review=1 WHERE id=?',(fid,))
                    continue

            # Follow only a single TV sequel at each step. A branch, split
            # cour, or an unverified link leaves the remaining folders for review.
            if db.uses_continuous_episodes({**record, "anilist_id": media["id"]}):
                numbered = []
            chain = {1: media}
            highest = max((season["season_number"] for season in numbered), default=1)
            for number in range(2, min(highest, 50) + 1):
                if cancelled():
                    break
                current = chain[number - 1]
                sequels = relatives(current, "SEQUEL")
                if len(sequels) != 1:
                    break
                node = next(iter(sequels.values()))
                if node["id"] in {release["id"] for release in chain.values()}:
                    break
                next_media = client.get_anime_by_id(node["id"])
                if not next_media or set(relatives(next_media, "PREQUEL")) != {current["id"]}:
                    break
                if next_media.get("status") in ("NOT_YET_RELEASED", "CANCELLED"):
                    break
                titles = [title for title in (next_media.get("title") or {}).values() if title]
                if any(re.search(r"\b(?:part|cour)\s*(?:[2-9]|II|III)\b", title, re.I) for title in titles):
                    break
                explicit = [re.search(r"\bseason\s*(\d+)\b", title, re.I) for title in titles]
                if any(match and int(match[1]) != number for match in explicit):
                    break
                chain[number] = next_media

            if cancelled():
                break
            with closing(db.get_connection()) as conn, conn:
                current = conn.execute("SELECT anilist_id FROM franchises WHERE id=?", (fid,)).fetchone()
                if not current or current["anilist_id"] != record["anilist_id"]:
                    continue
                if not record["anilist_id"]:
                    from app.core.scan_state import decision
                    if not decision(conn,'series',fid,media['id'],'AUTO'):
                        continue
                    if conn.execute("SELECT 1 FROM franchises WHERE anilist_id=?", (media["id"],)).fetchone():
                        continue
                    data = client.extract_franchise_data(media)
                    data.update(needs_review=0, is_custom=0)
                    fields = ", ".join(f"{key}=?" for key in data)
                    conn.execute(f"UPDATE franchises SET {fields} WHERE id=?", (*data.values(), fid))
                    conn.execute('DELETE FROM matching_review WHERE local_id=?',(fid,))
                for season in numbered:
                    number = season["season_number"]
                    release = chain.get(number)
                    if not release or sum(s["season_number"] == number and s["relation_type"] == "SEASON"
                                          and s["storage_state"] == "ON_DISK" for s in local) != 1:
                        continue
                    if conn.execute("SELECT 1 FROM seasons WHERE anilist_id=?", (release["id"],)).fetchone():
                        continue
                    data = client.extract_season_data(release, fid, number)
                    from app.core.scan_state import decision
                    if not decision(conn,'season',season['id'],release['id'],'AUTO'):
                        continue
                    conn.execute(
                        "UPDATE seasons SET anilist_id=?, title_display=?, episodes_total=?, airing_status=?, "
                        "next_airing_ep=?, next_airing_at=? WHERE id=? AND anilist_id IS NULL",
                        (data["anilist_id"], data["title_display"], data["episodes_total"], data["airing_status"],
                         data["next_airing_ep"], data["next_airing_at"], season["id"]),
                    )
        except (OSError, ValueError, KeyError) as error:
            errors.append(f"{folder.name}: {error}")
    return errors
