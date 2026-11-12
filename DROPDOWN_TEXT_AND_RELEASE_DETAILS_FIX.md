# Complete dropdown labels and automatic Release Details

## Shared dropdown repair

The shared row delegate painted 14px text but inherited its width estimate from
a different font. Qt also kept popups near the narrow trigger's width, after which
the delegate deliberately elided the label. This cut off ordinary setting/sort
choices and sometimes left short menus with an unnecessary scrollbar.

The common dropdown styler now:

- Measures all option labels with the actual scaled painting font.
- Reserves space for existing icons, the current-item check and scrollbar/frame.
- Expands the popup independently of the closed field's width.
- Keeps the popup within the available screen, placing it above the field when
  that offers more room.
- Wraps screen-limited long text into variable-height rows instead of eliding it.
- Computes popup height from row heights and real frame space. Short menus show
  every option; long menus retain vertical scrolling without horizontal clipping.
- Retains the original model, values, keyboard controls, disabled states, current
  selection and handlers. Existing native QMenus continue their own content sizing.

This covers the supplied examples: section placement, close behavior, scan schedule,
watch status, Library sorting and broadcast-state menus, plus other shared combos.
Rendered and inspected Placement and Broadcast menus with complete text and no
unnecessary vertical scrollbar. The Placement popup expanded from a 170px trigger
to 248px in the fixture. Checks cover 100% and 130% text sizes and a simulated
320px-wide screen requiring wrapped text.

## Release Details behavior

Clicking a release fetches that selected anime's missing timeline automatically.
It uses the clicked AniList ID and saves the result through the existing cache.
Subsequent visits reuse it; Check updates remains the explicit refresh action.
Discovery's cache-only opening/filter behavior remains unchanged.

The status says Loading release details while loading. The temporary local lookup
connection now closes explicitly after reading. Tests verify both the core cache
behavior and that opening the page for ID 1996 loads that ID without clicking
Check updates.

## Changed files and checks

- `app/ui/components/dropdowns.py`: measured popup geometry and wrapped rows.
- `app/core/release_news.py`: fetch-on-cache-miss for a selected timeline.
- `app/ui/pages/release_news_page.py`: clear loading label and connection cleanup.
- `tests/test_dropdown_text_fit.py`: full labels, screen bounds, short-menu height,
  wrapping, selected release identity and automatic first load.

The targeted dropdown, release, menu, preference and scrolling tests passed.
Full isolated validation (`python scripts/check.py`) passed compilation and all
453 tests in 94.218 seconds. The scanner heartbeat check measured 40.1 ms maximum
for its 500-file fixture. Full output: `data/dropdown-fit-validation.log`.
Fixtures use temporary databases; no real library or media records were reset.
