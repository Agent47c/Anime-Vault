---
name: Twilight Sakura
colors:
  surface: '#14121d'
  surface-dim: '#14121d'
  surface-bright: '#3a3744'
  surface-container-lowest: '#0f0d17'
  surface-container-low: '#1c1a25'
  surface-container: '#201e2a'
  surface-container-high: '#2b2834'
  surface-container-highest: '#36333f'
  on-surface: '#e6e0f0'
  on-surface-variant: '#dfbfc2'
  inverse-surface: '#e6e0f0'
  inverse-on-surface: '#312f3b'
  outline: '#a78a8c'
  outline-variant: '#584143'
  surface-tint: '#ffb2bc'
  primary: '#ffb2bc'
  on-primary: '#670023'
  primary-container: '#ff6584'
  on-primary-container: '#6a0024'
  inverse-primary: '#b0284b'
  secondary: '#ffb86c'
  on-secondary: '#492900'
  secondary-container: '#794700'
  on-secondary-container: '#ffb86c'
  tertiary: '#c9c3df'
  on-tertiary: '#312d44'
  tertiary-container: '#9c96b1'
  on-tertiary-container: '#332f45'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffd9dd'
  primary-fixed-dim: '#ffb2bc'
  on-primary-fixed: '#400012'
  on-primary-fixed-variant: '#8f0935'
  secondary-fixed: '#ffdcbc'
  secondary-fixed-dim: '#ffb86c'
  on-secondary-fixed: '#2c1600'
  on-secondary-fixed-variant: '#683c00'
  tertiary-fixed: '#e6defc'
  tertiary-fixed-dim: '#c9c3df'
  on-tertiary-fixed: '#1c192e'
  on-tertiary-fixed-variant: '#48445b'
  background: '#14121d'
  on-background: '#e6e0f0'
  surface-variant: '#36333f'
typography:
  display:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-code-lg:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: -0.01em
  label-code-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0em
  label-code-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.25rem
  gutter-compact: 0.75rem
  margin: 2rem
  margin-compact: 1.25rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system delivers an intimate, cinematic, and calm late-night atmosphere engineered specifically for modern desktop media management and playback. It evokes the feeling of a quiet sanctuary: a dusk-lit studio room, warm lamplight reflecting off dark matte hardware, and the understated elegance of contemporary Japanese editorial design.

The aesthetic marries restrained modern minimalism with physical warmth. It avoids the harsh optical fatigue of pure black surfaces and rejects saturated neon cyberpunk clichés or generic purple-blue gradients. Instead, the interface relies on deep velvet tones, tactile micro-borders, atmospheric coral focal points, and golden amber accents to guide attention effortlessly across dense media libraries and full-screen video surfaces.

## Colors

The palette is tuned specifically for low-light room environments to prevent eye strain during extended viewing sessions.

- **Canvas & Backdrops:** `#15131E` serves as the primary canvas baseline—a deeply warm twilight slate that grounds the application without the severe contrast of `#000000`.
- **Surfaces & Cards:** Layered containers use `#201D2C` (velvet charcoal) paired with structural hairline perimeter borders (`#2F2B40`). Elevated floating capsules and search controls sit on `#1E1B29` with borders tinted to `#353047`.
- **Primary Accent (Sunset Sakura Coral):** `#FF6584` is reserved for high-priority interactive touchpoints: active playback scrubbers, watch-resume indicators, active tab indicators, and primary action triggers.
- **Secondary Accent (Warm Lantern Amber):** `#FFB86C` is reserved for community ratings, VIP/curated indicators, and contextual status pings.
- **Typography & Icons:** Primary text utilizes warm off-white (`#F5F3F8`) to maintain WCAG AAA compliance against charcoal grounds. Supporting meta text uses lavender-gray (`#9E98B3`), and passive administrative details scale back to muted twilight gray (`#6B6580`).

## Typography

The typographic hierarchy implements an intentional division of labor:

1. **Plus Jakarta Sans:** Drives all expressive and semantic interface elements. Its geometric baseline and soft terminal curves yield a modern, warm reading experience across series titles, synopses, and navigation headings.
2. **JetBrains Mono:** Dedicated to utility metrics and technical metadata. Timestamps, resolution tags (e.g., `1080p`, `4K HEVC`), episode counters (`EP 08 / 12`), audio codec channels, and download sizes must always render in this monospace face to maintain tabular visual balance and structural precision.

## Layout & Spacing

The layout is structured around an adaptive desktop media grid:

