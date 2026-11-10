# Settings, setup and connected downloads

> **9 November 2026 update:** Anime Vault now uses the built-in engine only.
> External-client setup/control described below is historical and removed.
> See [current setup and legacy queue recovery](BUILTIN_ONLY_DOWNLOADS.md).

## What changed

Settings is now divided into six task-based tabs. Existing controls, saved values,
signals and player/organizer/import features remain available:

| Category | Controls and behavior |
| --- | --- |
| Appearance & Accessibility | Windows/dark/light theme, compact display, motion, text size, contrast, decorations, close/admin behavior and About |
| Scanning & Organization | Library roots, manual/scheduled scans, metadata preferences, season/episode detection, movement preview, subtitle/font handling and an Organizer shortcut |
| Watchers & Import Lists | Opt-in folder events, automatic TXT subscriptions, per-list enable/status/removal, manual checks, existing watched importer and import confidence/duplicate policies |
| Media Player | Existing player/custom executable/detection plus full-screen, audio language, subtitle language and subtitle enable preferences for VLC/MPV |
| Downloads & Sources | Guided setup, existing built-in/qBittorrent settings, browser connection, destination, source list/default source, query/group/quality, file review, speed/seeding preferences |
| Database & Backup | Backup, restore, JSON/CSV export, backup location and database integrity/checkpoint maintenance |

Tab labels are shortened where helpful; full category names remain in tooltips.
The download configuration reuses its existing controls without nesting a second
scroll area or a dismissible drawer inside Settings.

## First-time setup

Open **Downloads → Setup**, or **Settings → Downloads & Sources → Set up downloads
step by step**. The guide saves progress and can be reopened:

1. Load the extension folder in Chrome's `chrome://extensions` page, with Developer
   mode enabled. Paste its extension ID and connect it. Manual magnet users can
   explicitly skip Chrome setup for now.
2. Choose the built-in engine or qBittorrent. The latter needs its local Web UI
   credentials. Existing transfers stay with their original engine.
3. Choose the destination folder. Existing library media is not moved.
4. Choose the search URL and default release group/quality. The URL must contain
   `{query}` in a query parameter. Enable that exact website in the Chrome popup.
5. Test the engine, actual folder write access, live extension connection and a
   source query. Each step displays its state and failed tests explain a remedy.

The guide distinguishes *configured* from *connection tested*. An incomplete setup
can be saved for later; it is not reported as fully connected. All settings can
also be changed directly in Settings. Subtitle/audio preferences are disabled for
players whose command interface is not supported; those players use their own
preferences rather than receiving invented options.

## Chrome extension update

The extension is now **version 1.1.0**. If an unpacked older version is already
installed, reload it in `chrome://extensions`, then open its popup and enable the
chosen source. Its extension ID stays the same when using the same folder.
Saved configured sources are recognized by the native receiver; Chrome still
captures only the one exact website currently enabled in its popup.

The existing selected-site magnet capture remains available. An additional Chrome
Native Messaging connection delivers app-initiated search commands and structured
results. Chrome's alarm reconnects a lost bridge. It does not change the Windows
magnet handler or add a local streaming/HTTP API. The only added Chrome permission
is `alarms`; website access still requires the user's exact selected-origin grant.

Routine search steps:

1. The app builds a query using the chosen anime/release, saved search preferences,
   and alternative titles as fallbacks. A custom query can override the default.
2. The extension opens a temporary **inactive** tab for the permitted source.
3. It extracts Nyaa-style result rows, or basic generic rows containing magnets.
4. The tab closes and the app shows title, episode coverage, quality, release group,
   file size, seeders and source when supplied by the page.
5. The user selects releases and confirms a review inside the app.

Cross-origin redirects, missing permissions, disconnected Chrome, unreadable
pages and failed/empty searches have distinct feedback. A browser verification
page may require **Open source in Chrome**, followed by a retry. Complex sites
without readable magnet rows need a dedicated parser; arbitrary websites are not
claimed to be universally supported. Cookies, credentials and page scripts are
not exported into the app. Search requests/results are bounded and short-lived;
cancelled or replaced searches cannot populate the current result list.

## Find Download Files and missing episodes

Anime details now provides **Find Download Files**, opening a full page of results.
The page includes season/source selection, editable queries, availability and
quality/group/title filters, and sorting by seeders, title or episode number.
The **Show episode availability** virtual table lists each known episode's state:

