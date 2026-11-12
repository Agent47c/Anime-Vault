# Anime Vault — phased performance, security and architecture audit

Started **12 November 2026, Asia/Karachi**. Evidence timestamps are UTC.
Branch: `codex/audit-instrumentation`.

**Latest user validation:** the user reports testing the whole app with no crashes
and significantly better lag. The matching post-fix session
`6748-1794480712744937600` ran from **15:51:52 to 15:57:53 Asia/Karachi** on
12 November and recorded a clean session end. This is user-reported broad
functional coverage, not a checklist-level proof of every feature or the full
Phase 4 stress matrix.

**Status: Phase 3 started and was interrupted by a sustained real-app freeze.**
Function-only external stack captures were saved. The user then explicitly
approved a focused thumbnail/image-scaling fix and closing only frozen process
20052, and later approved the measured Details-styling fix. Those scoped
exceptions are documented below. Other proposed fixes remain audit-only. The
full Phase 4 scaling matrix has not run.

## 1. Executive summary — provisional investigation order

**Details delay investigation:** the user reports slow Details opening across all
titles. A copied-database probe reproduced roughly two seconds for a 24-release
series. Its final GUI build stage took about 1.39 seconds, including about 0.8
seconds clearing styles across 390 child widgets, followed by the final shared
theme application. One-season cases also repeated this work and loaded in
0.46–0.65 seconds. These were pre-fix measurements. See
[`DETAILS_LOADING_AUDIT.md`](DETAILS_LOADING_AUDIT.md) for source locations,
measurements, limits and the focused proposed fix.

The user subsequently approved that focused change. Details now constructs with
the final shared stylesheet, skips unnecessary child-style resets and avoids an
identical root-style reassignment. In the same copied-data probe, the 24-row
case changed from about 2.0 seconds to about 1.0 second; small cases changed from
about 0.46–0.72 seconds to about 0.2–0.4 seconds (the last first open was 276 ms).
These fixture results are not a claim about every live workload. Details data
handling, features and navigation lifetime were preserved. See the implementation
section of DETAILS_LOADING_AUDIT.md.

**Instrumentation correction:** the user's later Search releases crash was caused
by the profiler losing PyQt slot argument trimming, not by the search backend.
The wrapper now preserves real callable signatures. A profiled button-click
regression and checks of 207 wrapped signatures passed. See
[`AUDIT_CALLBACK_SIGNATURE_FIX.md`](AUDIT_CALLBACK_SIGNATURE_FIX.md) for the cause,
scope and latest measured findings. Instrumentation faults must not be attributed
to the underlying application.

**Highest-priority measured incident: image-scaling/GIL deadlock.** In real session
`20052-1794478825431514200`, logging stopped at 15:21:22 local time. Windows
reported Anime Vault Not Responding. Repeated native stack samples showed worker
9248 owning Python's GIL while waiting through `QImage::scaled` /
`QImage::smoothScaled` / `QSemaphore::acquire`. The Python caller was
`RefreshWorker.run -> cached_refresh_image`. The GUI thread, watchdog and logger
were waiting to reacquire the GIL. The GUI's Python stack was in
`VirtualPosters.sync`, submitting `_Read` to the global Qt pool.

The native wait and GIL blockage are **Confirmed / High severity**. The exact
internal Qt pool/semaphore ownership is not fully symbolized, so the detailed
pool-starvation mechanism remains a strong inference. Profiling may have exposed
or amplified the race; an unprofiled reproduction of the old code was not run.
This was not simply a slow SQLite query. Evidence and the narrowly approved fix:
[`THUMBNAIL_DEADLOCK_FIX.md`](THUMBNAIL_DEADLOCK_FIX.md).

There is not yet enough real-session evidence to rank ten issues by measured
impact. This table ranks **investigation priority**, not proven causes or claimed
speedups. Confirmed code behavior does not establish its performance impact.

| Priority | Location / finding | Severity | Confidence | Measured real-session impact |
|---|---|---|---|---|
| 1 | `MainWindow._setup_ui`: six primary pages are constructed eagerly, several with constructor-time data loads | High | Confirmed code; impact needs profiling | Unknown |
| 2 | `UpdatesPage._render_cards`: real widgets for each matching update/health row; retained pools are not viewport bounded | High | Confirmed code; impact needs profiling | Unknown |
| 3 | `StoragePage.refresh`: rebuilds cell widgets, queries seasons per record, sizes all columns | High | Confirmed code; impact needs profiling | Unknown |
| 4 | `RefreshWorker.run`: complete in-memory DB backup and all-artwork snapshot/facts preparation | High | Confirmed code; impact needs profiling | Unknown |
| 5 | `ThemeScopes.update/apply_scope`: widget enumeration and visible-scope stylesheet/font work | High | Confirmed code; impact needs profiling | Unknown |
| 6 | `MainWindow._refresh_dirty_page`: synchronous dirty-page refresh upon stack change | High | Confirmed code; impact needs profiling | Unknown |
| 7 | `DownloadMonitor.check`: GUI config/job JSON reads, overlapping monitoring paths | Medium | Confirmed code; impact needs profiling | Unknown |
| 8 | `downloads.poll`, `EngineClient.call`: sequential worker IPC snapshots with 20-second response timeout | Medium | Confirmed code; impact needs profiling | Unknown |
| 9 | Organizer, Merge and Rematch item-widget construction loops | High | Confirmed code; impact needs profiling | Unknown |
| 10 | `LibraryIndex.__init__/select`: full records/JSON, Python grouping, filtering and two stable sorts | Medium | Confirmed code; impact needs profiling | Unknown |

