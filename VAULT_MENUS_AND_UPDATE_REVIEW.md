# Vault menus and reliable update review

Implemented 12 November 2026.

## Reference-style menus

- Added a shared `VaultMenu` presentation for the top-right navigator and anime
  context menu: rounded panels, a small heading, cached SVG icons, tinted active
  rows with an accent stripe, shortcut badges where a shortcut already exists,
  separators and a clearly labelled Recycle Bin action.
- The navigator preserves Add anime, TXT import, Settings, all five collection
  filters, local refresh and internet sync. Its active collection reflects the
  current Library filter. The footer uses the app name instead of inventing a
  daemon state or version from the mockup.
- Anime context menus are available from posters and the virtual Library list.
  They expose existing Details actions: open details, resume/play, choose episode,
  edit metadata, rematch, find downloads, mark watched, open folder and the existing
  confirmed Recycle Bin workflow. Select/Unselect remains available.
- Context commands capture the original anime ID. Selection also keeps that ID
  if a virtual poster slot is rebound while the menu is open. Closed context
  menus are disposed instead of accumulating under retained poster widgets.
- Metadata uses the actual cached title, year, path and storage state when
  available. Mock episode titles, encoder details, shortcut bindings and version
  strings are not invented. Menu rendering and opening do not fetch artwork or
  contact an API.
- Menus retain native QActions, keyboard navigation and existing window-bound
  containment. Existing dropdowns outside these two menus keep their styling.

## Empty/stale update view

The Updates root can be awaiting a deferred background refresh when a Library
new-update card is clicked. The old change viewer read only the root's earlier
in-memory records, so it could show no changes even though newer changes were
already saved in the database.

- The change viewer now reads current saved changes in an app-owned worker when
  opened. It can immediately show cached rows while that local read completes.
  Opening it does not make an internet request.
- Added **Refresh data** beside the anime title. This explicitly checks only the
  selected anime/group's existing AniList links, using the existing updater
  comparison, metadata cache, publish/dismissal rules and cancellation support.
- Show a loading status and indeterminate progress bar; prevent duplicate refresh
  requests while one is active. On success, update the rows and notify the existing
  data-change pipeline so Library/Updates counts can reconcile.
- If no changes exist, show an explanation directing the user to Refresh data.
  Offline mode, missing AniList links and provider errors are visible. A failed
  internet check retains saved changes instead of replacing them with a blank view.
- Closing the viewer cancels its work safely, preserves the parent navigation
  path and does not reopen the viewer when the worker finishes. No download starts
  automatically, and upcoming episodes retain the existing “airing soon” wording.

## Files

- `app/ui/components/vault_menu.py`: shared menu painting and metadata rows.
- `app/ui/components/home_header.py`, `home_poster.py`, `virtual_library_list.py`:
  navigator/context integration.
- `app/ui/components/dropdowns.py`, `app/ui/icons.py`: preserve the rich menu's
  own presentation and reuse cached SVG icons.
- `app/ui/pages/library_page.py`, `app/ui/main_window.py`: context-action dispatch
  into existing Details workflows; preserve confirmation and playback behavior.
- `app/ui/pages/update_review_page.py`, `app/core/update_review.py`: asynchronous
  current-change loading and explicit scoped metadata refresh.
- `app/ui/pages/updates_page.py`: use the review page with the relevant anime IDs.
- `tests/test_vault_menus_and_update_review.py`: cache freshness, explicit refresh,
  offline/error retention, cancellation, menu containment/keyboard behavior,
  target identity and context-menu disposal. The existing right-click selection
  test now selects its named action instead of assuming Select is the first row.

## Verification

- Rendered and visually inspected both menus and the populated update viewer
  using a temporary database. A saved “Episode 21 airing soon” entry appeared
  despite an initially empty UI cache. Provider responses in automated tests are
  mocked; verification did not call a real provider or touch user media.
- Full validation log: `data/vault-menus-update-review-validation.log`.
- Compilation and all 495 isolated tests passed in 126.653 seconds. The existing
  500-file scanner fixture's maximum heartbeat delay was 45.7ms.
