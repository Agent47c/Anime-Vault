# Detail navigation and rematch performance

Implemented 11 November 2026.

## Findings

Profiling the local library found synchronous detail preparation rebuilding all
series groups twice and opening repeated SQLite connections on the GUI thread.
Opening one detail page took about 342 ms; the synchronous post-rematch detail
rebuild took about 303 ms in that profiling run, before any later library refresh.
The old Back path retained complete hidden detail widget trees in the page stack.
Repeated opens could accumulate these pages and their signal connections.

After moving data preparation out of the event loop, one layout build still
created enough controls in a single callback to leave a roughly 160 ms heartbeat
gap in the first local navigation check. Layout construction was then staged.

## Changes

- MainWindow opens an asynchronous DetailModal immediately, with a loading label.
  No network operation is required to display the locally cached details.
- `app/ui/detail_data.py` prepares a consistent SQLite snapshot in an app-owned
  IOTask. Series resolution, member seasons, episode coverage, poster image
  decoding/cache repair and last-played file checks run there.
- Season lookup accepts the already resolved series, avoiding the duplicate
  whole-library grouping pass. Existing callers and lookup behavior remain valid.
- The UI consumes the prepared snapshot through the existing read-only refresh
  context. Only Qt widget creation and QPixmap painting remain on the GUI thread.
- Detail layout creation yields between independent sections through queued
  timer steps. Updates are batched until the complete layout is ready.
- Post-rematch, grouping, manual-numbering, edit, Locate and season-deletion detail
  refreshes use the asynchronous path. Redundant immediate poster/data reloads
  before the complete rebuild were removed.
- Detail pages are disposable navigation pages. Back, close or navigation away
  releases their widget trees and restores the existing library. Child rematch,
  edit and review pages can still return to their parent details.
- A generation token rejects outdated/closed-page results. Result snapshots are
  closed after rendering or rejection. Active availability work is interrupted
  on close; data workers remain app-owned until safely finished.
- Calendar availability checking begins once the initial details have loaded.
- RefreshWorker prepares LibraryIndex alongside its database/artwork snapshot.
  Library refresh and default grouped metrics reuse this index rather than
  rebuilding the series groups on the GUI thread.

Matching validation, episode identities, file operations, download behavior and
confirmation steps are preserved. No library data was edited for the timing run.

## Measurements

`data/navigation_latency_check.py` used the local 230-series grouped library at
1500×900 with offscreen Qt, three open → post-rematch refresh → Back cycles.
Artwork network requests were disabled; the post-rematch callback was exercised
without actually changing metadata or downloading it.

| Measurement | Recorded range |
| --- | --- |
| Open/navigate call return | 11.5–13.7 ms |
| Post-rematch callback return | 0.1–0.2 ms |
| Back call return | 18.8–26.7 ms |
| Maximum event-loop heartbeat interval over the run | 95.2 ms |
| Stack pages remaining after each Back | 1, the original library |

The callback measurements indicate responsiveness; they are not the total time
to fetch AniList metadata, finish a rematch transaction or render all new details.
Results depend on library size, hardware, Windows display scale and concurrent
work. Offscreen checks do not guarantee identical physical-display latency.
Local detailed evidence: `data/navigation-latency.json`.

## Changed files and tests

| File | Purpose |
| --- | --- |
| `app/ui/detail_data.py` | Worker-side detail preparation |
| `app/ui/pages/detail_modal.py` | Async loading, staged layout, generation/close handling, refresh reuse |
| `app/ui/main_window.py` | Async library/calendar entry points |
| `app/ui/refresh.py` | Prepare the library index in the refresh worker |
| `app/ui/pages/library_page.py` | Reuse the prepared index |
| `app/db.py` | Optional resolved-series input and snapshot-local grouped result reuse |
| `tests/test_detail_navigation_performance.py` | Five regressions |

The focused tests verify background-thread preparation with a running heartbeat,
quick open/rematch callbacks, repeated Back cleanup, leaving before load completes,
snapshot release, unchanged records, one series-resolution pass, and reuse of the
prepared library index without reconstructing it in the UI.

The fully loaded asynchronous page was rendered and visually inspected at
1280×900 (`data/async-details.png`) with Segoe UI registered in the offscreen
test. Titles, poster, metadata, controls, synopsis, rating and notes remain present.

Final `python data/phase2_validate.py`: **302 tests passed**, compile/check steps
passed, exit code 0. Scanner heartbeat maximum: **50.0 ms** for 500 files.
