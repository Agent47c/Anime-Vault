# Changelog

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
