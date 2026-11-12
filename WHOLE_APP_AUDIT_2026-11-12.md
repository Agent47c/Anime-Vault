# Anime Vault — whole-app audit, 12 November 2026

## Scope and result

This is an audit, not an implementation pass. No production Python code, real library records, media files, user settings, or design assets were changed. The new files are this report and audit-only evidence in `data/`.

Reviewed the shell/navigation, Details, Library, Updates/release discovery, settings, artwork, playback, downloads, scanner/identities, organization/moves, duplicate removal, storage calculations, export/restore, shutdown, and local API boundaries. Existing unit/integration tests provide broader coverage than the targeted probes below.

- `python scripts/check.py`: **502 tests passed**, plus compilation and the scanner performance check.
- Scanner heartbeat: **40.2 ms maximum** in the supplied 500-file fixture. This is not an app-wide 100 ms guarantee.
- `python data/whole_app_audit_probe.py`: ten targeted edge-case observations, using a disposable database, synthetic media, mocked failures and an in-process API client.
- No real torrent, provider request, OS Recycle Bin operation, destructive media operation or database restoration was performed.
- The API test needed execution outside the sandbox because Windows event-loop socket initialization stalled inside it. That environment stall is not attributed to Anime Vault.

Evidence: local `data/whole-app-audit-validation.log` and `data/whole-app-audit-probes.log`. The reproducible probe is published as `scripts/audit_whole_app.py`; raw logs remain excluded from Git for privacy.

The passing suite and these findings are compatible: the suite checks many ordinary/regression paths; these probes check additional failure and boundary conditions.

## Recommended order

| Priority | ID | Finding | Evidence level |
|---|---|---|---|
| High | A01 | Shutdown can discard failed, pending user edits | Failure reproduced; quit path invoked with pending edits |
| High | A02 | Completed downloads can ignore a confirmed season/episode assignment | Temporary-file indexing reproduced |
| High | A03 | Restore does not exclude every database-writing background worker | Restore guard bypass reproduced; corruption itself not induced |
| High | A04 | Optional-token local API accepts arbitrary Host and same-host Origin | In-process request accepted; browser exploit not attempted |
| High | A11 | One season split between Downloads and Library appears as two seasons | Temporary two-location scan reproduced; one release identity, two displayed season rows |
| Medium | A05 | Queued refresh loses scan/internet options | Callback sequence reproduced |
| Medium | A06 | Connectivity check still blocks the GUI caller | Delayed socket-check substitute reproduced |
| Medium | A07 | Grouped-series counts disagree across pages | Temporary grouped-series fixture reproduced |
| Medium | A08 | Storage legend and capacity bar use inconsistent byte scopes | Arithmetic reproduced; offline-drive source paths inspected |
| Medium | A09 | Same-second exports overwrite the previous export | Sequential export collision reproduced |
| Medium | A10 | Valid JSON with the wrong shape can break Library loading | Cache-shape exception reproduced |
| Medium | R01 | Download queue lock spans slow engine, indexing and file-move IO | Source-confirmed contention risk; no real-drive timing claim |
| Medium | R02 | Dense table rebuilding and GUI fallback IO remain performance risks | Source inspection; no new live visual/performance measurement |

“High” means address before adding convenience features. It does not mean the issue happens in every session.

## Confirmed findings

### A01 — Failed saves are retained only until the process exits

**Where:** `app/ui/user_edits.py:18–37`; `app/ui/main_window.py:1151–1160`, `closeEvent`, `_cleanup_and_exit`.

The edit service correctly puts unsuccessful notes/rating/watch-status writes back into `pending`. Shutdown, however, waits for running workers and artwork tasks; it does not require that pending edits have been saved. Once the failed worker finishes, `_finish_pending_exit` can call `QApplication.quit()`.

**Probe:** simulate an `OSError` while persisting a note, wait for the worker to finish, then invoke the final exit check with no active workers. Result: `pending_edits=true`, `quit_called=true`.

**Impact:** notes, ratings or watch-status changes can be lost after a disk/SQLite save failure followed by exit. This is a failure-path problem, not evidence that ordinary saves fail.

**Fix:** one application-owned save barrier for all exit paths. If pending edits cannot be persisted, keep the application open and offer retry or an explicit discard choice. Optionally persist an atomic recovery draft. Do not loop indefinitely without explaining the failure.

