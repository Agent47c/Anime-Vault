# Preserved Sakura theme family

The current full visual design is preserved under the Git tag
`sakura-ui-baseline-2026-11-14`. The tag records all source, layouts, style helpers,
controls, fonts and reference assets; it does not contain personal databases or
runtime caches.

Settings names:

- **Sakura Dark** — the existing warm dark design.
- **Sakura Light** — the existing light design.
- **Sakura · Match Windows** — automatically selects the existing light/dark mode.

Existing saved preference IDs (`dark`, `light`, `system`) remain unchanged, so
users keep their selected mode. Naming this family does not change its visual
styles, functionality, navigation, data or API behavior.

## Before adding Neo Manga

The new design will be a separate visual family, starting with its supplied light
version. Preserve Sakura's entire presentation, not just its colors. Use shared
business logic/models with family-specific presentation adapters for layouts,
typography, controls and effects where needed. Keep Sakura selectable when the
new family is implemented. No Neo Manga option or unfinished placeholder is added
to Settings until its design is implemented.

Current presentation sources include `app/ui/theme.py`, `home_style.py`,
`settings_style.py`, the other page/drawer style modules, shared components and
page layouts. [Reference index](../../design/README.md).

The new family is not implemented in this checkpoint. Await the user's incoming
screens and guidelines before redesigning any page. If recovering the baseline,
inspect the tag in a separate worktree/checkout so later work is not overwritten.