**Database splitting is not justified by current evidence.** The real SQLite file
is 6,594,560 bytes (about 6.29 MiB) and already uses WAL and useful indexes. That
does not prove every query is fast, but there is no measured evidence that one
database file causes the lag. Multiple databases with exit-time consolidation
would introduce new atomicity and recovery questions. No such change was made.

## 2. Architecture, framework and real inventory

```text
main.py -> QApplication -> DB init -> FastAPI thread -> theme -> MainWindow
  MainWindow -> eager Library / Organizer / Updates / Storage / Settings / Downloads
  UI action -> IOTask / QThread / QRunnable -> services / SQLite / filesystem / HTTP
            -> queued result signals -> GUI models / cards / table widgets
  Library -> LibraryIndex -> grouped records -> visible reusable poster slots
  RefreshWorker -> WAL backup to memory + images/facts -> GUI application steps
  Downloads -> worker -> EngineClient -> private framed stdio helper -> libtorrent
  Chrome -> native host -> validated SQLite requests/inbox -> worker / GUI pump
  Local FastAPI bridge -> separate server thread -> shared SQLite library
```

Installed distribution/runtime inventory, read locally without network:

| Component | Version |
|---|---|
| Python | 3.13.2 |
| PyQt5 / Qt wheel | 5.15.11 / 5.15.2 |
| SQLite runtime | 3.45.3 |
| requests | 2.32.5 |
| FastAPI / Uvicorn | 0.141.1 / 0.52.4 |
| Pillow | 12.3.0 |
| Send2Trash | 2.1.0 |
| libtorrent distribution | 2.0.15 |
| pywin32 | 312 |

Libtorrent's installed package was inspected without starting an engine. Loaded
engine version and actual simultaneous transfers remain to be observed.

Real database read-only inventory (`audit.read_only_inventory`, session
`16604-1794477004000305800`): **452 franchises, 452 series identity rows, 360 seasons,
158 releases, 159 season/release links, 3,324 episodes, 3,499 physical files and
locations, 3,510 file/episode links and 15 history rows**. Also: one watched root,
104 scan scopes, 3,495 saved scan files, 363 matching decisions, 611 artwork rows,
434 app-state rows, zero repair candidates and three file-operation journal rows.
These are saved counts, not proof that every file is currently accessible.
Grouped live card count and active torrent count are Unknown.

## 3. Findings by area

Locations below are repository files and functions. Severity reflects potential
user impact; performance confidence is distinguished from source confirmation.

### Architecture, startup and navigation

- **A1 — High, Confirmed pattern; impact Needs profiling.**
  `app/ui/main_window.py:MainWindow._setup_ui` constructs all six pages and both
  header/sidebar shells. `LibraryPage.__init__` and `StoragePage.__init__` refresh
  data immediately. Hidden-page creation can contribute to startup cost.
- **A2 — Medium, Confirmed.** `MainWindow._on_nav_clicked` retains pages and changes
  the stack rather than recreating them. Dirty refresh and Show handlers can add
  work after the click. A short handler duration alone does not prove a fast tab.
- **A3 — Medium, Confirmed pattern; growth Needs profiling.**
  `app/ui/navigation.py:navigate` grabs a screenshot of the previous page for
  drawers. Some workflows dispose on leave, others preserve return chains.
  Repeated navigation must verify screenshot and page lifetimes.
- **A4 — Low, Confirmed inheritance/coupling.** `HomeHero` subclasses
  `library_page.py:HeroResumeCard`, so both constructor/refresh frames in logs are
  expected nested calls, not duplicate hero widgets or dead code. No dead-code
  removal is justified from that observation.

### UI widgets, scroll, resize, selection and refresh

- **U1 — High, Confirmed.** `UpdatesPage._render_cards` removes/reinserts layout
  rows and builds missing card/health widgets on category or sort changes. Pools
  reuse unchanged cards but retain visited records, not just visible ones.
  `_apply_choices` already patches affected records; it is not an unconditional
  whole-app refresh.
- **U2 — High, Confirmed.** `StoragePage.refresh` builds multiple cell widgets per
  row and calls `resizeColumnsToContents`. That construction/layout is GUI work.
- **U3 — High, Confirmed.** `OrganizerPage` preview and review tables use
  `setCellWidget`, including per-move checks. `MergePage` has per-series cells
  plus file items. Worker enumeration does not virtualize the resulting UI.
