---
name: Ink, Paper & Hot Pink
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#3a3939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#e2bdc7'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#a98891'
  outline-variant: '#5a3f48'
  surface-tint: '#ffb0c9'
  primary: '#ffb0c9'
  on-primary: '#640034'
  primary-container: '#ff4799'
  on-primary-container: '#58002d'
  inverse-primary: '#b90066'
  secondary: '#c6c6c7'
  on-secondary: '#2f3131'
  secondary-container: '#454747'
  on-secondary-container: '#b4b5b5'
  tertiary: '#ffb0ce'
  on-tertiary: '#64003a'
  tertiary-container: '#fb4aa3'
  on-tertiary-container: '#570032'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffd9e3'
  primary-fixed-dim: '#ffb0c9'
  on-primary-fixed: '#3e001e'
  on-primary-fixed-variant: '#8e004c'
  secondary-fixed: '#e2e2e2'
  secondary-fixed-dim: '#c6c6c7'
  on-secondary-fixed: '#1a1c1c'
  on-secondary-fixed-variant: '#454747'
  tertiary-fixed: '#ffd9e5'
  tertiary-fixed-dim: '#ffb0ce'
  on-tertiary-fixed: '#3e0022'
  on-tertiary-fixed-variant: '#8c0054'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display:
    fontFamily: Noto Serif
    fontSize: 3.5rem
    fontWeight: '700'
    lineHeight: 4rem
    letterSpacing: -0.03em
  headline-lg:
    fontFamily: Noto Serif
    fontSize: 2.25rem
    fontWeight: '700'
    lineHeight: 2.75rem
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Noto Serif
    fontSize: 1.75rem
    fontWeight: '600'
    lineHeight: 2.25rem
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Noto Serif
    fontSize: 1.25rem
    fontWeight: '600'
    lineHeight: 1.75rem
  title-lg:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: '600'
    lineHeight: 1.5rem
  title-md:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: '600'
    lineHeight: 1.375rem
  body-lg:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: '400'
    lineHeight: 1.5rem
  body-md:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.25rem
  body-sm:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '400'
    lineHeight: 1rem
  label-lg:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '600'
    lineHeight: 1.125rem
    letterSpacing: 0.02em
  label-md:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '600'
    lineHeight: 1rem
    letterSpacing: 0.04em
  label-sm:
    fontFamily: Inter
    fontSize: 0.6875rem
    fontWeight: '700'
    lineHeight: 0.875rem
    letterSpacing: 0.08em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  margin: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style
The design system channels the graphic velocity, discipline, and tactile starkness of serialized manga print culture translated directly into an unapologetic, performance-first desktop software application. Rejecting generic OS desktop idioms, it treats the screen canvas as physical print paper, ink washes, and mechanical screentones punctuated by an electric pop-culture shock.

### Aesthetic Foundation
- **Editorial High-Contrast Brutalism & Manga Craft:** Pure structural geometry, razor-sharp 1px to 2px structural ink lines, and absolute tonal separation.
- **Physical Print Metaphors:** Screentone dot halftones (kept strictly under 12% opacity) replace soft gaussian blurs; authentic kanji watermarks at 6% opacity add subtle compositional weight without impeding legibility.
- **Iconoclastic Punctuation:** A singular spot color—Hot Pink—shatters the monochrome spectrum for high-priority user interventions, focal states, and reading progression.
- **Tactile Authenticity:** Traditional *hanko* validation stamps applied at a strict -3 degree tilt with hard, un-blurred 2px cast offsets for status validation.

### Emotional Demeanor
Authoritative, fast, curated, and obsessive. The interface feels like handling an archival graphic compilation that executes desktop operations with zero latency and unwavering structural clarity.

## Colors
The color architecture relies on uncompromising contrast. It eschews gradients, colored glows, and atmospheric drop shadows entirely. Depth is achieved exclusively through stepped tonal planes, razor-thin borders, and inverse values.