- **Structure:** A fixed left icon/utility strip (64px to 72px) anchor, paired with a dynamic multi-column content canvas that flexes based on aspect ratio requirements (e.g., vertical anime poster ratio `2:3` vs horizontal episode thumbnails `16:9`).
- **Margins & Gutters:** Grid layouts enforce a consistent `1.25rem` gutter between media cards to give poster art room to breathe. Top and side canvas padding is anchored at `2rem` on wide desktop viewports (`>= 1440px`), compressing to `1.25rem` when the window shrinks below `1024px`.
- **Rhythm:** Internal component spacing follows a 4px sub-grid (`0.25rem` steps). Metadata stacks inside media cards use `space-xs` (4px) to `space-sm` (8px), preventing descriptive elements from detaching visually from their parent artwork.

## Elevation & Depth

Visual hierarchy does not use high-cast drop shadows. Depth is achieved via **tonal layering and hairline containment**:

1. **Level 0 (Main Canvas):** `#15131E` base layer.
2. **Level 1 (Structural Surfaces & Cards):** `#201D2C` velvet charcoal, bound by a crisp, 1px solid hairline border of `#2F2B40`.
3. **Level 2 (Floating System UI & Overlays):** Elements such as the top capsule search bar and floating contextual controllers sit on `#1E1B29` with a `#353047` hairline border, backed by a soft, warm ambient diffusion: `box-shadow: 0 12px 32px -4px rgba(10, 8, 16, 0.65)`.
4. **Level 3 (Modal Sheets & Media Player Chrome):** Semi-opaque backdrop diffusion utilizing `backdrop-filter: blur(20px)` at 85% opacity of `#15131E`, with inner glow borders (`inset 0 1px 0 0 rgba(255, 255, 255, 0.05)`).

## Shapes

The design system applies a disciplined dual-radius philosophy:

- **Cards & Panes:** Standard content containers, modal dialogs, and video preview tiles strictly adhere to a **12px (`rounded-md` / `0.75rem`)** corner radius, establishing a tailored, modern frame for visual media.
- **Controls & Capsules:** Navigational tabs, floating search bars, status badges, playback transport controls, and interactive pill triggers use a complete capsule radius (**9999px**), providing contrast against the rectangular media grid.

## Components

### Buttons
- **Primary Action (Watch / Resume):** Background `#FF6584`, foreground `#15131E`, font weight 600. Hover transitions to `#FF7A95` with a subtle outer glow: `box-shadow: 0 0 16px rgba(255, 101, 132, 0.35)`. Border radius is 9999px.
- **Secondary / Ghost Button:** Background `#201D2C`, border 1px solid `#2F2B40`, text `#F5F3F8`. Hover background shifts to `#282437` with border color lighting up to `#3F3956`.

### Top Capsule Bar
- Floating navigation capsule centered along the top axis.
- Background `#1E1B29`, border 1px solid `#353047`, border-radius 9999px. Internal items (quick search, profile avatar, active filter chips) are bounded within a compact height (44px) with subtle inline dividers (`#2F2B40`).

### Media Cards
- Base surface `#201D2C` with 12px border radius and 1px `#2F2B40` border.
- Poster image maintains a 2:3 vertical or 16:9 horizontal aspect ratio with top corners rounded to 11px to sit cleanly inside the border.
- Unwatched/Resume indicator: A 3px horizontal bar positioned directly at the bottom edge of the image container using `#FF6584` over a track of `rgba(255, 255, 255, 0.1)`.

### Chips & Metadata Badges
- **Technical Specs (`1080p`, `DUB`, `SUB`, `HEVC`):** Rendered in JetBrains Mono (`label-code-sm`). Background `rgba(32, 29, 44, 0.8)`, border 1px solid `#2F2B40`, text `#9E98B3`, padding 2px 6px, radius 4px.
- **Score / Rating Chip:** Background `rgba(255, 184, 108, 0.12)`, border 1px solid `rgba(255, 184, 108, 0.25)`, text `#FFB86C`, radius 9999px, typography JetBrains Mono (`label-code-sm`).

### Input Fields
- Background `#1A1724`, 1px solid `#2F2B40`, radius 8px, text `#F5F3F8`, placeholder `#6B6580`. Focus state shifts the border directly to `#FF6584` with an accompanying subtle focus ring (`0 0 0 1px #FF6584`).

### Playback Scrubber & Volume Slider
- Base track: `#2A263A`, height 4px, radius 9999px.
- Filled track: `#FF6584`.
- Thumb: 12px circular handle, `#F5F3F8`, visible on scrubber hover or active drag, eliminating persistent UI clutter during video playback.