**Acceptance:** simulate locked/read-only database and save failure during close; exit is blocked or explicitly confirmed, retry preserves the newest fields, successful save allows exit, tray and full exit behave consistently.

### A02 — Download completion reparses filenames instead of honoring confirmed mapping

**Where:** `app/core/downloads.py:213–229`, `_apply_download_context`; `app/core/scanner.py:180–266`.

Download records store `season` and `episode_keys`, but `_index_completed` invokes the ordinary filename/folder scanner without passing those verified assignments into identity mapping.

**Probe:** confirm `EPISODE:S2:10`; synthetic filename says `S01E07` under `Season 02`. Completion reports `indexed=true`, but the resulting season is **1** and episode identity is **number:7**, rather than the confirmed season 2 / episode 10.

**Impact:** manually confirmed encoder aliases or corrections can disappear at indexing time. Queue coverage and Library coverage can then disagree and offer downloads for already acquired episodes.

**Fix:** carry explicit, per-file confirmed mappings through completion into the identity layer. Preserve the filename's original number as evidence while storing the verified release number separately. If a multi-file torrent cannot be mapped unambiguously, show a review state instead of marking indexing successful. Never change confirmed mapping silently.

**Acceptance:** wrong filename with confirmed mapping, split-season numbering, absolute numbering, multi-episode packs, movies and retries all retain the assignment; queue coverage and Library coverage agree after restart.

### A03 — Restore can race a refresh or metadata updater

**Where:** `app/ui/pages/settings_page.py:482–513`; `app/ui/main_window.py:942–960`, `1100–1111`; `app/db.py:756–774`.

Restore checks `io_task.running()`, active torrent work and queue status. Main refresh and metadata-update QThreads are not registered in that same task collection. Disabling the window after starting restore does not stop an already running worker.

**Probe:** a window with `_refresh_worker.isRunning() == true`, no tracked IOTasks and no transfers still reaches the restore-start callback. The actual restore was mocked and did not run.

**Impact/risk:** an old scan/provider result may write after a backup has replaced the database, contaminating the restored state or applying stale record IDs. SQLite transaction integrity alone does not establish which database generation a result belongs to. Actual corruption was not induced.

**Fix:** use a common maintenance gate and database generation ID. Stop new work; cancel/drain all writers; flush pending edits; restore and migrate; invalidate snapshots/results from the previous generation; then resume work. Keep the existing safety backup.

**Acceptance:** restore is refused or safely deferred during every writer category, including refresh, metadata, rematch, scans and edits. A delayed old result cannot update the restored database.

### A04 — Host validation is missing at the local API boundary

**Where:** `app/api/server.py:50–65`.

With an empty API token and loopback binding, Origin validation considers the request's own `base_url` an accepted origin. That URL is derived from the supplied Host header. No explicit Host allowlist is enforced here.

**Probe:** an in-process request to `/api/library`, using Host `untrusted.example:8765` and matching Origin, returned **200** with `API_ACCESS_TOKEN=''` and loopback configuration.

**Impact/risk:** the server boundary does not reject attacker-chosen hostnames. This weakens protection against DNS-rebinding-style access to local library/media endpoints. A real browser attack depends on browser/network behavior and was not demonstrated. This is not a remote-code-execution finding, nor a claim that a loopback bind exposes the service to the LAN.

**Fix:** validate canonical permitted hosts, validate Origin independently of untrusted Host, and require authentication for sensitive local media/metadata access. Preserve existing containment checks and token support. Apply equivalent boundaries to any browser-extension bridge that exposes local control.

**Acceptance:** unknown Host is rejected even with a matching Origin; unauthorized requests cannot retrieve library/media data; intended localhost clients and authorized extension flows continue working.

### A05 — Busy refresh requests lose their intended operation

**Where:** `app/ui/main_window.py:936–960`, `1010–1026`.

When refresh is busy, `_start_refresh` records only `_refresh_pending=True`. It does not retain `scan_library`, `new_only`, `allow_network` or `sync_internet`. Completion calls `_on_data_updated`, which invokes `_start_refresh()` with default arguments.

**Probe:** request `scan_library=True, sync_internet=True` while busy. Next refresh invocation is `call()` without those options.