- **U4 — Medium, Confirmed safeguards; residual cost Needs profiling.**
  `VirtualPosters.sync` uses visible slots plus preload rows above 64 items,
  deduplicates queued image reads and skips unchanged visible signatures.
  `set_records` still reflows changed results; selection signatures sort IDs and
  keyboard navigation searches records. Library list and EpisodePage use delegates.
- **U5 — Medium, Needs profiling.** `SmoothScrollArea.wheelEvent` reads motion
  preference and animates one scrollbar target. Scroll values also trigger slot
  sync and painting. The source alone does not establish whether the animation,
  rebinding, painting or unrelated GUI completions cause the reported lag.

### Threads, cancellation and ownership

- **T1 — Medium, Confirmed architecture.** `app/ui/io_task.py:IOTask.run` executes
  service operations and emits queued results. `track` retains workers during
  navigation. Many heavy operations are already in workers; this is not evidence
  that every disk/API call is off the GUI thread.
- **T2 — Medium, Confirmed limitation.** Search generation checks reject stale
  results, but running requests can only stop between cancellation checks or at
  timeout. Interruption is cooperative, not instantaneous.
- **T3 — Medium, Needs profiling.** Concurrent image/scan/download work can compete
  for HDD bandwidth, CPU or the GIL despite running outside the GUI thread.
- **T4 — Low, Confirmed safeguards.** Detail data is prepared in a worker and
  built in GUI steps with generation/deleted-widget guards. Detail episode
  enrichment uses a direct signal connection for data processing in the worker,
  rather than constructing GUI widgets there.

Worker/thread inventory:

| Family | File / role | Cancellation or lifetime |
|---|---|---|
| IOTask | `ui/io_task.py`; facts, service actions, watchers, playback, searches | Caller checks; app-wide tracking |
| RefreshWorker | `ui/refresh.py`; backup/scans/images/facts | Interruption checks and updater cancellation |
| UpdaterThread | `core/updater.py`; metadata/calendar | Cooperative cancellation, HTTP timeouts |
| OrganizerWorker, ScannerWorker | `pages/organizer_page.py` | Stop/interruption paths |
| MergePlanWorker, MergeWorker | `pages/merge_page.py` | Plan interruption checked after plan; moves check cancellation |
| DuplicateWorker, ScanWorker | duplicate/settings pages | Cooperative scan checks |
| UpdateActionWorker | `pages/updates_page.py`; dispositions | Worker commit, GUI completion |
| AniListSearchWorker, ApplyMatchWorker | `dialogs/rematch_dialog.py` | Search generation/cancellation; worker apply |
| ParseAndMatchWorker | watched import dialog | Worker matching, review before applying |
| RecycleWorker | delete confirmation dialog | Confirmed OS recycle operation |
| EpisodeWorker, DetailEpisodeWorker, PreviewWorker | episodes/detail components | Cooperative checks and visible previews |
| NewsArtwork | release-news page | Worker and interruption checks |
| ArtworkLoader._Fetch | `ui/artwork.py` | Dedicated pool of 2, pending-ID deduplication |
| VirtualPosters._Read | grid/list thumbnail reader | Shared QThreadPool; stale-result identity checks |
| EngineClient._read | `core/builtin_torrents.py` | Reader thread, native subprocess, pipe timeouts |
| Chrome connected reader | `core/chrome_bridge.py` | Input queue, daemon reader, EOF |
| FastAPI-Server | `api/server.py` | Separate daemon thread; shutdown join |

### Images and artwork caches

- **I1 — High, Confirmed pattern; peak Needs profiling.**
  `RefreshWorker.run` loads every saved cover/banner into its snapshot dictionary.
  The shared decoded cache is bounded to 128 MiB, but snapshot references can
  retain all images independently during refresh/application.
- **I2 — Medium, Confirmed safeguards.** `cached_refresh_image` versions by file
  stat and limits decoded dimensions to 360x540/1280x720. Virtual views read in
  workers. ArtworkLoader has a two-worker limit and a 300-second retry guard.
- **I3 — Medium, Confirmed.** `anilist_client._cached_artwork` caches provider/URL
  versions and ABSENT/FAILED states, with per-key locks. READY cache validation
  decodes again. Its lock dictionary has no evident pruning; long-run impact is
  Unknown rather than an established leak.
- **I4 — Medium, Confirmed fallback; hot-path use Needs profiling.**
  `refresh_pixmap` falls back to synchronous `QPixmap(path)` outside snapshots;
  `artwork_version` falls back to stat calls. Trace actual calling threads first.
- **I5 — Medium, Confirmed protections; residual risk Unknown.**
  `_download_artwork` requires HTTPS, limits redirects and compressed response to
  16 MiB, validates decoding and atomically replaces cached files. No explicit
  decoded-pixel cap is evident there; decompression-heavy image behavior has not
  been tested. No exploit is asserted.

### Database schema, indexes and query behavior

