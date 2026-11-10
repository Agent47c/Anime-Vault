# Changelog

## Unreleased — Deterministic Windows scrolling regression

- Explicitly enable animation inside the wheel-reversal test so hosted Windows
  reduced-motion defaults do not bypass the branch being tested. Keep separate
  reduced-motion coverage and application behavior unchanged.

## Unreleased — Handle unsupported printer ICC profiles

- Identify `70727472` as the ICC printer/output class `prtr` in one cached banner.
- Remove only its unsupported JPEG ICC segments without recompressing pixels or
  relabeling the profile. Preserve other APP2 metadata and supported profiles.
- Apply the same handling to future artwork downloads and worker cache loads.
- Back up the affected banner; audit 967 cached files with zero Qt warnings.
- All six image-profile tests pass, including split ICC segments and preservation
  of non-printer profiles. See ARTWORK_ICC_FIX.md.

## Unreleased — Responsive details, Back and rematch refresh

- Prepare grouped detail records, coverage, poster decoding and resume checks in
  a worker using a consistent database snapshot. Show the detail loading state
  immediately, including when entering from the release calendar.
- Refresh after rematch/edit/group/number changes asynchronously; build the detail
  layout in short event-loop stages and ignore stale/closed-page results.
- Dispose detail navigation pages on Back/close instead of retaining hidden trees;
  preserve the existing library view and cancel availability checks when closing.
- Prepare the library index in RefreshWorker and reuse it for UI refresh/metrics.
  Reuse an already resolved series when loading its seasons.
- Add five focused regressions and document measurements/limitations in
  DETAIL_NAVIGATION_PERFORMANCE.md.

## Unreleased — Name conflicting rematch selections

- Replace the generic same-series error with full selected release names grouped
  under their verified series, plus instructions to deselect or group manually.
- Include the selected anime name when an earlier-season lookup cannot be verified.
- Keep matching rules and confirmation unchanged; 17 grouping regressions pass,
  including two new tests for error detail and unchanged library data on failure.

## Unreleased — Repair repeated Qt ICC warnings

- Trace repeated minimal-tag-size warnings to four artwork cache files with
  short ICC copyright text tags. Back up and losslessly repair those profiles.
- Preserve JPEG scan data/pixels and valid profiles; do not globally mute Qt logs.
- Repair future downloads before Qt validation and existing artwork during worker
  cache loading. Write repairs atomically and skip duplicate refresh decodes.
- Add four image-profile regressions; see ARTWORK_ICC_FIX.md.

## Unreleased — Reliable mouse-wheel scrolling

- Route wheel events over closed dropdowns and numeric editors to their scrolling
  page, without accidentally changing a season/match. Keep open popup scrolling.
- Hand off nested list wheels to the parent when the inner list reaches its edge.
- Use pixel-based vertical scrolling for item views and the shared smooth body
  for Rematch/import/edit/review workflows.
- Reverse smooth scrolling immediately on direction changes; preserve touchpad
  pixel input, scrollbar dragging and reduced-motion behavior.
- Add six mouse-wheel regression tests; see MOUSE_WHEEL_SCROLLING_FIX.md.

## Unreleased — Consistent grouping selection

- Make clicking a grouping row include/check that anime; clicking its checkbox
  also updates the main-series selection, without a second toggle.
- Unchecking the main entry chooses a remaining checked entry, or disables Review
  when none remain. Preserve additional season selections and keyboard toggling.
- Add a real mouse/keyboard regression; all 15 series-grouping tests pass.

## Unreleased — Full-page rematch, reliable season labels and editable download queries

- Open normal Rematch in the full content area; wrap full release and alternate
  titles so season suffixes remain visible. Preserve importer selection drawers
  and multi-release confirmation.
- Infer season numbers from explicit titles/verified prequel chains instead of
  response or selection order; keep unknown season labels unverified.
- Add Edit season numbers with confirmed, persistent manual overrides and stale
  edit checks. Keep file locations, provider links and episode/history records.
- Back up the local library and correct five metadata-only season labels across
  Iruma-kun and MASHLE; verify other fields remain unchanged.
- Add English/Romaji/Japanese/release title choices, editable exact download
  queries and a copyable website URL. Make alternate searches opt-in.
- Add nine regressions and document usage/verification in
  REMATCH_SEASON_NUMBERS_AND_DOWNLOAD_SEARCH.md.

## Unreleased — Searchable grouping and safe rematch confirmation

- Replace grouping dropdown with a searchable poster list and additional-season
  selection; review and confirm before atomic grouping.
- Add multi-season rematch confirmation with provider-family/assignment validation.
- Show announced releases explicitly without missing-download/Locate treatment.
- Preserve source IDs and local-season/history ownership when rematching under
  an existing canonical series; guard stale Library/calendar/detail references.
- Add grouping list styles, worker/progress handling and regression coverage.
- Document the flow and crash fix in SERIES_GROUPING_AND_REMATCH.md.

