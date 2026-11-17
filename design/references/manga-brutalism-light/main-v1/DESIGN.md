---
name: Manga Brutalism
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
  tertiary: '#5fe14a'
  on-tertiary: '#013a00'
  tertiary-container: '#1ba80e'
  on-tertiary-container: '#013200'
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
  tertiary-fixed: '#7cfe64'
  tertiary-fixed-dim: '#5fe14a'
  on-tertiary-fixed: '#012200'
  on-tertiary-fixed-variant: '#035300'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
  bg-dark: '#0A0A0A'
  bg-light: '#F7F7F7'
  surface-dark: '#141414'
  surface-light: '#FFFFFF'
  surface-2-dark: '#1F1F1F'
  surface-2-light: '#EFEFEF'
  border-dark: rgba(255, 255, 255, 0.14)
  border-light: rgba(0, 0, 0, 0.16)
  border-strong: '#FFFFFF'
  accent-pink: '#FF2E93'
  on-pink: '#0A0A0A'
  pink-text-dark: '#FF4DA6'
  pink-text-light: '#C4005F'
  status-ok-dark: '#5ED6A0'
  status-ok-light: '#0E7A4D'
  status-warn-dark: '#FFD23F'
  status-warn-light: '#7A5200'
  status-error-dark: '#FF8A80'
  status-error-light: '#B3261E'
typography:
  headline-hero:
    fontFamily: Noto Serif
    fontSize: 48px
    fontWeight: '800'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-hero-mobile:
    fontFamily: Noto Serif
    fontSize: 36px
    fontWeight: '800'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-title:
    fontFamily: Noto Serif
    fontSize: 22px
    fontWeight: '700'
    lineHeight: 28px
  body-default:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 21px
  body-bold:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '700'
    lineHeight: 21px
  label-uppercase:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.06em
  code-mono:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  margin: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

# DESIGN.md — Ink, Paper & Hot Pink (Manga Brutalism)

A high-contrast design system rooted in manga printing, Japanese ink, and sharp brutalist accents for desktop applications.

---

## 1. Core Philosophy & The Golden Rule

### 🚨 The Golden Rule of Hot Pink
- **Text on a pink fill is ALWAYS BLACK (`#0A0A0A`).** 
  - White text on `#FF2E93` only achieves a ~3.5:1 contrast ratio, failing WCAG AA standards.
  - `#0A0A0A` on `#FF2E93` achieves >10.5:1 contrast ratio, ensuring AAA accessibility.
- **Pink as typography on light surfaces:** Standard hot pink fails on light paper. When pink is rendered as text on a light background, use the deeper `#C4005F` token (`pink-text-light`).

---

## 2. Design Tokens

### 2.1 Color Tokens
| Token | Dark (Ink) | Light (Paper) | Usage Context |
|---|---|---|---|
| `bg` | `#0A0A0A` | `#F7F7F7` | Base application canvas / window ground |
| `surface` | `#141414` | `#FFFFFF` | Primary cards, sidebars, modals |
| `surface-2` | `#1F1F1F` | `#EFEFEF` | Secondary panels, elevated containers, input backgrounds |
| `border` | `rgba(255, 255, 255, 0.14)` | `rgba(0, 0, 0, 0.16)` | Razor-thin structural ink lines and dividers |
| `border-strong` | `#FFFFFF` | `#0A0A0A` | Inverted selection outlines, high-contrast borders |
| `text` | `#FFFFFF` | `#0A0A0A` | Primary typography, titles, active tabs |
| `text-2` | `#C2C2C2` | `#454545` | Secondary text, subtitles, captions |
| `text-3` | `#8F8F8F` | `#606060` | Subdued metadata, file paths, labels |
| `accent-pink` | `#FF2E93` | `#FF2E93` | Primary action fills, progress meters, urgent stamps |
| `on-pink` | `#0A0A0A` | `#0A0A0A` | **Strict Rule:** Text over any hot pink fill |
| `pink-text` | `#FF4DA6` | `#C4005F` | Pink typography rendered over background/surfaces |
| `focus-ring` | `#FFFFFF` | `#0A0A0A` | Accessible keyboard focus outline |
| `status-ok` | `#5ED6A0` | `#0E7A4D` | Success, healthy connection, sync OK |
| `status-warn` | `#FFD23F` | `#7A5200` | Warnings, re-indexing, pending reviews |
| `status-error` | `#FF8A80` | `#B3261E` | Validation errors, destructive actions, missing files |

### 2.2 Application Notes & Anti-Slop Rules
1. **No Gradients:** Solid flat fills only. No purple-to-pink or blue-to-pink gradients.
2. **Hard Shadows Only:** Absolutely zero soft, blurred drop shadows. Use hard offset shadows (`box-shadow: 2px 2px 0px #000000` or `4px 4px 0px #0A0A0A`) if depth is needed.
3. **Crisp 1px Borders:** Always use the `border` token for structural lines to emulate crisp manga inks.
4. **Resting State Flatness:** Resting cards and containers have 0 elevation. Only hover states or floating dialogs take hard offset shadows.

---

## 3. Typography & Geometry

### 3.1 Font Stacks
- **UI Font:** `"Zen Kaku Gothic New", "Inter", "Segoe UI Variable", -apple-system, sans-serif`
- **Display & Kanji:** `"Shippori Mincho B1", "Noto Serif JP", serif`
- **Monospace & Code:** `"JetBrains Mono", "Cascadia Code", monospace`

### 3.2 Type Scale
- `hero`: 44px – 52px (Weight: 800)
- `title`: 20px – 24px (Weight: 700)
- `body`: 14px (Weight: 500, line-height 1.5)
- `caption / label`: 12px (Weight: 600, uppercase, letter-spacing: 0.06em)

### 3.3 Corner Radii
- `radius-sm`: `4px` (Hanko stamps, badges)
- `radius-md`: `8px` (Inputs, filter pills, dropdowns)
- `radius-lg`: `12px` (Buttons, cards, modal frames)
- `radius-pill`: `9999px` (Status badges)

---

## 4. Component Patterns

### 4.1 Buttons
- **Primary Action (Only 1 per region):**
  - Fill: `#FF2E93` (Hot Pink)
  - Text: `#0A0A0A` (Jet Black), 14px Bold
  - Radius: `12px`, Height: `44px`
  - Shadow: Hard 2px black offset on resting (`2px 2px 0 #000`), pressed translates `+1px`
- **Secondary Action:**
  - Fill: `#1F1F1F` (Dark) / `#EFEFEF` (Light)
  - Border: `1px solid rgba(255, 255, 255, 0.14)`
  - Text: `#FFFFFF` (Dark) / `#0A0A0A` (Light)
- **Destructive Action:**
  - Outlined with `#FF8A80` (Dark) / `#B3261E` (Light) border and matching error text.

### 4.2 Inverted Selection (Manga B&W Filter Chips)
- Active chips invert completely: White background (`#FFFFFF`) with Jet Black text (`#0A0A0A`) in Dark mode.
- Inactive chips: Transparent background with `border` outline and `#C2C2C2` text.

### 4.3 Hanko Stamp Badges
- Tilted `-3deg`, 4px radius, `#FF2E93` fill with bold `#0A0A0A` text and hard offset shadow.
