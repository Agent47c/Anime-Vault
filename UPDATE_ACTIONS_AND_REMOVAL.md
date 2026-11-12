# Update actions and library removal

## Incremental notification choices

Previously, saving a choice called `UpdatesPage.refresh()` and emitted
`data_changed`, starting a global RefreshWorker and repeating visible layout work.

Now UpdateActionWorker returns committed records and dispositions. Watched and
ignore includes grouped series members. Updates patches its in-memory lists,
removes affected cards, and updates category counts, its empty state and footer.
Unaffected card widgets remain mounted. Destination cards are created lazily when
their category is opened.

A lightweight `choices_changed` signal updates navigation and watch-status counts.
Library and Storage refresh when next opened. Notification choices do not request
API sync, artwork refresh, disk scans, or global refresh. Other running jobs can
independently refresh data when their own work finishes.

Database writes stay in the background. A failed choice leaves its card enabled
for retry, while successful batch choices take effect. Errors name their anime.
Persistent dismissals, per-anime restoration, and future-change notifications keep
their existing behavior.

## Card layout

Actions sit at the bottom-right on the anime card's background, with consistent
widths, 8px gaps, compact text and padding. All existing actions remain visible.
Narrow windows wrap buttons without nested horizontal scrolling. Watched and
ignore is fully readable.

## Remove anime

Navigation: **Updates card → Remove anime**, or **Series details → Remove anime**.

The prompt defaults to Cancel and offers:

- **Remove entry — keep files:** hide the complete grouped series; leave media untouched.
- **Delete files and remove entry:** use the existing reviewed Recycle Bin flow
  for each grouped entry, then hide the series after successful completion.

Cancellation or deletion failures stop the workflow. Inaccessible/still-on-disk
seasons prevent final removal. Active downloads/seeding must be stopped first.
Deletion uses existing indexed-video rules; unrelated/unindexed files are kept.

Stable records, notes and history are retained internally. Removal is a persistent
visibility exclusion, not a destructive database cascade. Hidden entries are
excluded from visible statistics. Their known folders are excluded from automatic
scanning, and their completed downloads are omitted from Organizer previews.
This prevents kept files from being immediately reimported. No restore interface
is added in this change.

## Changed files

- `app/ui/pages/updates_page.py`: worker results, incremental list/counter updates,
  action layout and removal button.
- `app/ui/main_window.py`: lightweight notification signal handler.
- `app/ui/transfer_style.py`: compact action typography/padding.
- `app/core/library_removal.py`: grouped validation and transactional exclusions.
- `app/ui/remove_anime.py`: keep/delete/cancel prompt and Recycle Bin workflow.
- `app/ui/pages/detail_modal.py`: Details removal button.
- `app/ui/dialogs/delete_confirm.py`: expose deletion results to the workflow.
- `app/db.py`: removed-entry filtering and visible statistics.
- `app/core/download_queue.py`: removed-folder scan exclusions.
- `app/core/organizer.py`: omit removed completed-download entries.
- Regression tests, changelog and navigation inventory.

## Validation

45 targeted tests passed across `test_transfer_screens`,
`test_update_dates_and_buttons`, `test_library_removal`, `test_update_choices`,
`test_download_settings_polish`, and `test_ui_regressions`.

Tests cover unaffected card identity, absence of page/global refresh after a
choice, counters, persistent choices, grouped watch status, save failures,
retained files/notes, removal exclusions, active-download blocking and failed
removal visibility. An offscreen Updates rendering at 1600×800 was inspected.
No real library files were deleted. These checks do not establish a measured
latency guarantee on the user's HDD.
