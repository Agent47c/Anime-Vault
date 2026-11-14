# Rematch, season numbering and download search

Implemented 2026-11-11 for the reported Iruma-kun, MASHLE and truncated
Rematch screenshots.

## What changed and how to use it

### Full-page Rematch and complete names

Open Library → anime details → Rematch (or a season's Match season action).
Normal rematching now fills the main content area and has Back/Cancel controls.
English/display names, Romaji and native aliases wrap rather than being cut off
with an ellipsis. Important season/part suffixes remain part of the displayed text.
The body scrolls while the confirmation action stays accessible in its footer.

The importer's selection-only match picker remains a drawer. Existing multi-release
selection, local-season mapping, announced-release rules, review confirmation,
search cancellation and artwork previews are preserved.

### Correct season numbers

The old metadata-only numbering used insertion/selection order. Selecting Season 3
before Season 2 could therefore label them S2 and S3 respectively.

Numbering now uses explicit evidence such as `Season 4`, `2nd Season`, `S03`, or
`第2期`. If a title lacks a number, an unambiguous available prequel chain can
identify its place relative to the root release. Movies do not increment the TV
season counter. A `Part 2` or cour is not automatically treated as Season 2.
Conflicting or insufficient evidence remains unverified, shown as **S?**.

For manual correction: Details → seasons section → **Edit season numbers**.
Choose a number for each release, acknowledge the review checkbox and Save
numbering. Duplicate numbers are allowed for split parts of the same season.
Manual choices are stored per season and respected by later metadata upserts and
automatic repairs. An edit is rejected if its release snapshot changed while the
editor was open. Saving runs in a worker and a database transaction.

This editor applies to seasonal series. Continuing-series mode (such as One Piece)
keeps its existing continuous episode workflow.

Only the season number changes. File/folder names, physical paths, provider IDs,
episode identities, watch history, notes and ratings are not rewritten.

### Repair of the reported library entries

A backup was created before the local correction:
`data/backups/library_backup_20261111_013030_d9682c03.db`.

| Series | Release title | Old label | Corrected label |
| --- | --- | --- | --- |
| Iruma-kun | Season 2 | S4 | S2 |
| Iruma-kun | Season 3 | S2 | S3 |
| Iruma-kun | Season 4 | S3 | S4 |
| MASHLE | Base release | S2 | S1 |
| MASHLE | Season 2 | S1 | S2 |

All five affected rows were metadata-only entries. The repair explicitly skips
local folders, local video inventories, on-disk rows and manual overrides. It
verified that every other field in each affected row retained its original value.
Detailed local evidence: `data/season-number-repair.json`.

### Editable download searches

Details → **Find Download Files** now shows:

1. The series/season and website selectors.
2. A **Search title** selector containing available English, Romaji (Japanese in
   Latin letters), native Japanese, release-specific and alternate titles.
3. **Use title** to build a readable query with the existing saved uploader and
   quality preferences. Title selection also fills it automatically.
4. An editable query field. Users can change any words, numbers or group tags.
5. A read-only, copyable **Search URL** preview showing the website URL with that
   query encoded into it.
6. **Search releases** or **Open source in Chrome**, using the same visible query.

The explicit primary query is not silently rewritten. Optional **Try other saved
titles if this query has no results** is off by default; enabling it permits up to
three additional distinct title queries. Search status reports the query used.
Empty queries do not start hidden automatic searches. Season changes retain a
manually edited query; Use title can deliberately replace it.

Existing result filters, availability checks, release confirmation, file selection,
download review and built-in torrent queue are retained. No downloads start from
changing a title or previewing its URL.

## Implementation files

| File | Responsibility |
| --- | --- |
| `app/core/season_numbering.py` | Evidence-based inference, conservative metadata repair, transactional manual overrides |
| `app/core/anilist_client.py` | Apply shared numbering to traversed provider releases; preserve movie types |
| `app/core/matching.py` | Use verified numbers rather than insertion order during rematch |
| `app/core/series_grouping.py` | Use shared numbering for announced catalog releases |
| `app/db.py` | Preserve manual numbers during upserts; sort unverified seasonal rows last |
| `app/ui/dialogs/season_numbers.py` | Reviewed season-number editor |
| `app/ui/pages/detail_modal.py` | Editor entry point and unverified S? labels |
| `app/ui/dialogs/rematch_dialog.py` | Full-page mode and complete wrapping result names |
| `app/ui/dialogs/drawer.py` | Support full-page workflows without native drawer sizing |
| `app/ui/navigation.py` | Embed full-page Rematch in the content stack |
| `app/core/download_queries.py` | Available title choices and readable default query generation |
| `app/core/download_discovery.py` | Exact primary query, explicit alternates and query reporting |
| `app/ui/pages/release_search_page.py` | Language/title controls, editable query and matching browser URL |
| `tests/test_season_numbers_and_queries.py` | Nine focused regressions |
| `All Feature and their Navigation.md`, `CHANGELOG.md` | Updated navigation and change record |

## Verification

- Nine focused tests cover out-of-order selections, known title patterns, unknown
  parts, movie handling, conservative repairs, persistent manual overrides, the
  editor acknowledgement, full-width/full-name Rematch, language choices and exact
  browser/search queries.
- Rendered and visually inspected 1280×900 full-page Rematch and download search,
  plus the 560×900 season editor. Artifacts: `data/full-rematch.png`,
  `data/download-query.png`, `data/season-number-editor.png`.
- Rendering uses an isolated fixture database and offscreen Qt. It verifies layout;
  it does not establish real website availability or replace Windows display-scale
  testing. A system font without Japanese glyph coverage may render the decorative
  Japanese text as boxes in this test environment.
- The validation suite uses isolated databases and local loopback torrent fixtures;
  no public downloads are needed for these tests.
- Final `python data/phase2_validate.py`: **284 tests passed**, compile/check steps
  passed, exit code 0. Scanner heartbeat maximum **40.1 ms** for 500 files.
