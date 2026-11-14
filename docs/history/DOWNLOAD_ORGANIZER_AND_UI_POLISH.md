# Download organization and interface fixes — 11 November 2026

## Download staging and identity

Organizer no longer scans a download staging directory as one anime called
`animevault-downloads`. It excludes unverified payloads and the dedicated download
destination from generic folder organization (without excluding a download
destination that is itself a configured library root).

After **Organizer → Scan now**, completed tracked jobs appear individually under
their linked library anime names, irrespective of encoder filenames or saved
search aliases. Active/unverified downloads are excluded. Each completed job's
**Review** opens the existing safe completed-download move preview, filtered to
that job, which selects its anime/season destination. Files are moved only after
explicit confirmation; identities, paths and history use the established journal.

Old cached preview rows named `.animevault-downloads` route to the safe download
preview instead of generic season organization. Generic execution of a staging
container is blocked. Mixed batches containing download jobs ask for individual
Review, rather than flattening their files into a shared Season 1.

## Counts, responsiveness and release popup

Popup sizing correction: up to three complete rows are now shown. Additional
releases scroll vertically. Popup-specific min/max row sizes survive theme-scope
restyling, preventing layout compression after the popup is shown. Five-release
tests at 100% and 130% verify the first three rows and scrolling to the final row;
25 focused popup/Home checks pass. Existing hover and navigation are preserved.

- Metrics-only refreshes no longer overwrite the Downloads queue count with zero.
- Setting an unchanged navigation caption no longer emits geometry-change signals.
- Navigation/header styles are reapplied only when theme/scale changes, and active
  buttons are updated only when their state changes. Updates/Downloads avoid
  identical stylesheet reapplication; unchanged queue snapshots do not rebuild
  the transfer model. These remove repeated work; no universal latency bound is
  claimed without profiling the installed library.
- Release-hover height now accounts for actual row minimums, spacing and borders;
  horizontal scrolling is disabled. Long lists remain vertically scrollable and
  popup placement remains bounded by the screen. Two-row coverage verifies that
  the last row fits without being cut off.
- Updates exposes View changes, Later, Dismiss and all other existing actions
  directly. More is removed. Buttons have equal scaled width and wrap when needed.
  Download shortcuts and per-anime restore behavior are retained.

## Settings and players

- PotPlayer is available in Media Player, standard-path detection and launch;
  the playback menu shows its name. Existing VLC/MPV playback integration is not
  falsely attributed to PotPlayer: detailed progress integration remains limited
  to supported players.
- Player cards initially use system fallback icons. On first opening Media Player,
  a worker loads vendor artwork and caches PNGs under `data/player-icons` in the
  application's configured data directory. Installed executable icons are preferred;
  otherwise known vendor website icons are requested. Successful icons are reused
  across launches. Failed attempts have a one-day cooldown. No icon network or
  extraction work runs on the GUI thread. No live icon download was performed
  during validation, so unavailable vendor icons may retain the fallback.
- Extraction uses the bundled `scripts/cache_player_icon.ps1`, launched hidden;
  the EXE build includes it. Cache requests are bounded in bytes and time.
- Downloads/Sources labels and fields use larger text. Connect Chrome extension
  and Open Chrome extension folder share a compact row. Open Downloads, destination,
  watcher/import, source and backup/maintenance actions are content-sized and
  grouped into wrapping rows. Existing callbacks and controls are preserved.

## Validation and changed files

53 focused tests passed: settings reference (3), Organizer manual UI (6),
transfer screens (8), download recovery/moves (12), Home (17), and seven new
targeted tests in `tests/test_download_settings_polish.py`.

Inspected temporary-data Settings renders with compact Chrome actions. Tests
cover stable navigation counts, completed-job identity, staging exclusion and
execution guard, cached-icon reuse, PotPlayer detection, direct Update actions,
full release-hover height, and compact settings actions. No real library files
were moved or deleted. Live torrent transfer, live vendor icon downloads and
machine-specific latency measurements are outside these checks.

Implementation changes: `app/core/organizer.py`, new `app/core/player_icons.py`,
`app/config.py`, `build_exe.py`, `scripts/cache_player_icon.ps1`, navigation/header
and airing popup components, `app/ui/main_window.py`, settings presentation,
Organizer/Updates/Downloads/Details pages, regression tests and render helper.
