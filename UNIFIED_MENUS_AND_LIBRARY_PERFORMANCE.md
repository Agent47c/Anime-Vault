# Unified menus, episode navigation and Library performance

## What widget reuse means in this app

The Library page and its data remain available when navigating away and back.
Unchanged small-library cards and the New seasons/episodes strip are reused.
That does not mean allocating a permanent widget for every anime in a large
library. Above 64 entries the poster grid keeps a bounded set of visible slots
plus a preload margin; scrolling rebinds those slots to different records.

Selection, ratings, watch status, paths and release identity remain in their
existing data/database structures. They are never owned solely by a recyclable
card. A rebind updates its title, tooltip, image, accessible name, facts, badges,
selection and click target. Leaving the app, removing a record, or trimming the
slot pool can destroy widgets. No user state depends on a widget staying alive.

## Applied changes

### Choose Episode navigation

Find an episode / download now calls `open_release_search(self, fid)`. It opens
Find Download Files with the same anime context, rather than the download queue.
The download queue and its other entry points are retained.

### Dropdown and popover design

Reference: `Anime Vault — Unified Dropdown & Popover Menus System/code.html`,
`DESIGN.md` and `screen.png`.

- Shared combo-row delegate: 44px scaled rows, rounded hover surface, coral edge,
  current-item check, optional existing icons, disabled state and elided titles.
- Shared popup containers and QMenus: layered surface, 12px corners, hairline
  border, consistent spacing/type, separators and native keyboard/shortcut layout.
- Existing combo models, values, menu actions, check states and handlers remain.
  Qt still manages keyboard navigation, dismissal and menu placement.
- The calendar preview keeps its three-visible-row scrolling limit, clickable
  hover behavior and adds the same coral hover edge. It retains its own geometry.
- Appearance uses existing light/dark/high-contrast tokens and text scaling.
- The showcase's hash rechecks, profile, tracker/priority commands, new shortcuts
  and server/status claims were not introduced. This is presentation of existing
  controls, not implementation of every command pictured in the showcase.

### Large Library grids

- `VirtualPosters` positions a limited set of the existing HomePosterCard widgets
  within the existing full-page scroll canvas. The visual card and hover behavior
  are reused rather than replaced with a different design.
- Slot count depends on visible rows/columns and a small margin, not total anime.
  Sort/filter changes rebind slots; scrolling within the same visible range skips
  redundant updates. Empty cells and the full scroll extent are calculated from
  data and uniform row geometry.
- Arrow keys, Enter, selection mode, context selection, batch state, status/progress
  facts and download badges retain stable anime identities after rebinding.
- Local images decode on the shared thread pool through the existing bounded,
  version-aware QImage cache. QPixmap creation and widgets stay on the GUI thread.
  Image completions are matched by filename/version before updating a slot.
- Returning to an unchanged page reuses the resident slots and scroll state.

### Large Library list view

- Above 64 entries a QTableView/model/delegate paints the same cover/title,
  subtitle, status, size, rating, checkbox and Details columns. It creates no
  per-row labels, buttons or checkbox widgets.
- Existing sorts/search filters and batch selection use the same LibraryIndex
  and selected-ID set. Details clicks and Enter resolve the current record ID.
- Unchanged row identities use dataChanged instead of resetting the model;
  sorting or filtering changes model ordering without constructing row widgets.
- Covers load for painted rows through workers, with a bounded thumbnail cache.
- Smaller lists retain the existing reusable row widgets to avoid an unnecessary
  small-library implementation change.

### New-release strip reuse

The Library's New seasons/episodes cards are pooled by anime ID and fingerprint.
Unchanged cards survive refreshes; changed cards are rebound. Removed entries
release their widgets. No duplicate signal connections are added on reuse.

## Changed files

| File | Responsibility |
| --- | --- |
| `app/ui/components/dropdowns.py` | Common dropdown delegate and menu popup styling |
| `app/ui/components/airing_count.py` | Matching calendar popover hover treatment |
| `app/ui/components/home_poster.py` | Rebindable existing card and virtual keyboard routing |
| `app/ui/components/virtual_posters.py` | Bounded visible slots and worker image decoding |
| `app/ui/components/virtual_library_list.py` | Delegate-painted large Library table |
| `app/ui/pages/library_page.py` | Large-list/grid integration and release-strip reuse |
| `app/ui/pages/episode_page.py` | Correct Find Download Files navigation |
| `tests/test_virtual_home_and_menus.py` | Slot bounds, rebinding, selection, images, menus and navigation regressions |

## Measurement and verification

Synthetic offscreen run: 1,000 records, 1280×850 window, fallback posters, 21
scroll positions. It used **25 poster slots**, with mean event-processing time
**11.66ms** and maximum **61.33ms** in that run. These are local fixture measurements,
not a guarantee for every machine or a before/after benchmark of the user's files.
Adding the 1,000-row list increased descendant widget count from 374 to 393;
the count includes the surrounding Home controls and resident grid slots.

56 targeted regressions passed, including Home, navigation, scrolling, selection,
large list/grid virtualization and the existing loopback player test. Rendered and
inspected the grid, list and native menu against the supplied design language.
Tests and renders use temporary library data; no user's media was moved/deleted.

The full isolated `python scripts/check.py` pipeline also passed: compilation and
**440 tests** in 95.679 seconds, including existing file safety, imports, downloads,
artwork, navigation and release checks. The scanner heartbeat fixture reached a
39.6ms maximum for 500 files. A final card fingerprint adjustment includes metadata
so a changed provider score also refreshes a reused card.

## Limits and follow-up work

The database format is unchanged. Existing durable commits, release matching,
download validation, history and artwork validation/backoff remain.

The image transport was not rewritten to QNetworkAccessManager: downloads already
run in workers with persistent provider/version caching. This change moves the
large Library's local decoding away from GUI rendering and limits visible work.
HTTP cache replacement alone would not remove widget layout overhead.

Updates still pools individual card widgets. The global refresh worker still
builds a complete read snapshot and prepares artwork. Those are separate remaining
optimization opportunities; this change does not claim to eliminate every possible
tab-switch stall or virtualize every screen in the application.
