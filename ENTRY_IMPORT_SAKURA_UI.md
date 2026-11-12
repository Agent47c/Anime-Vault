# Add/Edit Entry & Watched TXT Importer Twilight Sakura UI

## Summary
Applied the approved Twilight Sakura visual design from
`add entry screen and txt importer screen/` to `CustomEntryDialog` (both Add and
Edit modes) and `WatchedImportDialog`, using centered wide modal panels
(`900px` and `980px`) while preserving 100% of existing features, signals,
widget attributes, and test contracts.

## What Was Added & Changed
- `app/ui/entry_import_style.py`: New scoped QSS and shared widget helpers
  (`palette`, `dialog_qss`, `build_twilight_chrome`, `field_block`,
  `TwilightComboBox`, `TwilightCheckBox`, `StatusDot`, `poster_thumbnail`,
  `apply_input_palettes`, `refresh_chrome_scale`, `center_modal_show`) supporting
  dark, light, high-contrast themes and dynamic `animevaultScale`.
- `app/ui/dialogs/custom_entry.py`: Updated both Add (`_setup_ui`) and Edit
  (`is_edit=True`) flows to use the centered Twilight Sakura two-column poster +
  titles card, `Synopsis`, side-by-side `Watch status` and `Your rating` (1–10 pills
  with live descriptor readout in Add mode; preserved `rating_combo` in Edit mode),
  `Anime folder` / `Linked folder` row with folder icon, `Notes`, `"Automatic sync
  policy"` banner in Add mode, and sakura-gradient `Save entry` footer.
- `app/ui/dialogs/watched_import_dialog.py`: Updated the TXT Importer to use the
  centered Twilight Sakura layout with `Ctrl + I` header badge, dashed `.txt`
  dropzone + real file size strip, 3-column config bar using `SettingsSwitch`
  for `rematch_existing`, 4-column horizontal KPI summary cards, custom painted
  checkboxes, tonal status pills, inline `Choose match` / `Add custom` buttons,
  and `"0 local files moved or deleted"` safety footer.
- `tests/test_entry_import_sakura_ui.py`: Added tests covering Add/Edit fields,
  status/filter preservation, absence of unapproved mockup additions, embedded
  navigation widths, and dark/light/high-contrast + `1.3x` supported text scale updates.

## What Was Removed / Replaced
- Replaced `app/ui/components/workflow.chrome()` / `workflow_drawer` styling and
  the narrow `560px` right-hand drawer width in `CustomEntryDialog` and
  `WatchedImportDialog` with scoped Twilight Sakura modal chrome and centered
  panel presentation (`900px` / `980px`).
- Replaced separate Add vs Edit panel builders (`_setup_edit_ui`) with a unified
  layout builder in `CustomEntryDialog` while keeping all Edit-mode widgets
  (`rating_combo`, `"Linked folder"`, `"Edit anime entry"`).
- Replaced the 2x2 KPI tile grid and standard `QCheckBox` (`rematch_existing`)
  in `WatchedImportDialog` with the 4-column KPI strip and `SettingsSwitch`.

## Unapproved Mockup Items Intentionally Omitted
- `"On Hold"` status option (unsupported by database schema).
- `"Supports Markdown"` hint on Synopsis (Synopsis renders as plain text).
- `"Vault Database v2.4.1"` / `"Encoding: UTF-8"` fabricated status strings.
- `"Select all"` checkbox, `"Filter imported list..."` search box, and poster
  drag-and-drop image handling (new interactive features excluded unless requested).

## Validation
- Offscreen visual inspection at `dark` (`1.0x`, `1.5x`) and `light` (`1.0x`).
- Targeted unit tests + `python scripts/check.py` (see final run results).