**Impact:** a scan/sync request arriving during another refresh can turn into a cached presentation refresh. Users can reasonably believe the requested check ran when it did not. The visible refresh button is disabled while busy, but other callers can still request refreshes.

**Fix:** retain/coalesce typed refresh requests. Local-only requests must never become network requests accidentally; explicit internet requests must not be silently downgraded. Show queued operation state and clear it only after completion/cancellation.

**Acceptance:** exercise local→online, online→local, repeated scans and failure/cancellation; each operation's scope is honored and the progress bar finishes correctly.

### A06 — Clicking connectivity status can stall the interface

**Where:** `app/ui/main_window.py:616`, `1081–1097`; `app/config.py:65–78`.

The status button connects directly to `_initial_online_check`, which calls blocking `socket.create_connection`. The function is described as non-blocking, but its implementation is synchronous and defaults to a two-second connect timeout. DNS resolution can also contribute delay.

**Probe:** replace the connectivity function with a 150 ms delayed response. The GUI caller takes **151 ms** before returning, exceeding the desired 100 ms event-loop budget.

**Fix:** run connectivity in the existing worker/task system, return immediately, reuse cached status and cancel/ignore stale responses. Update status without triggering unrelated full-page work.

**Acceptance:** a slow or unreachable endpoint leaves navigation, scrolling and Cancel responsive; duplicate clicks do not launch duplicate checks.

### A07 — Counts mix series cards with release records

**Where:** `app/db.py:get_library_stats`, `get_series_library`; `app/ui/main_window.py:_refresh_metrics`; `app/ui/pages/storage_page.py:251–258`.

Library counts grouped series. Storage title counts and collection counters count raw franchise/release records. These are different units presented as anime/title counts.

**Probe:** two ON_DISK, WATCHING releases manually grouped into one series produce **1 Library card**, **2 Storage titles**, **2 Watching entries**.

**Fix:** define series counts, release counts and physical-file counts explicitly. Use the same series aggregation for counters that promise anime counts; label release-level counts accordingly. Define mixed watch-status aggregation rather than guessing from one member.

**Acceptance:** grouped seasons, a mixed watched/watching series, removed entries and partially owned series show understandable and consistent counts across Library, Storage and navigation.

### A08 — Storage bar and legend can disagree when a drive is offline

**Where:** `app/core/storage.py:15–43`; `app/db.py:get_library_stats`; `app/ui/pages/storage_page.py:30–43`, `237–250`.

Disk capacity includes available volumes only. Saved anime bytes can still include unavailable volumes. The bar clamps anime bytes to online used bytes, while the legend displays the unadjusted total.

**Probe arithmetic:** online capacity 1,000; used 800; free 200; retained anime bytes 1,500. Legend totals **1,700** against capacity **1,000**, while the bar shows anime as **80%**. These are unitless test values illustrating the same byte calculation.

**Fix:** partition usage by physical volume and deduplicate physical files. Separate online disk consumption from remembered offline inventory. Compute the bar and legend from the same partition; display unknown/offline totals separately.

**Acceptance:** unplug one of two roots, overlapping roots, zero available drives and grouped releases never make legend totals contradict capacity. Available + other + free equals capacity within the documented rounding tolerance.

### A09 — Exports can overwrite each other within one second

**Where:** `app/core/exporter.py:17–42`, `49–70`.

JSON/CSV filenames have one-second resolution and open in overwrite mode.

**Probe:** two exports with the same timestamp produce the same pathname; the second replaces the first file's contents.

**Fix:** unique filenames with exclusive creation, followed by atomic publication. Distinguish a metadata export from a full database backup: JSON currently exports franchise/season data, not every identity/history/settings table. Do not advertise it as a complete restorable database backup.

**Acceptance:** repeated exports in one second preserve both files; failed writes do not publish a partial final export. The interface states what each export contains.

### A10 — Stored JSON shape is not validated before use

**Where:** `app/db.py:889–897`; related state readers should be checked consistently.

`series_relation_cache` is decoded then immediately treated as a dictionary. Syntactically valid JSON of another type is not rejected or recovered safely.

**Probe:** store `[]` for that cache key, then call `get_series_library()`: `AttributeError: 'list' object has no attribute 'values'`.

