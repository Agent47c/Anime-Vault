# Window sizing and Library status layout

Implemented 12 November 2026.

## Maximize and F11

- Corrected the Windows custom-caption maximize calculation. The retained native
  resize frame was being placed inside the available work area, leaving the
  visible app inset from its edges.
- Maximize now compensates for that resize frame using DPI-aware Windows frame
  metrics. The client fills the monitor work area; the Windows taskbar remains
  outside it. Monitor-relative coordinates also support negative monitor origins
  and taskbars on other edges.
- F11 retains the existing fullscreen toggle and restores the prior normal or
  maximized state when toggled again.
- Verified using a temporary native window, without opening the library:
  before the fix, maximize produced client geometry `(7, 7, 1906, 1018)` on a
  screen with a `(0, 0, 1920, 1032)` work area. After the fix, maximize and
  restored-maximize both produced `(0, 0, 1920, 1032)`. F11 produced
  `(0, 0, 1920, 1080)`.
- `scripts/window_layout_probe.py` reproduces the native sizing check. The
  monitor test is evidence for this Windows display, not a claim that every
  monitor/DPI arrangement was exercised physically.

## Status placement

- Hide the old bottom footer, including its streaming API indicator, last-scan
  text, connectivity badge and duplicate free-space display. Hidden status
  objects remain compatible with existing code; the streaming service itself
  is unchanged.
- Reuse the live connectivity and indexed-count labels beneath Library's
  All anime summary. The connectivity label keeps its click-to-recheck action
  and uses the Library's theme colors. It says status unchecked until a check
  has actually happened.
- The main summary now says `N anime`, without repeating the on-disk size. The
  indexed label says `N anime indexed`, without `Last scan just now`.
- Top-bar and Storage disk information remain available. Background-task banners
  and shutdown protection are unchanged.

## Header

- Widen each navigation tab's desired width by 12px while preserving the capsule
  centering, active colors, count badges and hover effects.
- Increase Quick Find's minimum/maximum widths to 180/260px before text scaling,
  compared with 100/170px. Keep the existing narrow-window second-row fallback.
- Use the existing three-line SVG list icon for the right-side actions menu.
  Suppress the extra native menu arrow and center the icon in its button. Menu
  commands remain unchanged.

## Verification

- New regressions cover frame compensation, wider centered navigation/search,
  menu-icon identity, narrow-window containment and Library status placement.
- The 42 existing focused checks passed with the loopback permission required
  by their existing VLC transport fixture. Seven sizing/status checks also passed.
- Rendered and inspected the complete 1920×1032 app using an empty temporary
  database with a synthetic anime. The footer was hidden; API/index status was
  beneath All anime; the header search was wider and the menu showed three lines.
- Full validation output: `data/shell-space-validation.log`.
- Compilation and all 481 isolated tests passed in 124.264 seconds. The 500-file
  scanner fixture's maximum heartbeat delay was 60.2ms.
- No user database or media files were changed by verification.
