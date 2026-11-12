# Simplified Find Download Files reference

Reference: `find download file page ui/code.html` and `screen.png`.

The native Qt page now groups season/source, title mapping, saved custom search,
fallback-title checkbox, editable query, exact source URL, progress and status in
one search panel. Search retains the existing Chrome-connected source workflow;
opening the page does not automatically start a search or download.

Result filters and the existing Show episode availability control share one row.
The coverage summary and optional availability cards appear above the result
table. The seven-column model remains virtualized, with full-title/reason tooltips,
checkbox selection, keyboard selection, sorting and conservative availability.
The title column uses remaining viewport space instead of a fixed oversized width.
At narrow widths, horizontal table scrolling keeps every column reachable.

A fixed bottom action area stays outside the content scroller. Match-confirmation,
paste and browser actions stay on the left; Missing Episodes and Review selected
downloads stay on the right. Buttons wrap without clipping at smaller window sizes.
All existing actions, including both match-confirmation entry points, are retained.
The literal ampersand in the confirmation label is escaped for Qt so it is not
displayed as a mnemonic underline.

No new provider, download profile, fake sync count, daemon/version label or network
latency is introduced from the mockup. Existing alias persistence, multi-file episode
assignment, uncertain-match confirmation and final review remain unchanged.

Changed code: `app/ui/pages/release_search_page.py`,
`app/ui/release_search_style.py`. Regression additions:
`tests/test_release_search_ui.py`.

Validation: 21 release-search/numbering/query tests passed. Rendered and inspected
the layout at 1450×1000 and 1100×720. Tests verify the fixed action bar, button
readability, coverage position, checkbox selection, custom-query persistence and
2,000 virtualized results without creating a widget per result.

All 21 download-experience regressions also passed, including a real local native
torrent-to-library fixture. That test required running outside the sandbox so its
loopback peer could bind normally. No user's actual downloads/media were changed.
