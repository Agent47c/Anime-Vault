"""An invalidatable in-memory view of one library refresh for instant UI sorting."""
from app import db
from app.core.series import build_groups
import json


class LibraryIndex:
    def __init__(self):
        self.records = db.get_all_franchises()
        from app.ui.refresh import artwork_version
        for record in self.records:
            record["_cover_version"] = artwork_version(record.get("cover_filename"))
        self.by_id = {row["id"]: row for row in self.records}
        related = list(json.loads(db.get_state("series_relation_cache", "{}")).values())
        overrides = json.loads(db.get_state("series_overrides", "{}"))
        self.groups = build_groups(self.records, related, overrides)

    def select(self, sort_by="display_title", sort_order="ASC", search="", storage_state=None, watch_status=None):
        query = search.casefold()
        def matches(record):
            if query and not any(query in str(record.get(key) or "").casefold() for key in ("display_title", "title_romaji", "title_native")):
                return False
            if watch_status and record.get("watch_status") != watch_status:
                return False
            if storage_state == "RECLAIM":
                return record.get("watch_status") == "WATCHED" and record.get("storage_state") in ("ON_DISK", "PARTIALLY_ON_DISK") and (record.get("total_size_bytes") or 0) > 0
            return not storage_state or record.get("storage_state") == storage_state
        rows = [group for group in self.groups if any(matches(self.by_id[mid]) for mid in group["series_member_ids"])]
        field = sort_by if sort_by in ("display_title", "total_size_bytes", "user_rating", "created_at", "watch_status") else "display_title"
        rows.sort(key=lambda row: (str(row.get("display_title") or "").casefold(), row["id"]))
        def value(row):
            item = row.get(field)
            if field in ("total_size_bytes", "user_rating"):
                return item if item is not None else -1
            return str(item or "").casefold()
        rows.sort(key=value, reverse=sort_order.upper() == "DESC")
        return rows
