# Changelog

## 1.2.2 — 26 November 2026

- Restore the window to its previous position, size, and maximized state when opening Anime Vault from the system tray.
- Count distinct seasons supported by release metadata or indexed episodes. Empty folder records no longer inflate the count on Series Details.
- Fit long discovery titles on two lines, show a disabled **Added** button for owned titles, start **Next** at the first row, and preserve scroll position on **Previous**.
- Use the same centered Anime Vault logo in Windows shortcuts, the taskbar, the tray, app headers, Setup, and the uninstall entry.

## 1.2.1 — 25 November 2026

- Bundle the video decoder so episode thumbnails work in the installed app without a separate FFmpeg installation. Short clips can also produce previews.
- Use a Windows file lock that expires when its owning process exits. A lock file copied with a library profile no longer causes the false “Anime Vault is already open” message.

## 1.2.0 — 22 November 2026

- Let users choose the Windows installation folder and reuse it for upgrades. Remove deferred file replacement during setup so an upgrade can finish without rebooting Windows once Anime Vault is closed.
- Offer four fixed themes, with Sakura Dark as the default and navigation previews in Settings. Preserve explicitly saved themes.
- Repaint the application in place during theme changes and load bundled fonts before the first window is drawn. Fix overlapping Library cards, stretched episode bars, stale Organizer surfaces, and mismatched release-strip backgrounds.
- Align Organizer rule rows with Appearance & Behavior, theme the saved-preview badge, and use a red trash icon for removing configured roots.
- Keep the Updates counter, Library cards, and Updates workspace in sync with the active adult-visibility preference.
- Show the current version and link to the project on GitHub from Settings → About.

## Manga Brutalism Dark — 22 November 2026

- Add Manga Brutalism Dark as a separate appearance choice alongside Manga
  Light and the existing Sakura modes.
- Apply the dark Library reference to shared navigation, controls, surfaces,
  dropdowns, cards, progress and compact dialogs using the current Manga layouts.
- Register the dark master and record the supplied and missing screen mockups
  in the Manga Dark reference inventory.

## Live extension status and complete release rows — 21 November 2026

- Show a live rounded-square red/green Chrome extension indicator in Downloads
  settings. Green requires a recent native-bridge heartbeat, independently of
  saved registration; show website capture being off as a separate condition.
- Mark native-host disconnection immediately and expire stale heartbeats. Check
  status asynchronously while the settings control is visible and stop its timer
  when hidden.
- Paginate release discovery by visible card capacity while retaining AniList's
  existing 20-result pages and cache keys. Carry unused results forward instead
  of leaving a partial row on every provider-page boundary or dropping titles.
- Calculate initial capacity after the page is shown at its actual width. Reuse
  cached provider pages, preserve filtering, and identify a genuine end of results.
- Validation: all 776 regression tests passed, followed by six focused status and
  pagination checks. Publication checks passed; inspected the six-column,
  18-card layout and connected-state indicator with temporary data.
- No personal library data was altered and no EXE was rebuilt for these changes.

## Lightweight move recovery and shared episode notation — 21 November 2026

- Reuse the existing timestamped move-operation records as temporary recovery
  proof. Queue recovery and move previews now require completed-operation evidence
  plus the destination's file identity, rather than accepting a same-size file.
- Save the completed destination signature for verified copy/move operations, so
  routine recovery checks use metadata without rereading video contents. Existing
  interrupted-copy verification remains in place.
- Remove completed download move records in the same transaction that saves the
  final queue acknowledgement. Interrupted operations and records still referenced
  by another pending move remain available for recovery.
- Share season/episode token recognition between remembered title matching and
  next-episode search. Accept common spaced, padded and separator spellings while
  preserving original filenames and confirmed logical episode assignments.
- Validation: 768 tests passed in the full check, followed by 10 focused recovery
  and parser checks after the final adjustment. Publication checks passed.
- No new database table, new installer build or episode-number migration.

## Duplicate drive scans, remembered searches and playback progress — 21 November 2026

- Make duplicate drive checks discover current video files inside recorded anime
  folders instead of relying on stale saved filename inventories or storage flags.
  Report directory/checking progress and missing locations, skip incomplete torrent
  destinations, and preserve the existing exact-copy verification and protected keeper.
- Automatically retain edited release searches as the selected Custom search for
  that anime/season, while keeping the separate English, Romaji and Japanese choices.
- Normalize full-word episode labels and spaced season/episode tokens consistently
  when matching remembered encoder titles and checking local episode availability.
- Correct PotPlayer IPC to use pointer-sized Windows handles and result buffers.
  Treat unanswered/empty media queries as unavailable responses rather than zero
  playback progress, preserve the last valid position, and restore saved progress
  when the Home hero refreshes.
- Show transfer speeds in KB/s below 1 MB/s and MB/s above that threshold, including
  the transfer details drawer. Add consistent SVG icons to download controls/menus.
- Use a three-line navigator button and a rounded-square red/green API status mark.
  Remove the shortcut hint from library search fields, retain their clear control,
  and label active library searches with their query and matching title count.
- Reduce the white overlays on Manga Light's hero artwork so more of the banner
  remains visible while preserving the established layout.
- Validation: all 760 regression tests and compilation checks passed; publication
  checks passed. Reviewed offscreen captures of the download controls and active
  library search. Live PotPlayer playback still needs verification on the user's PC.
- No personal media was moved or deleted during validation; no EXE was rebuilt.

## Theme transitions and application restart after restore — 21 November 2026

- Refresh theme scopes when switching between Sakura and Manga Light even when
  both themes share the same base light stylesheet. Keep the existing three
  registered themes: Sakura Dark, Sakura Light and Manga Light.
- Show a required-restart dialog after successful SQLite or full-profile ZIP
  restoration, with Restart Anime Vault and Close app actions. Disable the old
  library UI until shutdown so it cannot write stale state into the restored data.
- Restart only Anime Vault, waiting for the previous process to release its files
  and instance lock before starting normal initialization.
- Show a visible Restore not started warning when running transfers or background
  work prevent restoration, instead of reporting the reason only in a status label.
- Document the search, aliases, episode confirmation, download state and completed
  file movement flows in `docs/DOWNLOAD_ORGANIZER_FLOW.md`, including current
  limitations and proposed follow-up safeguards.
- Validation: 747 tests passed in the full check; 13 focused tests passed after
  the final restore-message changes. Unicode text survived tested theme transitions;
  the reported wrong-character symptom has not been reproduced directly.
- Source changes only; no new installer or executable was built for this change.

## 1.1.2 — Fix UNIQUE constraint collision on file_locations.path_key — 17 November 2026

- Fix `UNIQUE constraint failed: file_locations.path_key` error on the Downloads page
  during automatic or manual library moves and download indexing.
- Prevent path key collisions in `identity.relocate()` by safely replacing any existing
  obsolete or replaced records in `file_locations` when moving a downloaded file into
  its library destination.
- Delete recycled files from `file_locations` in `file_operations.recycle_file()` so
  sent-to-trash files do not retain conflicting unique path keys in the database.
- Broaden error handling in `downloads.poll()` and `download_library.move()` to capture
  and surface unexpected operational errors without aborting background queue checks.
- Enhance `download_queue.check_completed_files()` to automatically reconcile verified
  file paths when a transfer has already been moved to its intended library target,
  preventing false "Incomplete or missing files" status on completed downloads.
- Add regression test suite `tests/test_file_locations_unique.py` validating path key
  uniqueness, file recycling cleanup, move recovery, and intent reconciliation.

## 1.1.1 — Database restore path synchronization and WAL persistence — 17 November 2026

- Automatically synchronize internal database and storage paths (`database_path`,
  `database_local_path`, and `data_directory` in `app_state`) to the active local user
  application directory whenever a database is restored or initialized.
- Ensure that databases restored from external drives, previous machine setups, or
  development environments cleanly rewrite their internal location records to the
  active `%LOCALAPPDATA%\AnimeVault` user path without altering personal media paths,
  custom titles, episode mappings, ratings, or watch progress.
- Validate the restored `backup_directory` and normalize it to the local backups folder
  if the stored path points to a non-existent or foreign drive, preventing subsequent
  backup write errors.
- Force immediate SQLite WAL checkpointing (`PRAGMA wal_checkpoint(TRUNCATE)`) during
  restoration and rollback so that all incoming pages are written directly into the
  physical database file before application shutdown or restart.
- Invoke `sync_database_path()` on application launch within `init_db()` and upon
  extracting full-profile ZIP backups in `restore_backup()`.
- Add comprehensive regression tests in `tests/test_database_path_sync.py` covering
  startup synchronization, external path rewrites, and ZIP archive restoration.
- Windows EXE and Inno Setup installer package updated to version 1.1.1.

## Backup progress, required restore restart and CI reliability — 17 November 2026

- Show the themed major-operation progress screen for SQLite and full-profile ZIP
  backups and restores, with operation-specific titles and elapsed feedback.
- Explain the required restart before restoring. After success, prevent stale UI
  edits, show the restart-required notice and close the app; reopening reloads the
  restored database, settings and image caches. Preserve restored window settings
  instead of overwriting them on exit. Pause polling while restoring and resume
  it if restoration fails. Existing integrity checks and safety copies remain.
- Fix CI assumptions exposed by commit 341e09e: normal-animation tests explicitly
  choose normal accessibility settings, and setup waits for actual completion
  instead of assuming completion within 100 ms. Keep reduced-motion coverage.
- Replace broken public links to ignored local comparison artifacts with explicit
  local paths. Add staged publication validation to the pre-push hook.