## Unreleased — TXT presence preview and automatic metadata matching

- Show already-existing titles and duplicate lines in the importer with counts/filters.
- Add a saved option to find metadata for existing unmatched titles, preserving Apply confirmation.
- Clean uploader/codec packaging while retaining years, seasons and meaningful title text.
- Reuse conservative year/season/format evidence; reject conflicting or ambiguous automatic matches.
- Persist verified source-name aliases by stable identity to prevent duplicate reimports after provider naming changes.
- Audit both supplied lists, back up and add three absent versions; all 278 source lines are represented.
- Add 12 presence/matching regressions and document results in TXT_LIST_PRESENCE_AND_MATCHING.md.

## Unreleased — Numbered TXT imports and duplicate repair

- Strip list numbering before title matching without stripping legitimate numeric
  names, brackets, season numbers or Japanese text.
- Share safe UTF-8/UTF-16/Windows-1252 decoding and Unicode duplicate keys across TXT flows.
- Recheck duplicates when saving imports and preserve existing paths/user data.
- Back up and repair proven list-generated titles; consolidate exact duplicate
  cards through series grouping without deleting records or media.
- Add 10 parsing/import/repair regressions and document the applied cleanup in TEXT_IMPORT_FIXES.md.

## Unreleased — Built-in-only downloads

- Remove qBittorrent UI, credentials, API login, submission, polling and controls.
- Use Anime Vault's native helper for all new downloads and upgrade saved engine preferences.
- Preserve external queue history and files; explicit Retry confirms a fresh native
  transfer in a separate folder with duplicate checks and preserved episode mapping.
- Save source/identity before native attachment so failed submissions remain recoverable.
- Retain file selection, native resume, speed/seeding settings and verified library import.
- Update native transfer, migration, UI and browser-capture regressions; document
  recovery in BUILTIN_ONLY_DOWNLOADS.md and update the full navigation inventory.

## Unreleased — Source-search recovery (extension 1.1.1)

- Retry extraction briefly after page load for asynchronously rendered results,
  revalidating the selected origin and permission on each attempt.
- Distinguish explicit empty searches, browser-verification pages, unreadable
  layouts and result rows without magnet links instead of one generic failure.
- Preserve manual Chrome verification and magnet/torrent fallback; no challenge
  bypass, broader permissions or automatic download behavior was added.
- Add regressions for delayed rendering, verification, empty pages and missing magnets.

## Unreleased — Settings and connected download experience

- Split Settings into six categories, preserving existing configuration and adding
  connected watcher/list, playback-language, naming-rule and backup controls.
- Add revisitable five-step setup with live connection tests and saved progress.
- Add a queue-first main Downloads destination, standard statuses, transfer details,
  both-engine controls, integrity checks and separate remove/recycle actions.
- Add Find Download Files, Chrome-bridged structured results, local/queued/source
  availability, conservative matching, missing-episode plans and reviewed submission.
- Upgrade the selected-site extension to 1.1.0 with persistent native messaging,
  inactive source-tab extraction, origin/permission checks and reconnect feedback.
- Protect partial downloads from ordinary scans, preserve list corrections by
  stable identity, and use SQLite's WAL-aware backup/restore APIs in workers.
- Add complete local download-to-library and browser fixture regressions; document
  setup, changed files, safety behavior and limits in SETTINGS_DOWNLOAD_EXPERIENCE.md.

## Unreleased — Optional built-in downloader

- Add libtorrent as a selectable engine alongside the existing qBittorrent client.
- Add file selection, progress/speeds/remaining time, pause, resume, cancellation
  keeping files, rate limits and optional completed seeding.
- Preserve selected-site browser capture, anime/season confirmation and verified
  completion indexing; keep existing qBittorrent jobs with their original engine.
- Persist torrent identities, user selections and native resume data; isolate the
  native engine in a private background process and save it during graceful exit.
- Add generated loopback-transfer/restart tests, native-failure recovery tests,
  drawer checks, dependency/build configuration and upstream license notices.
- Document usage, safeguards, changed files and limits in BUILTIN_DOWNLOADER.md.

## Unreleased — Download confirmation layout

- Keep anime/season selectors inside the browser-magnet drawer even with long
  library titles; wrap filenames and long destination paths without clipping.
- Shorten the configuration button to Configure downloads, retaining its action
  and descriptive tooltip. Keep the confirmation footer visible while scrolling.
- Verify the layout at 480px and 560px with long titles and destination paths.

## Unreleased — Persistent two-week release calendar

- Show current and next week in full, retaining earlier days after release.
- Add Previous week, This week and Next week navigation with a visible date range.
- Cache dated releases for 12 weeks independently of next-episode metadata.
- Fetch past/current/next schedules in the existing internet updater; keep cached
  data on request failures and perform no network work during week navigation.
- Preserve day hover effects, release previews and anime-detail navigation.
- Add calendar regressions and document changes in `RELEASE_CALENDAR.md`.

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
