"""Group local records by verified sequel/prequel chains without merging user data."""
import json


def build_groups(franchises, related_media=None, overrides=None):
    parents, titles, prequels, formats = {}, {}, {}, {}
    def find(value):
        parents.setdefault(value, value)
        if parents[value] != value:
            parents[value] = find(parents[value])
        return parents[value]
    def join(a, b):
        parents[find(a)] = find(b)
    graph_entries = list(franchises) + [{"anilist_id": media["id"], "display_title": (media.get("title") or {}).get("english") or (media.get("title") or {}).get("romaji") or "Anime", "metadata_json": json.dumps(media)} for media in (related_media or [])]
    for entry in graph_entries:
        aid = entry.get("anilist_id")
        if not aid:
            continue
        find(aid)
        titles[aid] = entry["display_title"]
        try:
            media = json.loads(entry.get("metadata_json") or "{}")
        except ValueError:
            continue
        formats[aid] = media.get("format") or formats.get(aid, "TV")
        for edge in (media.get("relations") or {}).get("edges", []):
            node = edge.get("node") or {}
            relation = edge.get("relationType")
            if relation not in ("PREQUEL", "SEQUEL") or node.get("format") not in ("TV", "TV_SHORT", "MOVIE", "SPECIAL", "OVA", "ONA") or not node.get("id"):
                continue
            nid = node["id"]
            # A standalone web release can be related to a TV series without
            # being one of its seasons.
            if (formats[aid] == "ONA") != (node["format"] == "ONA"):
                continue
            formats.setdefault(nid, node.get("format"))
            join(aid, nid)
            title = node.get("title") or {}
            titles.setdefault(nid, title.get("english") or title.get("romaji") or entry["display_title"])
            later, earlier = (aid, nid) if relation == "PREQUEL" else (nid, aid)
            prequels.setdefault(later, set()).add(earlier)
    components = {}
    for aid in parents:
        components.setdefault(find(aid), set()).add(aid)
    grouped = {}
    for entry in franchises:
        aid = entry.get("anilist_id")
        key = ("provider", find(aid)) if aid else ("local", entry["id"])
        grouped.setdefault(key, []).append(entry)
    result = []
    for key, members in grouped.items():
        if key[0] == "provider":
            component = components[key[1]]
            roots = [aid for aid in component if not (prequels.get(aid, set()) & component)]
            television = {aid for aid in component if formats.get(aid) in ("TV", "TV_SHORT")}
            if television:
                # A short prequel special must not supply the name of a TV series.
                roots = [aid for aid in television if not (prequels.get(aid, set()) & television)] or list(television)
            root = min(roots or component)
            representative = next((m for m in members if m.get("anilist_id") == root), min(members, key=lambda m: m["id"]))
            title = titles.get(root, representative["display_title"])
        else:
            representative, title = members[0], members[0]["display_title"]
        card = dict(representative)
        card["display_title"] = title
        card["series_member_ids"] = [m["id"] for m in members]
        card["total_size_bytes"] = sum(m.get("total_size_bytes") or 0 for m in members)
        card["has_new_update"] = any(m.get("has_new_update") for m in members)
        card["release_count"] = len(members)
        result.append(card)
    # Explicit user corrections also work offline and never change file ownership.
    for source, target in (overrides or {}).items():
        source, target = int(source), int(target)
        left = next((g for g in result if source in g["series_member_ids"]), None)
        right = next((g for g in result if target in g["series_member_ids"]), None)
        if left is None or right is None or left is right:
            continue
        right["series_member_ids"].extend(left["series_member_ids"])
        right["total_size_bytes"] += left["total_size_bytes"]
        right["has_new_update"] = right["has_new_update"] or left["has_new_update"]
        right["release_count"] += left["release_count"]
        result.remove(left)
    for card in result:
        members = [entry for entry in franchises if entry["id"] in card["series_member_ids"]]
        # Manual grouping may keep an old unmatched representative. Its empty
        # presentation fields must not hide verified artwork/metadata in the group.
        matched=[m for m in members if m.get('anilist_id')]
        donor=next((m for m in matched if m.get('anilist_id')==card.get('anilist_id')),None)
        if donor is None and matched:
            try:provider=(json.loads(card.get('metadata_json') or '{}') or {}).get('id')
            except (ValueError,TypeError):provider=None
            donor=next((m for m in matched if m.get('anilist_id')==provider),matched[0])
        if donor:
            for field in ('synopsis','cover_filename','banner_filename','genres','anilist_id','metadata_json'):
                if not card.get(field) or card.get(field) in ('{}','[]','null'):card[field]=donor.get(field)
        on_disk = [m for m in members if m.get("storage_state") in ("ON_DISK", "PARTIALLY_ON_DISK")]
        if on_disk:
            card["storage_state"] = "PARTIALLY_ON_DISK" if any(m.get("storage_state") in ("PARTIALLY_ON_DISK", "WATCHED_REMOVED") for m in members) else "ON_DISK"
        elif any(m.get("storage_state") == "WATCHED_REMOVED" for m in members):
            card["storage_state"] = "WATCHED_REMOVED"
    return result


def refresh_series_links(franchises=None, cancelled=None):
    """Resolve missing intermediate prequels in the background; retain an offline cache."""
    from app import db
    from app.core import anilist_client
    entries = franchises if franchises is not None else db.get_all_franchises()
    cached = json.loads(db.get_state("series_relation_cache", "{}"))
    for entry in entries:
        if entry.get("metadata_json"):
            media = json.loads(entry["metadata_json"])
            cached[str(media["id"])] = media
    queue = [entry.get("anilist_id") for entry in entries if entry.get("anilist_id")]
    seen = set()
    while queue and len(seen) < 2000:
        if cancelled and cancelled():
            break
        aid = queue.pop(0)
        if aid in seen:
            continue
        seen.add(aid)
        media = cached.get(str(aid)) or anilist_client.get_anime_by_id(aid)
        if not media:
            continue
        cached[str(aid)] = media
        for edge in (media.get("relations") or {}).get("edges", []):
            node = edge.get("node") or {}
            if edge.get("relationType") == "PREQUEL" and node.get("format") in ("TV", "TV_SHORT", "MOVIE", "SPECIAL", "OVA", "ONA") and node.get("id"):
                queue.append(node["id"])
    db.set_state("series_relation_cache", json.dumps(cached))
