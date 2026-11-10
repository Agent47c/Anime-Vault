# Mouse-wheel scrolling fix

Implemented 11 November 2026 for the Rematch/list scrolling report.

## Causes and changes

- Native closed combo boxes and spin boxes consumed wheel input. In Rematch,
  moving the pointer over the wide local-season selectors could stop the page
  from scrolling, or change the selected local season instead.
- A shared wheel router now sends that input to the nearest scrollable ancestor.
  At the page edge it leaves the selector value unchanged. Menus, arrow keys,
  typed numbers and opened popup lists remain usable.
- Nested list/text/table viewports scroll themselves while they have room. At
  their boundary the parent page receives the wheel if it can move further.
- Item views use vertical pixel scrolling instead of whole-item jumps.
- Shared workflow bodies (including Rematch) now use SmoothScrollArea. Header
  and footer remain fixed. One existing animation handles wheel input; no
  background thread, per-row animation or repeated image loading is added.
- SmoothScrollArea previously accumulated its previous target even when the
  wheel reversed. It now starts the reversed movement from its current position.
  Touchpad pixel input remains native, dragging stops the animation, and reduced
  motion directly updates the scrollbar.

Files, matching choices, database records and download logic are unchanged.
The wheel over a closed selector intentionally scrolls the page rather than
changing the selector's value. Open it or use keyboard controls to change values.

## Changed implementation files

| File | Change |
| --- | --- |
| `app/ui/components/wheel_routing.py` | Shared editor/boundary routing and item-view scroll mode |
| `app/ui/theme.py` | Install the shared router once when applying the theme |
| `app/ui/components/workflow.py` | Smooth scrolling in shared workflow bodies |
| `app/ui/components/smooth_scroll.py` | Immediate reversal and reduced-motion handling |
| `tests/test_wheel_scrolling.py` | Six real Qt wheel-event regressions |

## Verification

The six focused regressions pass and cover:

1. Scrolling over a closed combo/spin box without changing its value, including
   upward movement and page boundaries.
2. Immediate reversal during an active smooth-scroll animation.
3. Reduced motion and touchpad pixel input.
4. Nested list scrolling and handoff at its lower boundary.
5. A populated Rematch body scrolling both ways over its season selectors.
6. Open combo popup scrolling without moving the surrounding page.

Tests use isolated fixture data and Qt's offscreen platform. Actual mouse-driver
behavior on the user's Windows desktop is not measured by the offscreen tests.

Final full validation: `python data/phase2_validate.py` passed all **291 tests**
and compile/check steps, exit code 0. Scanner heartbeat maximum was **45.1 ms**
for the 500-file fixture.
