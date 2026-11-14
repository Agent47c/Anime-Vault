# Updates release dates and unified buttons — 11 November 2026

Reference: `Unified Button Design System & Component Template` plus the supplied
vertical Updates action screenshot.

## Updates

Placement correction: the horizontal action row now sits **beside** the anime
information, centered vertically in the card. Equal buttons are reduced to 150px
(scaled), with 8px spacing; narrow screens retain horizontal scrolling. It is no
longer a separate strip underneath the anime information.

Correction: actions now use one **horizontal** row with equal widths and 8px
spacing, replacing the vertical arrangement below. Narrow windows scroll the row
instead of clipping labels or wrapping it into a vertical stack.

- Actions now appear in one right-side vertical column, without a wrapping
  horizontal toolbar or More menu. Every action has equal scaled width, including
  enough room for Watched and ignore. Existing download and restore actions remain.
- Relation updates show their release month/year from cached relation start dates.
  A separate visible date line accompanies the preview, and View changes includes
  dates for every relation. Year-only data stays year-only. Unknown dates say
  Date unavailable. Announcements say Expected release; airing entries say Started.
- Expanded AniList metadata queries request relation/root start dates and years.
  Existing cached records lacking dates need the normal internet metadata refresh;
  the UI never fetches dates synchronously or invents them from the current date.
- Persisted update strings and dismissal fingerprints are unchanged. Date labels
  are presentation-only so previously dismissed releases are not republished merely
  because date display was added. Card reuse now accounts for changed metadata.

## Buttons and folders

- New `app/ui/button_system.py` supplies shared Default (36px / radius 9), Large
  (44px / radius 10) and Extra-large (52px / radius 12) roles, scaled typography,
  primary/secondary/folder/destructive roles, hover, pressed, focus and disabled
  states. Existing custom-painted navigation, posters and specialized controls
  retain their behavior; card-specific sizing takes precedence where needed.
- Shared rules apply to the base application stylesheet and scoped Home, Details,
  Settings, Updates, Downloads, release search, Organizer, Merge and Duplicate
  styles. Primary contrast uses existing theme foreground tokens in scoped UI.
- Organizer configured roots and Merge preview source folders are actual clickable
  Open folder buttons, with full-path tooltips and accessible names. Merge rows
  are taller to fit the title and folder button. Offline root labels are retained.
- No file handling, scanning, download, release classification or deletion behavior
  is changed by these presentation rules.

## Changed files and validation

New files: `app/ui/button_system.py`, `app/ui/update_release_dates.py`,
`app/ui/components/folder_button.py`, `tests/test_update_dates_and_buttons.py`.
Updated: metadata query fields; Updates/Organizer/Merge pages; global and scoped
styles; changelog and feature/navigation documentation.

52 focused tests passed: Updates/transfer screens (8), Settings reference (3),
Organizer manual UI (6), Merge (6), Home (17), Details (8), and release-date/button
regressions (4). The regressions verify cached month/year display, future labels,
unknown dates, preserved dismissal, vertical alignment, full button labels and
folder opening. Inspected `data/update-buttons-vertical-preview.png`, generated
by `data/update_button_visual.py` using a temporary database. No real library files
were changed and no live metadata refresh was run during validation.
