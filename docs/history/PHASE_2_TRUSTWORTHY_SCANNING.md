# Phase 2 — Trustworthy scanning

Implemented 6 November 2026. Based on the Phase 1 data-safety branch; the v1.0.0
baseline and personal library have not been reset. This change adds no streaming
API, downloader or automatic file-moving behavior.

## User-visible behavior

1. A local refresh compares saved file inventories before parsing and indexing a
   folder. Unchanged folders skip indexing and API matching. The startup guard
   continues to look for new anime without recursively rescanning known titles.
   Use the existing local refresh to check changed episodes in known folders;
   use internet sync when provider metadata should also be refreshed.
2. Automatic matching combines cleaned filename, meaningful folder/series title,
   explicit season, part/cour, year and media format. Generic `Episode 01` names
   are not mistaken for series titles. Repacker and encoding text still use the
   existing parser. Strong conflicts, weak titles or close competing releases
   stay unresolved. They are stored with their evidence and candidates. Other
   meaningful filenames in the same folder are checked for conflicting titles.
3. The Library has a **Needs review** filter. The existing Rematch drawer shows
   the unresolved filename, folder, explanation and a scrollable file list. Existing multi-release and
   separately matched season workflows are retained. Manual matches/custom
   entries survive subsequent automatic scans and restarts.
4. A missing root is **Offline**; a permission/read error is **Inaccessible**.
   Settings and Organizer root lists show these states with error tooltips.
   Saved inventories, episode identities and history are retained. A file absent
   below a successfully enumerated root is marked **Missing**, separately from
   an unavailable drive. A verified unchanged inventory restores available files
   when a drive reconnects.
5. Searching again in Rematch cancels the obsolete search and queues the latest
   query. Old results/errors cannot replace the current query. Closing the
   drawer requests cancellation. Results are disabled while searching so an old
   visible result cannot be applied accidentally.
6. Cover/banner files are shared by AniList identity, artwork kind and URL
   version. Concurrent requests for that same asset share one download. A null
   banner persists as absent; opening the hero does not repeatedly re-query
   metadata. Provider metadata sync can later supply a new URL. A failed asset
   download has a persistent one-hour retry deadline. The existing poster or
   gradient remains the fallback. Existing custom/legacy artwork is preserved.
7. Custom-entry saving, changed-folder indexing from Edit, thumbnail extraction,
   imported-entry persistence, and Locate season indexing now run in IO workers.
   Import saving reuses artwork already downloaded by its parsing worker.
   Errors remain visible; the app waits for outstanding IO tasks before exiting.
8. Organizer still scans only on request. A changed saved inventory invalidates
   its preview cache; it must be scanned again before using an obsolete preview.
9. Follow-up requested during this phase: the Library poster grid distributes
   available row width among the cards, removing the unused right-side strip.
   It uses the real page margins, preserves 2:3 posters, two-line titles, existing
   hover lift, filtering, sorting and click behavior. Resizing reuses the loaded
   source poster; rendering respects the device pixel ratio.

## Persistence and migration

The existing SQLite initialization applies an additive, idempotent migration:

| Table / field | Purpose |
| --- | --- |
| `scan_roots` | Root state, last check and access error |
| `scan_scopes` | Last complete per-folder inventory fingerprint |
| `scan_files` | Path, metadata signature and presence tombstone per root |
| `matching_decisions` | Series/season provider selection, source and evidence |
| `matching_review` | Unresolved context, candidates, scores and reason |
| `artwork_assets` | Provider, kind, URL version, cached filename/state/retry time |
| `franchises.local_availability` | Last observed root accessibility |
| `app_state.inventory_revision` | Invalidates cached Organizer previews |

Existing provider links are seeded once as `LEGACY_CONFIRMED`: the app does not
invent whether a historical link was manual. Explicit rematching records
`MANUAL`. Auto decisions cannot replace either kind. Explicit custom entries
without a provider are also protected. Review rows are cleared when a user
confirms the match/custom entry. Existing fields and records are not dropped.

The inventory signature is size, modification time, device and file ID. Its
SHA-256 fingerprint hashes this **metadata list**, not episode contents. This is
change detection, not content-integrity or duplicate verification. Existing
Phase 1 content-hash and Recycle Bin safeguards remain in place.

Only a complete readable scope receives a new checkpoint. Unreadable subtrees
do not replace the previous inventory. Removed paths keep tombstones and
physical-file identities; no watch history is deleted. A scan interrupted after
a completed scope may retain that completed scope's checkpoint. A scan lock
serializes competing full scanner runs. Cross-table updates remain retryable:
an index change that precedes an interrupted checkpoint is rescanned next time.

## Changed code and responsibilities

