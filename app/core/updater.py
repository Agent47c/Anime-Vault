"""
Background updater — checks for new seasons, sequels, and airing status
for all franchises in the library.
Runs as a QThread on startup.
"""

import time
from typing import Optional

from PyQt5.QtCore import QThread, pyqtSignal

from app import db
from app.config import is_offline
from app.core import anilist_client


class UpdaterThread(QThread):
    """Background thread that checks AniList for updates to library entries."""

    # Signals
    progress = pyqtSignal(str, int, int)   # message, current, total
    update_found = pyqtSignal(int, str)     # franchise_id, update_details
    finished_signal = pyqtSignal(int)       # total updates found
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        if is_offline():
            self.finished_signal.emit(0)
            return

        try:
            franchises = db.get_all_franchises()
            total = len(franchises)
            updates_found = 0
            from app.core.release_calendar import saved
            self._airing_schedule=saved()

            for idx, franchise in enumerate(franchises):
                if self._cancelled:
                    break

                self.progress.emit(
                    f"Checking: {franchise['display_title']}",
                    idx + 1, total,
                )

                anilist_id = franchise.get("anilist_id")
                if not anilist_id:
                    continue

                try:
                    media = anilist_client.get_anime_by_id(anilist_id)
                    if not media:
                        continue

                    db.cache_media(franchise["id"], media)
                    update_info = db.publish_updates(franchise["id"], self._check_for_updates(franchise, media))
                    if update_info:
                        self.update_found.emit(franchise["id"], update_info)
                        updates_found += 1

                    # Rate limiting is handled inside anilist_client
                except Exception as e:
                    self.error.emit(
                        f"Error checking {franchise['display_title']}: {str(e)}"
                    )

            if not self._cancelled:
                from app.core.release_calendar import refresh as refresh_calendar
                try:
                    refresh_calendar(cancelled=lambda: self._cancelled)
                except InterruptedError:
                    pass
                except Exception as exc:
                    self.error.emit(f"Release calendar: {exc}")
            if not self._cancelled:
                from app.core.series import refresh_series_links
                refresh_series_links(cancelled=lambda: self._cancelled)
            self.finished_signal.emit(updates_found)

        except Exception as e:
            self.error.emit(f"Updater error: {str(e)}")
            self.finished_signal.emit(0)

    def _check_for_updates(self, franchise: dict, media: dict) -> Optional[str]:
        """Compare current library data against AniList for new updates.
        Returns update description string or None."""
        updates = []

        # Check relations for new sequels / movies
        edges = media.get("relations", {}).get("edges", [])
        existing_seasons = db.get_seasons_for_franchise(franchise["id"])
        existing_anilist_ids = {
            s["anilist_id"] for s in existing_seasons if s.get("anilist_id")
        }

        for edge in edges:
            node = edge.get("node", {})
            rel_type = edge.get("relationType", "")
            node_id = node.get("id")

            if rel_type not in ("SEQUEL", "SIDE_STORY", "SPIN_OFF"):
                continue
            if node_id in existing_anilist_ids:
                continue
            if node.get("format") not in ("TV", "TV_SHORT", "MOVIE", "OVA", "ONA", "SPECIAL"):
                continue

            status = node.get("status", "")
            title = (node.get("title", {}).get("english")
                     or node.get("title", {}).get("romaji")
                     or "Unknown")

            if status == "RELEASING":
                updates.append(f"{title} — Currently Airing")
            elif status == "NOT_YET_RELEASED":
                updates.append(f"{title} — Announced (Not Yet Released)")
            elif status == "FINISHED":
                updates.append(f"{title} — Released (Not in Library)")

        # Check if the main entry is currently airing
        from app.core.episode_updates import episode_notifications
        from app.core.release_calendar import saved
        import json
        cached_history=getattr(self,'_airing_schedule',None)
        history=list(saved() if cached_history is None else cached_history)
        try:
            previous=json.loads(franchise.get('metadata_json') or '{}') or {}
            if previous.get('id')==media.get('id') and previous.get('nextAiringEpisode'):
                history.append(dict(previous['nextAiringEpisode'],mediaId=media.get('id')))
        except (ValueError,TypeError):pass
        updates.extend(episode_notifications(media,history))

        return " | ".join(updates) if updates else None
