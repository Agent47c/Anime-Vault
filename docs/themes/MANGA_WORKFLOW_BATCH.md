# Manga Light workflow and master-control update

15 November 2026

The Library remains the shared visual authority. Its shell, navigation, colours,
typography and reusable control materials take precedence over later mockups.
Future differences to these shared elements require the user's approval.
This pass explicitly implements the user's requested master depth correction.

## Master controls

- Raised sort/select, page-number, refresh and sidebar controls have paired
  light/dark shadows and rounded faces.
- Search, filter and view-mode tracks have inset depth. The disabled Previous
  button looks recessed; enabled controls respond to their pressed state.
- Active filter counts receive a black badge. Inactive counts remain readable.
- Shadow tiles are generated once and reused. Parent tracks paint directly so
  Qt does not suppress the child button effects. No whole-library shadow or
  extra poster widgets were introduced.

## Reference coverage

| Supplied screen | Application implementation |
| --- | --- |
| Broadcast release updates | ReleaseNewsPage broadcast view: white panels, master fields/buttons |
| Confirm/review downloads | DownloadReview: compact coverage/destination summary and review gate |
| Downloads/transfers | DownloadsPage: existing virtual queue and guide with shared light surfaces |
| Find download files | ReleaseSearchPage: context, search, availability and review actions |
| Import watched list | WatchedImportDialog: light upload/configuration/results controls |
| Merge libraries | MergePage: source/destination, preview, file review and confirmation |
| New anime releases | ReleaseNewsPage discovery: uniform cards and compact actions |
| Tags/themes | Shared staged taxonomy panel with selected counts, Apply and Cancel |
| Organize/file management | Existing rules, roots and preview in light panels |
| View changes | UpdateReviewPage: individual release rows and actions |
| Five-step setup | Existing five setup pages reused in a responsive single scrolling page |
| Storage | Light capacity/statistics/table panels with cached pagination |

The watched-import reference PNG was blank; its supplied HTML was used.
Source references remain under `Light Theme (Manga Brutalism)`.

## Approved functional additions

- Broadcast filters: Today, In Library and Missing. Missing requires an aired
  episode and a linked local series; future/unlinked rows are not labelled missing.
- Share details copies real title, premiere and provider URL to the clipboard.
- Named discovery filter presets persist in application state. Adult tags still
  require the existing adult-content preference.
- Per-release Find release opens existing search; Ignore dismisses only that
  exact pending event. Existing dismissed events are retained. Date sorting uses
  known release dates and preserves unknown dates without inventing timestamps.
- Storage sorting, potential-reclaim filtering and four-row pagination reuse
  the loaded snapshot rather than rescanning disks for each page.

## Preserved and excluded

Sakura themes remain available. Existing routes, file-operation previews,
confirmation requirements, manual episode matching and download status colours
are retained. The setup screen reuses the existing registration/save/test steps.
No scans, downloads or file moves are triggered by the visual change itself.

CRC32 verification and the Chrome-extension Copy ID button were explicitly
declined and were not added. No fake Integrity Pass, drive temperature, SMART,
hash-check or decorative server/version claims were added. Unapproved bulk
Mark all as read and destination-changing controls were not introduced.

## Validation

- Full project checks passed: **560 tests**, including six new workflow tests.
- Focused tests cover exact event dismissal, broadcast filters, presets and
  adult-tag locks, reused setup steps, cached Storage paging, shadow-tile reuse
  and theme restoration.
- Twelve workflow screenshots were rendered with temporary data. The main
  Library was also checked at wide/narrow sizes, including seven-card pagination.
- The final visual pass tightened the download review summary and expanded
  Storage label/button space; focused tests were rerun after these refinements.
- Publication guard passed. No personal database/media changes or installer
  build were performed. Live provider/torrent availability and every Windows
  DPI configuration are outside this isolated visual validation.

Shared implementation: `manga_workflows.py`, `manga_setup.py`,
`components/neumorphic.py`, `components/taxonomy_panel.py` and
`release_view_tools.py`. Per-screen hooks retain the existing page classes.
