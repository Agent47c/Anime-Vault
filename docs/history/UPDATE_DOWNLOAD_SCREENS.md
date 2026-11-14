# Updates and Downloads screen redesign — 11 November 2026

## References and approval

The folder provided contains **update**, rather than upload, and download screens:

- `update and download screen/update screen/code.html` and `screen.png`
- `update and download screen/download screen/code.html` and `screen.png`
- `update and download screen/twilight_sakura/DESIGN.md`

The reference files are unchanged. Both pages use Home's Twilight Sakura tokens,
coral primary/selection accents, muted metadata, rounded cards, capsule navigation,
and light/high-contrast equivalents. Profile/avatar is excluded.

The user approved **Pause all**, **Clear completed**, and Updates **sorting and
batch selection**. Automatic gap repair, artwork/audio/subtitle diff tracking,
automatic dismissal rules, and a new completed-alert archive are not implemented.
The existing libtorrent engine remains; the mockup's Aria2 branding and sample
daemon versions/peer counts are not presented as real application data.

## Downloads

Navigation: **Downloads** in the capsule, or the existing navigation destination.

- Queue rows are painted by a custom delegate over the existing table model.
  There are no per-transfer widget trees. A 2,000-record fixture verifies bounded
  widget counts.
- Rows show real title/release, status, episode coverage, bytes, rate, ETA and
  progress. Full metrics/path/errors remain available on hover and through the
  accessible model. Unknown information is not replaced by sample values.
- Per-row vector controls use event coordinates: Pause/Resume/Retry as appropriate,
  Choose files, and More. Completed rows offer Open folder. These controls call
  the existing queue actions.
- The bottom selection toolbar retains Pause, Resume, Stop, Retry, Choose files,
  More and Refresh for keyboard access and existing workflows. More retains Open
  folder, Remove queue entry **keeping files**, and the separately confirmed
  Recycle Bin action.
- Counted filter pills retain All, Active, Paused/stopped, Completed and
  Failed/incomplete/missing categories. The saved selected ID survives filtering
  and refresh when still visible.
- **Pause all** affects eligible built-in active jobs, including completed jobs
  actively seeding. Paused/failed jobs and legacy external-client entries are
  not silently restarted or contacted.
- **Clear completed** asks for confirmation, captures the selected queue IDs,
  revalidates each job's current completed state, and calls the existing
  file-preserving Remove action. It never calls the download-file recycle/delete
  operation. Missing/incomplete or newly added jobs are not cleared accidentally.
- Both bulk actions execute off the UI thread, retain per-entry persistence, and
  report partial failures. Cancellation stops before the next operation and
  leaves the remaining entries intact.
- The setup panel edits the existing default destination and transfer limits,
  using the existing settings validation/write path in a worker. **Save
  preferences** applies edits; existing files stay in place. It also offers Browse,
  the original five-step Setup Guide, and All download settings. The panel scrolls
  on shorter windows; long paths have full tooltips.
- Torrent selection, source search, browser capture, startup recovery, download
  import verification and the native engine are unchanged.

## Updates

Navigation: **Updates** in the capsule, or the existing destination.

- The masthead retains truthful online/unchecked/offline state and Refresh
  metadata. No automatic repair button is added.
- The categories remain All, Episodes, Seasons, Health, New, Later, Not interested
  and Muted. Counts derive from the existing records. Health's count appears when
  calculated; it is not fabricated as zero while unchecked.
- Cards have cached artwork or a clear initial fallback, an existing-event tag,
  provider ID when known, bounded title/preview text and full-title tooltips.
- Normal cards retain View changes, Later, Dismiss and More. More retains Not
  interested, Mute anime, and Watched and ignore. Saved choices expose Restore
  updates on the relevant anime, preserving the existing per-anime behavior.
- Episode-update cards offer **Find Download Files**, which opens the existing
  editable release-search page. View changes remains in More. This shortcut does
  not submit a download automatically.
- **Severity & date** sorts ordinary alerts by existing change count then last
  metadata check; Health sorts by gap/repeated-number count then last check.
  This is a disclosed ranking over existing data, not a new severity classifier.
  Other choices are Latest checked, Oldest checked and Title A to Z. Sorting uses
  cached records without new API requests.
- **Select** or the header actions menu enables batch selection. Checkboxes are
  hidden by default. In selection mode card clicks select rather than navigate.
  The batch bar offers Later, Dismiss, Watched and ignore, Not interested, Mute,
  and Clear selection, using existing disposition handlers.
- Selections can span filters; the bar states the selected count. Entries no
  longer eligible are removed from selection. Completed actions clear selection.
  Failures name the affected anime while other entries can still be saved.
- Health rows remain individually inspectable. Batch disposition does not invent
  a new gap-ignore or automatic repair policy.
- Health calculations run in a worker and are cached for the current refresh.
  Stale results cannot replace a refreshed inventory, and failures do not create
  an infinite retry loop. Cards and artwork remain pooled across sorting/filtering.

## Shared navigation and preserved behavior

Home, Updates and Downloads use the same centered header and active destination
highlight, with no profile. The selection menu targets Library or Updates as
appropriate and is hidden for Downloads. Other destinations retain their existing
layouts. Search still navigates to Library; collections, import, refresh modes,
storage, status/task banners and shutdown protections remain accessible.

## Changed files

- `app/ui/pages/downloads_page.py`: queue presentation, setup panel and bulk UI.
- `app/ui/components/transfer_row.py`: virtual card painting and event handling.
- `app/ui/pages/updates_page.py`: themed cards/header, sorting, selection,
  background health calculation and multi-anime worker actions.
- `app/ui/transfer_style.py`: shared theme rules.
- `app/core/download_queue.py`: approved bulk adapter over existing safe actions.
- `app/ui/main_window.py`, `app/ui/components/home_header.py`: shared navigation.
- `app/ui/icons.py`: vector overflow icon.
- `tests/test_transfer_screens.py`: eight added regressions.
- `tests/test_update_choices.py`, `tests/test_performance_paths.py`: expectations
  updated for the approved sort control and asynchronous health calculation.

No database schema or API route was added or removed.

## Validation

73 focused tests passed across transfer-screen, download, update-choice,
performance, Home, UI, embedded-workflow and startup-import checks. Compilation
and diff checks pass. New checks cover partial bulk failures, completed-state
revalidation and file retention, cancellation, delegate button clicks, virtual
queues, selection persistence, saved notes and 130% text layout.

Rendered previews use isolated fixture data, not changes to the user's queue:
`data/updates-1280-dark.png`, `data/downloads-1280-dark.png`, 1920/1100 variants,
light-theme variants, and `data/updates-large.png` / `downloads-large.png` at 130%.
These are visual checks, not a real live torrent-transfer test. The historical
full-suite native process/torrent failures are not claimed resolved by this UI
pass. Existing native-transfer integration tests were not rerun as a substitute
for these targeted checks.
