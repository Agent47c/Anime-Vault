# Settings UI Screen implementation — 11 November 2026

Source: `setting ui screen/code.html`, `DESIGN.md`, `screen.png`.

## Separate categories

The reference's panels are applied to their respective category pages; they are
not combined into a long settings document. Sidebar groups now match the reference:

- Core System: Appearance & Themes; Library Roots & Scanning; Naming & Organization;
  Metadata & AniList.
- Automation & Ingestion: Watchers & TXT Lists; Downloads & Sources; Media Player.
- Maintenance: Database & Backups.

Naming and Metadata are separate pages containing their existing controls only.
Library Roots & Scanning contains roots and scanning preferences, with roots first.
Watchers contains subscriptions and watched-list import. Downloads contains setup,
download engine configuration and sources. Database contains backup/export/restore
and maintenance. Appearance and Media Player retain their existing controls/cards,
including accessibility, application behavior, PotPlayer and cached player icons.

Original category indices 0–5 remain stable for existing in-app links. Naming and
Metadata use indices 6 and 7; their visual sidebar order follows the reference.
The sidebar itself can scroll on short windows. Category changes switch pages
without automatic scrolling between unrelated settings.

## Presentation changes

- Settings & Configuration title, compact grouped sidebar, coral active indicator,
  reference card/background/border colors and smaller panel headings.
- Existing theme-aware and shared button styles retained, including light/high
  contrast support. Buttons remain content-sized and related actions share rows.
- Download configuration now sits inside a bordered Download engine panel.
  Release group/quality and download/upload limits are paired side by side.
  Destination input and Choose destination are on one row. The Chrome actions
  remain on one compact row. All original controls, signals and save handlers stay.
- No sample source URLs, extension IDs, folder entries, connection states or
  daemon/database-health claims are copied from the mockup.
- Reference-only Filter settings, Discard changes and Save All controls are not
  added. Existing automatic-saving preferences and explicitly saved download/source
  forms keep their actual behavior; no fake staging/save workflow is introduced.

## Changed files and checks

- `app/ui/settings_style.py`: category navigation, reference styles and download
  form arrangement.
- `app/ui/pages/settings_page.py`: two additional UI categories and metadata routing;
  matching download form surface.
- `app/ui/settings_sections.py`: place naming rules in their own category.
- Settings regressions and existing category-count expectations updated to eight.

14 focused tests passed: reference settings (5), download/settings polish (8),
existing settings/download persistence (1). The new checks verify that only the
selected category is visible, Naming and Metadata do not leak into Scanning, old
links remain stable, and paired download fields share their intended rows.
Temporary-database wide/compact renders were inspected, including Watchers and
Downloads. Render helper: `data/settings_reference_visual.py`.
No scanner/API/download/database backend behavior or real library files changed.
