# Performance, security and architecture audit — implementation response

Source reviewed: `PERFORMANCE_SECURITY_AND_ARCHITECTURE_AUDIT.md`.
The original audit is preserved. Findings were checked against the current code;
this document distinguishes completed fixes from partial improvements.

## Status by finding

| Finding | Status in this pass | Change / remaining work |
| --- | --- | --- |
| PERF-01 | Core issue fixed | App-owned UserEdits coalesces notes for 450ms; ratings/status changes queue background writes. A transaction saves pending fields. Close/Back flushes pending notes into the worker. The main window patches its cached records, groups and visible library instead of invoking a global refresh or watcher reload. Storage is invalidated separately. Failed writes retain pending edits and report the error. |
| PERF-02 | Fixed | Rating clicks update changed rating-button properties and the label only. They no longer construct ten legacy stylesheets or reapply the entire modal stylesheet. |
| PERF-03 | Partly fixed | Detail preparation copies only relevant franchises/seasons plus app state, not scan/file inventories. It carries a pre-resolved last-played path to retain snapshot compatibility. Prequel matching checks valid cached provider metadata first. API pacing reserves time under a short lock and waits outside it. Structural rematches/custom edits still rebuild Details, and rematch artwork still finishes in the matching worker before completion. These need a separate binding/artwork lifecycle refactor. |
| PERF-04 | Fixed write cascade | Batch watched/watching changes use the same background queue and one transaction rather than N UI-thread commits plus duplicate refreshes. Existing selection controls remain. |
| PERF-05 | Partly fixed | Refresh snapshots carry app state, season rows, stats, storage health and disk capacity for reuse. GUI metrics reuse worker disk data. Decoded refresh artwork is version-aware, downsampled for display and cached with a 128MiB LRU limit. The global refresh still copies the database and holds artwork for the snapshot; this is not a constant-memory/fully incremental refresh architecture. |
| PERF-06 | Partly fixed | Storage reuses worker-prepared health, statistics, disk data and batched season rows during normal main-window refreshes. Refresh storage requests the background refresh path. Duplicate continuous-numbering lookups were removed. Dense cell widgets remain; standalone direct Storage.refresh calls still use their fallback data path. |
| PERF-07 | Quick wins applied | WAL is initialized by schema setup, rather than reissuing journal-mode configuration for every connection. Added season-owner and watch/storage indexes. Player-path settings save on editingFinished rather than each keystroke. Global snapshot lookups reuse app-state/season caches. No cross-thread connection pool was introduced. Drawer screenshot capture and remaining settings/calendar work are still candidates for profiling. |
| PERF-08 | Organizer fix applied; virtualization remains | Organizer search debounces for 150ms and hides existing rows, instead of reconstructing cell widgets per keystroke. Library/Organizer model-delegate migration is not complete; existing widget identity and behavior are preserved. |
| PERF-09 | Downloads fix applied | Stable queue IDs/order emit dataChanged instead of resetting the whole model. Reset is retained for real insertion/removal/reordering. A stale Downloads badge callback was changed to an auto-disconnecting QObject-bound slot. Hero paint caching and deeper scroll/animation profiling remain. |
| SEC-01 | Fixed identified API exposure | Enforce configured tokens with constant-time comparison, reject non-loopback operation without a token, restrict origins/methods, validate cover containment and remove local paths/notes/personal ratings from HTTP JSON. The in-process JSON inspector retains private fields. |
| SEC-02 | Fixed | Sort direction is normalized at the DB boundary and validated by the HTTP route. Explicit franchise/season identifier allowlists protect dynamic field helpers and entry saving. Unknown fields fail before SQL execution. |
| SEC-03 | Partly fixed | Windows custom players must be .exe files; POSIX MPV uses a private temporary directory instead of a shared socket pathname. VLC's temporary HTTP password is still in its process arguments. Removing that exposure while retaining owned playback controls requires a separate VLC transport/configuration change; it is not claimed fixed. |
| SEC-04 | Fixed identified cases | Escape genres in rich tooltips, render Details labels as plain text and neutralize formula-leading CSV text. JSON and stored strings remain unchanged. |
| SEC-05 | Artwork fixed; launcher retained | HTTPS-only artwork requests, bounded redirects without downgrade, a 16MiB streamed size limit, response cleanup, image validation and cache-path containment. HTTP source templates remain supported with an explicit security hint. The existing fixed-path Chrome native-host batch launcher remains; replacement with a packaged dedicated executable needs packaging verification. |
| ARCH-01 | Partial | Storage now shares the current header/navigation shell. Five-screen styling reuses existing components through a scoped shared stylesheet. Existing legacy styling layers elsewhere have not been comprehensively removed. |

