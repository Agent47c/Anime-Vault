# Library list, grouping confirmation and duplicate review references

Applied the screenshots and HTML in:

- `Anime Library List View`
- `confirm series grouping screen`
- `Review duplicate files screen`

## Library list

The existing List toggle opens the restyled table: 78px base rows, larger cover
thumbnails, bold English titles, muted italic alternate titles, rounded storage
status pills, size, the existing personal rating and Details button. Long titles
elide with their existing tooltips. Selection remains opt-in and existing batch
actions, filtering and sorting remain unchanged. Hidden grid geometry no longer
forces excess list height. Grid geometry is restored when switching back.

## Grouping confirmation

The existing review step now opens in a centered panel up to 720px wide over the
existing backdrop. It shows the main-card anchor, a primary-container marker,
season/arc rows, announced/finished status, the history-preservation note and
explicit review checkbox. Cancel remains the default focus. No grouping data or
confirmation requirements changed. Navigation accepts an optional panel width;
other workflows retain their previous defaults.

## Duplicate review

The existing Organizer duplicate tab uses the reference's decorative header,
summary tiles, action panel, file tree, protected-copy labels and safety footer.
Summary values come only from existing scan results: affected anime, redundant
copies and their sizes. File rows display paths and the already-recorded file size.
The action column is right-aligned in the layout and fits its full labels.

Preserved: database/drive scan dropdown, Stop, saved review revalidation, manual
copy selection, one protected copy per group, existing byte verification and
Recycle Bin confirmation. Per your response, no select-all, encode filters or
Preferences shortcut were added. No new hashing feature or mockup-only scan status
was introduced. Unavailable encoding/date information is not fabricated.

## Changed files and validation

- `app/ui/review_reference_style.py`: scoped list/group reference colors and styles,
  retaining light-theme/high-contrast token fallbacks.
- `app/ui/pages/library_page.py`: list row presentation and view sizing.
- `app/ui/pages/group_series_page.py`: grouping confirmation layout.
- `app/ui/navigation.py`: optional workflow width.
- `app/ui/pages/duplicate_page.py`: duplicate layout and scan-result summaries.
- `app/ui/merge_duplicate_style.py`: duplicate panels/tree styling.
- `tests/test_three_reference_screens.py`: new UI/safeguard checks.

52 targeted tests passed: Home (17), Organizer (4), series grouping (17), workflow
dialogs (7), embedded workflows (4), and reference screens (3). The Home loopback
test was rerun successfully outside the sandbox after a socket-permission error.
All three offscreen previews were rendered and visually inspected. Test previews
used temporary synthetic records; no actual library files were changed.
