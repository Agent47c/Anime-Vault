# Every supplied Manga design: implementation review

16 November 2026. This replaces the earlier mapping-only completion report.

Follow-up: the user's verdict on the four compact dialogs has now been applied.
See [the refinements and fresh comparisons](COMPACT_MODAL_REFINEMENTS_2026-11-16.md).
The counts and comparison inventory below record the preceding full audit;
they are not a fresh re-certification of all 32 designs after this follow-up.

## Result

There are **32 current Manga reference folders**, including the new Operation
Progress design. Every one now has a fresh runtime capture and a comparison
image. The actual result is:

| Result | References |
|---|---:|
| Applied within the approved scope | 7 |
| Partially applied, with concrete visual gaps | 22 |
| Original design superseded by a later explicit user decision | 2 |
| HTML layout checked; supplied screenshot is blank | 1 |
| Entire runtime screen missing | 0 |
| Total | **32** |

**The full redesign is not complete.** An existing screen or shared button style
does not mean its supplied composition was applied. “Applied” below means the
main layout and approved controls are present; it does not promise identical
artwork, identical data or certification of every hover/loading/error state.

## How this was checked

- Opened all 32 supplied reference images and compared them with fresh captures
  of their runtime implementations. The importer PNG is blank, so its HTML
  supplies the structural reference instead.
- Rendered with isolated temporary database/media fixtures, no network, no
  torrent engine and no personal database writes. Populated queue, search,
  duplicate, grouping, calendar and import states were supplied directly.
- Used the actual navigation embedder for workflows, including its centered
  presentation and width limits. The main Library capture includes the actual
  application shell. Other workflow captures omit that already-shared shell;
  this is not evidence that the rail/header is missing in the app.
- Captured all eight Settings categories separately. They deliberately remain
  separate rather than copying the mockup's one long page.
- Sample artwork, titles, counts, playback availability, connectivity and drive
  capacity differ by fixture. Those differences alone are not design failures.
- Offscreen static captures do not validate Windows composition, animation
  timing or every interaction state. These remain practical limits of this
  review, rather than unreviewed screen mappings.

Reproducible capture script: `scripts/capture_design_audit.py`.
Evidence: `data/design-audit-complete-2026-11-16/` (32 runtime images, 32 comparison
images, eight comparison sheets, eight Settings-category captures and inventory).

## Screen-by-screen verdict

Each Evidence link opens a supplied/current comparison. Numbers match the
capture inventory, not the older report's numbering.

