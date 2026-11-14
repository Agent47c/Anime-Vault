# Merge and Duplicate Review UI — 11 November 2026

Implemented the two references under `merge and duplicate ui/stitch_untitled_project_creation`.

## Navigation

Organizer now has three destinations:

1. Organize seasons and folders.
2. Merge all anime into one root library.
3. Review duplicate files.

The duplicate-review button is removed from the season/folder screen. Duplicate
review is a persistent tab rather than a separate popup/navigation page. Opening
it starts no scan; Check duplicate files is explicit. Existing task-banner
navigation and shutdown worker tracking now include this embedded workflow.

## Merge presentation

The Merge Libraries into Single Root heading, source/destination cards, Move
Preview Ledger, file-details table, folder approval and move-confirmation panel
use Twilight Sakura styling. All original controls and handlers remain: source
selection, Browse, Generate move preview, per-anime selection, highlighted-file
inspection, editable folder choice, Approve folder, review checkbox, Move selected
anime, Stop after current file, progress, failures and saved destination.

No move semantics, overwrite checks, journals or database reconciliation were
changed. Existing roots and generated plans are not recreated for theme changes.

## Duplicate presentation and safety

Review & Clean Duplicate Files uses a bordered header, explicit verification
note, scan/stop controls, grouped anime/episode/file review and a bottom Recycle
Bin action. Full file paths remain available as tooltips. The retained copy has
no checkbox; extra copies are initially unchecked. Removal retains the existing
confirmation and backend revalidation before recycling.

No SHA-256/encryption wording is exposed in this UI. Existing exact-duplicate
verification is unchanged. Different seasons/releases/encodes are still kept
separate. Scan/deletion waits while the owner Organizer or Merge is busy, and
the existing busy signals protect other file operations while duplicates run.

## Skipped reference-only features

No new filter/sort engine, select-all/invert operations, media-inspection action,
rollback feature, symlink/hardlink mode, extra root actions or fabricated drive,
studio/codec/bitrate statistics were added. Existing functionality and true data
are styled; unsupported example content is omitted.

## Files and validation

- `app/ui/merge_duplicate_style.py`: shared scoped styling and merge heading.
- `app/ui/pages/merge_page.py`: style hook using existing controls.
- `app/ui/pages/duplicate_page.py`: embedded presentation and owner busy checks.
- `app/ui/pages/organizer_page.py`: third-tab ownership and signal routing.
- `app/ui/organizer_style.py`: remove the old visible duplicate-review button.
- `app/ui/main_window.py`: embedded duplicate worker tracking/task navigation.
- `tests/test_organizer_reference_ui.py`: navigation/manual-scan/keeper/busy checks.

19 focused tests passed: reference UI (4), merge page (6), duplicate backend (3),
manual Organizer UI (6). Inspected merge and duplicate temporary-data renders,
including duplicate review at 1100×720. Render helper:
`data/merge_duplicate_visual.py`. No real library move or deletion was performed.
