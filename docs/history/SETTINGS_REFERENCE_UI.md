# Settings reference UI — 11 November 2026

Applied `Sertting UI/code.html`, `DESIGN.md` and `screen.png` to the existing
PyQt settings presentation.

## Layout and navigation

Update: category navigation now switches between separate pages. Only the selected
category's options are visible; the continuous document and automatic section
scrolling have been removed. Each category retains ordinary scrolling when its
own options exceed the available height. Existing tab-index links still work.
This supersedes the continuous-document description below.

- Settings now uses the shared top navigation capsule, with a Settings &
  Preferences heading and an explicit automatic-saving note.
- A left section navigator links to Appearance & UX, Scanning & Folders,
  Watchers & Import, Media Player Engine, Downloads & Sources, and Database &
  Maintenance. The right side is one scrolling settings document.
- The original six-category tab object remains as an invisible navigation
  adapter. Existing callers selecting category 4 (download settings), for example,
  scroll to the correct section. No settings controls or callbacks were removed.
- Theme preview cards mirror Match Windows, Dark (Twilight Sakura) and Light
  (Sakura Paper). Player cards mirror all existing players, including MPC-HC and
  custom executable. They use the existing combo callbacks and persisted values.
- Existing text size, compact view, accessibility, decoration, close behavior,
  administrator launch, metadata, scanning, roots, naming rules, watch-list/import,
  download/source/Chrome configuration, player/audio/subtitle, backup/restore,
  export and maintenance controls remain available.
- Panels, controls, section navigation and switches follow the shared Twilight
  Sakura colors; light/high-contrast use existing theme tokens. Theme and player
  choices remain synchronized after repeated clicks.

## Selection belongs to All anime

- All anime has a Select anime button beside the sort/view controls. It changes
  to Done selecting while selection mode is active.
- Right-click selection and Clear Selection synchronize this button. Existing
  batch actions and selections are retained.
- Select multiple anime/updates is removed from the visible top-right menu. That
  menu retains library actions/collections and now has an explicit Settings link;
  its icon is an ellipsis to distinguish actions from configuration.

## Scope

This is a presentation pass. Existing immediate-saving behavior is preserved.
No Save All/export-configuration feature, profile, cloud sync, PIN protection,
embedded SQL diagnostics, new codec engine, invented drive/backup statistics or
new keyboard shortcuts were added from the reference. Existing database export
and integrity-check functions remain available under their real labels.

No database schema, scanner, matching, transfer or file-operation changes were
made. SettingsSwitch uses the new colors only when marked by SettingsPage;
switches elsewhere retain their existing presentation.

## Files and checks

- `app/ui/settings_style.py`: section layout, scoped style and preview cards.
- `app/ui/pages/settings_page.py`: layout adapter, section routing and restyling.
- `app/ui/components/settings_switch.py`: opt-in settings palette.
- `app/ui/pages/library_page.py`: local selection control and synchronization.
- `app/ui/components/home_header.py`: remove visible selection menu action,
  distinguish actions icon and retain Settings access.
- `app/ui/main_window.py`: shared capsule on Settings.
- `tests/test_settings_reference_ui.py` and `tests/test_home_screen.py`: coverage.

21 focused tests passed: three reference-settings regressions, 17 Home tests and
one existing settings/download-persistence check. Inspected temporary-database
renders at 1500×1000 and 1100×720, fixing the clipped theme preview discovered in
the first render. Render helper: `data/settings_reference_visual.py`.
No real library files or downloads were changed during validation.