- **In Library**: the indexed file exists locally and is not an unfinished transfer.
- **Downloading or Queued**: matching episode coverage is already tracked.
- **Missing — Release Found**: absent locally, with a matching result in this search.
- **Missing — No Release Found**: absent within known boundaries, with no matching
  result in the current successful search.
- **Match Uncertain**: title, season, numbering, special/movie type or release date
  needs confirmation before coverage can be assigned.

Local availability is separate from source availability. Seeder counts are shown
when provided; a listing or nonzero count is not proof that a download can finish.
Alternate titles use exact normalized matching, including Japanese characters.
A shared title prefix is not sufficient to assign another release automatically.
S1E10 and S2E10 remain separate; continuing series aggregate their numbered folders
and root files. Season-relative files in an absolute show require verified offsets
or manual confirmation. Future episodes beyond a verified aired boundary require
review and are not silently described as missing downloads. Unverified folders
still use conservative internal gaps rather than invented season boundaries.

**Confirm highlighted match** lets the user explicitly choose episode/movie/special
type, season or absolute numbering, and episode range. This does not start a
download. Search coverage annotations do not replace the existing stable episode
IDs or watch-history records.

**Download Missing Episodes** selects confident releases covering missing episodes.
It does not automatically select a batch that also covers locally owned/queued
episodes. Such a batch can be selected manually, with an overlap warning and file
selection afterward. The review shows releases, covered episodes, destination and
remaining gaps. Overlapping selections and active queued duplicates are rejected
before submission; local/queue state is rechecked immediately before adding jobs.
Magnet identities are canonicalized across hexadecimal and base32 representations.

After adding transfers, the page refreshes local/queue coverage without repeating
the source search. Existing pasted magnets and `.torrent` selection remain available.

## Downloads navigation and queue actions

**Downloads** is a main-sidebar destination, independent of Settings. It immediately
opens the persisted queue and current activity, with filters for active,
paused/stopped, completed and failed/missing-file transfers. Available fields include
anime/release, episode range, percent, downloaded/total bytes, speed, remaining time
and a clear normalized status:

`Queued`, `Downloading`, `Paused`, `Stopped`, `Completed`, `Failed`, or
`Incomplete or missing files`.

Completed selected files are periodically checked in IO workers. A known completed
transfer whose files disappear or change size is distinguished from an unfinished
transfer. An unavailable drive is a repair/retry condition; history is retained.

- Pause/resume/stop/retry work through the selected job's original engine.
- Built-in file selection uses the existing virtual file picker. qBittorrent file
  selection remains in that client and the app explains this requirement.
- Retry can restart a failed native helper and request a native piece recheck.
- **Open download folder** reports missing/unavailable folders clearly.
- **Remove queue entry — keep files** stops/removes the tracked transfer and removes
  its queue record, preserving downloaded files and library history. The qBittorrent
  request explicitly uses `deleteFiles=false` and only the uniquely tagged hash.
- **Move download files to Recycle Bin** is a separate confirmation. It acts only on
  known torrent payload paths inside the isolated job destination, rejects changed
  links/junctions, uses the existing per-file operation journal and recycle-only
  implementation, and keeps unrelated user files and history. Empty folders/private
  client cache files can remain. Space returns after the Recycle Bin is emptied.

Connection failures remain visible and use bounded retry delays. Saving corrected
settings or explicitly retrying clears those delays. Existing user job records are
not migrated into a different torrent engine, and no transfer is started merely by
viewing Settings or a result.

## Completion, watchers and import lists

Verified selected videos continue through the existing scanner/indexing path,
keeping the stable series identity, other locations, notes and history. Organizer
previews are marked stale for a deliberate new preview. Files are not silently moved
away from a torrent's save location while its client may be seeding.

Folder watchers are **off by default**. When enabled, they watch available configured
roots and indexed season folders, coalesce changes for 1.8 seconds and request a
local incremental scan. Paths are loaded/checked in a worker and registered with Qt
in small chunks. Unavailable roots do not erase records. The watch set is bounded
to 5,000 directories; manual scans remain available for other paths/reconnected roots.

Unverified download scopes are excluded from normal scans, preventing a watcher
from importing a preallocated partial `.mkv`. Removing an unfinished queue entry
keeps that exclusion so its retained partial files are not mistaken for completed
media. Confirmed completion indexing is the authoritative import path.

TXT subscriptions are also opt-in. Each can be enabled/disabled, assigned a watch
status, removed or checked manually. Enabled lists are checked once a minute and
unchanged content is skipped. Existing notes and metadata corrections are preserved;
per-list stable series links survive display-title edits and reject deleted/reused
identities. New unmatched names become custom entries needing review rather than
receiving a weak API match. Ambiguous links remain visible for manual review. Removing
and re-adding a subscription resets its saved associations without deleting library
records. Lists are bounded to 4 MB each and 50 subscriptions.