- **D1 — Medium, Confirmed.** `db.get_connection` opens a connection and applies
  PRAGMAs per call, except during refresh snapshots. Small `get_state` operations
  can incur repeated connection/query overhead. Timers distinguish connect,
  execute, fetch and commit rather than attributing all time to SQL execution.
- **D2 — High, Confirmed N+1 pattern.** `StoragePage.refresh` calls
  `get_seasons_for_franchise` for every record. Within refresh snapshots these are
  memory SELECTs, not HDD queries, but still N calls plus JSON parsing/layout.
  Duplicate discovery has a similar worker-side season-per-franchise loop.
- **D3 — Medium, Confirmed.** `LibraryIndex.__init__` loads full franchise records,
  metadata and grouping state. `select` traverses groups and performs two Python
  sorts for stable ordering. Scaling costs remain unmeasured.
- **D4 — Low, Confirmed positive design.** Existing indexes cover title NOCASE,
  rating, size, watch/storage status, season owner/number, physical-file season,
  episode history and scan scope. Identity/location keys have uniqueness indexes.
  Extra indexes or split databases are not automatically improvements.
- **D5 — Medium, Confirmed.** Jobs, preferences, release caches and bridge requests
  share serialized `app_state`. `downloads.poll` saves the whole job array;
  `source_bridge.wait` repeatedly reads state. Write amplification and contention
  need measurements before schema changes.

### Torrent engine

- **Q1 — Medium, Confirmed.** Libtorrent is isolated from Qt in a private process.
  `EngineClient.call` uses framed JSON with a 20-second response timeout.
  `downloads.poll` requests per-job snapshots sequentially under a shared lock.
  This is worker time but may age progress for large queues.
- **Q2 — Medium, Confirmed.** DownloadMonitor checks every 3 seconds for active
  built-in jobs, otherwise 15 seconds. Visible DownloadsPage refreshes at 2.5
  seconds; a drawer has a 2-second timer. GUI checks read configuration/job JSON
  before launching workers. Actual received-update rate is pending.
- **Q3 — Medium, Confirmed.** `DownloadsPage.render` retains its model when row IDs
  match, but emits dataChanged over all rows/columns, recomputes category counts
  and aggregate rates. It does not recreate a widget per torrent each tick.

### Filesystem, scanning, identity and recovery

- **F1 — Medium, Confirmed.** `scan_state.inventory` enumerates/stats video files
  before comparison. Incremental matching does not eliminate enumeration. Offline
  root state and saved inventories exist; a real unplug/reconnect test is pending.
- **F2 — Medium, Confirmed.** `LibraryWatchers` is opt-in, debounces for 1.8 seconds,
  watches at most 5,000 directories and adds paths in chunks of 20. It schedules
  local scans, not a guaranteed recursive event for every new nested folder.
- **F3 — High safety importance, Confirmed safeguards.** `file_operations` journals
  intent with FULL durability, rechecks signatures, blocks overwrites and refuses
  cross-volume moves without a separate workflow. Recovery flags ambiguity rather
  than guessing. No real move/fault-injection was performed by the audit.
- **F4 — Medium, Confirmed existing behavior.** `duplicates.digest` already uses
  SHA-256, including rechecking retained/candidate files before OS recycle. This
  predates the audit and needs clarification against the earlier request to skip
  SHA-256. It has not been changed or invoked in setup.

### Chrome bridge and local API security

- **C1 — Low current concern, Confirmed safeguards.** `chrome_bridge` validates the
  connected extension ID, action, selected-site origin and magnet. Native frames
  have a 65,536-byte limit. Capture transport is framed stdio, not a localhost
  HTTP capture endpoint. Host stdout must never contain profiling output.
- **C2 — Medium, Confirmed.** `source_bridge.finish` caps cleaned results at 100
  and limits strings. `claim` uses a transaction; `wait` polls every 150 ms with
  cancellation/deadline. The native connection checks roughly every 300 ms and
  heartbeats every 4 seconds. Cross-process DB contention is unmeasured.
- **C3 — Medium, Confirmed boundary; acceptability Unknown.** FastAPI defaults to
  loopback, checks configured origins and optional tokens and disallows
  non-loopback startup without a token. Without a token, local non-browser
  processes can access allowed endpoints. This is a deployment/threat-model
  decision, not proof of an exploit.
- **C4 — Medium, Confirmed.** Several async FastAPI handlers call synchronous DB
  helpers directly. This can block the server event loop, which is separate from
  Qt's GUI event loop. Concurrent API stress has not run.

### Reliability, logging, coupling and tests

- **R1 — Medium, Confirmed.** `ArtworkLoader._Fetch.run` catches broad exceptions
  and preserves fallback art, concealing some failure causes. Wrappers record
  escaping error types only; swallowed failures remain an observability gap.
- **R2 — Medium, Needs profiling.** Detail read snapshots span incremental GUI
  construction; workers can outlive pages. Existing generation/deleted-widget
  checks help, but repeated navigation must measure cleanup/WAL/widget growth.