- Focused validation: 34 tests passed, including real full ZIP restoration with
  optional cached artwork/resume metadata and mandatory-close behavior mocked.

## 1.1.0 — 17 November 2026

- Release the Manga Brutalism light theme and shared controls while retaining
  Sakura themes, reference guidelines and the existing app features.
- Improve download confirmation, remembered search/match titles, queue completion,
  rate controls and transfer status. Correct season-folder naming and reviewed
  moves between Downloads and library seasons without renaming episode files.
- Improve Organizer/root controls, duplicate review and safe recycling, season
  editing, update actions and notification visibility after Watching imports.
- Preserve per-tab navigation and in-memory library snapshots; reduce repeated
  season lookups, episode-mapping work, badge scans and duplicate-removal IO.
- Polish popup input, menu placement, modal backgrounds, progress routing,
  calendar cards and consistent button states. Include regression tests and
  implementation/design/performance reviews for the accumulated changes below.
- Windows EXE file/product version: 1.1.0. Previous builds and user profiles remain
  separate from the new application payload. Pre-release validation: 727 tests
  and repository checks passed before the packaging-only version change.

## Snapshot lookup optimization review — 17 November 2026

- Index cached seasons by anime owner instead of scanning the full inventory
  for each lookup; keep sorting, independent results and import invalidation.
- Reuse verified episode-mapping presentation results within each read snapshot,
  reducing repeated queries and path resolution during health calculations.
- Index active download jobs once for Home badges while preserving ordering.
- Record implementation evidence and remaining profiling opportunities in
  `docs/PERFORMANCE_REVIEW_2026-11-17.md`.
- All 727 regression tests and repository checks passed.

## Reuse the loaded library during navigation — 17 November 2026

- Keep the completed SQLite memory snapshot and decoded artwork alive between
  page visits. Dirty tab redraws use that snapshot instead of launching file
  recovery, storage checks and artwork loading again. Clean visits do no work.
- Replace and close the previous snapshot after a real refresh. Keep confirmed
  notification choices, personal edits and imported anime synchronized with the
  retained database so navigation does not restore stale state.
- Keep explicit scans and refresh actions available; initial navigation waits
  for the existing startup load instead of starting another worker.
- Validation: 30 focused navigation, Details and import checks passed, including
  replacement cleanup and imports staying present in the retained database.

## Immediate update visibility after discovery import — 17 November 2026

- Publish committed Watching imports directly to the Library release strip and
  Updates page instead of routing them through the download-monitor signal and
  general disk/recovery/artwork refresh. Update the badge from the same records.
- Refresh the Library index, filters and cards without rebuilding its hero or
  calendar. Reapply committed imports after an older in-flight snapshot finishes
  so it cannot leave the imported update hidden.
- All 26 focused import, release-tracking, cache and progress regressions passed
  using temporary library data.

## Header menu placement and transfer-rate clarity — 17 November 2026

- Anchor the Manga header's shared More and Refresh menus to the visible header
  controls instead of their hidden original buttons; keep menus within the window.
- Shorten shared upload/download presets to Unlimited and 512 KB/s steps through
  3 MB/s, with six visible rows. Keep Custom and preserve saved arbitrary limits.
- Show queue, upload/download summary and footer rates in KB/s while keeping
  file-size labels unchanged. All 22 focused regression checks passed.

## Exit backdrop artifacts and duplicate-removal overhead — 16 November 2026

- Capture compact-dialog backgrounds while the dialog is hidden, preventing its
  old footer from entering the snapshot. Refresh the matching background crop on
  moves/resizes and paint every pixel of the opaque window to avoid black strips.
- Remove the second inventory update after duplicate recycling. Update matching
  season inventories without resolving every unrelated episode path on disk.
- Reuse a retained copy's hash only within the current deletion batch while its
  file identity/timestamps remain unchanged. Fully hash each selected copy and
  recheck the keeper before recycling. Keep Recycle Bin, durable journals and
  cancellation protections intact. Large files still require disk reads.
- Validation: 17 focused duplicate/modal checks passed on Qt's Windows backend,
  including active-download exit layout, mouse input, keeper mutation protection
  and avoiding per-file resolution of 1,000 unrelated inventory entries.
  The full 715-test run and repository compilation checks also passed; final
  focused tests additionally cover keeper changes during candidate verification.

## Download review completion and Organizer root controls — 16 November 2026

- Close the review immediately after successful queue submission and open
  Downloads & Transfers. Queue monitoring no longer runs synchronously before
  closing the review; Downloads refreshes asynchronously when shown.
- Mark submitted search results as queued, clear their checkboxes and prevent
  submitting them again from the same result list. Disable Review selected
  downloads when nothing is selected; preserve other results and cancellation.
- Let configured library-root rows fit the themed buttons instead of clipping
  them inside a fixed 44px row. Preserve Open folder and confirmed Remove root
  actions; removing a root does not delete its files.
- Verification: four Windows Qt regressions pass, including actual window-level
  mouse hit testing for both root controls. All 41 related search, assignment,
  season-edit and Organizer regressions pass against temporary data.
  The broader 710-test run and compilation checks passed; final focused checks
  also cover the subsequently added selective-result regression.

## Exit dialog mouse input — 16 November 2026

- Make the compact dialog's blurred backdrop ignore mouse/focus input and keep
  the actual modal in front. Replace its translucent native window with an opaque
  matching background crop, retaining the rounded face, shadow and blur.
- Verify both choice cards/radios, Remember my choice, Cancel and confirmation
  using window-level mouse events on Qt's Windows backend, including the nested
  close-dialog event loop. Remember saves only on confirmation; Cancel saves nothing.
- All nine focused checks passed using temporary data; no personal library or
  preferences were changed. The full 706-test regression run and repository
  checks also passed (the additional nested-loop test passed separately).

## Compact reference dialogs and balanced discovery actions — 16 November 2026

- Apply compact, rounded Manga overlays to Change Password, Unlock Adult Anime,
  Exit Choice and Confirm Series Grouping, with the reference face widths and
  one blurred/tinted background snapshot per opening.
- Keep dialog controls sharp and restore the underlying page on dismissal.
  Grouping confirmation now overlays its existing page; its review gate remains.
- Place remembered exit preference below the choices; restore status/choice wells,
  primary grouping badge and safety/review treatments.
- Reduce the Library hero's pale washout slightly and keep its cached artwork intact.
- Equalize Details/Add button sizes, including the labels after importing a title.
- Verify fresh fixture renders and five focused modal/UI regressions. One full
  703-test run passed; the final broad run had one scanner heartbeat timing outlier
  (198.8 ms against 100 ms). All 17 scanner checks passed separately at 55.9 ms;
  no timing assertion was relaxed.

## Major-only progress and quiet navigation feedback — 16 November 2026

- Make large circular/bar progress an explicit opt-in for confirmed disk actions:
  Organizer scans/moves, duplicate drive scans/deletion, Storage refresh,
  completed-download moves, season moves and local-file recycling.
- Route routine page loads, tab refreshes and merge-preview generation to the
  bottom bar with an operation name. Keep overlapping task messages correct
  after navigation and preserve queued explicit Storage requests.
- Simplify the Manga footer to operation feedback plus download speed and the
  currently downloading count. Move indexed information back to Library and
  remove API/free-space text from this footer.
- Add the approved red/green API dot beside the top-right menu button. Check
  AniList and Jikan asynchronously; green requires successful responses from both.
- Reduce the indeterminate circle label size so Working fits inside the gauge.
- Validation: all 698 tests and repository checks passed, including routine/major
  routing, footer overlap/navigation cleanup, queued Storage requests and API states.

## Complete design review and shared operation progress — 16 November 2026

- Replace the mapping-only UI completion claim with fresh captures and individual
  verdicts for all 32 current Manga references: 7 applied within approved scope,
  22 partial, 2 superseded by later user instructions and 1 HTML-only reference
  whose supplied PNG is blank. Record concrete gaps and comparison evidence.
- Add the supplied circular/bar progress treatment to library/root scans,
  Organizer reviews/moves, merge preview/execution, duplicate checking/recycling,
  local-episode disk checks, watchlist parsing and foreground file tasks,
  including completed-download moves and backup/restore operations.
- Display real worker totals/messages and elapsed time. Unknown totals remain
  indeterminate; short operations do not flash a stale progress window.
- Preserve deletion confirmation, existing Stop behavior and background workers.
  Do not add mockup CRC claims, fabricated speed/stages or unsupported controls.
- Final validation: all 691 tests and repository checks passed. The design review
  records a prior intermittent scanner heartbeat assertion and its isolated pass.

## Design audit, sequel calendars and duplicate bulk selection — 16 November 2026

- Audit all 31 current Manga reference mappings and correct earlier completion
  wording. Fresh renders confirm Unlock, Change Password and Exit Choice are
  visually partial; the report distinguishes runtime presence from design sign-off.
- Map cached official sequel/side-story/spin-off IDs to their library owner when
  unambiguous, and include those IDs in schedule refreshes. Home and Full Calendar
  now share the same dated entries; unknown dates remain unassigned.
- Add Select all duplicate copies and per-anime/per-episode checkboxes for eligible
  redundant copies only. Protected originals and Recycle Bin confirmation remain.
- Reduce duplicate-review heading and overview padding to leave more room for files.
- Validation: all 687 tests and repository checks passed, including new sequel-calendar
  and protected duplicate bulk-selection regression tests.

## Keep popup styling inside scoped pages — 16 November 2026

- Stop the page theme-scope handler from replacing transient menu/list styles
  with the base page stylesheet on Show. This reproduced the blue playback-menu
  selection and native row edges shown in the screenshots.
