# Changelog

## Unreleased — Selected-site Chrome magnet capture

- Add an opt-in Chrome extension that catches magnet clicks only on the selected
  source website; retain the existing global MAGNET handler and other sites.
- Add private Native Messaging registration restricted to the connected extension
  ID, with independent caller/site validation and bounded framed messages.
- Deliver links through a durable, deduplicated inbox to the existing app window;
  launch the app when closed and preserve single-instance/elevation behavior.
- Prefill a compact anime/season confirmation without automatic downloading;
  protect browser submissions against uncertain/duplicate API retries.
- Add browser/native-host/UI regressions and full setup/change documentation in
  `BROWSER_MAGNET_CAPTURE.md` and `browser-extension/README.md`.

## Unreleased — qBittorrent download integration

- Add a configurable website search template and editable title, group, episode
  and quality query, with the supplied Nyaa search URL as the default.
- Add authenticated loopback-only qBittorrent magnet/`.torrent` handoff, encrypted
  Windows password storage, isolated destinations and persistent tracking.
- Monitor explicitly submitted downloads in workers; verify completed selected
  video files and index them without moving, renaming or deleting seeding files.
- Add themed entry points in Settings, anime Details and the episode browser;
  preserve existing library paths, history, features and API routes.
- Document setup, native-browser handoff limits, safety and validation in
  `DOWNLOAD_INTEGRATION.md`.

## Unreleased — Phase 2: Trustworthy Scanning

- Persist scan inventories and match decisions; index changed scopes only and
  retain offline/inaccessible roots, missing-file tombstones and watch history.
- Rank filename/folder/season/part/year/format evidence conservatively, expose
  unresolved entries for review and protect manual/legacy matches.
- Cancel obsolete rematch searches, reject stale results, bound rate-limit
  handling, and pass interruption through scanner enumeration and matching.
- Share validated artwork by AniList identity and URL version; persist missing
  banners and failed-download retry deadlines instead of retrying on every visit.
- Move entry/import saves, thumbnail extraction and Locate indexing into IO
  workers; preserve outstanding tasks during shutdown.
- Invalidate Organizer previews after inventory changes; retain manual scanning.
- Fill Library grid rows across the available width while preserving poster
  proportions, title limits, hover effects and cached images during resizing.
- Add acceptance/heartbeat/layout regressions and a complete change record in
  `PHASE_2_TRUSTWORTHY_SCANNING.md`.

## Unreleased — Phase 1: Data Safety and Core Identity

- Follow-up: fixed Organizer Review button sizing/focus, replaced the review close
  glyph with a vector cross, and widened the refresh menu button for busy labels.
- Follow-up: Organizer scanning is manual; persist previews between launches and
  invalidate them when roots, rules or completed file operations change.

- Added separately persisted series, release, episode and physical-file identities,
  episode-linked history/notes, verified number mappings and current file locations.
- Back up existing databases before identity migration; retain legacy season fields
  as a compatibility inventory rather than dropping existing user data.
- Journal each move durably and update references per file; reconcile interrupted
  moves on startup, with unresolved failures retained for review and retry.
- Require review for external-move repair candidates; never relink by filename alone.
- Route duplicate removal through the OS Recycle Bin with no permanent-delete fallback.
- Add release-state filtering to the episode browser and exclude future release
  boundaries from missing-episode reports.

## 1.0.0 — Version 1 — 2026-11-05

- Initial Git baseline of the existing Anime Vault application.
- Preserved library, episode, updates, organizer, merge, storage, import and settings workflows.
- Added shared local validation, a pre-push test hook and Windows GitHub Actions checks.
- Isolated the test runner from personal data with an initialized temporary database.
- Excluded private runtime data and documented development and release expectations.

This is a source baseline, not a claim that all proposed improvements or installer
acceptance checks are complete. Future work is listed separately in
`SEANIME_COMPARISON_AND_PRIORITIES.md`.