- **R3 — Low, Confirmed coupling.** `LibraryIndex` imports UI artwork helpers and
  refresh imports Storage health. Shared components coexist with legacy inline
  presentation paths. No coupling refactor was attempted.
- **R4 — Positive evidence with limits.** Hundreds of regression tests cover
  identity, safe moves, scanners and UI. Passing fixtures do not establish actual
  HDD smoothness or long-run native memory bounds.

## 4. Widget inventory

Counts distinguish saved records from live observed widgets. Runtime selected
counts will be filled from Phase 3/4 logs.

| Screen | Approach | Item count | Pooled? | Virtualized? |
|---|---|---|---|---|
| Library grid | Poster slots in outer scroll area | 452 saved records before grouping/filter; visible count Unknown | Yes | Above 64 items |
| Library list | QTableView/delegate at scale, small-table fallback | Grouped/filtered count Unknown | Model/delegate | At scale |
| New seasons strip | Poster QWidget per update | Unknown update count | Per ID | No |
| Schedule | Fixed day cards/release popover | Selected range/day Unknown | Day content reused | Small fixed display |
| Updates/Health | Cards in layouts | Current filter Unknown | Per ID | No |
| New Anime Releases | QWidget grid | At most 20 per discovery page | Render rebuild | Bounded pagination |
| Broadcast timeline | Row widgets | At most 50 per schedule page | Render rebuild | Bounded pagination |
| Organizer/review | QTableWidget/cell widgets | 104 saved scopes; live preview Unknown | No bounded pool | No |
| Merge | Series cell widgets + file items | Actual plan Unknown | No bounded pool | Item table, not widget pool |
| Duplicate review | Group/file review widgets | Actual candidates Unknown | No bounded pool identified | No |
| Storage | Cell widgets for every row | Current on-disk count Unknown, <=452 records | Recreated on refresh | No |
| Settings | Eager fixed tab panels | Fixed settings set | Retained | Not necessary for fixed fields |
| Details | Incremental widgets, delegated embedded episodes | Selected season/file count Unknown | Disposed on leave | Episodes yes; season rows no |
| Choose Episode | QListView/model/delegate | 3,499 saved files overall; selected series Unknown | Model/delegate | Yes |
| Find Download Files | Delegate-based results and availability | Source result cap 100/message | Models updated | Yes for rows |
| Group series | QListView/proxy/delegate | Grouping candidates Unknown | Model/delegate | Yes |
| Rematch | Result cards/assignment widgets | Returned count Unknown | No viewport-bound pool | No |
| TXT import | Worker matching and review widgets | Input line count Unknown | Runtime Unknown | No bounded virtualization confirmed |
| Custom/Edit/Delete/Season numbers | Forms/dialogs | Fixed fields or selected entries | Per workflow | Usually not applicable |

## 5. GUI blocking measurements and instrumentation verification

### Latest completed user test

Session `6748-1794480712744937600`, about six minutes, profiling enabled:

| Operation | Count | p95 | Maximum |
|---|---:|---:|---:|
| Tab queued return | 86 | 331.631 ms | 428.046 ms |
| Virtual poster sync | 831 | 13.687 ms | 99.201 ms |
| Wheel handler | 546 | 4.364 ms | 170.543 ms |
| Search releases handler | 3 | 1.069 ms | 1.069 ms |
| Search result GUI application | 1 | 5.227 ms | 5.227 ms |
| Theme change | 7 | 651.963 ms | 651.963 ms |
| Text-size change | 2 | 728.594 ms | 728.594 ms |
| Full refresh worker | 25 | 8,957.025 ms | 12,694.476 ms |
| Detail restyling | 8 | 84.349 ms | 84.349 ms |

Startup remains expensive: first event-loop turn **11,175.116 ms**, including a
**4,748.740 ms GUI-thread Storage refresh**. These are inclusive wall times;
they are not additive. Worker refresh durations do not directly equal GUI stalls.
The user reports a significant improvement, but these different session workloads
do not support a precise percentage speedup.

There was **no recorded callback TypeError** and the session ended cleanly. The
log includes a source-search cancellation, a source-search ValueError of unknown
specific cause (error text is deliberately not captured), and release-cache
misses. Propagation through multiple wrappers repeats some exception records;
they must not be counted as independent crashes.

Twenty-four memory samples peaked at **706,600,960 bytes** of working set (about
674 MiB); final sampled RSS was **426,786,816 bytes** (about 407 MiB). Tracked
QWidget wrappers went from 2,454 to 3,268 as more screens were visited. This
short, changing workload does not establish a leak. Sampled and final logger
queue-drop counters were zero, but **44 malformed JSONL lines across the entire
accumulated file** were excluded; that is a separate cross-process evidence
integrity limitation, not equivalent to queue drops.

Next measured investigation priorities: startup Storage construction, theme/text
restyling, repeated full-refresh work and transient artwork memory. No additional
application changes were made following this positive user test. Larger scale,
long-run, external-drive and many-torrent tests remain pending.

