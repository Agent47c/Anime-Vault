# Hierarchical breadcrumb navigation

Implemented 12 November 2026.

## Behavior

Breadcrumbs now follow the existing parent-page history instead of combining
only the root tab name and the current screen name. Examples:

- Library / The Exiled Heavy Knight Knows How to Game the System
- Library / The Exiled Heavy Knight Knows How to Game the System / Choose episode
- Library / The Exiled Heavy Knight Knows How to Game the System / Choose episode / Find Download Files
- Library / Overgeared / Edit Anime Entry
- Library / Overgeared / Rematch Anime Metadata
- Library / Overgeared / Broadcast & Release Updates
- Library / Overgeared / View API JSON
- Library / Overgeared / Group seasons and arcs

The same shared navigation logic applies to other nested workflows and tab
owners. Switching to Downloads, Settings or another tab retains the current
page and complete breadcrumb. Back removes the last step. Returning explicitly
to the Library root resets the path, so a different anime starts its own history.
This is session memory, not a persisted history across application restarts.

## Changes

- `app/ui/navigation.py`: derive breadcrumb parts from `_nav_previous`; retain a
  parent-path snapshot for a closed/deleted ancestor; guard recursive history
  traversal; refresh descendants after asynchronous anime-title changes and when
  restoring a tab. These operations inspect only retained workflow pages, without
  database queries, API calls or poster-grid traversal.
- Show the existing shared Back/breadcrumb header in drawers as well as full
  pages. A drawer's Back action cancels it and returns to its parent, matching
  Cancel/Close behavior. Existing drawer content and save actions remain intact.
- `app/ui/pages/detail_modal.py`: use `View API JSON` for the viewer's breadcrumb
  segment. The anime already appears in its parent path; the full window title
  and JSON viewer functionality remain unchanged.
- `tests/test_navigation_breadcrumb_history.py`: cover nested navigation, tab
  restoration, all requested child-screen labels, asynchronous parent-title
  updates, drawer Back, Library-root reset and the actual API-viewer route.

## Verification

- The focused navigation/workflow run passed 36 tests.
- Compilation and all 487 isolated tests passed in 134.959 seconds. Full log:
  `data/breadcrumb-history-validation.log`.
- Rendered and inspected Choose episode and Edit Anime Entry with a long anime
  name at 1280×850. Verified the complete path before and after a Downloads tab
  round trip. Rendering used a temporary database and disabled the episode file
  scan; it made no changes to user media or the real library database.
- The existing 500-file scanner fixture recorded a maximum heartbeat delay of
  50.2ms during full validation.
