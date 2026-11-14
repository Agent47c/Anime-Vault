# Download, discovery and backup fixes

Implemented 13 November 2026. Design reference: `new anime release screen`.
Existing playback, grouping, download confirmation and library features remain.

## Download speed controls

- Both Downloads and download settings use one shared rate picker: Unlimited,
  512 KB/s increments through 10 MB/s, and Custom. Arbitrary saved limits such as
  15 or 2,000 KB/s are preserved exactly instead of being rounded.
- Labels use KB/MB for readability; the tooltip states that KB means 1,024 bytes.
  Internally values stay KiB/s and libtorrent receives bytes/s.
- Saving settings reconfigures the existing engine session immediately. It does
  not submit another torrent or require an app restart. Both open settings views
  receive updated rate values. Disabled downloads still stop the engine.
- Empty/invalid custom input produces a readable validation message.
- Files: `app/ui/components/rate_limit.py`, `app/ui/settings_events.py`,
  `app/ui/downloads.py`, `app/ui/pages/downloads_page.py`,
  `app/core/downloads.py`, `app/core/builtin_torrents.py`.

## Window state

Normal geometry and maximized state are saved separately and restored on launch,
including closing to the tray. F11 exclusive fullscreen is not restored as the
normal startup mode. File: `app/ui/main_window.py`.

## Chrome extension and privacy

The popup now has a consistent dark/coral layout, website connection controls,
setup guidance and an offline Privacy & data use page. Existing element IDs,
capture logic, permissions and the native bridge remain unchanged. The policy
explains local storage, selected-site access, provider requests, torrent peer
visibility and private backup contents. It does not claim third-party services
collect no data. Reload the unpacked extension to see the updated interface.

Files: `browser-extension/popup.html`, `popup.css`, `privacy.html`, `PRIVACY.md`.

## New anime releases

- The discovery action reads **Check new animes**. Initial entry uses saved data;
  explicit refresh requests fresh data. Changing filters or pressing Next obtains
  a missing page automatically and reuses it on later visits.
- Grid layout updates its scrollable content height after arranging cards, making
  the last row reachable without a resize or page change.
- Adult discovery defaults off for profiles without a saved choice. Explicit
  existing choices remain intact. Settings changes immediately hide/show adult
  controls and Hentai, invalidate stale workers and filter visible cached cards.
- **Only adult (18+)** is available only when mature content is enabled. Both
  requests and displayed results enforce the preference, including related titles.
- Cache and network identities include the adult-only mode so filtered and
  unfiltered results cannot share the wrong page.

Files: `app/preferences.py`, `app/core/release_news.py`,
`app/ui/pages/release_news_page.py`, `app/ui/components/tag_picker.py`,
`app/ui/main_window.py`.

## Selected release details and artwork

The selected anime now has a banner, poster, complete display title, alternate
Romaji/English/native titles, plot, genres, format, release status and premiere
date above its existing broadcast table. Related prequels/sequels are explicitly
labeled as separate titles. Requested/returned provider IDs are checked to prevent
showing another anime under the selected title. Existing import, reminder and
download actions remain.

Artwork reuses the existing persistent provider cache and background loader.
Network access follows the current refresh/offline policy. Missing artwork keeps
a stable placeholder. Banner downloads now support the same cache-only option as
posters; worker failures are reported without escaping a Qt thread callback.

The mockup's fabricated live/technical labels are not presented as real data.
Files: `app/ui/pages/release_news_page.py`, `app/core/release_news.py`,
`app/core/anilist_client.py`.

## Optional full app-state backup

In Settings → Database & Backups, enable **Full app-state backup (ZIP)**.
Optionally enable **Include cached posters, banners and thumbnails**. Creation
warns about private contents and potentially very large cache backups.

Included: every committed database table (library locations, ratings, notes,
watch history, settings and download records/status), native torrent/resume
metadata, and optionally poster/banner/episode-thumbnail/player-icon caches.
Excluded: video/media payloads, application binaries/source, `.env` and
machine-specific Chrome registration. This is a portable profile backup, not a
Windows installation image. Restored paths still refer to their original drives.

Creation uses SQLite's snapshot API and a temporary ZIP with atomic final rename.
Restore accepts DB or ZIP, validates archive contents, rejects traversal/linked
paths and duplicate entries, limits extraction to 64 GB/100,000 entries, and checks
SQLite integrity before applying changes. It retains a safety backup and rolls
back applied DB/cache changes if replacement fails. Stop downloads/scans and
finish pending edits before restoring. Keep backups private. A backup does not
guarantee that old torrent peers or external media locations remain available.

Files: `app/core/profile_backup.py`, `app/ui/pages/settings_page.py`, `.gitignore`.

## Verification

- 519 Python tests passed via `scripts/check.py`, including nine new targeted
  regressions in `tests/test_experience_followups.py`.
- 18 existing Chrome-extension tests passed.
- Offline Qt renders checked selected-release layout and both rate controls;
  an isolated headless Chrome render checked popup spacing and text fit.
- All regression data and artwork were temporary/fictional. No real media moves,
  deletions, personal database restores or live download submissions were used.
- A live internet/provider outage or real peer speed is not covered by these
  offline checks. Limits are caps, not promised download throughput.

Visual checks: `data/new-release-details-visual.png`,
`data/new-transfer-limits-visual.png`, `data/new-extension-popup-visual.png`.
Detailed test log: `data/experience-final-validation.log`.

## Updated standalone setup

Rebuilt `dist/installer/AnimeVault-Setup-1.0.0-windows-x64.exe` (56,216,536 bytes).
SHA-256: `dd34ef534f9a766ebe6cf5c1ca533201ddbdc736086dee773c195ffff904bbc2`.
The previous setup remains in `dist/installer/previous/`. No installation was run.
The rebuilt executable passed isolated first-run schema, all navigation tabs,
Details, SQLite backup/restore, native torrent helper and Chrome native-message
checks with Python removed from PATH. Full-profile ZIP behavior was covered by
the source regression tests. Existing installed copies need this updated setup;
editing source files does not update an already installed executable.