### Earlier incident and verification measurements

First real session measurements (12 November, session
`20052-1794478825431514200`; inclusive times, not additive):

| Operation | Measurement | Thread / evidence |
|---|---|---|
| MainWindow construction | 6,814.808 ms | MainThread, constructor wrapper |
| Startup Storage refresh | 3,058.420 ms | MainThread, `StoragePage.refresh` |
| Tab handler / queued return, six switches | Max 1,314.213 / 1,363.495 ms | MainThread, tab wrappers |
| Organizer style application | 1,113.481 ms | MainThread, `refresh_home_style` |
| Virtual poster sync | Max 734.322 ms, p95 16.997 ms over 458 calls | MainThread |
| Background full refresh | 4 runs, max 6,613.666 ms | Worker threads; not itself a GUI stall |
| Wheel handling | 170 calls, max 75.047 ms, p95 24.036 ms | MainThread; paint/queued work is separate |
| Sustained freeze | User-reported, Windows Not Responding; logs stopped 15:21:22 and native wait persisted at 15:28:02 capture | Native image worker held GIL; GUI/logger/watchdog blocked |

Peak working set in the pre-freeze memory samples reached 631,545,856 bytes
(about 602.3 MiB); sampled live QWidget wrappers rose from 2,454 to 2,736. A short
run with active image loading does not establish a memory leak. Three malformed
JSONL lines were detected and excluded by the summary; appending from multiple
processes is not assumed perfectly atomic. This limitation needs addressing in
instrumentation if further sessions show lost evidence.

Post-fix focused verification used 128 synthetic records, 32 **copied** cached
artworks, 25 live poster slots and a deliberately small native global pool. With
profiling enabled, the cold/warm scrolling tours took 934.280 / 874.882 ms,
including deliberate test waits. There were zero >100 ms heartbeat delays;
maximum lateness was 46.592 ms. Peak working set was 107,200,512 bytes (about
102.2 MiB). Evidence: `audit.image_stress_end`, session
`13336-1794479560482805000`. These are isolated regression observations, not a
promised speedup or a completed real-library retest.

Initial verification used a temporary DB and a single empty QWidget, **not a
benchmark of the user's running app**. The injected pause below must never enter
the real-action ranking.

| Location / operation | Measured duration | Frequency/scope | Evidence |
|---|---|---|---|
| Deliberate `time.sleep(.18)` callback | Approximately 180 ms | Artificial once/run | `audit.smoke_begin/end`, `gui.heartbeat_late` |
| Watchdog sampled lateness during injected pause | Maximum 116.010 ms in initial verification | Artificial | `gui.stall_sample` |
| Memory-sample QWidget enumeration | Maximum 0.114 ms in initial fixture | Four samples, one widget | `memory.sample` |
| Empty temporary schema initialization | Maximum 49.545 ms in initial fixture | Two runs | `app.db.init_db` |
| Real read-only DB counts/index inventory | 7.279 ms | One metadata inventory | `audit.read_only_inventory`, session `16604-1794477004000305800` |
| Real startup, scroll, tab return and rematch | Unknown | Awaiting guided session | Not measured yet |

Initial one-widget fixture working set reached about 40.5 MiB. That is not the
full app baseline. Later full-window checks also use an **empty temporary DB**,
offline, without starting the API server. They test hook compatibility/clean exit,
not real-scale performance. Earlier development runs exposed a profiler teardown
  crash associated with enumerating Qt's native widget wrappers. The probe now
  counts already existing GC-tracked QWidget wrappers instead, does not create
  or retain native transient wrappers, and explicitly detaches before Qt
  destruction. Native-only widgets are excluded from that count. Failed
  development sessions must be excluded from performance conclusions.

One completed full-window verification session (`17952-1794478542654107300`)
measured MainWindow construction at 787.920 ms, Settings construction at
251.183 ms and first event-loop turn at 1,497.004 ms from recorder startup.
It sampled 808 GC-tracked live QWidget wrappers and 101,285,888 bytes of working
set (about 96.6 MiB). This confirms measurable fixed startup UI cost even with
an empty DB **under instrumentation**, but cannot be generalized to the real
library, an uninstrumented app, normal rendered Windows performance or a memory
leak. Nested constructor times overlap.

## 6. Scaling results — Phase 4 pending

Every future cell must include duration, peak memory, >100 ms stalls, counts and
thread. No synthetic library copies have been generated yet.

| Action | 350 | 1,000 | 5,000 | 10,000 |
|---|---|---|---|---|
| Startup / Library load | Not run | Not run | Not run | Not run |
| Scroll / resize / select | Not run | Not run | Not run | Not run |
| Search / filter / sort | Not run | Not run | Not run | Not run |
| Grid/list and tab round-trip | Not run | Not run | Not run | Not run |
| Full local refresh | Not run | Not run | Not run | Not run |
| Cold/warm artwork | Not run | Not run | Not run | Not run |

