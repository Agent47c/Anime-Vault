# Immediate update-choice propagation — 14 November 2026

## Reported behavior

Later, Not interested, Mute, Watched and ignore, Dismiss and Restore could take
10–15 seconds to appear in the Library home update strip and the Updates list.
The single remaining update and restoring into an empty list made this obvious.

## Causes found in the shared UI path

- The save worker already committed choices asynchronously, but the shell only
  marked Library/Storage dirty. The retained Library index and release strip
  were not patched, leaving them dependent on a later global refresh/navigation.
- Updates removed affected cards without reconciling the current list. A restored
  record could stay absent from an empty active category until the next refresh.
- A background read snapshot captured before a choice could subsequently render
  old flags again if it finished after that choice was saved.

## Changes

- Patch committed fields into the existing LibraryIndex. Recompute a grouped
  series' update flag across all members, so suppressing one season doesn't hide
  another season's pending update.
- Immediately reconcile the Library release strip, filter counts and visible
  grid/list using the existing card pools. Do not reload the hero, rebuild the
  calendar, rescan files or create another full LibraryIndex for these choices.
- Reconcile Updates source/destination lists after saving, retaining unaffected
  pooled cards, existing sort/filter behavior and error handling. Restore now
  populates an already empty active list immediately.
- Keep the shell's badge/count updates. Mark Storage dirty only when watch status
  actually changes; notification preferences alone need no storage refresh.
- Assign choice revisions and overlay only choices newer than a pending refresh's
  start revision into its memory snapshot, including disposition app-state rows.
  This protects recent choices without permanently masking later internet updates.
- Keep durable saving before UI publication. No optimistic success is shown when
  a database write fails; failed choices retain their original enabled card.

Files: `app/core/library_index.py`, `app/ui/pages/library_page.py`,
`app/ui/pages/updates_page.py`, `app/ui/main_window.py`, `app/ui/refresh.py`.

## Verification

Four focused regressions cover all six choices across the two retained screens,
restoring into an empty list, grouped-series aggregation, stale memory snapshots,
and avoiding a global Library refresh. On temporary fictional data the first
focused run completed the save-and-propagate path in **78.8 ms maximum** across
the five suppressing actions. This is test-machine evidence, not a guarantee
about a busy HDD or SQLite writer contention in every installation.

Tests: `tests/test_update_choice_propagation.py`.
Focused log: `data/update-choice-propagation-focused.log`.
Full-suite log: `data/update-choice-final-validation.log`.

Final validation: **539 tests passed** in 137.055 seconds; compilation and the
regression completion guard passed. Publication hygiene/documentation-link checks
also passed. No Chrome extension behavior changed in this fix.

This pass edits source and tests; it does not install or modify an existing EXE,
download media, change saved user choices, or rebuild the setup package.
