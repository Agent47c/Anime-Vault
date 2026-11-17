# Supplied design implementation audit — 16 November 2026

> Superseded by [the complete 32-design visual review](DESIGN_COMPLETENESS_REVIEW_2026-11-16.md).
> That pass freshly renders every current screen, adds comparison evidence and
> gives an Applied/Partial/approved-replacement verdict for each reference.

## Honest count

- 31 current Manga reference folders found, each with HTML and an image file. The importer image is blank.
- 31 references have a runtime screen/section mapping; this is **not 31 completed designs**.
- 0 are certified as fully faithful by this audit.
- 3 specifically reported screens are freshly rendered and confirmed visually partial: Unlock, Change Password, Exit Choice.
- 27 other references have implementations/adaptations but still need final visual acceptance; code hooks and older renders cannot certify completion.
- 1 reference (Edit Season Numbers) has an explicitly approved replacement workflow.
- 0 reference folders were found with no runtime mapping. Missing design details remain a real implementation gap.

This is a conservative completion report, not a claim that every other screen is missing. Earlier inventory wording that all screens were applied overstated visual completion. Automated functional tests do not certify design fidelity.

## Evidence and method

Reviewed all 31 source thumbnails, supplied HTML/file inventory, mapping documents and current route/style code. Fresh temporary-data renders checked the three screens named by the user and initial password setup. Existing older workflow renders are supporting evidence only. This pass does not claim fresh pixel-by-pixel validation of all 31 pages. No password was entered or changed and no real quit action, scan or file move was executed.

## Reference-by-reference findings

| # | Reference | Finding |
|---|---|---|
| 01 | Anime Details Light Theme (Manga Brutalism) | Personal band has approved changes; episode/release presentation still needs reference-level spacing review. |
| 02 | broadcast_release_updates_ Light Theme (Manga Brutalism) | Shared release page exists; hero, broadcast table and compact actions are adapted. |
| 03 | change_password_light_theme_manga_brutalism | CONFIRMED PARTIAL: generic form; missing reference modal shell, watermark, icon, backdrop and field proportions. |
| 04 | choose_episode_light_theme_manga_brutalism | Episode picker exists; grid/footer use existing data. Mockup-only filters/placeholders were declined. |
| 05 | close_anime_vault_light_theme_manga_brutalism | CONFIRMED PARTIAL: remember choice is above content, status panel and shadows differ, excessive empty height; background is not the reference blur. |
| 06 | confirm_2_selected_downloads_light_theme_manga_brutalism | Confirmation exists; selected-release cards use a simpler existing form. |
| 07 | confirm_review_downloads_ Light Theme (Manga Brutalism) | Review gate exists; illustrated metadata/destination multi-panel composition is not reproduced. |
| 08 | confirm_series_grouping_light_theme_manga_brutalism | Grouping confirmation exists; current safety review differs in row anatomy and modal presentation. |
| 09 | downloads_transfer_engine_light_theme_manga_brutalism | Only Search & Auto Ingest was requested. Full transfer-engine mockup was intentionally not copied. |
| 10 | downloads_transfers_ Light Theme (Manga Brutalism) | Queue/guide implemented and recently restyled; capacity/source panels are not equivalent to the reference. |
| 11 | Edit Anime Entry Light Theme (Manga Brutalism) | Shared Add/Edit form exists; field grouping and density differ from the two-column reference. |
| 12 | edit_season_numbers_light_theme_manga_brutalism | APPROVED REPLACEMENT: user subsequently requested direct file selection and physical season moves instead of the original number-only screen. |
| 13 | episode_coverage_franchise_breakdown_light_theme_manga_brutalism | Coverage cards and export exist; requires final typography/spacing sign-off. |
| 14 | find_download_files Light Theme (Manga Brutalism) | Search workflow exists; retains approved existing match controls and differs in search/table composition. |
| 15 | full_calendar_light_theme_manga_brutalism | Calendar page exists; shared day tiles require final full-page comparison. Missing schedule entries are a separate data issue. |
| 16 | group_seasons_arcs_light_theme_manga_brutalism | Grouping selection exists; pagination intentionally declined, virtual scrolling retained. |
| 17 | import_watched_list Light Theme (Manga Brutalism) | Reference PNG is blank: HTML is the only usable visual specification; import controls are adapted. |
| 18 | Main Screen (Light Theme ) | Master shell/hero/schedule/archive/pagination implemented; later approved changes mean the original image is not a pixel-equality test. |
| 19 | merge_libraries Light Theme (Manga Brutalism) | Merge preview and safety review exist; shared surfaces do not prove exact panel composition. |
| 20 | new_anime_releases Light Theme (Manga Brutalism) | Discovery cards/filters/pagination implemented; card composition and metadata density differ. |
| 21 | new_anime_releases Tags Themes Light Theme (Manga Brutalism) | User subsequently removed staged Apply/Clear/Cancel and presets; transient tag popovers are an approved divergence. |
| 22 | organize_file_management Light Theme (Manga Brutalism) | Organizer rules/roots/preview exist; individual movement review is a separate screen. |
| 23 | overlord_view_changes Light Theme (Manga Brutalism) | Shared View Changes exists, but the Overlord artwork/metadata hero is absent from the simple title header. |
| 24 | Rematch Anime Metadata Light Theme (Manga Brutalism) | Rematch exists; result metadata density and footer differ from the reference. |
| 25 | review_duplicate_files_light_theme_manga_brutalism | Duplicate review exists; this pass compacts the header and adds newly approved bulk/per-anime selection. Full reference fidelity still requires visual acceptance. |
| 26 | set_up_downloads_5_steps Light Theme (Manga Brutalism) | Five existing steps are reused in one page; precise card hierarchy differs. |
| 27 | settings_preferences_light_theme_manga_brutalism | Separate categories deliberately retained; do not flatten settings to match the long reference page. |
| 28 | Storage Light Light Theme (Manga Brutalism) | Storage panels/sorting/pagination exist; illustrative drive/SMART/hash claims intentionally omitted. |
| 29 | the_rising_of_the_shield_hero_view_changes_light_theme | Same View Changes implementation as Overlord; do not count as an independently implemented feature. |
| 30 | unlock_adult_anime_light_theme_manga_brutalism | CONFIRMED PARTIAL: generic unlock form; missing reference modal frame/backdrop/watermark/lock treatment and helper arrangement. |
| 31 | Updates Light Theme (Manga Brutalism) | Updates exists; action hierarchy changed by explicit user requests. Shared button styling is not full layout certification. |