- Reapply a cached popup style if another handler changes its actual stylesheet;
  preserve the deliberate compact-menu padding used for short windows.
- Measure both action labels and their right-hand hints so the player name and
  Change in Settings label fit side by side.
- Apply dropdown setup after the new theme properties are installed, and refresh
  existing hidden combo/menu containers. Native popup effects now disable on the
  first Manga switch even when Windows starts with its menu animations enabled.
- Add regression coverage for the real scoped-window path and initially enabled
  native effects, rather than relying only on standalone/offscreen defaults.
- Validation: all 684 regression tests passed. Reproduced the screenshot's blue
  selection before the change and verified no blue selected-row pixels afterward.
  Personal media/database records and installer builds were unchanged.

## Prevent the unfinished popup frame — 16 November 2026

- Prepare combo popup styling and transparency while the native container is
  hidden. Fit the list before presentation and keep it invisible until Qt's
  final native geometry pass and the backing-store paint have completed.
- Disable Qt's native combo/menu fade and slide effects for Manga, avoiding
  captured frames of the narrow, unstyled popup. Restore the original Qt effect
  preferences when switching back to Sakura.
- Remove the deferred reposition of contained menus. Guard popup presentation
  by generation so closing or reopening immediately cannot reveal a stale pass.
- Keep the approved list shadow, separate option buttons and all menu actions.
- Validation: all 682 regression tests passed, including first-presentation and
  immediate-close/reopen checks. No personal database/media or installer changes.

## Raised menu options and Windows popup transparency — 16 November 2026

- Configure translucent Manga popups as frameless before showing them and turn
  off the native Windows shadow, preventing the opaque black rectangular surround.
- Keep a soft shadow around the complete list and paint each actionable option
  as its own raised button with a fine dark border, spacing and a small shadow.
  Selected options retain the shared recessed treatment and pink accent.
- Apply the option material to standard menus, rich context menus and combo
  lists without adding per-row widgets or replacing existing QAction callbacks.
- Preserve shortcut/check/submenu indicators, disabled actions, keyboard
  navigation and text fit. Compact menu rows reduce their gap to keep labels
  readable when the owning window is short.
- Validation: all 680 regression tests passed, plus focused text-fit and rich
  menu checks. Rendered the eight-action download menu and combo lists with
  isolated data; no personal database/media changes or installer build.

## Clean button edges and shared dropdown depth — 16 November 2026

- Align the small-control shadow mask with the button's corner shape and clip
  inset shading inside the border. Soften the dark rim and bright highlight.
- Keep faces stable on hover to prevent fractional raster resampling artifacts;
  retain animated inset feedback, checked states and physical click compression.
- Give combo controls the same light border and raised shadow as other buttons,
  while leaving native popup painting, input and keyboard navigation intact.
- Add matching rounded borders and reserved shadow margins to standard menus,
  rich context menus, combo lists and boxed tag popovers. Reuse native popup
  painters across reopening and release them with their Qt owner.
- Keep editable combo fields and tool-button arrow areas transparent to avoid
  a second inner border or an extra rectangular face.
- Validation: 677 full-suite tests and three focused dropdown lifecycle/input
  checks passed. Rendered hover controls, menus and tag popovers using temporary
  data. No installer build or personal database/media changes were performed.

## Pressed filters, collection totals and padded move destinations — 16 November 2026

- Keep selected Library filters, checked controls and rail collections visibly
  pressed, rather than only changing their count badge or face color.
- Show live collection totals on the expanded Manga sidebar, including zeroes,
  and synchronize them after edits and update actions without a global refresh.
- Correct Edit season's legacy-folder reuse: Season 01 targets the padded folder
  even when Season 1 already exists. Confirmed moves preserve filenames and update
  database paths; optional cleanup removes only empty old directories.
- Use padded default destinations in download assignment, completed moves and
  Organizer plans. Preserve already-started recovery plans and require refreshed
  Organizer previews after the naming-policy change.
- Apply the reference's card depth, serif headings, inset fields and spacing to
  Downloads and Settings. Keep Browse beside the download folder, make settings
  theme cards responsive, and retain the existing categories and options.
- Validation: all 677 regression tests passed, followed by five final Settings
  checks. Rendered the filters, sidebar totals, transfer cards and Settings panels
  using temporary data; no personal media or database records were modified.

## Season folder naming and separate playback controls — 16 November 2026

- Use a shared `Season 01`, `Season 02` naming policy for new Organizer,
  loose-file import, torrent staging, completed-download and merge destinations.
- Reuse an existing legacy season folder instead of creating another spelling;
  ignore stale or differently numbered database paths during completed moves.
- Remove the playback controls' shared colored background, round each button
  independently, and keep a visible 16-pixel gap between Resume and its arrow.
- Existing personal folders are not automatically renamed or moved.
- Validation: 675 full-suite tests passed, plus final completed-destination and
  Organizer-cache checks. Visually verified the separate playback controls.

## Season reconciliation and staged-file movement — 16 November 2026

- Open Edit season directly as a file selector with season buttons, duplicate-slot
  prevention, explicit episode numbering and reviewed destination-folder choices.
- Reconcile stale paths using strong identity proof; index newly observed physical
  files separately instead of guessing that matching names identify the same file.
- Distinguish the anime root from its season folders, respect real folder numbers,
  and preserve explicit season assignments through metadata refreshes.
- Allow empty shared-folder and no-folder entries to be removed without deleting
  live videos; retain metadata/history and hide empty local source entries.
- Explain unavailable completed-download moves, support explicit destinations and
  refreshing, and expose indexed staging files even after queue records are cleared.
- Verify that new episodes return after Dismiss/Watched and ignore, while Later
  and Not interested remain persistent choices.
- Validation: all 671 regression tests and project checks passed using isolated
  test data. Personal media and database records were not modified by the agent.

## Organizer review presentation — 16 November 2026

- Apply the Manga light master styling to the organization review table instead
  of its hard-coded dark inline styles.
- Show Finished before the organization-result alert. Replace stale, disabled
  Review controls with an explicit Refresh preview action.
- Validation: three focused Organizer UI regressions passed. No personal file
  moves, episode renumbering or folder merging were performed.

## Search memory, remembered matches and physical season editing — 16 November 2026

- Restore each anime's last search text, title choice, provider and season. Cache
  English, Romaji and Japanese title choices for later use.
- Remember alternate titles with their confirmed encoder, source season and
  episode-number mapping; refresh matching results immediately. Recognize earlier
  title-only aliases without rewriting existing records.
- Default continuous numbering to off. Replace the duplicate match controls with
  **Confirm season / episodes**, followed by the existing download review.
- Make Stop idempotent for completed, non-seeding or already detached transfers;
  preserve their Completed status and files.
- Restore **Edit season** for continuous and separate-season libraries. Add reviewed
  episode selection and physical movement into a chosen season folder, updating
  the database while preserving filenames, file identities and watch history.
- Keep partial downloads out of physical moves, reject filename collisions, and
  retain interrupted move plans for explicit retry.
- See [usage and behavior](docs/SEARCH_MEMORY_AND_SEASON_EDITING.md).
- Validation: 651 full-suite tests passed; final search/season-move, release-search,
  confirmed-download, episode-inventory and episode-selection checks also passed.
  All filesystem tests used temporary databases and files.

## Confirmed download assignments — 16 November 2026

- Reuse episode confirmation for source results, pasted magnets and torrent files.
- Preserve original filenames while indexing future downloads with confirmed
  season/episode identities; keep existing records and series numbering unchanged.
- Ask Replace, Skip or Download another copy for owned episodes. Replace retains
  the original until the verified new copy reaches the library, then recycles it.
- Keep manual movement as the default; add opt-in completed movement to an
  approved season destination, including confirmation for new season folders.
- Remove Download Missing Episodes. Auto-Grab now searches the next learned
  source episode and requires user confirmation rather than starting downloads.
- Preserve learned mappings when completed queue entries are cleared.
- Keep future downloads in one selected season while files span staging and the
  library; support Windows short-path aliases and partial moves across drives.
- See [the approved flow](docs/CONFIRMED_DOWNLOAD_FLOW.md).
- Validation: 635 full-suite tests passed, followed by 17 confirmed-download and
  14 move/recovery checks after the final replacement-retry safeguard. Tests used
  temporary databases and media; no installer was generated.

## Watched-root path identity and download-plan review — 16 November 2026

- Treat Windows slash style, case and trailing separators as one watched-folder
  identity. Return the existing root ID rather than adding a second spelling.
- Display legacy aliases once while retaining their saved scan records; root
  removal explicitly removes all aliases for that same logical watched folder.
- Deduplicate filesystem watcher registrations using the same path identity.
- Review the proposed shared download flow against current behaviour and earlier
  decisions; identify numbering, automatic-move, feature-removal and migration
  conflicts. No download-flow redesign was applied by this review.
- See [the review](docs/planning/DOWNLOAD_FLOW_PLAN_REVIEW_2026-11-16.md).
- Validation: 619 regression tests passed, including four path-identity tests;
  publication and whitespace checks passed.

## Download/Organizer state synchronization — 15 November 2026

- Use tracked completion rather than file existence/allocated size for readiness.
- Reconcile Organizer rows after completion/moves and reject stale scan results.
- Coordinate scan commits with file moves; invalidate old scan locations atomically.
- Preserve review/retry for interrupted moves; avoid UI rebuilds on progress ticks.
- Add confirmed red-bin cleanup for empty/missing folder entries, with optional
  non-recursive empty-directory deletion and metadata/history preservation.