## Backup and maintenance

Backups use SQLite's online backup API, including committed WAL content, and a
configurable destination. Restore validates the backup, keeps a safety snapshot,
restores through SQLite and reapplies additive migrations. Transfers/background
work must be stopped before restoration; interaction is blocked briefly during the
restore to prevent competing writes. Integrity checking and passive WAL checkpointing
are available as maintenance. Backups/restores/exports run in app-owned IO workers.

## Changed files

- `app/ui/pages/settings_page.py`, `app/ui/settings_sections.py`: six categories,
  preserved controls, real watchers/import/source/player/backup controls.
- `app/ui/download_setup.py`, `app/core/download_setup.py`: saved five-step guide
  and real engine/folder/extension/source validation.
- `app/ui/pages/downloads_page.py`, `app/core/download_queue.py`: queue model,
  statuses, integrity checks, controls and distinct safe removal/recycling actions.
- `app/ui/pages/release_search_page.py`, `app/core/download_discovery.py`: in-app
  releases, coverage, conservative matching, filters, review and duplicate guards.
- `app/core/source_bridge.py`, `app/core/chrome_bridge.py`: durable bounded source
  requests/results and the authenticated persistent native connection.
- `browser-extension/background.js`, `search.js`, `popup.js`, `manifest.json`:
  version 1.1.0 search bridge, parser, exact-origin checks and reconnect feedback.
- `app/core/downloads.py`, `app/core/builtin_torrents.py`, `builtin_torrent_host.py`:
  coverage/size metadata, retry/recheck, durable failures and completion integration.
- `app/core/import_lists.py`, `app/ui/library_watchers.py`: opt-in incremental list
  imports, stable manual associations and debounced folder watching.
- `app/core/incremental.py`: exclude unverified torrent scopes from normal scans.
- `app/ui/main_window.py`, `app/ui/navigation.py`, `app/ui/icons.py`: main Downloads
  destination, watcher lifecycle and safe navigation into/out of child review drawers.
- `app/ui/downloads.py`, `app/ui/pages/detail_modal.py`: reused configuration,
  engine-aware controls and the Find Download Files entry point.
- `app/config.py`, `app/preferences.py`, `app/db.py`, `app/ui/theme.py`: connected
  playback preferences, saved opt-in defaults, safe backup/restore and theme styling.
- `tests/test_download_experience.py`, `browser-extension/tests/search.test.js`,
  `scripts/check_download_workflow.py`: focused and complete-flow regressions.
- README, extension README and CHANGELOG: setup and release notes.

## Validation and practical limits

Final validation on 2026-11-08: `python data/phase2_validate.py` passed all
237 tests in 47.961 seconds, including both Chrome JavaScript test wrappers
(14 JavaScript checks) and the real local-only torrent-to-library workflow.
The 500-file scanner heartbeat check recorded a maximum of 44.8 ms.
Compilation and whitespace checks also passed. These are test-environment
measurements, not a guarantee for every machine or drive.

Tests cover category/settings persistence, extension origin/permission failures,
structured result extraction, temporary-tab cleanup, cancellation, local/queued
coverage, future boundaries, batches, duplicate checks, child-drawer navigation,
queue persistence, missing completed files, safe deletion, player arguments, stable
TXT corrections, WAL-safe backup/restore and partial-download scan exclusions.

The generated end-to-end check runs a real loopback torrent through a source-result
fixture, real native download and real scanner import, then verifies duplicate
rejection, preserved notes and queue persistence after reopening. Existing native
interruption/resume and the rest of the regression suite also run. Visual checks
cover the main navigation, Settings, setup, queue, results and review surfaces.

No real library files, public torrents or live browser settings are changed by
these checks. A live Chrome/Nyaa session still needs the user's reloaded extension
and source permission; the setup guide performs that actual connectivity test.
Packaged EXE/clean-machine validation remains a separate release check. Source
layouts and anti-bot pages can change, so failures remain actionable rather than
being treated as confirmed absence of an episode.

Implementation references: Chrome's Native Messaging/runtime and scripting APIs
at https://developer.chrome.com/docs/extensions/reference/api/runtime and
https://developer.chrome.com/docs/extensions/reference/api/scripting ; player options
at https://mpv.io/manual/stable/ and https://github.com/videolan/vlc .
