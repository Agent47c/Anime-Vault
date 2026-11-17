# Manga Brutalism Light — master screen contract

Latest user-approved Details arrangement (15 November): Notes takes the flexible
left section, watch status sits in the middle, and rating is right-aligned in
the same inset band. Use the entire available width and wrap on narrow windows.

User-approved poster frame correction, 15 November 2026: artwork has a thin
1px black inner outline followed by a 3px white outer border. Rounded corners,
existing shadow and hover behavior remain. This replaces the white-only frame.

The [visual recheck](MANGA_VISUAL_RECHECK.md) records the later cumulative-rating,
calendar shadow/TODAY and Details personal-band corrections, along with explicit
remaining fidelity differences. Add Custom Entry reuses the Edit Entry form.

## Original reference and precedence

The user identified `Light Theme (Manga Brutalism)` as the new design folder.
The light master is [Main Screen (Light Theme )](../../Light%20Theme%20%28Manga%20Brutalism%29/Main%20Screen%20%28Light%20Theme%20%29/),
containing the original `screen.png`, `code.html` and `DESIGN.md`.
An unchanged, checksum-verified reference copy is saved under
[design/references/manga-brutalism-light/main-v1](../../design/references/manga-brutalism-light/main-v1/).
The original user-supplied folder remains in place.

The main image is authoritative for appearance. The HTML contains leftover dark
neumorphic utilities and the design notes contain both light and dark tokens;
those do not override the supplied light image. Other screen folders in the
same collection do not authorize conflicting changes to this shell or its controls.
Follow [UI Design Guidelines](UI_DESIGN_GUIDELINES.md).

## Shared master elements

| Role | Light treatment / implementation |
|---|---|
| Canvas | Paper `#EEF0F5`; `app/ui/manga_style.py` |
| Raised surfaces | White, rounded geometry, bounded soft drop shadows |
| Inset / secondary surfaces | `#E2E5ED`; borders `#C4C9D4` |
| Main text | Ink `#111217`; secondary `#596175` |
| Primary action | Hot pink `#FF2E93`, black `#0A0A0A` label |
| Pink text on paper | Deeper `#C4005F` |
| Titles | Bundled Noto Serif; offline Inter body and existing JetBrains Mono metadata |
| Navigation | 94 px icon rail and 70 px search/action header; existing routes/menus |
| Hero | Light artwork scrims, serif title, resume/details/open-folder actions |
| Broadcasts | Seven cached day tiles with current-day accent and existing hover previews |
| Archive | Existing filter/count/sort/selection controls; seven titles on wide viewports, six on smaller ones |
| Footer | Real provider/index/storage and built-in downloader data; no fabricated transfer figures |

Reusable presentation modules: `app/ui/manga_style.py`,
`app/ui/components/manga_shell.py`, `app/ui/components/manga_hero.py`,
`app/ui/components/library_pagination.py`, `app/ui/manga_library.py`.
Existing models, cards, navigation and download/playback actions remain shared.

## Approved functionality and preserved differences

- The user approved **Library pagination** and **Full Calendar** in the clarification
  following delivery of this reference. Calendar uses cached broadcasts and local
  time, with month navigation and the existing release preview/detail action.
- Profile remains excluded under the earlier explicit user instruction.
- Keep the built-in torrent engine; the mockup's qBittorrent footer is illustrative.
- Keep English-title search behavior. Manga/hash search claims are not implemented
  because the backend does not provide them.
- Keep the existing week buttons, release strip, collection actions, refresh modes,
  keyboard access and native window controls even where omitted from the image.
- Use actual saved playback progress and local availability. Do not display the
  mockup's sample CRC, watched counts, studio/quality labels or transfer speeds as data.
- Sakura Dark, Sakura Light and Match Windows retain their own shell and layouts.
  Manga Light is an additional saved theme selection (`manga_light`).

## Scope