- Keep existing exclusion rules unchanged. See [flow and test steps](docs/DOWNLOAD_STATE_SYNC.md).
- Validation: 614 regression checks passed; final focused readiness, move and
  cleanup checks passed. No personal media or database was changed during tests.

## Shared alerts, Organizer and Manga polish — 15 November 2026

- Separate continuous episode identity from per-file destination season; keep
  episode numbers editable, preserve filenames, and reject duplicate assignments.
- Use a shared themed alert dialog with stable hover/press buttons, preserved
  confirmation roles/defaults and existing path-repair details.
- Stop auto-selecting Organizer moves; correct status/action column sizing and
  inset active tabs; allow completed-download review to revalidate cached rows.
- Reuse existing unindexed season folders instead of creating padded-name duplicates.
- Save the main library destination immediately; distinguish nested watched roots,
  shared download staging and selected-transfer folder actions.
- Prevent move previews from treating another torrent job or a custom staging
  folder as the anime's permanent library folder.
- Polish update action hierarchy, discovery cards/popovers, import controls,
  setup/review panels, missing banners and exit choice visibility.
- Keep the Home update strip horizontal and restore cached card material when
  switching theme families.
- See [changes and verification scope](docs/themes/MANGA_POLISH_FOLLOWUPS.md).
- Validation: 601 combined regression checks passed; all 14 relocation/recovery
  checks passed after the final cross-job staging guard. No personal media moved.

## Selected-download confirmation and manual ingest — 15 November 2026

- Apply the Confirm Selected Downloads reference to existing episode matching.
- Use only Search & Auto Ingest from the Transfer Engine mockup for manual
  magnet/torrent entry; retain configuration in Settings and queue in Downloads.
- Keep submission, validation, alias memory and season numbering unchanged.
- Correct clipped native spinbox editors and stop the hidden queue's timer.
- Refresh the remaining-screen inventory; see
  [implementation details](docs/themes/MANGA_DOWNLOAD_CONFIRMATION_UPDATE.md).
- Validation: 582 full-suite checks passed with local socket access. After
  final visual refinements, 24 focused matching/numbering/UI tests passed.

## Twelve additional Manga screens — 15 November 2026

- Apply the supplied light designs to password access/change, app exit,
  episode selection, season numbering, grouping/confirmation, coverage,
  Full Calendar, duplicate review, Settings and saved update changes.
- Preserve Settings options, automatic saving and separate sections. Retain
  existing grouping browsing/duplicate filters; omit declined checksum features.
- Add the approved read-only Inspect selected file action without changing
  duplicate selection, protected originals or Recycle Bin confirmation.
- Reuse master controls and native models/delegates; preserve Sakura styling.
- Details and decisions: [twelve-screen update](docs/themes/MANGA_TWELVE_SCREEN_UPDATE.md).
- Validation: 576 full-suite tests and three additional focused tests passed.
  All twelve workflows were rendered with isolated data; publication and
  whitespace checks passed. No installer or personal database changes.

## Startup control states and flexible Details band — 15 November 2026

- Keep caption buttons out of automatic startup focus and application button
  surfaces. Only pointer hover highlights the window controls.
- Do not animate window-activation focus as button hover; retain Tab feedback.
  Keep busy Refresh raised and mirror Checking/Refreshing labels into the Manga
  header, restoring Refresh when the operation finishes.
- Stretch the Details band: flexible Notes on the left, watch status in the
  middle and rating on the right. Preserve narrow-window wrapping and Sakura's
  original arrangement.
- Verification: 30 focused tests passed across startup/refresh, window chrome,
  tactile interaction, shared Details controls and the Manga Library. Rendered
  the caption and flexible Details band with isolated temporary data.

## Rating, entry form and calendar/Details consistency — 15 November 2026

- Fill rating values cumulatively in yellow; selecting 7 fills 1–7, lowering
  or clearing the value updates all chips. Keep a single saved rating value.
- Give Manga Add Custom Entry the same combo-backed form and controls as Edit;
  synchronize Sakura's existing Add rating pills with the shared value.
- Remove the calendar's accidental nested button/card border. Reserve space
  around each day for its shadow, split weekday/date, and float TODAY across
  the top edge. Show transfer tracks only when real progress is available.
- Restore Details' shared inset personal band, transparent inactive watch
  statuses, flat cumulative rating chips and inset notes. Preserve actions/data.
- Keep native window-caption controls outside the Manga application-button
  policy. Record the reference recheck and remaining differences separately.
- Fix mixed inline/selector QSS that could suppress rating colours. Verify
  actual rendered yellow pixels, not only selection properties.
- Validation: full suite passed 572 tests; the additional high-contrast
  calendar check passed. Visuals were checked against 17 reference folders.
  No installer build or personal database/media changes.

## Manga poster card border — 15 November 2026

- Replace the thick white-only Library poster frame with a 1px black inner
  outline and 3px white outer frame, following the user's recording/instruction.
  Keep rounded corners, cached artwork, hover effects and Sakura unchanged.

## Shared Manga controls across workflows — 15 November 2026

- Apply Library light states to visible and lazily created buttons, tool
  buttons, sorting dropdowns and search fields throughout Manga workflows.
- Reuse cached effects, preserve rail effects and avoid nested effects.
  Sorting dropdowns use the raised master surface consistently.
- Restore prior local styles on Sakura switches; preserve layouts and actions.
- Add tests for lazy controls, reuse, playback, nested effects and restoration.
- Record supplied and missing Manga designs in the
  [screen reference inventory](docs/themes/MANGA_SCREEN_REFERENCE_INVENTORY.md).
- Validation: 567 tests passed; Updates, Details, Edit, Rematch and twelve
  workflow states were rendered with isolated data. Publication and whitespace
  checks passed. No installer or personal database changes.

## Library filter outline — 15 November 2026

- Remove the extra blue inner focus ring from Manga Library filter chips.
  Keyboard focus uses the existing thin pink outer edge; selection, counts and
  tactile effects are unchanged. Sakura keeps its original focus treatment.

## Light hover treatment correction — 15 November 2026

- Remove the dark hover fills from navigation, Refresh, pagination and shared
  controls. Keep light faces and dark text, with a raised-to-inset shadow blend
  on hover and a deeper compression on click, following the user's screenshots.
- Remove the nested hero graphics effect that could suppress the labels/icons
  on Resume, Series Details and Folder. Keep their individual effects/actions.
- Update the shared interaction specification and regression tests to record
  this correction; it supersedes the previous dark-face hover interpretation.

## Manga tactile interaction animations — 15 November 2026

- Add spring hover lift and cached pink glow to primary actions; retain black
  text and add a slightly brighter pink hover face.
- Add shared paint-only lift/press compression to raised controls, filter chips,
  pagination and hero buttons. Disabled Previous stays recessed.
- Add sidebar scale/depress feedback and immediate tooltips while preserving
  the existing navigation blur/reveal. Reuse the calendar preview with a single
  Manga lift instead of stacking position and paint animations.
- Respect reduced motion/high contrast, preserve geometry and click signals,
  and cache the glow alongside existing shadow tiles.
- Validation: 563 tests passed; focused motion/Library/workflow tests and
  rendered resting, hover and pressed states also passed review.
- See [interaction details and validation](docs/themes/MANGA_INTERACTION_MOTION.md).

## Manga master depth and workflow screens — 15 November 2026

- Correct raised/inset shadows for Library pagination, filters, search, sort,
  refresh and sidebar tiles using cached reusable shadow surfaces.
- Extend the shared light material to twelve supplied workflow references;
  reuse the existing five setup steps in one responsive scrolling page.
- Add approved broadcast filters, clipboard sharing, saved filter presets,
  per-release Ignore/Find release/date sorting and cached Storage pagination.
- Keep Sakura themes and existing workflows; omit declined CRC32 and Copy ID
  features. No installer build or personal database migration was performed.
- Full checks: 560 tests passed. See
  [scope, changes and validation](docs/themes/MANGA_WORKFLOW_BATCH.md).

## Navigation discoverability — 15 November 2026

- Keep all inactive navigation and collection controls faintly visible instead
  of transparent. Reduce blur to retain recognizable button outlines; reveal
  controls fully on hover or keyboard focus. Preserve overlay positioning.
- Correct float/integer QVariant animation endpoints so previously blurred
  controls actually return to zero blur on hover or selection.

## Related-season updates and existing-library detection — 15 November 2026

- Fix dismissed season announcements hiding all subsequent episodes: emit
  distinct dated episode events for related releases and check linked season
  identities during online refresh. Keep saved update dispositions intact.
- Preserve pending notices on linked-release lookup failure and retain related
  episode timestamps in the existing calendar cache.
- Show “Already in library” before import for both series and linked seasons;
  prevent duplicate season imports without changing notes or watch status.
- Add regression coverage and [diagnosis/change details](docs/RELEASE_UPDATE_TRACKING_FIX.md).

## Selected navigation depth correction — 14 November 2026

- Anchor expanded rail depth to the selected tab/tag. Keep it clear, reduce
  immediate neighbours to 12% opacity, and hide items at distance two or more.
  Reveal hovered/keyboard-focused controls temporarily; keep every route active.
- Preserve overlay geometry and reduced-motion/high-contrast fallback. Verified
  Library/Updates renders and passed nine focused regressions.
- Analyze raised/inset shadows and hover/pressed states across all five supplied
  references. Record Qt fidelity gaps in the neumorphic reference analysis.

## Manga light workflows and motion — 14 November 2026

- Apply the supplied Updates, Anime Details, Edit Anime Entry and Rematch
  references through shared Manga-only paper surfaces, typography, pink accents,
  input treatments, cached dot patterns and existing actions. Preserve Sakura.
