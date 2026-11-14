# Navigation memory and compact headings

Implemented 12 November 2026.

## Navigation behavior

- Each main tab remembers its current live page during this app session. Library
  → series details → Settings → Library returns to the same details widget.
- Updates → New anime releases → another tab → Updates returns to the releases
  page, retaining its filters, results and scroll position. Nested workflows keep
  their existing Back chain.
- Switching tabs no longer rejects disposable workflows owned by another tab.
  Explicit Back, Cancel and Close still finish them and release disposable pages.
- Completed or deleted workflows are skipped when restoring navigation; the tab
  falls back to its parent/root rather than reopening a dead widget.
- Global Library search and collection shortcuts explicitly show the Library
  results instead of restoring an unrelated details page over the results.
- This is in-memory session navigation, not saved navigation across restarts.
  It adds no database tables, metadata requests or media-file operations.

## Presentation

- Page/workflow heading styles use 24px before the existing text-size scaling.
  Hero and anime-title typography is unchanged.
- Updates removes the ledger/library-tracking eyebrow and uses “Updates”.
  Following the header revision, New episode updates, New anime releases and
  Refresh metadata sit together on its right in that order. AniList connection
  status sits below the title. Existing refresh behavior, health filters and
  actions are preserved.
- Downloads removes the network-transfer-core/built-in-libtorrent eyebrow;
  Downloads & Transfers moves up into the header.
- Organizer removes the consolidation-engine eyebrow and uses
  “Organize & File Management”. Merge uses “Merge libraries”, duplicate review
  uses “Duplicate files”, and Settings uses “Settings”.
- Existing controls remain available; no features were removed.

## Open download folder

- A selected transfer opens its existing library destination, download root or
  staging destination, in that order. A stale moved location no longer blocks
  opening another valid location recorded on the same transfer.
- With no transfer selected, the action opens the configured download folder.
- Missing folders and Windows open failures produce visible status messages.
  The menu explicitly discards QAction's checked argument.
- No files are moved, renamed or deleted by this action.

## Validation

- Added regression coverage for independent Library/Updates navigation, nested
  Back, explicit Library resets, moved-download folder fallback and opening the
  configured folder without a selected transfer.
- The first focused runs passed 45 tests (4 new and 41 existing).
- Rendered and visually inspected Updates, Downloads, Organizer and Duplicate
  review at 1100×680 using a temporary database. Their headings and header actions
  fit; all existing controls remained present.
- Compilation and all 471 isolated tests passed in the final full run (102.486
  seconds). Scanner heartbeat maximum was 40.1ms for its 500-file fixture.
  The full-suite result is recorded in `data/navigation-memory-validation.log`.

## Follow-up: update review and aligned navigation

- Clicking a Library poster in New seasons and episodes opens its saved change
  list under Updates, rather than opening anime details. Back returns to the
  main Updates page. Grouped series collect saved changes from their member
  entries without making an additional database or network request.
- Clicking an update card's body also opens View changes. The existing download,
  health-review and disposition actions remain available; ordinary Library cards
  still open anime details.
- Full-page workflows share a navigation row with a vector left-arrow Back
  button and a breadcrumb beside it. Details updates that breadcrumb to its
  actual anime title as loading finishes, instead of adding a second row inside
  the page. Release discovery shows Updates / New anime releases when opened
  from Updates. The breadcrumb follows the owning tab on other workflows.
- View changes uses the shared theme, plain-text labels, wrapping change rows
  and its existing Close action. Its disposable page is released on Back/Close.
- New anime releases uses the Library's surface, raised, text and accent colors
  in dark, light and high-contrast modes. It supports retheming retained pages.
  Check updates now sits at the right of its title row.
- Organizer places its existing scan/find/stop controls at the right of its
  heading. Its ready/busy status stays below the title and subtitle. A sizing
  regression check prevents the status badge from squeezing the heading.
- New navigation/update regressions cover Back/breadcrumb alignment, the vector
  arrow, header button order, Library update-poster routing, change-list return,
  update-card behavior, Organizer title width and release-news palette parity.
- Follow-up validation is recorded in
  `data/update-navigation-headers-validation.log`. Offscreen temporary-database
  renders were inspected at 1280×720 and 1100×680. No user media files were
  modified during these checks.
- Final follow-up compilation and all 478 isolated tests passed in 106.453
  seconds. The 500-file scanner fixture's maximum heartbeat delay was 40.3ms.
