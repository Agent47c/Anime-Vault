# Twelve additional Manga Light screens

> This historical note records routing/styling work, not completed design fidelity.
> See the [complete visual review](DESIGN_COMPLETENESS_REVIEW_2026-11-16.md)
> for current Applied/Partial verdicts and fresh comparisons for every reference.
> The earlier decision against duplicate bulk selection was subsequently reversed
> by the user; bulk/per-anime selection is now implemented.

15 November 2026. These use the corrected Library controls, light surfaces,
serif headings and cached neumorphic effects. Sakura remains available.

| New reference | Runtime screen |
| --- | --- |
| Change Password | AdultPasswordDialog change mode |
| Unlock Adult Anime | AdultPasswordDialog unlock mode; existing recovery remains |
| Close Anime Vault | QuitConfirmDialog, preserving tray/exit/remember choices |
| Choose Episode | EpisodePage, retaining virtual cards and playback footer |
| Confirm Series Grouping | GroupReview, preserving explicit confirmation |
| Edit Season Numbers | SeasonNumbers, preserving manual mapping and review gate |
| Episode Coverage / Franchise Breakdown | CoveragePage and existing JSON export |
| Full Calendar | FullCalendarPage using shared Manga day tiles and cached dates |
| Group Seasons & Arcs | GroupSeriesPage with current search/selection model |
| Review Duplicate Files | DuplicatePage with current protected-copy verification |
| Settings & Preferences | Existing separate settings sections with Manga materials |
| Rising of the Shield Hero — View Changes | Shared UpdateReviewPage, actual saved events |

## Scope decisions

- Settings retains every current option, automatic saving and separate sections.
  No settings-only export, cloud sync, SQL console or new playback controls.
- Grouping retains its current virtualized continuous browsing.
- No new duplicate-pool filters or Select All Duplicates action.
- The approved **Inspect selected file** action is read-only. Select a file row
  to inspect its title, cached path/size/episodes and protected/copy state. The
  view states that its verification comes from the loaded scan. It does not
  open, change, hash or delete files, and cannot select a protected original.
- CRC32/SHA additions, integrity claims, fake statistics, qBittorrent examples,
  profiles and unsupported sample controls remain omitted.

## Implementation and validation

Shared styling lives in `app/ui/manga_additional.py`; existing page classes and
handlers are reused. Existing inline button styles remain safely normalized.
The older shared-button decorator no longer appends conflicting Sakura rules
after Manga-specific styles. Label-only report/group cards get bounded shadows;
episode/group views retain delegate painting rather than per-row widgets.

All twelve screens were rendered with temporary data. Focused tests cover
password masking, theme restoration and Inspect preserving protected selections.
The full suite and existing workflow checks are recorded in the changelog.
The supplied Settings screenshot is a long single-page composition; preserving
the user's requested separate sections intentionally differs from that layout.
Native window chrome, real data and retained controls can also differ from the
mockup. No installer was built and no personal database/media was modified.