- Reproduce the expanding rail animation from the Updates HTML. Replace uniform
  inactive-item blur with a distance falloff: hovered/focused item sharp, adjacent
  items slightly softened, farther items progressively softer. Reset on leaving;
  reduced motion/high contrast apply instantly without blur.
- Keep expansion above the page in an overlay, with a fixed 94 px layout slot;
  hovering the rail never pushes or resizes the Library or other page content.
- Replace black collection tiles with white controls and reveal existing Watching,
  Plan to watch, Watched, Dropped and Watched/removed filters when the rail expands.
- Fit seven Library titles per page on wide viewports and six on smaller ones,
  preserving the visible position when the page size changes. Reuse at most seven
  Manga grid card slots rather than creating the whole collection.
- Arrange Manga Edit Entry as a poster column and complete details form. Link its
  status/rating buttons to the existing fields, including the no-rating choice.
  Keep all save, folder, image, multi-release rematch and update disposition actions.
- Correct clipped update-action labels and the Manga play button hover colors.
- No EXE/installer build is part of this source UI update. Build only on request.

## Manga Brutalism Light — main Library screen

- Register the supplied main-screen image as the light master, retain original
  assets and save a checksum-verified v1 reference copy. Keep Sakura selectable.
- Add a separate saved Manga Brutalism Light selection with shared paper/ink/pink
  tokens, offline Inter/Noto Serif fonts, icon rail, search/action header, light
  hero, framed posters and real status footer. Preserve existing routes/actions.
- Implement the approved six-title numbered pagination using six reusable poster
  slots, and Full Calendar using cached broadcasts, month navigation and existing
  hover/detail actions. No extra provider requests run when Calendar opens.
- Preserve existing search, collection filters, updates strip, refresh modes,
  selection, grid/list, playback and native window controls. Exclude profile,
  fabricated metadata and the retired qBittorrent client from the mockup.
- Add focused regressions for selection persistence, theme isolation, card reuse,
  search reset, cached calendar ownership/month navigation and larger text layout.
- Details, Edit Entry, Rematch and Updates remain subsequent screen-specific
  passes. See the [master contract](docs/themes/MANGA_LIGHT_MASTER.md).

## UI working guidelines — 14 November 2026

- Establish the user-approved main Library screen as the master design reference
  for both light and dark modes. Require explicit approval for conflicting later
  mockups, while respecting changes already directly requested by the user.
- Specify reusable shared components/tokens, theme-family preservation,
  feature retention, reference versioning and rendered visual verification.
- Add the [UI Design Guidelines](docs/themes/UI_DESIGN_GUIDELINES.md); no screen
  redesign or runtime behavior changes are included in this documentation update.

## Preserved Sakura theme family — 14 November 2026

- Name the current designs Sakura Dark and Sakura Light, with a Sakura Match
  Windows option. Preserve saved `dark`, `light`, and `system` preference IDs.
- Identify the existing runtime visual family as Sakura without changing its
  colors, layouts or features. Preserve the full source baseline with the tag
  `sakura-ui-baseline-2026-11-14` before adding the new Neo Manga design separately.
- See the [Sakura preservation contract](docs/themes/SAKURA_BASELINE.md).
- Isolate production hard-exit calls in the temporary audit smoke fixture so
  timing cannot bypass its completion marker and cleanup; runtime behavior stays unchanged.

## Pre-redesign source baseline — 14 November 2026

- Publish the current source, regression tests, packaging scripts and organized
  design/documentation references before starting the next UI redesign.
- Include the recent immediate update-choice propagation fix, completed/seeding
  presentation, PotPlayer integration, transfer-limit controls, window-state
  persistence, cached release discovery, profile backups and installer work below.
- Record the previously added adult-content password/recovery controls and
  multi-site Chrome extension (1.2.0), alongside the 1.0.1 application source.
- Preserve existing features and the original v1.0.0 tag. This source baseline
  is not a new installer or a claim that the open audit findings are resolved.
- Next phase: apply the user's incoming UI screens one at a time after receiving
  the new guidelines. No new redesign has been implemented in this checkpoint.
- Validation reused from the unchanged code: 539 completed Python tests and
  compilation; Chrome extension and publication hygiene checks verified separately.
- See the [baseline and remaining risks](docs/maintenance/PRE_UI_REDESIGN_BASELINE.md).

## Unreleased — Immediate update choices on both screens

- Apply Later, Not interested, Mute, Watched and ignore, Dismiss and Restore to
  the cached Library index/release strip and Updates categories after saving.
- Reconcile empty lists immediately, retain unaffected cards, and avoid full
  Library/hero/calendar refreshes for notification choices.
- Protect committed choices against older in-flight refresh snapshots; preserve
  grouped-series update aggregation and failure recovery.
- Add four focused regressions. See the [propagation fix report](docs/maintenance/UPDATE_CHOICE_PROPAGATION_FIX.md).
- Validation: all 539 Python tests and compilation checks passed; focused
  temporary-data propagation measured 78.8 ms maximum across suppressing choices.

## Workspace maintenance and source review — 14 November 2026

- Consolidate supplied UI references under `design/references`, local previews
  under `design/previews`, and implementation reports under `docs/history`.
  Retain guides/planning notes separately and repair local Markdown links.
- Preserve runtime locations, personal database/media and existing installers;
  update the build's moved master-icon reference. Record 165 file move checksums.
- Fix exit-test watchdog leakage and require a regression-suite completion record
  so premature process termination with exit code 0 cannot falsely pass validation.
- Review the new adult-content password/recovery lock and multi-site Chrome
  capture changes, which were absent from the latest release notes. These remain
  source-reviewed additions with unresolved findings, not newly approved features.
- Document shutdown, installer termination, PotPlayer ABI, visibility-policy and
  credential-update risks in the [current review](docs/maintenance/CODEBASE_REVIEW_2026-11-14.md).
- Verification completed: 535 Python tests, compilation checks and 18 Chrome
  extension tests passed with the new full-suite completion guard.

## Version 1.0.1 — Downloads queue colors, PotPlayer playback tracking and upgraded installer

- Fixed downloads queue progress calculation for completed and restored torrents:
  clamped completed and seeding jobs to 100% progress and total / total bytes,
  eliminating stale partial progress counters from restored database snapshots.
- Updated download status colors: completed downloads now display in blue (`#6cb6ff`),
  seeding torrents display in orange (`#ff922b`), and active transfers display in coral.
  Selected row borders match the status tint.
- Added native Windows IPC playback tracking for PotPlayer via SendMessageTimeoutW
  (`POT_GET_TOTAL_TIME`, `POT_GET_CURRENT_TIME`, `POT_GET_PLAY_STATUS`). Anime Vault
  now tracks seconds watched, seconds remaining, and playback progress for PotPlayer.
- Added `/seek=` command-line argument for PotPlayer resuming and updated Settings
  player auto-detection to discover PotPlayer alongside VLC, MPV and MPC-HC.
- Bundled the multi-resolution master app icon from `Anime Valt Installer Pkg` into
  `assets/app.ico` for the executable, desktop shortcut, window chrome and system tray.
- Built versioned standalone installer `AnimeVault-Setup-1.0.1-windows-x64.exe` with
  matching `AppId={{BB4AB6A4-91CC-4BBF-B367-BC22D14E8C37}}` for seamless in-place
  upgrade over version 1.0.0 while preserving previous installer and user data.
- Fixed clean process shutdown on Exit / Close: eliminated background zombie processes
  caused by indefinite thread wait loops. Added a 2.5s exit watchdog, instant window/tray
  hiding, torrent host process kill on exit, and immediate kernel-level teardown via `os._exit()`.
- Resolved installer upgrade error (`DeleteFile failed; code 5. Access is denied.`):
  updated Inno Setup with `CloseApplications=yes`, automated process cleanup in `PrepareToInstall`,
  and `restartreplace` flags to cleanly replace files when updating over an installed version.
- Added comprehensive regression tests in `test_playback_potplayer.py` and `test_exit_completely.py`;
  all 526 Python tests pass.


## Unreleased — Download controls, release discovery and portable backups

- Apply saved transfer limits to the running built-in engine immediately; share
  readable 512 KB/s presets and exact custom values across both settings views.
- Remember normal window geometry and maximized state, including tray-close paths.
- Restyle the Chrome popup without changing permissions or capture logic, and
  include an offline privacy page and application privacy documentation.
- Rename discovery refresh to Check new animes; fetch uncached pagination/filter
  results automatically while reusing cached pages. Keep every card scrollable.
- Enforce the mature-content setting immediately; hide adult controls/Hentai when
  disabled and offer adult-only discovery only when enabled.
- Add selected-release artwork, alternate titles, plot, genres and premiere/status;
  verify identity and label related releases separately. Reuse cached artwork.
- Add ZIP profile backups with native resume metadata and optional image caches;
  validate restores and retain rollback backups. Exclude videos and code.
- Add nine regression tests; all 519 Python checks and 18 extension checks pass.

See [the complete change report](docs/history/DOWNLOAD_DISCOVERY_BACKUP_FIXES.md).

## Unreleased — Standalone Windows setup and installed-profile isolation

- Build a one-folder standalone application inside an Inno Setup installer for
  C:\Program Files\Anime Vault; include Python/Qt, fonts, extension files and native dependencies.
- Keep installed state in %LOCALAPPDATA%\AnimeVault while preserving the source
  checkout's data directory. Do not ship, migrate or delete any personal database.
- Package libtorrent in a separate Qt-free helper to avoid the GUI runtime-hook
  native crash; keep hidden pipe-based worker startup and recover windowed Chrome pipes.
