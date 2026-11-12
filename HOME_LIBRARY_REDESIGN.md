# Home Library redesign — 11 November 2026

## Approved scope

Reference: `Home Library Screen/code.html`, `DESIGN.md`, and `screen.png`.
The folder contains DESIGN.md rather than a README. The reference files remain
unchanged. The user excluded the profile/avatar and approved playback progress,
time remaining, application-wide Space play/pause and live download badges.

## Presentation

- Twilight Sakura surfaces and coral/amber accents, capsule navigation, compact
  Quick Find, storage chip, cinematic hero and responsive five-column poster grid
  at typical 1280px windows. Wider windows use additional columns.
- Bundled Plus Jakarta Sans and JetBrains Mono, with their OFL licenses.
- One full-width seven-day calendar row, filter counts, sort and grid/list controls,
  provider/user rating badges and batch actions.
- Navigation is centered on the whole window using equal left/right columns;
  narrow windows and large text move the centered capsule onto its own row.
  Quick Find has explicit readable text and placeholder colors in both themes.
- Poster checkboxes stay hidden until the actions menu's double-check
  **Select multiple anime** action or a poster's **right-click → Select** is used.
  Space on a focused poster also enters selection mode. Clicking a card in that
  mode toggles selection; **Clear Selection** leaves the mode. Compact-list
  checkboxes follow the same mode, and new-release cards stay synchronized.
- Schedule tiles show the anime title for one release, **N anime releases** for
  multiple releases, and **No releases** for none. Hover and click previews retain
  all entries and navigation to details. Preview rows use theme colors, aligned
  thumbnails, bounded/elided text, full-title tooltips, fixed row heights and
  screen-edge positioning.
- Poster lift/hover behavior and calendar hover previews are preserved.
- Light/high-contrast modes use corresponding accessible tokens. Large-text
  headers move navigation onto a second row; filters/batch controls wrap.

## Preserved features missing from the reference

- Previous/This/Next navigation and saved calendar history remain available;
  each selected week occupies one row, as requested in the latest design review.
- New seasons and episodes remains available when updates exist.
- Collections (including Dropped and Watched, removed), Add anime, watched TXT
  import and both local/internet Refresh actions are in the Home actions menu.
- Storage review is accessible from the storage chip. All six destinations remain.
- Compact list view, sorting/filtering, selection and existing deletion review
  behavior remain. Batch Delete retains the existing safe per-title review flow;
  it does not introduce automatic bulk deletion.
- Detail/rematch/import/edit/Organizer/Downloads workflows, title bar, task banner,
  tray/close protections and status bar remain. Other pages retain their layouts.

## Approved playback additions

VLC and MPV launched by Anime Vault receive private player-control arguments.
VLC uses a loopback-only HTTP interface with a random per-launch password; MPV
uses a unique local named pipe (Unix socket off Windows). No profile/account UI
or Anime Vault streaming service was added by this change.

The hero shows real elapsed/remaining time when available. Progress is saved by
stable Episode ID using existing app state and episode-history position fields,
and survives app-controlled path changes. Supported-player launches resume the
saved position; near-complete episodes restart from the beginning. Unknown timing
is labelled unavailable instead of estimated from filenames. Default/custom/MPC
players continue launching normally, with no unsupported control claims.

Space toggles the app-owned player while Anime Vault is active, across its pages.
It does not intercept typing, focused buttons/selection controls, menus or key
repeat, and it is not an operating-system-wide hotkey. The hero playback button
also toggles a connected player. F11 retains the existing fullscreen behavior.

Player communication and progress writes run in bounded workers. Polling is
approximately once per second while active; idle polling avoids database reads.
Progress writes are throttled to five seconds. Media changes are checked before
recording progress so another file cannot overwrite the original episode's data.
The last few seconds of unsaved progress may be lost on abrupt termination.
Switching playback retires the previous app-owned player in the background after
checking its media and saving progress. A player whose media changed independently
is left alone.

Live download labels reuse the built-in queue and its monitor; they do not add
automatic downloads. Posters show transfer progress while a transfer is active,
otherwise local episode coverage. Calendar labels explicitly say **Series DL**
because a series transfer is not proof that a specific scheduled episode is in
that torrent. Failed/paused transfers retain meaningful text labels.

## Implementation

- `app/ui/home_style.py`: Home tokens, theme-aware stylesheet and bundled fonts.
- `app/ui/components/home_header.py`: Home navigation, search/actions/collections.
- `home_hero.py`, `home_poster.py`, `home_day.py`, `flow_layout.py`: Home components.
- `app/core/home_facts.py`: read-only coverage/download presentation facts.
- `app/core/playback.py`: stable-identity progress and VLC/MPV adapters.
- `app/ui/playback.py`: bounded workers and guarded Space handling.
- Existing Library, MainWindow, refresh/download monitors, theme scopes and player
  launch entry point connect the adapters. The executable build includes fonts.
- `tests/test_home_screen.py`: 16 added regressions. The existing grid-width test
  now reads actual layout margins rather than assuming the previous design's 28px.

## Verification

- Sixteen focused Home/player tests pass: navigation/action preservation, avatar
  exclusion, checkbox selection, grouped download badges, typing-safe Space,
  stable progress through a file move, resume arguments, invalid data, media
  identity checks, idle behavior, wrapping and hidden-page theme updates, centered
  navigation, selection-mode entry/exit, schedule counts and preview alignment.
- Transport tests exercise real local HTTP and Windows named pipes.
- A hidden installed-VLC test using a generated 30-second silent sample verified
  duration 30s, advancing position 1s, pause and resume. No user video was opened.
- MPV's protocol/transport is tested; an installed MPV binary was not available.
- Screens rendered at 1280, 1920 and 1100 widths, light/dark, and 130% text:
  `data/home-1280-dark.png`, `home-1920-dark.png`, `home-1100-dark.png`,
  `home-1280-light.png`, `home-1100-large.png`. These use isolated fixture records;
  the application uses actual library data and never the mockup's sample counts.
- Offscreen rendering does not establish identical behavior on every physical
  monitor or Windows DPI setting.

## Primary implementation references

Before the latest calendar/selection review, full validation passed 318 tests.
The latest changes pass **16 Home tests + 4 calendar tests**; the **17 scanning
tests** also pass separately (500-file heartbeat maximum 44.9 ms). Compile and
diff checks pass. Fresh full-suite runs did not complete cleanly: Windows native
process aborts (3221226505), and sandboxed loopback torrent-transfer failures,
prevent a current whole-suite pass claim. No download/backend behavior was
changed to bypass those checks.

Latest visual review includes `data/home-default-1280.png` (checkboxes hidden)
and `data/home-release-preview.png` (two complete, aligned clickable release rows),
alongside the dark/light and large-text renders listed above.

- [MPV JSON IPC manual](https://mpv.io/manual/stable/)
- [VideoLAN HTTP request commands](https://github.com/videolan/vlc/blob/master/share/lua/http/requests/README.txt)
- [VideoLAN HTTP interface implementation](https://github.com/videolan/vlc/blob/master/share/lua/intf/http.lua)
- [Plus Jakarta Sans source/license](https://github.com/google/fonts/tree/main/ofl/plusjakartasans)
- [JetBrains Mono source/license](https://github.com/google/fonts/tree/main/ofl/jetbrainsmono)