### Dark Mode Palette (Default)
- **Canvas Base (`bg`):** `#0A0A0A` (Deep archival ink)
- **Primary Panel (`surface`):** `#141414` (Dense cell tone)
- **Elevated Panel (`surface-2`):** `#1F1F1F` (Offset card container)
- **Ink Border (`border`):** `rgba(255, 255, 255, 0.14)` (Precision frame line)
- **Text Tiers:**
  - `text`: `#FFFFFF` (Primary title & high-emphasis text)
  - `text-2`: `#C2C2C2` (Secondary captions & body metadata)
  - `text-3`: `#8F8F8F` (Subdued hints, column titles, shortcuts)

### Light Mode Palette
- **Canvas Base (`bg`):** `#F7F7F7` (Uncoated pulp paper)
- **Primary Panel (`surface`):** `#FFFFFF` (Bleached plate)
- **Elevated Panel (`surface-2`):** `#EFEFEF` (Recessed tray)
- **Ink Border (`border`):** `rgba(0, 0, 0, 0.16)` (Graphic register line)
- **Text Tiers:**
  - `text`: `#0A0A0A` (Primary copy)
  - `text-2`: `#454545` (Secondary metadata)
  - `text-3`: `#606060` (Tertiary captions)

### The Electric Spot Accent & Selection System
- **Spot Accent Fill (`#FF2E93`):** Reserved exclusively for active playback, primary action triggers, and progress trackers. Text rendered over a `#FF2E93` fill is strictly locked to `#0A0A0A` (pure black). Never use white text over hot pink.
- **Pink Text on Dark Surfaces (`#FF4DA6`):** When hot pink is applied as typographic color against dark surfaces (`#0A0A0A`, `#141414`, `#1F1F1F`), use `#FF4DA6` to maintain WCAG AAA compliance.
- **Inverted Selection Principle:** Default active row, navigation rail, and tab selections use inverted monochrome: pure `#FFFFFF` background with `#0A0A0A` text in dark mode; pure `#0A0A0A` background with `#FFFFFF` text in light mode.
- **Hero Scrim:** Only linear vertical masking from `#0A0A0A` to transparent `rgba(10, 10, 10, 0)` is permitted behind title graphics. No diagonal, ambient, or tinted gradients are allowed.

## Typography
Typographic discipline pairs the literary cadence of classic editorial manga with the sharp, utilitarian density of an elite desktop workspace.

### Font Hierarchy
- **Editorial Display & Chapter Titles:** `Noto Serif` (with fallback to traditional Mincho serifs). Delivers authoritative literary cadence across hero banners, volume headers, and modal chapter labels.
- **Application Interface & Metadata:** `Inter` (with pairing to Zen Kaku Gothic New for CJK glyphs). Neutral, unyielding, and ultra-crisp at high DPI, maximizing data density and numeric alignment.
- **Kanji Composition:** Watermark kanji glyphs sit behind section headers at 6% opacity, oversized (300%–500% scale), cropped along panel borders to function as textural structural landmarks.

## Layout & Spacing
Designed for desktop screen densities and fixed multi-pane productivity layouts, the system behaves like a dynamic manga storyboard page.

### Desktop Layout Architecture
- **Sidebar / Navigation Rail:** Fixed width at `240px` or collapsed icon rail at `64px`, locked flush against the left canvas frame with a `1px` border delimiter.
- **Grid Structure:** Fluid 12-column masonry grid across content regions with uniform `1rem` (`16px`) gutters.
- **Split-Screen Manga Reader / Inspector Panels:** Right-hand metadata drawers snap to fixed `320px` or `400px` widths.
- **Canvas Margins:** Outer padding defaults to `1.5rem` (`24px`), anchoring the content comfortably inside window frames.

## Elevation & Depth
Elevation is rendered strictly through tonal planes, mechanical screentone textures, and architectural border offsets. Soft drop shadows, colored ambient glows, and glass blurs are completely forbidden.