- Add an installed-app mutex, leave post-install launch unchecked, and preserve
  user data on uninstall/update. Add backup/restore and standalone verification guides.
- Verify real packaged navigation, Details, isolated SQLite backup/restore,
  native helper and Chrome pipe handling without installing the app on the user's PC.

## Unreleased — Public repository documentation and source snapshot

- Declare HTTPX2 in a separate development requirements file and install it in
  CI, correcting fresh-runner API tests that previously depended on an undeclared
  local test-client package. Runtime dependencies and application behavior stay unchanged.

- Rewrite the README around verified features, source installation, current
  built-in downloads, privacy, validation and explicitly open audit findings.
- Add six current-app screenshots generated from fictional, isolated demo data;
  publish their reproducible capture script and original placeholder artwork.
- Add a documentation index, current download guide, discoverability notes,
  repository topics, security-reporting guidance and a redaction-aware bug template.
- Preserve the v1.0.0 baseline and retained design/implementation history. No
  finished installer or resolution of the open whole-app audit is claimed.
- Pre-publication validation: 502 Python tests and 18 Chrome-extension tests pass.

## Unreleased — Update details, correct episode timing and refresh progress

- Add Open details beside Refresh data, retaining the selected series identity
  and Back navigation to its update review.
- Separate the latest timestamp-confirmed aired episode from the next scheduled
  episode. Correct cached next-only labels without guessing episode numbers or
  treating upcoming episodes as available downloads; preserve dismissal rules.
- Add a themed bottom-edge progress bar for local refresh, internet sync, metadata
  updates and per-anime refresh, including overlapping jobs and failure cleanup.
- Validation: all 502 isolated tests and compilation passed; the complete update
  view and bottom-edge progress placement were rendered and visually checked.
- See UPDATE_DETAILS_EPISODE_TIMING_AND_PROGRESS.md for cause, changes and tests.

## Unreleased — Reference menus and refreshable update review

- Style the navigator and anime context menus with rounded panels, SVG icons,
  active rows and actual metadata. Preserve existing navigator/selection actions
  and route context commands through existing Details and confirmation flows.
- Read current saved changes asynchronously when opening View changes, fixing
  stale/empty results while the Updates root is awaiting its refresh.
- Add scoped Refresh data with progress, clear empty/error states, cached-data
  retention and safe cancellation. Internet checks remain explicit.
- Keep context-menu selection attached to its original anime ID and dispose
  closed menus. See VAULT_MENUS_AND_UPDATE_REVIEW.md for details and validation.
- Validation: compilation and all 495 isolated tests passed; both menus and the
  populated change viewer were rendered and visually inspected.

## Unreleased — Preserve full anime context in breadcrumbs

- Build nested breadcrumbs from the retained parent-page history: Library /
  Anime / Choose episode, including deeper download/edit/rematch/group routes.
- Retain that path across tab switches; shorten it on Back and reset it when
  returning to the main Library. Refresh child breadcrumbs after async title loads.
- Show the shared navigation header in drawers and avoid repeating the anime
  title in the API JSON viewer's final breadcrumb segment.
- Validation: all 487 isolated tests and compilation passed; long-title episode
  and entry-edit navigation were rendered and visually checked.
- See BREADCRUMB_NAVIGATION_HISTORY.md for the full behavior and file changes.

## Unreleased — Maximize, roomier header and Library status placement

- Fill the Windows work area on maximize by compensating for the native resize
  border; keep the taskbar visible and preserve F11 fullscreen/restore behavior.
- Hide the old footer and reuse its live connectivity/index labels beneath All
  anime. Remove duplicate disk-size text from the Library summary; keep disk
  information in the header and Storage. The streaming service is unchanged.
- Widen centered navigation tabs and Quick Find; use a centered three-line menu
  icon without an extra dropdown arrow. Preserve menu actions and count badges.
- Validation: all 481 isolated tests and compilation passed; native Windows
  maximize/F11 sizing and a full-window temporary-database render were checked.
- See WINDOW_AND_LIBRARY_STATUS_LAYOUT.md for measurements and validation.

## Unreleased — Update review routing and aligned breadcrumbs

- Library new-update posters and update-card bodies open View changes; Back
  returns to Updates. Keep ordinary Library details and download/health actions.
- Share one vector-arrow Back/breadcrumb row across full-page workflows; update
  asynchronously loaded anime titles without adding a second breadcrumb row.
- Align the three Updates header actions in one row with AniList status beneath
  the title; align Organizer actions right without squeezing the heading.
- Match release-news colors to the Library palette and move Check updates to
  the title row. Theme the existing change viewer with the same shared tokens.
- Validation: compilation and all 478 isolated tests passed; rendered navigation
  and page headers were visually checked at 1280×720 and 1100×680.
- See NAVIGATION_MEMORY_AND_COMPACT_HEADINGS.md for details and validation.

## Unreleased — Navigation memory and compact page headings

- Retain each tab's open workflow and view state across tab switches; preserve
  explicit Back/Close disposal and direct Library search/collection navigation.
- Use compact, consistent page headings; remove redundant system-label eyebrows.
  Place the two Updates navigation buttons beside the title, below Refresh metadata.
- Repair Downloads → More → Open download folder with current-location fallback,
  a configured-folder target without a selected transfer, and visible errors.
- Validation: compilation and all 471 isolated tests passed; four compact page
  renders were visually inspected at 1100×680.
- See NAVIGATION_MEMORY_AND_COMPACT_HEADINGS.md for behavior and validation.

## Unreleased — Remove redundant Details styling work

- Build Details with its existing final theme; remove temporary per-control
  styles and avoid resetting empty child styles or reassigning identical QSS.
- Preserve controls, data handling, plain-text safeguards and navigation. Add a
  24-season regression for style churn, ratings, notes and horizontal fit.
- Copied-data measurements: the 24-release case decreased from about 2.0 seconds
  to 1.0 second; smaller cases loaded in about 0.2–0.4 seconds. These are fixture
  results. See DETAILS_LOADING_AUDIT.md for validation and limits.
- Validation: compilation and all 467 isolated tests passed; before/after Details
  renders and four copied-data cases were checked.

## Unreleased — Preserve Qt callback behavior while profiling

- Preserve real callable argument signatures in the audit wrapper; Search
  releases and other zero-argument handlers correctly discard extra Qt signal
  arguments again when profiling is enabled.
- Verify six signal categories, the actual search-button worker path and 207
  wrapped callable signatures. See AUDIT_CALLBACK_SIGNATURE_FIX.md.
- Validation: compilation and all 466 isolated tests passed.

## Unreleased — Focused thumbnail deadlock repair

- Replace worker-side Qt smooth image scaling with bounded Pillow resizing and
  owning QImage pixels; preserve poster/banner bounds and decoded cache keys.
- Isolate grid/list Python thumbnail readers in a dedicated two-worker pool,
  separate from Qt's native global rendering pool.
- Add image/pixel/cache safety checks and a process-isolated concurrent-scroll
  regression. See THUMBNAIL_DEADLOCK_FIX.md for captured GIL/native-wait evidence.
- Validation: compilation and all 464 isolated tests passed; copied-artwork cold
  and warm scrolling completed with profiling off and on.

## Unreleased — Keep header actions inside the app

- Anchor the top-right actions menu to the button's right edge and clamp its
  position to the app's visible client area with an 8px inset.
- Reduce excess row padding in short windows so the final actions remain visible.
  All existing actions and keyboard navigation are retained.
- Validate right-edge placement, short-window sizing, reopening after resizing,
  and keyboard access to the final action. All 13 targeted menu tests passed.

## Unreleased — Complete dropdown text and first-load release details

- Expand shared combo popups to the actual option text width, keep them onscreen,
  and wrap exceptionally long labels. Short menus no longer need extra scrolling.
- Fetch a selected anime's uncached Release Details automatically, then reuse the
  saved timeline. Keep manual refresh and discovery's cache-only behavior.
- Add popup sizing/wrapping and automatic selected-ID loading regressions.
  Full isolated validation passed compilation and all 453 tests.
  See DROPDOWN_TEXT_AND_RELEASE_DETAILS_FIX.md.

## Unreleased — Search focus and readable release filters

- Add default-on Focus search results automatically in Appearance & Accessibility.
  Explicit searches reveal results; live typing and hidden pages retain focus.
- Replace New Anime Releases genre/theme/format dropdowns with boxed multi-select
  popovers and selection counts; sorting uses readable single-choice boxes.
- Omit unused optional AniList filters: format:null caused empty Last 30 Days
  results. Live corrected Last 30 Days and Announced checks each returned 20.
- Keep Announced, adult safeguards and persistent/manual-refresh cache behavior.
  Full isolated validation passed compilation and 448 tests.
  Details and validation: SEARCH_FOCUS_AND_RELEASE_FILTERS.md.

## Unreleased — Unified menus and bounded Library rendering

- Route Choose Episode's download finder to Find Download Files for the same anime.
- Apply the new dropdown/popover reference to existing combo menus, context menus
  and calendar hover rows, retaining their actions and keyboard behavior.
- Use bounded reusable poster slots and delegate-painted list rows for Library
  collections above 64 entries; preserve card visuals, selection and click targets.
- Decode visible Library artwork in workers and reuse unchanged new-release cards.
- A 1,000-record fixture used 25 poster slots; 56 targeted regressions passed.
  Full isolated validation also passed compilation and 440 tests.
  See UNIFIED_MENUS_AND_LIBRARY_PERFORMANCE.md for measurements and limitations.

## Unreleased — Simplified Find Download Files UI

- Apply the new search reference: consolidated setup panel, coverage before
  results, balanced table columns and a fixed bottom action area.