## Password and exit routes

- Unlock: Settings adult-content toggle opens unlock if a password exists. If none exists it opens **Set Initial Password** instead.
- Change Password: Settings opens AdultPasswordDialog in change mode.
- Set Initial Password and recovery questions have no separate dedicated Manga reference folder; they reuse the access dialog.
- Exit choice: MainWindow.closeEvent opens QuitConfirmDialog only when the saved close preference is Ask. Saved Tray/Exit preferences intentionally bypass it.
- Unlock/Change use generic manga_additional styling rather than a dedicated faithful composition.
- Exit uses the shared workflow chrome; its content order, status well, card elevation, remembered-choice placement and height differ from the supplied image.

Current audit captures: Unlock (local artifact: `../../data/design-audit-2026-11-16/current-unlock.png`), Change (local artifact: `../../data/design-audit-2026-11-16/current-change.png`), Exit (local artifact: `../../data/design-audit-2026-11-16/current-exit.png`), Initial setup (local artifact: `../../data/design-audit-2026-11-16/current-initial-password.png`).

## Scope and deliberately excluded material

The archive has 28 older code.html documents under design/references. These include superseded Sakura designs, the archived Manga master copy and shared component templates; they are not 28 additional current Manga screens. Profiles, CRC32/SHA additions, fabricated integrity/drive-health figures, RSS catch-up and physical-disc registration were intentionally omitted. Settings stay in separate categories. No new feature is authorized by mockup text alone.

## Recommended order

1. Finish Unlock/Change modal composition and bring initial setup/recovery into the same shell.
2. Finish Exit Choice layout and backdrop; keep its actual tray/exit behavior and remember preference.
3. Correct review/confirmation compositions, then compare each remaining page at matching sizes and record explicit acceptance.
4. Track data bugs separately from layout fidelity (including missing calendar broadcasts).

## Completed follow-up and validation

The newly approved duplicate Select All and per-anime/per-episode checkboxes select eligible redundant copies only. Protected originals remain unselectable, scans do not automatically select copies, and the existing Recycle Bin confirmation remains. The heading and overview are shorter; a fresh render is saved in data/design-audit-2026-11-16/duplicates-bulk-current.png.

Calendar investigation found that Black Clover's cached parent metadata has no next airing episode, while its cached sequel has a separate AniList ID and schedule. The calendar previously discarded related IDs without a local season row. Home and Full Calendar now share ownership resolution for unambiguous cached official sequel/side-story/spin-off relations, and refresh includes their IDs. Unknown dates still produce no invented event. This diagnosis uses saved metadata, not independent live broadcast verification.

Validation: all 687 tests and repository checks passed. Three new regression tests cover sequel ownership, unknown dates and protected duplicate selection. No personal database or media files were changed during this audit.

Local comparison artifacts are generated under ignored `data/`; they are not included in the public source snapshot.