**Impact:** malformed/legacy/corrupted state can prevent Library loading. This is not evidence that ordinary matching currently writes this invalid value.

**Fix:** typed readers with schema/version validation. Rebuild disposable caches safely and preserve invalid evidence for diagnostics. Do not clear user grouping, mappings or history merely because one cache is invalid.

**Acceptance:** test invalid JSON, null, list-vs-dict mismatch, outdated cache versions and invalid item types; Library still opens with a recoverable warning.

### A11 — Download staging and Library locations inflate the season count

**Added after the user's follow-up:** this exact scattered-file issue was not explicitly included in the initial audit. A02 concerned verified episode assignment; A07 concerned grouped-series counters. Neither fully described this separate case.

**Where:** `app/core/scanner.py:_update_on_disk_info`, `app/core/identity.py:_release`, `app/ui/pages/detail_modal.py:334–336`; `app/core/download_library.py:preview` and `move`; `app/ui/pages/downloads_page.py:97`, `142–145`.

The scanner keeps location-specific inventory rows for different scan roots. Those rows can correctly share a release identity, but Details counts the number of SEASON rows rather than unique releases. Consequently two physical locations become two displayed seasons.

**Probe:** one synthetic S01E01 file under Library and one S01E02 under Downloads, linked to the same anime. After both scans: season numbers `[1, 1]`, Details badge count **2**, distinct release identities **1**. Reproduce with `scripts/audit_split_season.py`; raw evidence remains in local `data/split-season-audit-probe.log`. Only temporary files were created; none were moved.

**Impact:** users see duplicate Season 1 rows/counts, fragmented episode coverage and potentially confusing folder actions. Do not fix this by deleting a season row and its history, or by treating all equal season numbers across unrelated releases as identical.

**Existing feature:** Downloads already contains **Move completed to library**, backed by a preview and journaled move service. It attempts to reuse the anime's main Library folder and matching season folder, and updates paths during moves. This should be repaired/clarified and reused, rather than adding a second competing move service. It currently targets indexed completed queue records; arbitrary untracked downloads need separate resolution/review.

**Recommended behavior:**

1. Display one logical season/release and aggregate its files from all verified locations, even before consolidation. Separate physical storage locations from season identity.
2. Present the existing move action clearly as **Move downloaded files to anime folders**. Preview anime, verified release/season, source and destination before the move. Ambiguous assignments require review.
3. Reuse the actual existing season folder, including custom arc names, using verified identity. Do not create another Season 1 merely because the directory name differs. Keep continuous series and movies/specials separate.
4. Move only completed, verified files through the existing journal/preflight system. Never overwrite an existing destination or silently delete duplicates. Account for active torrent/seeding use before relocation.
5. Update file locations, playback/Open folder/last-played references, download inventory and presentation caches consistently. Retain watch history, release mapping, artwork and notes.
6. Reconcile the old location inventory after success; remove an empty inventory fragment only when safe, without deleting the logical release or its history. Interrupted moves must retain recoverable partial state.

**Acceptance:** S1 episodes 1–5 in Library and 6–7 in Downloads show **one season with seven distinct episodes** before and after a reviewed move. Restart, filename collisions, offline destination, interruptions, multiple actual seasons and continuous numbering do not inflate counts or lose files/history. Same-number alternate encodes remain distinct physical files, not extra seasons.

**Status:** reproduced and documented; no application fix or real media move made in this audit update.

## Source-confirmed risks needing performance measurements

### R01 — Queue controls share a long-held global lock

`app/core/downloads.py:170–210` holds `_lock` over engine snapshots, completion indexing and saves. `app/core/download_library.py:75` onward holds that same lock across the selected file-move loop, including cross-volume copies. Queue actions use this lock too.

**Likely effect:** Pause, Retry and Remove wait behind slow disk/engine work even when their own operations are short. No claim is made here about an exact delay on your current drive.

**Recommendation:** keep short lock-protected state transitions; perform slow IO outside the global lock; revalidate job revision/cancellation when applying results. Use per-job serialization and preserve move journaling. Measure control-command latency during large copies, metadata stalls and multiple active torrents.

### R02 — Some table pages still rebuild many GUI widgets