- Preserve saved custom searches, alternate-title fallback, match confirmation,
  availability, browser/manual source actions and reviewed download submission.
- Retain virtualized results and full text tooltips; wrap action buttons at
  smaller sizes and display the confirmation label's ampersand correctly.
- 21 search/numbering/query regressions passed; inspected 1450×1000 and 1100×720
  renders. See FIND_DOWNLOAD_SIMPLIFIED_UI.md for scope and validation.

## Unreleased — Season numbering and episode selection reference UI

- Apply the new centered Edit season numbers design with release cards, folder
  fields, SVG number steppers, review checkbox and fixed save footer.
- Apply the new full-page Choose episode layout and rounded episode blocks,
  preserving virtualized inventory, release filters, playback and cancellation.
- Add only the approved playback footer, using the selected file and existing
  configured-player/history handler. Other mockup-only additions are omitted.
- 39 targeted tests passed; both screens were rendered and visually inspected.
  See EPISODE_SELECTION_REFERENCE_UI.md for full scope and validation.

## Unreleased — Persistent release results and thumbnails

- Open New anime releases and release timelines from saved SQLite results only;
  Check updates is the explicit online refresh. Filter/page caches persist across
  restarts and date changes, with migration from compatible older cache keys.
- Retain and display previous results after a failed refresh. Show the real last
  checked time, and explain when no results have ever been saved for a query.
- Read release thumbnails from the provider/version disk cache on reopen. Fetch
  missing thumbnails only after an explicit successful update, retaining existing
  artwork deduplication, validation and retry safeguards.
- Validation: 32 targeted tests passed, including stale/day-change cache reuse,
  timeout fallback, cache migration and thumbnail disk reads without re-downloads.
  A further 19 API/audit and transfer-screen regressions passed.

## Unreleased — Release discovery cards and filters

- Give New anime releases equal-width responsive columns regardless of title
  length. Reflow after viewport resizing and reserve space for wrapped titles
  and actions so they cannot overlap posters.
- Add genre, theme (including Isekai), format and Most popular controls. Filters
  apply in the AniList query before pagination; filter combinations have separate
  cache keys. Existing premiere/title sorts, release periods and actions remain.
- Initialize Include adult (18+) from the existing Allow mature setting. When
  that setting is off, the checkbox is unchecked/disabled and the query excludes
  adult entries. A response-side guard also excludes adult cached results.
- Validation: 11 release-news/additions tests passed. Offscreen layout checks at
  1100, 1500 and 1900 pixels verify equal widths and poster/title separation;
  inspected a rendered 1900-pixel page. API responses were mocked for these tests.

## Unreleased — On-disk Details loading repair

- Replace the incomplete three-table Details copy with a complete read-only WAL
  transaction. Physical-file, location, episode and history queries now use the
  same consistent database view while Details builds incrementally.
- Keep preparation off the UI thread, avoid a whole-database copy, and close the
  read view after loading or cancellation. No library reset or media changes.
- Add regression coverage for on-disk asynchronous loading, physical-file and
  history access, resume paths, read-only enforcement and concurrent saves.
- Validation: 43 targeted tests passed across Details loading/presentation,
  navigation and file-operation/data-safety tests, using temporary databases.

## Unreleased — Five screens and audit fixes

- Apply Rematch, Broadcast, Group seasons/arcs, Coverage and New releases references.
- Add approved exact-episode Auto-Grab, local reminders, broadcast filters,
  coverage JSON export and discovery sorting/announced filters.
- Coalesce background user edits, reduce detail snapshots, cache refresh artwork
  and prepared storage data, debounce Organizer filtering and retain stable queue models.
- Enforce API token/origin/path rules, whitelist SQL identifiers, escape UI/CSV
  metadata and bound HTTPS artwork responses.
- Align Storage's shell and fix a stale Downloads badge callback after window disposal.
- See FIVE_UI_SCREENS_IMPLEMENTATION.md and AUDIT_FIXES_APPLIED.md for validation
  and explicitly outstanding architecture/security work.

## Unreleased — Add Entry & TXT Importer Twilight Sakura UI

### Added
- Scoped Twilight Sakura style and modal chrome module
  `app/ui/entry_import_style.py` (`palette`, `dialog_qss`, `build_twilight_chrome`,
  `TwilightComboBox`, `TwilightCheckBox`, `StatusDot`, `poster_thumbnail`,
  `apply_input_palettes`, `refresh_chrome_scale`, `center_modal_show`) supporting
  dark, light, high-contrast palettes and dynamic text scaling.
- Centered wide modal layouts (`centered_workflow = True`, `workflow_width = 900`
  on `CustomEntryDialog`; `workflow_width = 980` on `WatchedImportDialog`) matching
  the approved Twilight Sakura reference screens while keeping embedded navigation.
- Two-column top layout in `CustomEntryDialog` (left 2:3 dashed `Poster artwork`
  preview with action buttons; right `Title information and details` card with
  2x2 title grid and comma-separated `Genres` hint), live rating descriptor readout
  beside the 1–10 pill bar (`Add custom entry`), `"Automatic sync policy"` banner
  framing, and Japanese subtitle badge `日本語タイトル`.
- `Ctrl + I` header shortcut badge, three-column configuration bar (replacing the
  plain checkbox on `rematch_existing` with `SettingsSwitch` in Twilight Sakura
  mode), 4-column horizontal KPI metric cards with colored status dots, file strip
  with real file size readout, tonal status pills, and inline `Choose match` /
  `Add custom` row actions in `WatchedImportDialog`.
- Regression suite `tests/test_entry_import_sakura_ui.py` and implementation note
  `ENTRY_IMPORT_SAKURA_UI.md`.

### Removed / Replaced
- Replaced the legacy 560px right-hand `workflow_drawer` chrome (`workflow.chrome()`,
  `workflow.card()`, `workflow.field()`, `workflow.button()`, and legacy
  `workflow_edit_panel` split layout) in `CustomEntryDialog` and `WatchedImportDialog`
  with the Twilight Sakura modal chrome and scoped QSS (`#custom_entry_dialog`,
  `#watched_import_dialog`).
- Replaced the stacked 2x2 KPI tile grid and plain `QCheckBox` for `rematch_existing`
  in `WatchedImportDialog` with the 1x4 Twilight Sakura KPI row and `SettingsSwitch`.
- Replaced raw QSS checkbox/combobox arrow styling inside both dialogs with custom
  painted `TwilightCheckBox` checkmarks and `TwilightComboBox` vector chevrons.
- Intentionally omitted unapproved mockup-only additions (`"On Hold"` status option,
  `"Supports Markdown"` claim, fabricated database version badge, `"Select all"`
  master toggle, `"Filter imported list..."` search box, and poster click/drop).
  All existing features (`Edit anime entry` mode with `rating_combo`, `English title`
  field, `Duplicate lines` filter, FFmpeg frame grabber, cover picker, `Add custom`
  row action, and manual match review) remain intact.

## Unreleased — New anime releases AniList query & error diagnostics fix

- Fix `release_news.discover()` declaring `$from`/`$to` as `Int` instead of
  `FuzzyDateInt`, which caused AniList to reject live New anime releases checks
  with HTTP 400.
- Fix lower-bound date arithmetic in `discover()` to use `lower - timedelta(days=1)`
  instead of integer `- 1` across month boundaries.
- Record concise per-thread error reasons in `anilist_client.last_error()`
  (HTTP 400/GraphQL errors, HTTP 429, timeouts, network errors, Offline Mode) and
  surface them in `release_news.cached()` / `ReleaseNewsPage` while retaining cache.
- Guard malformed cached entries and nullable nested fields in `ReleaseNewsPage.render()`.
- Add inline issue/fix comments and regression coverage in `tests/test_release_news.py`;
  document changes in `RELEASE_NEWS.md`.

## Unreleased — List, grouping confirmation and duplicate-review references

- Apply the three new UI references while preserving current behavior and safeguards.
- Restyle Library list rows, centered grouping confirmation and duplicate summary/tree.
- Retain opt-in selection, saved scans, Stop, protected copies and Recycle Bin review.
- See THREE_REFERENCE_SCREENS.md for files changed and validation.

## Unreleased — Details, Organizer and Home fixes

- Fix watch-status cursors, Organizer cell clipping/alignment and optional synopsis scrolling.
- Add saved duplicate-review/drive-check dropdown, retained scan backups and location revalidation.
- Make duplicate scan Stop responsive before file checking begins.
- Hide Home promotions during search; add configurable new-release section placement.
- Fill missing grouped-card details from verified matched members, fixing Fairy Tail presentation.
- Full implementation notes: DETAIL_ORGANIZER_HOME_FIXES.md.

## Unreleased — Release discovery and anime timelines

- Add Details → Check release updates and Updates → New anime releases.
- Display premiere dates, related seasons, and aired/scheduled episode times.
- Add paginated recent/upcoming discovery, cached checks and import as Watching.
- Preserve existing entries on repeat imports. See RELEASE_NEWS.md.

## Unreleased — Incremental Update choices and explicit library removal

- Save Update choices in the background and patch only affected cards and counts;
  do not trigger a global refresh. Refresh Library/Storage lazily when opened.
- Position compact, equally spaced actions at the bottom-right on the card's
  background. Wrap on narrow windows rather than clipping labels or scrolling.
- Add Remove anime to Updates and Details, with keep-files or reviewed Recycle
  Bin choices. Preserve history records and exclude removed folders from scans.
- Document implementation and validation in UPDATE_ACTIONS_AND_REMOVAL.md.

## Unreleased — Settings UI Screen by category