This phase implements the new main Library shell and shared light primitives.
Details, Edit Entry, Rematch and Updates use their supplied light references via
the shared `manga_pages.py` presentation module. Existing data/actions stay shared.
No new dark Manga variant has been supplied or implemented.

## Approved follow-up — 14 November 2026

The user explicitly authorized the Updates HTML's navigation animation as a
shared change, white collection tags, responsive seven/six-card Library pages,
and continuation through the four supplied workflow screens. This supersedes
the initial fixed six-card limit. The original main reference remains retained.

- Navigation expands from the master 94 px rail to the Updates HTML's 240 px.
  A fixed 94 px layout slot holds a sibling overlay: expansion covers the page
  instead of changing its geometry, card widths, scroll position or pagination.
  The latest correction anchors depth to the selected tab/tag: selected stays
  sharp, immediate neighbours have 0.65 px blur and 50% opacity, and farther
  controls remain faintly visible (at least 30% opacity; blur capped at 2.4 px). Hover/focus reveals
  an item temporarily without changing the anchor. Shrink remains bounded at 4%.
  Leaving restores the closed icon strip. Reduced motion/high contrast skip it.
- Seven cards fit when the archive viewport can accommodate seven 200 px cards
  plus six 20 px gaps (text scale increases the width requirement). Otherwise
  pagination uses six, with extra row wrapping on narrow layouts.
- Edit Entry keeps all existing fields; status and rating buttons synchronize
  with the original save fields. Selecting the dash clears the rating.
- References' sample IDs, checksum claims, qBittorrent stats and unsupported
  favorite/profile actions are not introduced. Existing extra update actions
  remain visible and wrap rather than disappearing to imitate a three-button row.
- No installer or executable is rebuilt during UI work without an explicit request.

### Follow-up verification

- Full regression run passed **548 tests**. After the overlay correction, all
  **nine Manga-focused tests** passed again, including content-geometry stability
  during expansion, seven/six-card resizing, blur falloff and reduced motion.
- Rendered the expanded overlay at 1920×1080 and confirmed that the cards and
  controls stay in place underneath it. Rendered all four workflow screens at
  1400×1000 and corrected clipped update labels and primary playback colors.
- Temporary test data and artwork were used; no personal library data or media
  was changed. Windows-specific DPI configurations still require device testing.

All five reference screens' depth/shadow treatments and remaining Qt fidelity
gaps are recorded in [Neumorphic reference analysis](NEUMORPHIC_REFERENCE_ANALYSIS.md).

## Verification — 14 November 2026

The follow-up [workflow and master-control update](MANGA_WORKFLOW_BATCH.md)
records the twelve additional references, approved controls, cached paired
shadows and 560-test validation on 15 November. The initial checks below remain
as a record of the first Library implementation.

- Full project checks passed: **545 tests**, including the existing workflows and
  six focused Manga tests. The final title-wrapping refinement was also rendered
  and checked with the focused suite.
- Rendered the Library at 1590×1600 and 1280×800, and Full Calendar at 1400×900,
  using an isolated temporary database and generated demonstration artwork.
  Checked the light shell, title wrapping, calendar alignment, and pagination.
- Tested runtime switching back to Sakura, search synchronization, six-card
  reuse, cached calendar ownership/month navigation, and 130% text layout.
- Publication guard passed: no guarded secret patterns, private runtime files,
  oversized files, or missing primary documentation links.
- Visuals follow the master while retaining the existing native title bar,
  extra feature controls and actual artwork/data. Pixel-perfect equivalence and
  every Windows DPI configuration have not been established.
- No personal database, media files, installer or installed application was
  modified by these checks. This is a source UI update; no installer was built.

Font sources and licenses: [Inter](https://github.com/google/fonts/tree/main/ofl/inter)
and [Noto Serif](https://github.com/google/fonts/tree/main/ofl/notoserif), bundled
with their SIL Open Font Licenses in `assets/fonts/`.
