# Series grouping, multi-season confirmation and rematch crash fix

Updated 11 November 2026.

## Searchable grouping page

Open Details → **Group with another series**.

- Search field, Search button, Enter support and a clear control replace the old combo.
- Search covers English, Romaji and Japanese names of the existing group members.
- Virtual rows show small cached posters, entry counts and storage/announced state.
  Missing artwork uses an icon fallback. Image decoding/scaling runs in a worker.
- Click the desired **main series card** to include/check it. Clicking a checkbox
  includes the same entry and highlights it as the main card; a checked box can
  be clicked again to remove it. Other checked season/arc entries remain included;
  the anime you started from is included automatically.
- Unchecking the main card selects another checked entry if one remains. With no
  checked entries, Review grouping is disabled. Space uses the same checkbox state.
- Searches retain checked entries, supporting differently named seasons/arcs.
- **Review grouping** shows the main card and every included record. An
  acknowledgement is required before Confirm grouping.
- **Reset manual grouping for this series** remains available with confirmation.

The grouping plan is checked again before an atomic write. Changed/deleted entries
require a fresh review. No files move, rename or get deleted. Existing records
retain IDs, local paths, notes, ratings and watch history. Known announced members
without a local season row receive a metadata-only catalogue entry.

Manual grouping works without a provider relationship. It differs from online
Rematch, whose multi-release selections must have a verified common series root.

## Multi-season rematch confirmation

Details → Rematch preserves multi-release selection and per-local-season mapping.
Selection-only import pickers and continuing-series single-match mode remain.

1. Search and select related releases, including differently named seasons/arcs.
2. Assign each released selection to the appropriate local season or Metadata only.
3. Two or more selections change the action to **Review N seasons**.
4. A worker verifies the common series root and unique, valid local assignments.
5. Review the main series, each release/status, available preview images and local
   folder or metadata-only assignment.
6. Acknowledge the review and Confirm matches to save.

Unrelated releases, duplicate local assignments and local assignments for
unreleased seasons are rejected. Cancelling review writes nothing. Verification
and application have progress feedback. A background verification does not force
its drawer back onto the screen after navigation away.

If selected releases resolve to different provider series, the error now lists
their complete release names grouped by the verified series title. It tells the
user to deselect the conflicting releases or group existing entries manually.
The message does not guess which provider group is the intended one. If an
earlier-season lookup fails instead, it names the selected anime whose relation
could not be verified. Matching criteria and database-write behavior are unchanged.
Validated by all 17 series-grouping tests, including two error-detail regressions.

## Announced releases

- Provider status `NOT_YET_RELEASED` appears as **Announced · Not released** in
  search results, confirmation and grouped details.
- Those releases stay Metadata only; local-season assignment is unavailable.
- Details does not overwrite their status with Missing from disk. Their episode
  field says Not released; they have no missing-download count or Locate action.
- Unknown release status is kept unknown, rather than guessed as finished/announced.

## Stale-card crash cause and fix

The reported error came from an old card referencing an ID deleted by rematching
into an existing canonical series. `get_series()` returned None, then the detail
page attempted to read its continuous-episode setting as a dictionary.

- Rematching into an existing owner now keeps the original record, local-season
  ownership and user/history data, grouping it under the canonical card instead
  of deleting it. Corrected release names/metadata and matching decisions remain.
- An old retained ID resolves the current main card; subsequent detail actions
  use that representative.
- Library/calendar clicks for an already-missing legacy ID request a data refresh
  instead of opening invalid details.
- Direct details construction for a missing ID displays a friendly changed/removed
  message. `uses_continuous_episodes(None)` safely returns False.
- Artwork callbacks and stale season-match controls validate their records too.
- Rematch can access local seasons across an existing grouped series.

This does not invent replacements for records deleted before the fix or reset
the database. Restart the app to load the updated code. No real user grouping was
automatically executed during development/testing.

## Changed implementation

- `app/core/series_grouping.py`: preview, atomic grouping, announced catalogue rows.
- `app/ui/pages/group_series_page.py`: searchable poster list and confirmation.
- `app/ui/dialogs/match_review.py`: verified multi-release confirmation.
- `app/ui/dialogs/rematch_dialog.py`: review, grouped local choices, announced states,
  tracked workers and progress.
- `app/core/matching.py`: source-record preservation and release validation.
- `app/ui/pages/detail_modal.py`: new entry point, canonical routing, stale-ID guards
  and announced-season presentation.
- `app/ui/main_window.py`, `app/db.py`: missing-card/None handling.
- `app/ui/io_task.py`: an earlier worker cannot clear a newer worker reference.
- `app/ui/theme.py`: theme-aware grouping list, selection and checkbox styling.
- `tests/test_series_grouping.py`, `tests/test_matching.py`: regression coverage.
- Changelog and feature/navigation inventory updated.

## Validation

The focused suite covers non-destructive grouping, stale-plan rejection, search,
poster selection, acknowledgement/cancel, announced catalogue rows, source/history
preservation, immediate old-card reopening, missing-ID guards, related-release
checks, unique assignments and navigation away during verification.

Rendered fixture checks cover the grouping page, grouping confirmation, rematch
confirmation and announced Details rows. All use temporary records/files.
Final full validation passed **275 tests** in 43.700 seconds, including 14 focused
grouping/rematch regressions. The 500-file scanner heartbeat recorded a 40.0 ms
maximum. Compilation and whitespace checks passed. The tests use generated local
fixtures and mocked provider responses; no real anime files are moved/deleted.
