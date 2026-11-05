# Organizer button fixes and manual scanning

Follow-up to Phase 1, requested after reviewing the running Organizer page.

## Changes visible in the app

- Review buttons use 14 px theme-scaled text, a 44 px click target and rounded
  corners. The action column has enough room for the control and its margins.
- Focus/pressed styling keeps the same border dimensions, so clicking Review no
  longer squeezes it into a thin pill. Table-cell padding no longer clips it.
- The review page uses the existing painted cross control instead of a font glyph;
  it has a 44 px target and the accessible name “Close organization review”.
- Refresh has a 148 px minimum width and reserved room for the dropdown arrow.
  Busy labels are “Refreshing…” and “Checking…”; progress details remain in the
  existing status area. Both local-only and internet refresh menu actions remain.
- Opening or revisiting Organizer does not start a filesystem scan.
- The existing Scan now button is the explicit way to build/update the preview.
  Find missing files remains an independent manual action.

## Preview caching and invalidation

The scan worker saves the preview in the existing SQLite app-state store. A newly
opened Organizer can restore that snapshot without walking media directories or
contacting metadata APIs. The status says Saved preview rather than implying a
fresh scan occurred.

The cache records roots, detection rules and completed-operation information. Root
or rule changes and app-controlled file operations make an old preview stale.
Stale results remain visible, but move/review execution is disabled until Scan now
creates a fresh preview. Root/configuration checks on navigation read database
settings only; they do not scan files.

Adding/removing roots, changing rules, accepting a review operation and finishing
an organization batch no longer start an automatic Organizer rescan. The page
asks the user to click Scan now instead. Configuration changes during an active
scan also prevent its outdated result from being used as a current preview.

External file changes cannot be discovered from a cache. After moving/adding files
outside the app, click Scan now. The Phase 1 per-file preflight checks still protect
execution of a previously saved preview. Cache restoration preserves the existing
features rather than inventing an automatic background watcher.

## Files changed

| File | Responsibility |
|---|---|
| `app/ui/pages/organizer_page.py` | Button/close control layout, manual scan lifecycle, restoration and stale-preview handling |
| `app/ui/organizer_cache.py` | Versioned persistent cache and configuration validation |
| `app/ui/main_window.py` | Refresh width, dropdown spacing and bounded busy labels |
| `app/ui/theme.py` | Theme-token Review styling with stable focus geometry |
| `tests/test_organizer_manual_ui.py` | Six regression tests for manual scans, cache restoration/invalidation, button text fit and vector close control |
| `CHANGELOG.md`, `README.md`, this file | Reviewable change record |

## Validation

The full suite contains 156 tests. New tests cover opening/revisiting without a
scan, restoring cached results, stale roots requiring a scan, retained manual scan
functionality, Review text at 130% sizing with focus, Refresh labels alongside the
dropdown, and the glyph-free close control.

Offscreen renders were visually inspected in dark/light themes at 100% text size
and dark theme at 130%. At 130%, Review text measured 61 px inside a 68 px content
area; the busy Refresh label measured 92 px inside a 102 px content area. The
Review control remains 44 px tall, including when focused.

The renders use temporary example rows, not the user's library. A full interactive
monitor/DPI pass is separate from these offscreen layout checks. Existing file
operation preflight and recovery behavior remains unchanged.
