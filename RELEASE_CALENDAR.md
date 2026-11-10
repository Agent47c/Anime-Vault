# Persistent release calendar

## Behavior

- The Library shows two complete Monday–Sunday rows: the current week and next
  week. Earlier days of the current week remain visible, including on Sunday.
- Previous week and Next week move the window one week; This week resets it.
  The date range includes the year. Times use the computer's local timezone.
- Existing hover previews, hover lift, thumbnails, multi-release previews and
  navigation to anime details remain intact. Selecting a release does not play it.
- Schedule records are saved independently from `nextAiringEpisode`. Updating an
  anime to its next episode no longer removes the previous saved release.
- Saved history is retained for 12 weeks. Week navigation itself performs no API
  calls, scans, or cache writes; reopening the app reads the same saved data.

## Fetching and persistence

`app/core/release_calendar.py` uses the existing SQLite `app_state` table with key
`release_calendar.v1`; no destructive migration or library reset is needed.
Records contain provider media ID, episode number and air timestamp. Matching
uses current AniList links, never title guessing or assumed seven-day intervals.
The same episode's corrected air timestamp replaces its previous timestamp.

The existing internet metadata updater fetches the previous, current and next
week through AniList's paginated `Page.airingSchedules` query, restricted to
linked library releases. Both aired and future records are requested. Requests
run in the existing worker and respect its cancellation and rate limiter. A
failed/empty fetch does not clear saved history. Local refresh and page visits
do not fetch the schedule.

`db.cache_media` saves both the previous and incoming next-episode records before
replacing metadata. The calendar also continues to display existing season and
franchise next-episode metadata as a fallback. Artwork still uses existing caches.
Personal notes, watch history, files, matching and download behavior are unchanged.

## First use and limitations

Use **Refresh and sync with internet** once to backfill past days and load the
next week's published schedule. Past data cannot be reconstructed reliably from
one next-episode value alone. AniList only aims to guarantee future airing data;
historical or unannounced entries can be absent. The app preserves what it has
received and does not invent release dates. An empty day means no known records
in the local schedule, not proof that nothing aired globally.

Provider reference: https://docs.anilist.co/reference/object/airingschedule

## Changed files and checks

- `app/core/release_calendar.py`: persistent history, deduplication, retention,
  linked-library scope and cancellable paginated schedule fetching.
- `app/db.py`: preserve next-episode history when metadata is replaced.
- `app/core/updater.py`: refresh dated schedules during internet synchronization.
- `app/ui/pages/library_page.py`: two-week grid, date range and week navigation.
- `app/ui/components/airing_count.py`: tighter narrow-card padding, avoid a
  redundant release dot beside Today, and show full episode/time in a tooltip.
- `tests/test_release_calendar.py`: Sunday/past-day rendering, 14 cards,
  navigation without network requests, metadata replacement, timestamp changes,
  pagination, offline/failure retention and cancellation.
- `tests/test_ui_regressions.py`: mock schedule refresh in the updater regression
  so tests never make real schedule requests.

Validation uses temporary databases and mocked network data. No user media is
moved or altered. Rendered calendar checks are stored in ignored `data/`.
