# Edit season numbers and Choose episode reference screens

References: `edit season number ui screen/code.html` and `screen.png`, and
`choose episode page/code.html` and `screen.png`.

## Edit season numbers

- Centered editor over the existing navigation backdrop, with a scrolling body
  and fixed Cancel / Save numbering footer. The header reuses the decorative
  Details motif and accessible Close control.
- Release cards show real On disk / Metadata only status, inventory file count,
  complete release title and a selectable folder field with full-path tooltip.
- Centered number field and SVG up/down controls retain the existing 1–999 range,
  keyboard editing, repeatable numbers for season parts and `controls` mapping.
- The review checkbox still gates saving. Existing expected-release validation,
  background save, manual override persistence and busy-close guard remain.
- Files, paths, release IDs and history are not moved or rewritten by styling.

## Choose episode

- Full navigation page with title/series header, existing release-state filter
  on the right, compact download action, inventory status and availability notice.
- Uniform rounded Twilight Sakura blocks show only the episode/movie title and
  season/category. Hover, selection/focus and last-played coral accents are kept.
- The existing virtualized QListView/model remains: 2,000 rows do not create
  2,000 widgets. Inventory enumeration and cancellation remain in EpisodeWorker.
- Existing click-to-play, Enter playback, filters, download navigation and
  release-aware missing-episode notices are preserved.
- **Approved addition:** a fixed playback footer shows the current selection,
  read-only path with full tooltip and a Play button for the configured player.
  Keyboard selection updates it without launching playback; the button reuses
  the existing play/history handler. It disables when no episode is selected.
- Not added: watched/unwatched filters, scheduled placeholder blocks, file-info
  inspection, Ctrl+D, checksum claims or decorative server/version assertions.
  The user approved only the playback footer from the mockup additions.

## Changed files and validation

Presentation: `app/ui/episode_selection_style.py`,
`app/ui/dialogs/season_numbers.py`, `app/ui/pages/episode_page.py`.
Regression tests: `tests/test_episode_selection_ui.py`.

39 tests passed across new UI coverage, season numbering/query behavior and data
safety. They verify review-gated numbering, unchanged folder paths, footer
selection/play routing, release filtering and 2,000 virtualized blocks at 100%
and 130% text sizes in an 1100×720 window. Both screens were rendered offscreen
and visually compared with the supplied references. No real media was launched,
moved or deleted by validation.

A further 12 Details/navigation regressions passed alongside the three new UI
tests, for 51 distinct targeted tests overall. Changed Python modules compile.
