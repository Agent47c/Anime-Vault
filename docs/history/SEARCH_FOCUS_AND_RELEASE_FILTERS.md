# Search focus, boxed filters and release-query repair

## Search-result navigation

Settings → Appearance & Accessibility → **Focus search results automatically**.
The setting is enabled by default and saved as `preference:search_results_focus`
using the existing preference store. Turning it off takes effect without restart.

- Find Download Files: after an explicit Search releases / Enter search completes,
  focus and the enclosing page scroll move to the result table. Empty results
  reveal the explanatory status instead. Background availability refreshes do not
  trigger this behavior.
- Rematch: manually submitted searches reveal/focus their result area; automatic
  initial searches do not. If the user has since typed another query, the old
  result does not take focus from that unfinished input.
- Group seasons/arcs: Search / Enter reveals the list; live filtering keeps the
  typing cursor in the field.
- Library and Home Quick Find: Enter moves to the displayed result area. Text
  changes retain the existing live filtering and keep the input focused.
- Release discovery/timelines: explicit Check updates reveals the returned content;
  loading cached filters/pages does not steal focus.

The shared deferred helper ignores hidden/deleted pages, disabled targets and
active popovers. It never activates another window, opens a result, checks a row,
starts playback or confirms an import/download.

## New Anime Releases tag boxes

Genres, themes and formats open reusable boxed-choice popovers instead of narrow
text dropdown lists. Select multiple options; both the popover and trigger display
the selected count. All genres/themes/formats clears that category. Selected names
remain available in tooltips and accessible descriptions.

Premiere newest/earliest, English title and Most popular use readable single-choice
boxes. Popovers support keyboard focus, Escape, outside-click dismissal and Done /
Close, and stay within the available screen. They reuse current theme and size
tokens. The adult-content preference and cache-only page-opening policy remain.

The existing discovery function accepts single strings or multiple approved
values. Multiple selections use AniList `genre_in`, `tag_in` and `format_in`
arguments before pagination. Canonical value ordering keeps cache keys stable.
Official argument reference: https://docs.anilist.co/reference/object/page .

## Last 30 Days and Announced repair

The empty recent-release results were reproduced with read-only public API queries.
`format:null` made AniList return zero recent releases, while the same date bounds
with the unused format argument omitted returned 20. Queries now omit unselected
optional filters and unused variables entirely. Explicit adult blocking remains.

After the fix, both Last 30 Days and Announced returned HTTP 200, no GraphQL errors
and 20 results in a live diagnostic. Announced is therefore retained: it is supported
by AniList's NOT_YET_RELEASED status, without requiring a known premiere date.

The UI distinguishes never-fetched filters from saved empty results. Click **Check
updates** once for a previously empty period to replace its old cached response.
It does not automatically go online on each filter change or delete existing cache.
Diagnostic requests did not write the user's release cache or library.

## Files and verification

- `app/preferences.py`, `app/ui/pages/settings_page.py`: persisted default-on switch.
- `app/ui/search_navigation.py`: shared guarded focus/scroll helper.
- Search integrations: `release_search_page.py`, `rematch_dialog.py`,
  `group_series_page.py`, `library_page.py`, `main_window.py`, `home_header.py`,
  and `release_news_page.py`.
- `app/ui/components/tag_picker.py`: reusable boxed multi/single-choice popovers.
- `app/core/release_news.py`: multiple filters and omitted-null query fix.
- Tests: `tests/test_search_focus_and_tags.py` and `tests/test_release_news.py`.

Eight targeted focus/filter tests pass, covering default/persisted settings,
no focus theft from hidden pages, explicit-search focus, no auto-checking, live
typing, rematch initialization, selected counts and list-valued provider arguments.
Other targeted release/search/preferences/grouping and Home regressions passed.
Rendered and inspected the tag, sort and selection-count UI. Live API diagnostics
confirmed the query fix separately from mocked regression tests.

Final validation: `python scripts/check.py` passed compilation and **448 tests**
in 94.226 seconds. The 500-file scanner heartbeat fixture reached 45.1ms maximum.
Validation log: `data/search-focus-validation.log`.
