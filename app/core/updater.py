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
            checked_media={}

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
                    media = checked_media.get(anilist_id) or anilist_client.get_anime_by_id(anilist_id)
                    if not media:
                        continue
                    checked_media[anilist_id]=media

                    # A later season can be linked in the library without being
                    # a direct relation of season one. Check each exact release
                    # identity once per explicit refresh, never by title guessing.
                    linked=[];linked_failed=False;linked_ids=set()
                    for season in db.get_seasons_for_franchise(franchise['id']):
                        release_id=season.get('anilist_id')
                        if self._cancelled:break
                        if not release_id or release_id==anilist_id or release_id in linked_ids:continue
                        linked_ids.add(release_id)
                        release=checked_media.get(release_id)
                        if release is None:
                            try:release=anilist_client.get_anime_by_id(release_id)
                            except Exception as exc:
                                linked_failed=True;self.error.emit(f"Error checking {season.get('title_display') or release_id}: {exc}");continue
                            if release:checked_media[release_id]=release
                        if release:
                            linked.append(release)
                            from app.core.release_calendar import remember_metadata
                            remember_metadata(release)
                        else:
                            linked_failed=True;self.error.emit(f"Could not check {season.get('title_display') or release_id}; saved updates are kept.")
                    if self._cancelled:break

                    db.cache_media(franchise["id"], media)
                    if linked_failed:continue
                    update_info = db.publish_updates(franchise["id"], self._check_for_updates(franchise, media, linked))
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

    def _check_for_updates(self, franchise: dict, media: dict, linked_media=()) -> Optional[str]:
        """Compare current library data against AniList for new updates.
        Returns update description string or None."""
        updates = []
        from app.core.episode_updates import episode_notifications
        from app.core.release_calendar import saved
        cached_history=getattr(self,'_airing_schedule',None)
        history=list(saved() if cached_history is None else cached_history)
        import json
        try:
            previous=json.loads(franchise.get('metadata_json') or '{}') or {}
            if previous.get('id')==media.get('id'):
                for entry in [previous]+[e.get('node') or {} for e in (previous.get('relations') or {}).get('edges',[])]:
                    if entry.get('id') and entry.get('nextAiringEpisode'):history.append(dict(entry['nextAiringEpisode'],mediaId=entry['id']))
        except (ValueError,TypeError):pass

        # Check relations for new sequels / movies
        edges = media.get("relations", {}).get("edges", [])
        existing_seasons = db.get_seasons_for_franchise(franchise["id"])
        existing_anilist_ids = {
            s["anilist_id"] for s in existing_seasons if s.get("anilist_id") and s.get('storage_state')!='NOT_DOWNLOADED'
        }

        for edge in edges:
            node = edge.get("node", {})
            rel_type = edge.get("relationType", "")
            node_id = node.get("id")

            if rel_type not in ("SEQUEL", "SIDE_STORY", "SPIN_OFF"):
                continue
            if node.get("format") not in ("TV", "TV_SHORT", "MOVIE", "OVA", "ONA", "SPECIAL"):
                continue

            status = node.get("status", "")
            title = (node.get("title", {}).get("english")
                     or node.get("title", {}).get("romaji")
                     or "Unknown")

            # A dismissed season announcement is not a dismissal of every later
            # episode. Related releases already carry their own schedule data.
            if status in ('RELEASING','HIATUS'):
                updates.extend(f'{notice} — {title}' for notice in episode_notifications(node,history))
            if node_id in existing_anilist_ids:
                continue

            if status == "RELEASING":
                updates.append(f"{title} — Currently Airing")
            elif status == "NOT_YET_RELEASED":
                updates.append(f"{title} — Announced (Not Yet Released)")
            elif status == "FINISHED":
                updates.append(f"{title} — Released (Not in Library)")

        # Check if the main entry is currently airing
        updates.extend(episode_notifications(media,history))
        seen={media.get('id')}|{(edge.get('node') or {}).get('id') for edge in edges}
        for release in linked_media:
            if not release.get('id') or release['id'] in seen:continue
            seen.add(release['id'])
            title=(release.get('title') or {}).get('english') or (release.get('title') or {}).get('romaji') or 'Unknown'
            updates.extend(f'{notice} — {title}' for notice in episode_notifications(release,history))

        return " | ".join(dict.fromkeys(updates)) if updates else None
