# Performance review — 17 November 2026

Scope: navigation snapshots, season/database lookups, episode health, Home facts,
artwork preparation and download polling. Tests use synthetic or temporary data;
this review did not scan or modify personal media. No installer was built.

## Applied

| Path | Previous work | Change | Evidence |
| --- | --- | --- | --- |
| Cached season lookup | Filter every season for every anime | Build a snapshot-owned owner index once; preserve sorting and return independent dictionaries | 100 lookups over 1,000 rows now visit 1,000 rows, versus 100,000 previously; appended imports invalidate the index |
| Verified episode inventories | Repeat the same mapping query and filesystem path normalization during Home/Storage health work | Memoize per season, inventory and output mode within the read snapshot | Repeated reads use one computation; a new snapshot recomputes; caller edits do not mutate the cached result |
| Home download badges | Filter every queued job for every group | Index active jobs by owner once and merge only the group's jobs | The test reads three jobs once across 101 groups, preserving original order, progress and labels |

These are reductions in measured work counts, not claims of a specific speed-up
on the user's drive. Filesystem verification for destructive actions is unchanged.
Caches belong to each snapshot and are released when that snapshot is replaced.

## Further opportunities

1. **Bound retained artwork memory.** `RefreshWorker.run` eagerly prepares every
   stored cover and banner. The decoded-image LRU has a 128 MB limit, but a retained
   snapshot holds its own QImage references. Profile process memory on a large
   fixture, then load banners for active surfaces and enforce a shared byte budget.
   Preserve placeholders, first-open behavior and image-version invalidation.
2. **Share asynchronous download snapshots.** `DownloadMonitor.check` reads settings
   and jobs on the GUI thread, while Downloads separately requests queue snapshots.
   Measure callback duration and database calls while transfers run; consolidate
   reads in a worker if they consume the event-loop budget. Preserve shutdown and
   completed-download indexing semantics.
3. **Separate database changes from disk maintenance.** Navigation now reuses the
   memory snapshot, but genuine data-change refreshes still call file-operation
   recovery and disk capacity checks. Profile those phases separately before
   routing metadata-only changes through a smaller snapshot update. Explicit
   scans, moves and recovery must retain their current guarantees.

Existing useful optimizations were retained: virtualized/model-based lists,
retained navigation, bounded thumbnail workers, asynchronous Details preparation,
queue redraw suppression for identical snapshots and off-screen download timers
being stopped. Splitting the database or saving only at exit is unnecessary for
the work identified here.

## Verification

`tests/test_snapshot_lookup_optimization.py` covers work counts, ordering, output
isolation and cache lifetimes. Broader verification is recorded in
`data/snapshot-optimization-full.log`. An initial unprivileged focused run stalled
on a sandbox-blocked loopback player fixture; only that test subprocess was
stopped. The separately authorized full suite includes that fixture.

Final result: all 727 regression tests and repository compilation/completion
checks passed. The three isolated optimization tests also passed. No hardware
latency or real-library memory benchmark was claimed from these fixture results.