| # | Supplied design / implementation | Verdict | What is applied, and what is still different | Evidence |
|---|---|---|---|---|
| 01 | Anime Details / `DetailModal` | **Partial** | Hero, action row, personal band and local-folder table exist. The episode section remains a folder summary rather than the reference's thumbnail episode rows. Hero/action spacing and density also differ. Notes-first order was explicitly requested later. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/01-comparison.png`) |
| 02 | Broadcast & Release Updates / `ReleaseNewsPage(media_id)` | **Partial** | Release identity, artwork slot, description, library/import action, sharing and broadcast table exist. The hero omits the reference's raised metadata well, spotlight hierarchy and grouped status/genre details; the composition is simpler. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/02-comparison.png`) |
| 03 | Change Password / `AdultPasswordDialog(change)` | **Partial** | Masked fields, validation, Cancel and Update exist. Rounded modal shell, subdued watermark, reference title-bar treatment and background blur are not applied. The flat generic form is not the supplied dialog design. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/03-comparison.png`) |
| 04 | Choose Episode / `EpisodePage` | **Applied** | Heading, availability notice, raised episode blocks, selected state and playback footer follow the reference. Additional mockup filters/scheduled placeholders were declined. Episode counts/paths differ with data. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/04-comparison.png`) |
| 05 | Close Anime Vault / `QuitConfirmDialog` | **Partial** | Both real exit choices, remember preference and confirmation exist. Remember is above the choices rather than below; the status well is flattened, the dialog has excessive empty height, and the reference's compact rounded/blurred modal treatment is absent. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/05-comparison.png`) |
| 06 | Confirm Selected Downloads / `ConfirmCoverage` | **Partial** | Centered workflow and per-file assignment cards exist. Per-file season controls and move-on-completion are later approved changes. Panel width, spacing, form hierarchy and heading/watermark treatment differ from the supplied compact composition. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/06-comparison.png`) |
| 07 | Confirm & Review Downloads / `DownloadReview` | **Partial** | Raised payload cards, coverage/destination information and explicit review gate exist. The linked-anime metadata/assignment panel and destination-well composition are not reproduced; assignment lives behind a separate existing action. CRC/integrity claims were intentionally declined. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/07-comparison.png`) |
| 08 | Confirm Series Grouping / `GroupReview` | **Partial** | Centered grouping confirmation, parent badge, entry cards and explicit consent exist. Current panel proportions, row badge treatment, safety-note well and footer spacing differ; the reference's blurred backing is a dimmed backing in the navigation implementation. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/08-comparison.png`) |
| 09 | Download Transfer Engine / `DownloadsDrawer` manual ingest | **Applied to requested section** | Only Search & Auto Ingest was requested: it has title, season, episode targeting, source URL, encoder/quality and magnet/torrent controls. The other reference panels were explicitly outside this request. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/09-comparison.png`) |
| 10 | Downloads & Transfers / `DownloadsPage` | **Partial** | Queue cards, raised transfer controls, completion colors, filters and guide panel exist. Guide density, allocation/source treatment and queue/guide spacing still differ. Do not count an empty queue as a successful comparison; this capture includes four transfer states. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/10-comparison.png`) |
| 11 | Edit Anime Entry / `CustomEntryDialog` | **Partial** | Two-column artwork/form layout, status, cumulative rating and save footer exist. Field/control proportions, personal-field grouping and image-panel details remain different. Add Custom Entry shares this form as requested. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/11-comparison.png`) |
| 12 | Edit Season Numbers / `SeasonFileMoves` | **Superseded with approval** | User replaced the original number-only workflow with episode-file selection, explicit Season 01/02 destinations, reviewed physical moves and database updates. Reapplying the old sliders would contradict that instruction. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/12-comparison.png`) |
| 13 | Episode Coverage / `CoveragePage` | **Applied** | Two-column report, raised per-release cards, franchise/movie summaries and export/close footer implement the reference's structure. Counts and number of release cards are data-dependent. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/13-comparison.png`) |
| 14 | Find Download Files / `ReleaseSearchPage` | **Partial** | Context/title-source search panel, filters, availability/results table and fixed review actions exist. Reference header/status chips, compact result presentation and spacing are not fully reproduced. Two confirmation actions were intentionally merged later; Download Missing was explicitly removed. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/14-comparison.png`) |
| 15 | Full Calendar / `FullCalendarPage` | **Partial** | Seven-column month grid, month navigation, raised date tiles and Today treatment exist. Tile height/row spacing makes the final week fall below the captured viewport, whereas the reference fits the month. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/15-comparison.png`) |
| 16 | Group Seasons & Arcs / `GroupSeriesPage` | **Applied within approved scope** | Search, checkable raised entries, main-series selection and reset/review actions follow the layout. Continuous virtual browsing was explicitly retained instead of reference pagination. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/16-comparison.png`) |
| 17 | Import Watched List / `WatchedImportDialog` | **HTML checked; blank reference PNG** | Drop zone, centered file chooser, status/matching/show controls, four counters, match-review rows and Cancel/Apply footer are present. A screenshot-level match cannot be claimed against a blank supplied PNG. | Current/blank reference (local artifact: `../../data/design-audit-complete-2026-11-16/17-comparison.png`) |
| 18 | Main Library / actual `MainWindow` shell + `LibraryPage` | **Partial** | Rail/header, hero, week schedule, filters/archive and pagination exist. Hero and section heights consume substantially more vertical space than the reference; the archive/pagination are below the initial viewport. This is a density/layout gap, independent of absent sample artwork. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/18-comparison.png`) |
| 19 | Merge Libraries / `MergePage` | **Partial** | Source/destination, move-preview, highlighted-file and review sections exist. Panels remain flatter than the raised reference and have different spacing/density; review controls extend further down the page. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/19-comparison.png`) |
| 20 | New Anime Releases / `ReleaseNewsPage` discovery | **Partial** | Filters, card grid, details/add actions and paging exist. Reference release/status badges, studio/category hierarchy, poster overlays and the card-footer arrangement are not fully applied. Removed presets are an approved difference, not a gap. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/20-comparison.png`) |
| 21 | New Releases Tags & Themes / transient taxonomy popovers | **Superseded with approval** | User explicitly removed staged Clear/Cancel/Apply and saved presets, and requested direct tag popovers that close outside. The original large staged panel should not be restored. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/21-comparison.png`) |
| 22 | Operation Progress (Circular & Bar) / shared `OperationProgress` | **Applied to real operation data** | New circular gauge, bar, message, processed/elapsed/status wells and keep-open notice are connected to actual workers. Unknown totals are indeterminate. Sample CRC, NVMe speed, version and fabricated stages are omitted. Existing task Stop controls retain their original behavior; no unsupported Pause/Cancel actions were added. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/22-comparison.png`) |
| 23 | Organize & File Management / `OrganizerPage` | **Partial** | Three organizer destinations, rule/root panels and preview/review table exist. Panels lack the reference's full raised depth, and top section/preview proportions differ. Current compact headings and selection safety remain intentional. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/23-comparison.png`) |
| 24 | Overlord View Changes / `UpdateReviewPage` | **Partial** | Open Details/Refresh, detected-change cards, Find Release/Ignore and sorting exist. The supplied artwork/title hero, structured release badges and compact metadata rows are not reproduced. Actions are present after saved entries load; they must not be called missing based only on a pre-load capture. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/24-comparison.png`) |
| 25 | Rematch Anime Metadata / `RematchDialog` | **Partial** | Current link, search, match results, confidence and safety/apply actions exist. Result cards, association-control presentation, border/depth and overall panel density differ from the supplied composition. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/25-comparison.png`) |
| 26 | Review Duplicate Files / `DuplicatePage` | **Partial** | Compact summary, protected-copy review, Inspect and newly approved bulk/per-anime checkboxes exist. File rows are still a plain tree rather than the reference's individual raised file cards. Pool filters and checksum additions were declined; compact heading/bulk selection were later requested. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/26-comparison.png`) |
| 27 | Five-Step Download Setup / `DownloadSetup` | **Partial** | Five steps use a single two-column page with raised cards. Card heights/control spacing leave steps below the viewport instead of the reference's compact overview of all five. Copy Extension ID was explicitly declined. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/27-comparison.png`) |
| 28 | Settings & Preferences / `SettingsPage` | **Applied within approved scope** | Section navigation, raised settings panels, inset controls and light typography are present in all eight categories. Separate categories and existing options were explicitly required; the source's combined long page and unapproved extra settings are intentionally absent. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/28-comparison.png`) |
| 29 | Storage / `StoragePage` | **Partial** | Capacity panel, five summaries, collection table and paging exist. Reference status-chip hierarchy, compact rows and raised summary treatment are not fully matched. No SMART/temperature/hash claims are added. Unavailable fixture capacity is honest data, not a style failure. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/29-comparison.png`) |
| 30 | Shield Hero View Changes / same `UpdateReviewPage` | **Partial** | Correct title/action row, saved changes, sorting, Find Release/Ignore and close exist. The reference's compact status/date row anatomy and spacing remain simplified. This is a second supplied design using the same runtime class, not a second independent feature. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/30-comparison.png`) |
| 31 | Unlock Adult Anime / `AdultPasswordDialog(unlock)` | **Partial** | Password field and real unlock/cancel behavior exist. Rounded modal surface, muted watermark, lock-field detail and reference backdrop/helper treatment are not applied. Recovery/setup modes have no separate supplied Manga design. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/31-comparison.png`) |
| 32 | Updates / `UpdatesPage` | **Applied within approved scope** | Compact header/right actions, filters, shadow-separated cards and approved Find Download / View Changes / Later / More / destructive-remove hierarchy are present. This later hierarchy intentionally differs from the older screenshot. | Compare (local artifact: `../../data/design-audit-complete-2026-11-16/32-comparison.png`) |

## Important corrections to earlier claims

1. Password Unlock, Change Password and Exit Choice are **not finished designs**.
2. View Changes is not missing its Find Release/Ignore implementation. The
   controls are constructed once structured saved entries have loaded. The
   missing artwork/metadata composition is a separate, real design gap.
3. “Every screen has Manga styles” was insufficient evidence of completion.
   Several pages have the right buttons but the wrong spacing, card anatomy or
   vertical density. The 22 Partial rows identify those gaps individually.
4. The 28 older HTML documents under `design/references` are preserved historical
   Sakura/mockup/component references, not 28 additional current Manga pages.
   They are not silently included in the current-theme completion count.

## Progress operation coverage

Update: [major-only operation routing](OPERATION_PROGRESS_ROUTING.md) supersedes
the initial broad attachment list below. Routine loads now use footer feedback;
only explicitly selected major disk actions open the circular/bar card.

The shared circle/bar card is attached to:

- Main library refresh/scanning, with worker message and known item totals.
- Settings library-root scans.
- Organizer scans, missing-file search, individual moves and batch moves.
- Merge preview disk reads and merge execution.
- Duplicate verification and duplicate deletion; deletion reports per-copy counts.
- Confirmed local-file Recycle Bin operations.
- Watchlist parsing/matching.
- Local-episode file enumeration and release-availability disk checks.
- Shared foreground IO tasks: completed-download moves, season moves,
  backups/restores and other existing actions using `io_task.start`.

It observes existing background workers and does not move work onto the GUI
thread. It waits 180 ms before appearing so immediate actions do not flash a
window; it closes at actual task termination, including errors and stops.
Percentage means worker-reported items processed, not a fabricated remaining
time or per-byte disk measurement. Existing confirmation dialogs remain before
any deletion. Existing bottom-edge refresh feedback remains available.

The mockup's Pause/Run in Background/new Cancel controls are not inferred as new
features. Existing navigation and Stop behavior are preserved. No checksum,
hardlink migration, drive-health or fake throughput claims are introduced.

## Next design corrections, in order

1. Password/Exit modal shells and compact centered composition.
2. Library/Calendar/Setup vertical density, so useful content fits the viewport.
3. Details episode rows and View Changes artwork/structured metadata.
4. Confirmation, duplicate/merge/organizer card anatomy and surface depth.
5. Discovery card badges and field/control spacing in remaining Partial pages.

These are findings, not claims that this review already redesigned the 22
Partial screens. Any correction that conflicts with the authoritative Library
or a later explicit user decision must be discussed before changing it.

## Validation evidence

- All 32 fixture render paths completed: 32 current images, 32 comparisons and
  zero capture errors. The eight Settings categories were also captured/reviewed.
- Four dedicated progress tests pass: real worker updates/cleanup, short tasks,
  unknown totals/bounds in Manga and Sakura, and legacy worker signal adapters.
- One full regression run hit a scanner timing assertion (133.4 ms heartbeat
  versus a 100 ms ceiling). This test directly runs the core scanner and does
  not construct the new progress UI. Its complete 17-test scanning module then
  passed in isolation with an 82.2 ms maximum heartbeat. This is retained as
  timing variability, rather than deleting or relaxing the assertion.
- Full-run logs are kept under `data/design-progress-*-validation*.log`.
- Final complete recheck: **691 tests passed**, with all repository checks passing
  (`data/design-progress-complete-validation-recheck.log`). The intermittent
  timing observation above is retained for transparency.
- No installer was built, and no personal database/media was changed.

Local comparison artifacts are generated under ignored `data/`; they are not included in the public source snapshot.