- Apply the new setting ui screen reference to matching pages, with grouped
  sidebar, compact panels, download engine card and paired form rows.
- Give Naming and Metadata their own pages while retaining original category
  indices and every existing setting, callback and save behavior.
- Keep categories separate; omit unsupported mockup-only save/filter controls.
- Document validation and file changes in SETTINGS_UI_SCREEN.md.

## Unreleased — Three complete release-popup rows

- Keep popup-specific row sizing through theme-scope changes; show up to three
  complete releases and scroll additional entries. Retain hover, click navigation,
  posters, title tooltips and screen-bounded placement.
- Verify 25 focused tests, including five releases at 100% and 130% text scale.

## Unreleased — Horizontal Updates actions

- Correct Updates actions to one horizontal row with equal button widths and
  equal spacing. Narrow windows can scroll the row without truncating labels.

## Unreleased — Release dates and unified buttons

- Show cached release month/year in Updates, distinguishing expected releases,
  airing starts and unknown dates without changing dismissal identities.
- Put all Updates actions in one vertical, equal-width column with full labels.
- Introduce shared button size/state rules from the supplied component template,
  and turn Organizer roots/Merge source paths into explicit Open folder buttons.
- Verify 52 focused tests and a rendered Updates preview. See UNIFIED_BUTTONS_AND_RELEASE_DATES.md.

## Unreleased — Download organization, responsive actions and player settings

- Exclude torrent staging from generic organization; list verified completed jobs
  by linked anime and route Review to safe anime/season relocation previews.
- Stabilize Downloads counts and avoid redundant header/style/model work on tab
  switches. Fix release popup height and expose equally sized Updates actions.
- Add PotPlayer detection/launch selection and background disk-cached player icons.
- Group Settings actions into compact wrapping rows and enlarge download labels.
- Document 53 focused tests and validation limits in DOWNLOAD_ORGANIZER_AND_UI_POLISH.md.

## Unreleased — Merge and Duplicate Review references

- Apply both supplied Merge and Duplicate Review designs while preserving
  existing previews, confirmation, stop and Recycle Bin safeguards.
- Move duplicate review into its own Organizer tab; remove its season/folder
  button. Keep scans manual and include embedded workers in task/close tracking.
- Omit hash/encryption wording and unsupported reference-only features.
- Validate 19 focused tests and inspect rendered previews. See MERGE_DUPLICATE_REFERENCE_UI.md.

## Unreleased — Organizer reference presentation

- Apply organizer screen design with rules/roots above full-width preview,
  grouped actions and Twilight Sakura styling. Retain Merge library, manual scans,
  saved previews and every existing organization/review control.
- Connect Review duplicate files to the existing workflow; omit hash/encryption
  wording and unsupported mockup-only operations. Document in ORGANIZER_REFERENCE_UI.md.

## Unreleased — Separate settings category pages

- Replace scrolling section jumps with instant category switches. Each Settings
  category displays only its own existing controls, retaining individual overflow
  scrolling and its position. Keep sidebar styling and existing category links.

## Unreleased — Reference Settings and local anime selection

- Apply Sertting UI reference with section navigation, continuous settings
  document, Twilight Sakura panels, theme previews and connected player cards.
- Preserve all existing controls, saving behavior and category navigation adapters;
  skip unsupported reference-only features. Share the top capsule on Settings.
- Move anime selection into All anime, synchronize context-menu/batch selection,
  and remove selection from the visible global actions menu.
- Validate 21 focused tests and inspect wide/compact renders. See SETTINGS_REFERENCE_UI.md.

## Unreleased — Checked-file confirmation and simpler episode mapping

- Confirm checked releases together, without requiring a separately highlighted
  title. Highlighted-row confirmation remains available when nothing is checked.
- Replace first/last and encoder-title form fields with one episode field per
  selected file plus shared type/season. Accept single episodes, comma lists and
  ranges; reject invalid input and duplicate assignments before applying changes.
- Keep optional alias remembering and separate reviewed download submission.
- Validate 22 focused tests and inspect a two-file confirmation render.

## Unreleased — Start confirmed downloads directly

- Remove the Choose files before starting setting and ignore its saved legacy
  value. Confirmed torrents start automatically after metadata arrives.
- Resume upgrades old selection-gated paused entries in place, retaining torrent
  identity, destination and any explicit file subset. Retry follows the same rule.
- Keep Choose files as an optional action; remove misleading start instructions.
- Verify 35 focused tests, including direct start and resuming an old paused job.

## Unreleased — Confirm download aliases and episodes

- Add Confirm anime & episodes while retaining Confirm highlighted match; both
  open a simple centered confirmation instead of a sliding drawer.
- Show the target anime and release name; require explicit approval of release
  type, season and first/last episode before attaching coverage.
- Optionally remember an encoder's alternate title per series/season in the
  existing state store. Future searches recognize that exact normalized title,
  while retaining season conflicts, special mapping and aired-boundary checks.
- Validate 20 focused tests, including episode-range confirmation, alias scope,
  future/conflicting numbering and nested navigation.

## Unreleased — Saved custom release searches

- Add Use Custom One beside Use title in Find Download Files. Save the exact
  current query per series/season and reuse it on reopening, without adding
  uploader, quality or season tokens a second time.
- Keep custom searches in title mapping; choosing a normal title switches the
  saved default back while retaining the custom option. Reject empty saves.
- Cover reopening, switching back and anime/season isolation in UI regressions.

## Unreleased — Find Download Files reference UI

- Apply the supplied file download page design using grouped search controls,
  Twilight Sakura styling, painted release rows/status pills, episode availability
  cards and a wrapping action panel with selected-release count.
- Preserve existing source search, language/season choices, filters, sorting,
  match confirmation, coverage, manual torrent entry and reviewed submission.
- Skip unsupported mockup features; retain the built-in libtorrent engine.
- Verify 18 focused tests and inspect wide/compact renders. See FIND_DOWNLOAD_SCREEN.md.

## Unreleased — Download retry and completed-library moves

- Reuse existing native queue IDs, partial files and selections when retrying;
  clear native errors before rechecking. Convert legacy external records in place.
- Bind row menus to their original transfer so queue refreshes cannot redirect
  Remove/Retry/Choose files. Remove keeps files and cancels tracking.
- Default new transfers to isolated staging under the main library while retaining
  explicit custom destinations and existing job paths.
- Add Move completed to library with a source/destination preview, no-overwrite
  checks, per-file journal, verified cross-volume copy, interruption/retry and
  stable identity/history/path updates. Preserve filenames and unknown files.
- Document behavior and 66 focused regressions in DOWNLOAD_RETRY_AND_LIBRARY_MOVES.md.

## Unreleased — Larger animated navigation

- Increase capsule navigation text to 14px, horizontal padding to 16px and click
  targets to 44px; preserve centered positioning and responsive wrapping.
- Add a 180ms hover lift/color animation painted at device resolution, with no
  layout movement or graphics effects.
- Render the Updates count in a rounded rectangle that grows for larger numbers
  and hides when the count is zero. Counts and all navigation routes are unchanged.
- Cache Reduce motion state when applying/following appearance settings so hover
  events do not read the database. Reduced motion skips the animation.
- Validate with 20 focused navigation/Home tests and dark/light visual captures.

## Unreleased — Updates and Downloads screens

- Apply the supplied Twilight Sakura references to both destinations and share
  the centered capsule navigation with Home, excluding the profile/avatar.
- Paint virtual transfer cards, retain all existing per-job actions and settings,
  and add the approved Pause all / file-preserving Clear completed operations.
- Add Updates sorting and batch dispositions, keeping per-anime restore behavior,
  existing health checks and all individual actions. Move health calculation to
  a cached worker with stale-result protection.
- Preserve libtorrent; do not add the reference's Aria2 engine, automatic repair,
  detailed media-diff tracking or dismissal rules.
- Add eight regressions and document navigation, approval, safety and verification
  in UPDATE_DOWNLOAD_SCREENS.md.

## Unreleased — Details screen and startup flicker

- Prevent one temporary native window per poster by parenting metadata labels
  before showing them.
- Apply the Anime Detail Screen reference's Twilight Sakura presentation, with
  responsive controls, high-DPI artwork and a full-width season table.
- Preserve auxiliary actions under More and retain the existing episode grid.
- Add the approved virtual episode list, local frame cache, verified-release
  descriptions and stable-history playback dates. Keep preview IO bounded,
  cancellable, lazy and cached; exclude profile, new encoding/audio filters,
  RSS catch-up and physical-disc registration.
- Document implementation, navigation, checks and limitations in
  DETAIL_SCREEN_REDESIGN.md; add nine focused regression checks.

## Unreleased — Twilight Sakura Home Library

- Apply the Home Library Screen design to Home with capsule navigation, bundled
  fonts, cinematic resume banner, poster selection and responsive filters/toolbars.
- Preserve collections, Add/Import/Refresh actions, calendar week navigation, new-release
  cards, list view, deletion confirmations and existing page workflows.
- Exclude the profile/avatar as requested. Add the separately approved real
  playback progress/time remaining, guarded Space control and live download badges.
- Keep progress attached to stable Episode IDs; use bounded local VLC/MPV adapters
  and background queue/coverage facts. Label unsupported player progress honestly.
- Center the Home navigation, correct Quick Find contrast, use one seven-day
  schedule row with week navigation, and hide checkboxes until batch selection.
- Show one anime title or a multiple-release count on schedule tiles; align and
  theme the hover release list, keeping all entries clickable.
- Add 16 regressions and a real installed-VLC check; document scope, navigation,
  verification and adapter limitations in HOME_LIBRARY_REDESIGN.md.

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
