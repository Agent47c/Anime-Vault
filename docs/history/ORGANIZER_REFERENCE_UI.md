# Organizer reference UI — 11 November 2026

Reference: `organizer screen/code.html`, `DESIGN.md`, `screen.png`.

Navigation update: duplicate review now has its own third Organizer tab, and its
button has been removed from the season/folder screen. Merge and duplicate styling
are documented in MERGE_DUPLICATE_REFERENCE_UI.md. This supersedes the grouped
duplicate-button description below.

- Organizer now shares the top navigation capsule with Library, Updates,
  Downloads and Settings. The season/folder screen uses Twilight Sakura styling,
  a Library Organizer & File Management heading, and grouped Scan, Find missing
  files, Review duplicate files and Stop controls.
- Detection rules and configured roots are side by side above a full-width
  organization preview. All five rules, root addition/removal, drop zone, search,
  counted filters, selection, per-anime review, progress and batch organization
  remain connected to their original handlers.
- Merge all anime into one root library is retained as its existing tab; its
  workflow has not been rewritten or removed.
- Review duplicate files opens the existing duplicate-review page. No SHA-256
  wording or encryption feature has been added to the UI. Existing backend
  duplicate verification remains unchanged.
- Scans stay manual and saved-preview behavior is retained. The new layout
  performs no enumeration, hashing or file moves when opened. Compact windows
  scroll the page to keep every control reachable.
- Mockup-only symlink mode, schema-pattern editor, undo-history claims, fabricated
  drive metrics, sample thumbnails and extra journal/codec metadata are omitted.
  The preview displays the actual existing data and four existing columns.

Changed files: `app/ui/organizer_style.py`, `app/ui/pages/organizer_page.py`,
`app/ui/main_window.py`, new reference UI tests, changelog and navigation index.

Validation: six existing manual-scan/review tests and two reference UI tests.
Temporary-data renders checked at 1450×1150 and 1100×720 using
`data/organizer_reference_visual.py`. No real scans, moves or duplicate removal
were executed during these checks.