## User-visible behavior

- Typing notes does not synchronously commit or refresh the whole library.
- Closing Details flushes note edits into an app-owned writer; closing the main
  window flushes pending edits before existing background-task shutdown checks.
- Rating/status changes patch local cached data and collection counts. Fresh UI
  snapshots are reconciled with recent user edits to avoid overwriting a newer
  displayed value with an older snapshot.
- Failed edits are retained for retry on a subsequent edit/flush; an error is
  shown. They are not silently treated as saved. No automatic infinite retry loop.
- Search in Organizer keeps its existing rows and selection instead of causing
  repeated widget construction.
- Transfer progress updates retain selection when queue membership/order is stable.

## API configuration change

`API_ACCESS_TOKEN` is now enforced when set. Send `Authorization: Bearer <token>`
or `X-API-Token`; tokens are not accepted in URLs. A non-loopback bind requires a
token. For browser clients, explicitly set comma-separated `ALLOWED_API_ORIGINS`.
The default is no cross-origin browser access; wildcard credentials are removed.

HTTP clients no longer receive `root_folder_path`, `season_folder_path`,
`scan_root`, `user_notes`, `user_rating` or raw `metadata_json`. Video routes still
require indexed relative filenames and keep their containment checks. The desktop
JSON inspector is an in-process call and retains local inspection details.
Only `.env.example` was updated; the user's actual secrets/config were not changed.

## Code areas changed

- Persistence/security: `app/db.py`, `app/api/server.py`,
  `app/core/entry_service.py`, `app/core/exporter.py`, `.env.example`.
- Artwork/provider: `app/core/anilist_client.py`, `app/core/matching.py`,
  `app/ui/refresh.py`.
- Background edits/snapshots: `app/ui/user_edits.py`, `app/ui/detail_data.py`,
  `app/core/identity.py`, `app/ui/main_window.py`.
- UI consumers: Details, Library, Storage, Downloads, Organizer and settings.
- IPC: `app/config.py`, `app/core/playback.py`.
- Regression tests: `tests/test_audit_fixes.py`, `tests/test_release_additions.py`
  plus existing tests adapted for asynchronous saves and earlier approved behavior.

## Verification and limits

The normal `python scripts/check.py` pipeline passed compilation and **419 tests**.
Its 500-file scanner heartbeat measured **40.0ms maximum** in that run. This is a
specific regression-test measurement, not a guarantee for all workloads/drives.

The pipeline used isolated temporary databases and mocked/native local test
fixtures. Windows sandbox restrictions on loopback sockets required running the
pipeline outside the sandbox. Temporary diagnostic modifications to the test
runner were restored before the final passing run.

Tests exercise token/origin failures, cover traversal, SQL identifiers and sort,
CSV formulas, bounded artwork, note coalescing/close flush, exact-episode download
selection, reminder deduplication, announced discovery and existing safety/history
contracts. Subsequent targeted checks passed after final presentation/source
selection changes. No real media was moved/deleted, no live torrent was queued,
and no GitHub publication was performed in this pass.

## Recommended next work

1. Measure dirty-page refresh memory on the actual full library, then replace the
   remaining full refresh snapshot with selective read models and visible artwork.
2. Convert Library grid/list and Storage/Organizer tables to delegates in separate
   changes, preserving keyboard, selection, context menus and sorting contracts.
3. Separate structural rematch updates from poster/label refreshes to avoid full
   Details reconstruction when artwork changes.
4. Replace VLC CLI credentials and the Chrome batch launcher with verified
   platform-specific transports/packaged launchers without removing controls.
