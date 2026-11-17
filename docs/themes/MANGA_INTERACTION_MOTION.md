# Manga Light interaction motion

15 November 2026

These are shared controls, rather than page-specific variants. The user's
15 November screenshot correction supersedes the earlier dark hover/lift pass:
keep faces light and make hover feel recessed. No dark hover fill is approved.

## What the states mean

- **Resting:** the existing raised face and tactile shadow.
- **Hover/focus:** the raised outer shadow fades into the cached inset shadow.
  The face stays at its original pixel size and position. Fractional hover
  transforms caused dark edge fringes and bright corner slivers and were removed
  on 16 November. Light controls retain dark text; pink actions retain black text.
- **Pressed:** the face drops one pixel and shrinks around its centre. An inset
  shadow makes the button look compressed into the surface. Releasing restores
  the hovered state, or the resting state when the pointer has left.
- **Disabled Previous:** remains recessed and does not animate or become clickable.

## Implementation and coverage

`components/tactile_motion.py` owns bounded 230 ms hover animations using the
requested cubic Bezier control points `(0.34, 1.56, 0.64, 1)`. Click compression
is immediate. Paint transforms leave layout geometry and action signals intact.

| Control | Hover | Press |
| --- | --- | --- |
| Add Anime / Resume and other installed primary actions | Pink face, soft inset blend, stable face | +1 px, 0.97 scale, inset |
| Refresh / Details / Folder / sort / selection / view / pagination | Light face, soft inset blend, stable face | +1 px, 0.98 scale, inset |
| Sidebar navigation and collection tiles | Light face, inset depth, immediate tooltip | 0.95 scale, inset |
| Installed filter chips and calendar cards | Light face, inset blend, border highlight | +1 px, 0.97 scale, inset |

The sidebar keeps its existing selected-distance blur and hover reveal. Calendar
cards reuse their existing preview logic; the new paint transform replaces the
old Manga position animation so the two lifts do not add together. Sakura's
existing calendar motion is retained.

Primary actions keep Jet Black text on hot pink. Secondary faces stay white or
paper grey with dark text in every interaction state. Painted filter chips keep
their existing count badges. Shadow rendering is a Qt visual equivalent, not a
claim of pixel-identical CSS filters.

The hero no longer has a parent graphics effect around buttons that have their
own animated effects: nested Qt effects could leave the button faces visible
while their labels disappeared. Button text/icons and callbacks are preserved.

## Performance and accessibility

- Shadow/glow masks are generated once and reused as small nine-slice tiles.
- Control shadows use the same 8-pixel corner shape as the face. Inset shading
  is clipped inside the border, with softened highlights and dark tones.
- Combo boxes keep native painting and keyboard interaction. A reusable,
  input-transparent sibling supplies depth without capturing their popup window.
- Menus, combo lists and tag popovers reserve shadow margins inside their popup
  bounds and use one rounded border. Native Qt popup surfaces retain their Python
  painter for the lifetime of the popup and release it when the popup is destroyed.
- Each actionable menu/combo option has its own fine dark border and small raised
  shadow, with spacing between options. Selected options use the recessed state.
  Rows keep their native model or QAction and callbacks; no row widgets are added.
- Windows translucent popups use frameless popup flags before showing, with the
  native shadow disabled. This preserves popup dismissal while avoiding the black
  rectangle that appeared around the list on Windows.
- Native combo/menu fade and slide are disabled only while Manga is active.
  Combo containers are styled while hidden and stay invisible through the final
  geometry and backing-store paint pass, then appear at full opacity. Closing or
  reopening invalidates older presentation passes. This prevents a clipped,
  black intermediate frame without changing the finished popup design.
- Dropdown setup runs after the new family/scale/contrast properties are set.
  Existing hidden containers are refreshed on theme switches. Scoped page themes
  delegate popup styling to the shared dropdown handler rather than copying base
  page QSS over it; otherwise the legacy blue selected-row fill reappears around
  the custom option face. Cached styles also verify the actual stylesheet.
- Only the active controls animate; no continuous timer or whole-page animation.
- Existing widget reuse, card limits, navigation and click handlers remain intact.
- Reduced motion suppresses translation/scaling; static press feedback remains.
- High contrast bypasses the decorative effects.
- Hiding a control or losing focus clears its pressed state. Effects and their
  event filters share ownership so replacing themes does not retain old controllers.

## Validation

Four focused tests check unchanged geometry, exactly one action on click,
hover/press transforms, reduced motion, cached glow reuse and effect reuse/cleanup.
The earlier complete project check passed 563 tests before this correction.
The corrected motion and Library suites were rerun; the Library/calendar and
separate resting/hover/pressed control states were rendered with isolated data.
No installer build or personal database/media changes were performed.