`app/ui/pages/storage_page.py:237–288` rebuilds rows/cell widgets and sizes columns. `_create_title_cell` performs smooth pixmap scaling; the fallback refresh path queries filesystem/health data when no prepared snapshot exists. The Organizer also remains a table/widget-heavy area.

**Recommendation:** retain the existing virtualized Library approach; extend model/delegate rendering to dense tables if profiling confirms the cost. Rebind changed rows instead of reconstructing all cells, prepare thumbnails off-thread, and always supply worker-prepared disk/health facts. Keep page/scroll state but bound caches; retaining every widget forever is not necessary.

**Measure before refactoring:** page-switch time, GUI heartbeat, row binding time and memory with 250/1,000 series and a 1,200-episode series. Preserve every row action, keyboard behavior and current visual design.

## Areas checked without a new confirmed failure

| Area | Current evidence / limit |
|---|---|
| Scanner, path identity and unavailable roots | Regression suite passes. Stable series/release/episode/file tables exist; splitting the database is unnecessary. Real drive disconnect was not performed. |
| Moves, reconciliation and Recycle Bin | Existing journal/preflight/recovery tests pass. Current delete wording correctly says selected indexed videos; remaining unlink operations require context and are not automatically unsafe deletion bugs. No real power interruption or trash operation was performed. |
| Artwork and caching | Prior bounded image handling and deadlock regressions pass. No infinite retry or image-scaling hang reproduced in this run. Remaining GUI scaling risk is described in R02. |
| Navigation, breadcrumbs and update review | Existing tests pass, including recently added episode-timing/progress behavior. No fresh live pixel-by-pixel review at every scaling factor was performed. |
| Release-aware episode labels | New timing tests pass. Do not replace verified timestamps with a blanket minus-one adjustment. Provider data can still be stale; show its checked time. |
| Duplicate handling | Existing tests pass; repeated episode numbers are not proof of identical files. Keep season/release boundaries and explicit review. Do not add the previously declined SHA-256 feature in this pass. |
| Settings and downloads UI | Existing regression coverage passes. PotPlayer, retained menu/actions and explicit download matching remain intact. No real torrent was submitted. |
| API security already fixed | Existing path containment, SQL field validation, configured-token and Origin tests pass. A04 is an additional boundary gap, not a claim that these fixes are absent. |
| Player integrations | Existing tests pass. VLC's local HTTP password is still passed as a process argument; another sufficiently privileged local process can inspect it. Treat this as local hardening, not an exposed internet password. No player sessions were launched. |
| Packaging and platform behavior | Not validated against a fresh Windows installation, final EXE, real power failure or every DPI/theme combination in this audit. These remain release-gate checks. |

## Improvements proposed, not implemented

1. **First fix A01–A04 and A11:** save durability, verified episode identity, restore maintenance barrier, API boundary and scattered-file season aggregation/consolidation.
2. **Then fix A05–A10:** accurate refresh scope, asynchronous connectivity, consistent counts/bytes, safe exports and resilient cache readers.
3. **Then measure and address R01/R02:** short queue locks, row-level updates and remaining table virtualization. Retain navigation memory and existing cached data.
4. Add regression cases for every reproduced failure. Add performance gates for p95 page switches, maximum GUI stalls, queue-control response and bounded memory; document hardware/fixture sizes so results are comparable.
5. Before distributing an EXE, run fresh-install/upgrade/restore, external-drive-offline, permission-denied, interrupted move, restart-after-download and 100/125/150% DPI tests in both themes.

Optional new UX features needing separate approval: a Diagnostics page with sanitized logs/task timings, and a unified recovery center listing failed edits, move errors and unresolved mappings. These are suggestions only; do not silently add them or remove existing functionality.

### Database architecture recommendation

Keep one SQLite database with WAL, normalized identities, short transactions, indexed queries and bounded in-memory presentation caches. Do not split names, ratings, downloads and watch history into databases that merge only on exit. That would introduce cross-database consistency problems and make a crash/forced close a data-loss boundary. The confirmed stalls involve synchronous work, rebuilding and lock scope; they do not demonstrate that one SQLite database is too large.

### What changed in this audit

Added only this Markdown report, `data/whole_app_audit_probe.py`, `data/split_season_audit_probe.py`, and evidence logs. Existing application files and existing user changes were left intact. No fixes, new application features, commits or GitHub uploads were made in this audit pass.