Also pending: 5/20/50 legal test torrents or clearly marked simulated progress;
large Updates sets; real HDD scans; tens of thousands of temporary files;
external/offline drive if available; rapid tabs under load; 30–60 minute memory
run. Real and simulated downloads must be separate findings.

Discovery currently exposes past 30 days and future 90 days, **not a 60-day
control**. No new range was silently added for the audit.

## 7. Slowest real actions ranked

Latest real session `14700-1794480166778843100` additionally measured Storage
startup refresh at 3,255.656 ms, search-page construction at 548.523 ms and Details
restyling up to 227.387 ms. Eleven tab queued-return measurements reached
248.574 ms. Seven worker full refreshes reached 9,225.787 ms each; worker duration
is not equivalent to GUI blocking. Peak sampled working set was 679,358,464 bytes.
Nineteen malformed records across the whole audit file were excluded. See the
callback report for the complete separation of measured facts and interpretations.

The sustained image/GIL freeze is now the top incident; startup Storage and the
Organizer tab's style work are the largest completed GUI operations measured so
far. Remaining guided coverage and scale tests are pending. Use
`python scripts/audit_session.py --session SESSION_ID`
to report count, median, p95, maximum and thread for one session. Durations are
inclusive wall time; nested calls overlap and cannot be summed as CPU time.
Correlate each user-reported pause with timestamps and input/action records.

## 8. Candidate quick wins — suggestions only

1. If hidden constructors dominate startup, defer that specific page/data load.
2. If dirty-tab Storage refresh dominates, prepare immutable row data in a worker
   and update changed rows rather than recreating the entire table.
3. If tiny GUI DB calls dominate, reuse the action's existing snapshot with clear
   invalidation rather than adding arbitrary caches.
4. If full-artwork snapshots dominate RSS, bound snapshot ownership and load
   visible art first, not merely the shared decoded cache.
5. If repeated background completions dominate GUI time, coalesce the measured
   model updates rather than rebuilding every page.

None were implemented. No specific speedup is promised.

## 9. Larger possible refactors and rough effort

| Candidate | Rough effort including basic QA | Evidence needed |
|---|---|---|
| Delegate-based Updates/Health using existing components | 2–4 engineering days | Widget growth/render stalls |
| Delegate-based Storage/Organizer preview | 3–6 days each | Table construction/layout timings |
| Consolidate download snapshots and row-level progress updates | 2–4 days | Delivered rate, duplicate reads, GUI handler time |
| Shared projections/snapshot ownership and invalidation | 3–7 days | Query/JSON counts and memory lifetime |
| End-to-end cancellation/visible-first artwork scheduler | 2–5 days | Queue waits/stale work versus useful completions |

These are planning ranges, not commitments or approved work.

## 10. Recommended fix order and re-measurement gates

1. Finish guided baseline and correlate user-reported slow actions.
2. Rank real actions by p95/max/stalls and address the largest measured GUI block.
3. Repeat the same action, count, window size and cache state after each reviewed fix.
4. Address the next largest startup/memory contributor and repeat scale tests.
5. Verify safety/recovery and Chrome/download responsiveness under concurrent load.

Metrics: startup to first event-loop return; tab handler and queued-return time;
wheel-handler/queued-return time and stalls; render/refresh p95; query count and
duration by thread; thumbnail hit/miss and queue time; progress delivery rate;
RSS/private bytes/live widgets over time; scan throughput/cancellation latency.
Avoiding >100 ms GUI stalls is a target, not an achieved guarantee.

## 11. Instrumentation inventory, launch, limits and removal

Full touched-file list and exact safe removal procedure:
[`audit_logs/CHANGES.md`](audit_logs/CHANGES.md).

PowerShell launch after closing any existing tray instance:

```powershell
Set-Location 'E:\Anime Details'
$env:APP_PROFILE='1'
python .\main.py
```

Evidence appends to **one file**, `audit_logs/profile.jsonl`. Recording is queued
to a writer thread. It never prints to Chrome/torrent framed stdout. No SQL
parameter values, raw browser payloads, magnet links, tokens, search strings or
exception messages are logged. Paths may appear in scan metadata and stacks;
logs are local and ignored by Git. Existing source code is only changed within
AUDIT-START/AUDIT-END blocks. The switch is not stored in Windows settings.

Instrumentation coverage:

- Startup app-module imports, QApplication creation, constructors, DB init,
  theme, server start, first loop turn; explicit Qt attachment/detachment.
- Every main tab handler and next queued callback, not GPU presentation time.
- Library load/render/filter/sort/view/selection, visible-slot sync, wheel and
  resize methods; queued return after wheel/click inputs.
- Updates/discovery range/render/import, Details, Choose Episode, matching,
  download search and settings actions.
- Download queue operations, delivered GUI snapshot handlers, native engine IPC
  duration/command, monitor cycles and worker queue wait.