### Depth Mechanics
1. **Tier 0 (Window Canvas):** Base dark `#0A0A0A` or base light `#F7F7F7`.
2. **Tier 1 (Panels & Rails):** `#141414` surface bounded by a crisp 1px border (`rgba(255, 255, 255, 0.14)`).
3. **Tier 2 (Cards & Active Shelves):** `#1F1F1F` surface bounded by a 1px border.
4. **Tier 3 (Floating Menus & Command Palette):** `#1F1F1F` surface with a 2px high-contrast structural outline (`#FFFFFF` in dark mode, `#0A0A0A` in light mode) paired with a hard, un-blurred 4px offset shadow (`box-shadow: 4px 4px 0px #000000`).

### Screentones & Mechanical Textures
- **Halftone Screentones:** Patterned dot overlays used to define secondary empty states or panel headers. Strict ceiling of 12% opacity.
- **Hanko Stamps:** Status indicators (e.g., "COMPLETED", "CANON", "ARCHIVED") use a rectangular double-border stamp tilted strictly at `-3deg`, anchored with an uncompromising 2px solid, un-blurred black offset shadow.

## Shapes
Geometry is disciplined and tightly controlled. Rather than uniform pillowy shapes, corners reflect purposeful mechanical precision:

- **Form Inputs & Tags/Chips:** `8px` (`rounded-sm`) for compact desktop ergonomics.
- **Interactive Action Buttons:** `12px` (`rounded-md`) providing distinct focal click targets.
- **Major Window Panels & Shelves:** `18px` (`rounded-lg`) framing artwork and list modules.
- **Status Badges & Episode Progress Pills:** Full pill radius (`9999px`) for singular metadata items.

## Components

### Buttons
- **Primary Action:** Solid Hot Pink (`#FF2E93`) background, `#0A0A0A` (pure black) bold text, `12px` border radius, no border. On hover, background shifts to `#FF4DA6`. On click/active, scale down by 0.98.
- **Secondary Action:** Transparent background, `1px` solid border (`rgba(255, 255, 255, 0.14)` in dark mode), `#FFFFFF` text. On hover, inverse monochrome triggers: background becomes `#FFFFFF` and text becomes `#0A0A0A`.
- **Destructive Action:** Deep crimson wash background with `1px` solid `#FF2E93` outline and `#FF4DA6` text.

### Chips & Filter Tags
- **Default State:** Background `#1F1F1F`, border `1px` solid `rgba(255, 255, 255, 0.14)`, text `#C2C2C2`, radius `8px`.
- **Selected State:** Inverse monochrome fill (`#FFFFFF` background, `#0A0A0A` text, 0px border).

### Cards (Manga / Anime Entries)
- Framed in `#141414` with a `1px` ink border. Cover art is displayed flush with top-corner radii.
- **Episode Progress Tracker:** A needle-thin (3px) bar at the base of the card thumbnail. Completed portions fill with `#FF2E93`, unread portions remain `#1F1F1F`.
- **Kanji Stamp Overlay:** Top right corner holds the canon/status hanko badge tilted at `-3deg`.

### Form Controls & Inputs
- **Text Field:** Height `36px`, background `#141414`, `1px` border, text `#FFFFFF`, radius `8px`. Active focus state drops the subtle border and applies a 2px solid `#FFFFFF` border (or `#FF2E93` when validation triggers).
- **Checkboxes & Radios:** Sharp square check boxes (with `4px` subtle radius); unchecked shows `1px` border with empty interior; checked state fills completely with `#FFFFFF` and shows an inked `#0A0A0A` checkmark glyph.

### List Rows & Data Tables
- Row height `44px`. Alternating rows do not use zebra striping; division is achieved via a hairline 1px border-bottom (`rgba(255, 255, 255, 0.06)`).
- **Hover Row:** Tonal shift to `#1F1F1F`.
- **Active/Selected Row:** Full inverse monochrome treatment (`#FFFFFF` background, text shifted to `#0A0A0A`, hot pink progress ticks retained intact).