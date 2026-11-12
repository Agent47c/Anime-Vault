# Find Download Files — reference UI implementation

11 November 2026. Reference files: `file download page/code.html`, `DESIGN.md`
and `screen.png`.

## Navigation and retained features

**Simplified checked-file confirmation:** Check one or more release rows, then
Confirm highlighted match (or Confirm anime & episodes). Checked releases take
priority; no title click is required. If nothing is checked, the highlighted row
is used. The centered dialog now has shared release type and season, followed by
each selected filename and its own **Attach as episode(s)** field. Enter `6` for
one file and `7` for the other, or `6, 7` / `1-12` for an actual multi-episode file.
Invalid and overlapping assignments are blocked before saving. The Confirm match
button itself is approval; the extra confirmation checkbox and separate first/
last/encoder-title inputs are removed. Optional remembering uses each filename's
extracted alternate title. Confirmed rows stay checked; Review selected downloads
performs the existing final submission step. This supersedes the older form
description below.

**Direct download start:** Once download review is confirmed, the torrent starts
without a second Choose files step. The old start-paused setting is retired and
ignored even if saved previously. Existing paused entries can use Resume without
being recreated. Resume retains an explicitly chosen subset, or enables all
torrent files when there was no selection. Choose files remains optional; batches
can contain additional episodes, so review their coverage before confirming.
No existing paused transfers are silently resumed just by opening the app.

**Confirm anime & episodes:** Highlight a search result and click this action
(or the existing Confirm highlighted match). A centered dialog names the anime
and torrent, lets you set release type, season and first/last episode, and requires
the title/numbering confirmation checkbox. First 5 / last 6 attaches episodes 5
and 6. Confirmation itself never starts a download; review remains required.

Optionally edit the proposed encoder title and tick **Remember this title for
this anime and season**. Future search classification recognizes the normalized
title only within this series/season. An explicitly different season, ambiguous
episode coverage, special/movie format or episode beyond the verified aired
boundary still requires review. This does not change internet metadata, filenames
or general scanner matching. The custom search text remains separate from this
explicitly confirmed download alias.

**Saved custom searches:** Enter your preferred text in the search field and
click **Use Custom One** beside Use title. The exact text is saved for this
series and selected season (continuing/unknown is a separate context), selected
in title mapping, and restored next time. No extra uploader/resolution/season
tokens are appended. Choose a normal title and click Use title to restore the
normal default; the custom option remains available. Empty saves are rejected.
This uses the existing persistent application-state store, without a schema
migration or change to anime display titles, filenames, matching or downloads.

Open an anime → **Find Download Files**. Existing Updates download shortcuts
also open the same search destination. Back returns through the existing
navigation stack; confirmation/review drawers return to the live search page.

The presentation now groups the existing controls into:

- Title, anime context and Release Search tag.
- Bordered search panel with season and source selectors, saved title-language
  mapping, Use title, alternative-title fallback, editable query, Search releases,
  Cancel search, exact read-only source URL and search progress.
- Result filters and sorting, followed by a virtual table with checkboxes,
  release title, episodes, quality/group, size, seeders, source and availability.
- Rounded, theme-colored availability pills and selected rows. Long titles keep
  their full tooltip; compact windows allow horizontal table scrolling.
- Show episode availability, existing coverage summary, and virtual episode cards
  displaying the existing episode identifier and availability status.
- Wrapped action panel: Confirm highlighted match, Paste magnet/torrent,
  Open source in Chrome, Download Missing Episodes and Review selected downloads.
  Review displays the current number of checked releases.

## Presentation and performance

- Reuses bundled Plus Jakarta Sans and JetBrains Mono, Twilight Sakura tokens,
  coral actions, rounded panels and themed scrollbars. Light/high-contrast colors
  follow the existing shared theme; no new theme setting was added.
- Search controls and availability checkboxes have antialiased indicators with
  explicit ticks. Result checkboxes retain mouse and Space-key behavior.
- Result rows and episode cards are delegate-painted, without one widget per
  result/episode. A 2,000-result regression confirms bounded widget count.
- The outer page scrolls at smaller heights. Action controls wrap rather than
  disappearing. Existing search workers, cancellation and stale-result guards
  are retained; opening the page starts no download or network search.

## Deliberately skipped reference-only features

No Aria2 engine/indicator, fabricated connectivity/free-disk readings, copy-URL
button, invented batch/alternative-group statuses, or additional metadata fetching
was introduced. Availability cards use only the existing coverage data; no fake
local paths, resolution, sizes or release claims are displayed.

No backend matching, source parsing, download submission, identity, database or
file-operation logic changed in this UI pass. Search and review confirmations
continue using the existing implementations.

## Files and validation

- `app/ui/pages/release_search_page.py`: layout and presentation wiring.
- `app/ui/release_search_style.py`: scoped theme, painted checkboxes/rows/cards.
- `tests/test_release_search_ui.py`: four UI/virtualization regressions.
- `data/release_search_visual.py`: temporary-database render helper; no real
  files or downloads touched. Captures inspected at 1600×1300 and 1100×720.
- Changelog and feature/navigation index updated.

18 focused tests passed: four new UI checks, nine season/query tests, and five
download-experience checks covering availability, batches/pending transfers,
continuing-series boundaries, duplicate revalidation and nested review navigation.
Native/live torrent downloading was not exercised by this presentation validation.