- Artwork network calls, decode time, decoded-cache hit/miss and worker queue wait.
- SQL execute/fetch/iteration/commit/backup with redacted SQL and known row counts.
- Scan inventory folder/file counts/duration; native browser message type,
  estimated serialized size and processing time.
- 50 ms GUI heartbeat and independent sampled Python stacks when excess delay
  exceeds 100 ms; memory and live QWidget counts every 15 seconds.

Measurement limits:

- Hooks add overhead; off/on real-session calibration is still pending.
- Queue limit is 50,000 events; memory/session-end records expose drops. A crash
  can lose queued logs. Multiple processes append one write per record; malformed
  records must be counted rather than assumed impossible.
- A GUI timer gap includes OS scheduling or desktop sleep. Native code holding
  the GIL can prevent accurate watchdog sampling. Python stack attribution is
  therefore a clue, not guaranteed native blame.
- Input queued-return time is not exact paint/presentation latency. Nested modal
  waits can inflate action wall time; exclude user thinking time from CPU claims.
- SELECT row count initially is -1; fetches provide known counts. Early-broken
  cursor iteration may not produce a final count.
- HTTP outer timings include pacing/retries; streaming requests may return before
  body download, which is included in the outer artwork operation.
- Browser size is reserialized JSON length, not an exact native-frame byte count.
- Generator UI builders are not timed as complete generators; event-loop/child
  work is observed instead. Paint/delegate data methods are intentionally not
  wrapped on every call to limit perturbation.
- RSS/private bytes are per process. Whole-process-tree/GPU/Python-allocation
  attribution has not been implemented or claimed.
- Widget counts cover GC-tracked live QWidget Python wrappers, excluding
  C++-only internal widgets. Sampling does not force garbage collection or keep
  widgets alive. Sampling overhead is recorded in memory.sample duration.
- Swallowed application exceptions are not fabricated as successful network hits.

Disable on the next launch:

```powershell
Remove-Item Env:APP_PROFILE -ErrorAction SilentlyContinue
```

For permanent removal, close app/native hosts, unset the switch, remove only
marked blocks from `main.py`, both host entry points and `.gitignore`, then remove
the new profiler/helpers/test files listed in CHANGES.md. Keep the report/evidence
if desired. **Do not reset/clean this branch:** it began with extensive uncommitted
app work. A whole-file restore could discard that work.

## 12. Guided-session status, remaining coverage and questions

Phase 3 checklist 1 was initially interrupted by the freeze. After the image fix
and profiler callback correction, the user reports broad app testing without
crashes and with much better lag. The latest matching session ended cleanly;
its 86 tab switches, 546 wheel handlers and search/settings operations are
recorded above. Detailed per-feature coverage beyond the logged actions is still
user-reported rather than independently verified. Continue with non-destructive
workflow checks and the remaining Phase 4 matrix before declaring the audit done.

Later checklists must cover all main pages and controls: search/filter/sort,
selection/bulk/context actions, imports, rematch/group/numbering, episode picker,
release discovery/timeline, download search/actions, every settings section,
Chrome connection/source results and safe file-operation previews. Moves and
deletion stress use disposable fixtures/copied data, not real media.

Open questions, not assumptions:

1. Which checklist action feels slow, and is it cold or repeated?
2. Is the watched root local HDD, USB/external or network storage? Is a separate
   drive available later for unplug/reconnect testing?
3. What display scaling, text size and window dimensions are used?
4. For later torrent stress, use user-supplied redistributable torrents or clearly
   labeled simulated progress?
5. How long can the app remain open for the memory run?
6. Should the existing duplicate SHA-256 code be reviewed separately given the
   earlier instruction to skip it? No hashing changes now.
7. Is a 60-day discovery range intended later? It is not currently a control.

## Validation status

Final isolated validation (`python scripts/check.py`) passed compilation and
**all 460 tests in 96.308 seconds**. The six instrumentation tests cover SQL
row/rollback/backup semantics, SQL redaction, wrapper return/error behavior,
disabled mode, native-host stdout, and clean full-window subprocess teardown.
The scanner heartbeat fixture measured a 40.1 ms maximum for 500 files; that is
not a real-HDD benchmark. Full pipeline output is in
`data/audit-instrumentation-validation.log` (local/ignored).
No real library reset, move, delete or torrent submission was used.

After the separately approved image fix, full isolated compilation and **464
tests passed in 100.819 seconds** (`data/thumbnail-deadlock-validation.log`).
The copied-artwork image stress checks also completed with profiling both off
and on. Real-library repeat testing remains pending.

After repairing profiler callback signatures, the full isolated pipeline passed
compilation and **466 tests in 101.206 seconds**. The actual Search releases
button path now has an enabled-profiler regression, not only direct method tests.
Output: `data/audit-slot-signature-validation.log`.

After the approved Details styling change, compilation and **all 467 isolated
tests passed in 98.153 seconds** (`data/details-style-validation.log`). The
copied-data before/after renders and timing probe are recorded in
DETAILS_LOADING_AUDIT.md; the next real-library Details retest remains pending.