| File | Change |
| --- | --- |
| `app/core/scan_state.py` | Migration, inventories, checkpoints, availability and decision locks |
| `app/core/incremental.py` | Incremental root/scope scan orchestration, cancellation and network guard |
| `app/core/scanner.py` | Compatible public scanner adapter; reuse enumerated paths/sizes; serialize scans |
| `app/core/identity.py` | Skip unchanged physical-file syncing while retaining identity/history |
| `app/core/match_evidence.py` | Explainable candidate ranking with conflict veto and ambiguity margin |
| `app/core/matching.py` | Persist rematches, honor manual locks, save unresolved evidence |
| `app/core/anilist_client.py` | Cooperative cancellation, bounded 429 handling, shared/versioned validated artwork |
| `app/core/entry_service.py` | Worker-side entry/import persistence and FFmpeg extraction |
| `app/db.py` | Initialize scan migration; expose root availability to existing UI |
| `app/ui/artwork.py` | Validate assets in workers, recognize version changes, stable missing-banner fallback |
| `app/ui/io_task.py` | App-owned IO task lifecycle, GUI completion/error callbacks |
| `app/ui/refresh.py` | Pass interruption through file enumeration and matching |
| `app/ui/organizer_cache.py` | Include inventory revision in preview validity |
| `app/ui/dialogs/rematch_dialog.py` | Latest-query search lifecycle, stale-result guard and review context |
| `app/ui/dialogs/custom_entry.py` | Capture fields on GUI; save/index/extract in worker |
| `app/ui/dialogs/watched_import_dialog.py` | Persist accepted imports in worker without duplicate downloads |
| `app/ui/pages/detail_modal.py` | Locate-season indexing in worker |
| `app/ui/pages/settings_page.py` | Cancellation-aware scan worker and root-state labels |
| `app/ui/pages/organizer_page.py` | Root-state labels and error tooltips |
| `app/ui/pages/library_page.py` | Needs-review filtering and full-width responsive grid |
| `app/ui/components/poster_card.py` | Proportional resizing, source-poster reuse and high-DPI painting |
| `app/ui/main_window.py` | Include outstanding drawer IO tasks in shutdown waiting |
| `tests/test_trustworthy_scanning.py` | Phase 2 acceptance, caching, cancellation, heartbeat and layout regressions |
| `tests/test_workflow_dialogs.py` | Wait for asynchronous saves before checking preserved fields |
| `README.md`, `CHANGELOG.md`, this report | Full implementation and review record |

## Verification

Run `python scripts/check.py`. It compiles the application and runs the Windows
offscreen Qt suite using isolated temporary databases/configuration. No actual
anime files are moved or deleted by this validation.

The expanded suite checks:

- Unchanged scans do not re-index or request metadata/connectivity checks.
- Adding one episode updates only its changed scope and preserves existing
  physical identities and episode-linked history.
- Offline/reconnect and permission-denied cases retain saved inventories.
- Actual removal under a readable root differs from offline state.
- Cancellation never writes a partially enumerated inventory.
- Season/year/format evidence, conflicting filenames, tied candidates and
  duplicate API candidates produce safe matching decisions.
- Unresolved choices persist for review; manual locks survive reinitialization.
- Concurrent artwork requests deduplicate; null banners and failures persist;
  a changed URL selects a different artwork version.
- HTTP 429 does not recurse; cancelled searches issue no further requests;
  stale search responses cannot overwrite the latest query.
- A 500-file scan with simulated HDD delays runs off the GUI thread while a
  5 ms heartbeat timer checks that the maximum observed gap is below 100 ms.
- Grid rows exactly fill their available width and resizing does not reload
  posters. Offscreen renders were inspected at 1100, 1450 and 1920 px: used
  widths 1034, 1384 and 1854 px respectively, matching the full grid width.
- Existing Phase 1 safety, release-aware gaps, manual Organizer behavior,
  import/edit fields, multi-season matching and UI workflows remain covered.

Pre-publication run: **173 tests passed**, maximum scanner heartbeat **40.1 ms**
on this machine. Independent GitHub Windows checks are reported in the PR/chat.

## Practical limits and review steps

- Explicit full refresh still enumerates/stat-checks names to detect changes;
  this is incremental **processing**, not an OS change-journal/file-watcher.
  Reconnect verification requires a local refresh when startup skips known
  titles. Startup's new-title guard deliberately remains inexpensive.
- Matching is conservative. A later season whose release cannot be verified,
  split-cour ambiguity or contradictory folder title stays in review. No API
  result is accepted merely because it was returned first.
- Cancellation is cooperative. An already-sent HTTP request waits for its
  existing 10-second metadata / 15-second artwork timeout; no thread is killed.
  Newer rematch queries wait for that obsolete request to return.
- The heartbeat is measured evidence for the scanner path, not a universal
  hardware guarantee for every page, theme change or OS scheduling event.
  Existing small preference/history writes and legacy non-snapshot image reads
  elsewhere in the UI are not a claim of whole-app IO elimination.
- Offline titles retain their last known legacy inventory/size. Root states
  and physical-file availability indicate that those are cached observations,
  not evidence that the media was deleted. Actual manually moved files still
  use Phase 1 repair review; scanning does not silently relocate history.
- A metadata-preserving content rewrite can evade metadata-only change checks;
  use the existing content-hash verification when byte identity matters.
- Provider artwork versions use URL changes because AniList supplies no separate
  artwork revision in this client. Images replaced behind an unchanged valid URL
  remain cached. Cache cleanup/eviction is not introduced in this phase.
- Network behavior is tested with mocked providers. No live library migration,
  physical drive disconnection, real power failure or production AniList load
  test was performed.

For manual review: open a cached Library; perform a local refresh twice; add a
new episode then refresh; temporarily make a test root unavailable then reconnect;
rematch an ambiguous test entry and rescan; change search queries rapidly; verify
the hero uses its cached artwork on repeat visits; resize the grid. Check the
Phase 1 journal/repair workflows using disposable media before organizing a real
collection. Organizer previews and moves still require their existing review.
