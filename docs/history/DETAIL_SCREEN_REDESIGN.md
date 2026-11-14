# Anime Detail Screen and startup flicker — 11 November 2026

## Scope and design reference

The implementation uses `Anime Detail Screen/code.html`, `DESIGN.md`, and
`screen.png`. These reference files are unchanged. Details shares Home's Twilight
Sakura colors and fonts, with a larger rounded poster, a layered information
panel, metadata chips, coral playback control, amber rating buttons, personal
status/notes, and a full-width separated season table.

The user approved the embedded episode list with thumbnails, descriptions, and
watch dates. Profile/avatar, encoding/audio **filters**, RSS catch-up, and physical
disc/rip registration are excluded. The existing Quality column remains because
it is an existing feature, rather than the proposed new filter.

## Startup flicker fix

The base poster creates its metadata label without a parent. Home called
`show()` before adding that label to its layout. On Windows, each label therefore
briefly became a native captioned top-level window and then disappeared when
reparented. Building many posters repeated this flash and could steal focus.

`HomePosterCard` now parents the label through its layout **before** showing it.
The regression observes QApplication Show events while creating eight posters
and asserts that no top-level window is shown. No sleeps, hidden startup windows,
or changes to the native title-bar/maximize behavior were introduced.

## Existing behavior preserved

- Primary Play/Resume and its menu: resume, first episode, Choose episode, player
  settings. The existing episode-block page remains available.
- Open folder, Edit title, Rematch, and Find Download Files remain visible.
- **More** contains View API JSON, Group with another series, Episode and movie
  check, and Combine episode folders / Use separate seasons when applicable.
- Edit season numbers remains above the season table.
- Watch status, all ten ratings, note saving, per-season Play/Match/Delete/Locate,
  announced-release labeling, and Delete files confirmation remain connected to
  their existing handlers.
- All synopsis paragraphs remain accessible by scrolling, with the existing
  one-line trailing space. Text-size changes recalculate its height.
- No database schema, existing API route, scanner matching rule, or file-move/
  deletion policy was changed. Episode listing reuses the existing EpisodeWorker
  inventory/identity logic.

## Embedded episode list

- A QListView and painted delegate render a bounded number of visible rows rather
  than creating one widget per episode. A regression covers 2,000 rows.
- The release selector shows all local seasons/movies or one release. Unreleased
  episodes are not invented as missing list entries.
- Each row contains the season/episode label, episode title, thumbnail or clear
  fallback, description, recorded date, and Play/Resume. Hover exposes the full
  description/title/filename. Enter activates playback; the right-hand Play area
  is clickable. The last-played item has a coral outline.
- Watch dates come from stable Episode-ID history. They are labeled **Last
  played**, since launching a file does not prove the entire episode was watched.
  No history displays **No watch date recorded**.
- Local thumbnails are extracted with FFmpeg, when installed on PATH, into
  `data/episode-thumbnails`. There is no encoding operation or media-file rewrite.
  File identity, size, and modification time form the cache key. FFmpeg receives
  CREATE_NO_WINDOW on Windows and a six-second timeout, so preview work does not
  introduce console flashes.
- Descriptions/titles use Jikan only when a verified release episode number and
  matching MAL release ID are available. Unknown mappings get a clear fallback
  rather than a description from a different season.
- Metadata requests are serialized and throttled to at most one per 1.1 seconds,
  with bounded connection/read timeouts. Successful descriptions cache for seven
  days; failed metadata/frame lookups wait six hours before retrying. Offline
  mode still uses saved descriptions.
- Only visible previews are requested, in batches of at most three. At most 48
  thumbnails remain in the list's memory cache. Enumeration, hashing of cache
  keys, frame extraction, cache writes, image decoding, and HTTP run off the UI
  thread. Leaving the page cancels queued work; an in-flight bounded operation
  finishes safely. Returning from a child drawer reuses the inventory.

The description endpoint is documented in the
[official Jikan API reference](https://docs.api.jikan.moe/#tag/anime/operation/getAnimeEpisodeById).

## Changed implementation files

- `app/ui/components/home_poster.py`: parent metadata labels before showing.
- `app/ui/home_style.py`: register Windows' installed Yu Gothic face for Japanese
  fallback without distributing Windows font files.
- `app/ui/pages/detail_modal.py`: responsive Details composition and preserved
  action wiring; theme hook, high-DPI poster and episode panel lifecycle.
- `app/ui/detail_style.py`: shared-theme Details stylesheet.
- `app/ui/components/detail_episodes.py`: virtual list, lazy workers, cancellation,
  preview rendering, accessible descriptions and playback integration.
- `app/core/episode_preview.py`: stable history lookup and bounded preview caches.
- `app/ui/icons.py`: vector playback-menu chevron.
- `tests/test_home_screen.py`: native-window-flash regression.
- `tests/test_detail_screen.py`: preview caches, release identity, cancellation,
  virtual list, and preserved/excluded actions.

## Verification and limits

Focused checks: 17 Home tests, 8 Details-screen tests, 11 UI regressions, 5 Details
navigation/performance tests, 4 window-chrome tests, and 1 startup-import test.
All 46 focused checks pass, including the 130% text-size layout check. Compilation
and `git diff --check` also pass.
The historical full-suite native torrent/process failures recorded in
`HOME_LIBRARY_REDESIGN.md` are not claimed resolved by this UI work.

Visual checks use isolated fixture records and saved artwork; preview descriptions
in the visual fixture are explicitly marked as sample data. The real app does
not use those fixtures. Captures include 1280/1920/1100 widths, dark/light themes,
and the lower episode section. Offscreen rendering is not a full real-monitor
Windows DPI test. Native startup behavior should also be checked by running
`python main.py` in the user's normal Windows session.
