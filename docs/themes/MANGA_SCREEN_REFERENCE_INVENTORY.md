# Manga Light screen reference inventory

> Completion correction, 16 November: this older inventory maps reference folders
> to runtime code; it does not certify finished visual implementation. Use the
> [current design audit](DESIGN_IMPLEMENTATION_AUDIT_2026-11-16.md) for the
> conservative completion report and confirmed password/exit layout gaps.

> Latest: [complete 32-design review](DESIGN_COMPLETENESS_REVIEW_2026-11-16.md),
> including Operation Progress, fresh runtime comparisons and explicit verdicts.

Update: twelve more reference folders were supplied and applied on 15 November.
There are now **29** Manga reference folders. See the
[twelve-screen mapping and decisions](MANGA_TWELVE_SCREEN_UPDATE.md).
The older missing-reference list below records the previous inventory; the new
mapping supersedes its Settings, episode/numbering, grouping, coverage, calendar,
duplicate review, close and password entries.

Checked against the application and design folders on 15 November 2026.
The main Library remains authoritative for shared controls. Older Sakura
references are retained; they do not count as Manga-specific layouts.

## Supplied Manga references: 17 folders

Under `Light Theme (Manga Brutalism)`:

1. Main Library
2. Anime Details
3. Edit Anime Entry
4. Rematch Anime Metadata
5. Updates
6. Broadcast & Release Updates
7. Confirm/Review Downloads
8. Downloads & Transfers
9. Find Download Files
10. Import Watched List
11. Merge Libraries
12. New Anime Releases
13. New Anime Releases — Tags & Themes
14. Organize & File Management
15. View Changes (the Overlord example)
16. Set Up Downloads — Five Steps
17. Storage

The import PNG is blank; its HTML supplies the reference. The master backup in
`design/references/manga-brutalism-light/main-v1` is not an additional screen.

## Still no dedicated Manga reference found

Current count: **31 supplied Manga reference folders** (the original 17, the
next 12, and these latest 2). Add Custom Entry reuses Edit by explicit approval.

| Screen/workflow | Existing context |
| --- | --- |
| Library list view | Older Sakura List View reference |
| Delete local files / remove library entry confirmation | Existing safety confirmations |
| Organizer individual file/season review | Overview supplied, separate review layout missing |
| Scanner ambiguous-match review | Separate from Rematch Metadata |
| Move completed downloads to library | Existing move-preview workflow |
| Torrent file selection | Optional file-selection drawer |
| Browser Magnet Received | Separate from manual Add Magnet / Torrent |
| Password setup and recovery questions | Unlock and Change supplied; these additional modes are not |
| API JSON inspector | Existing diagnostic view; optional dedicated design |

The Chrome extension and installer are separate surfaces and have no Manga
reference here either. Native file pickers/system prompts are OS-managed.
No Manga Dark master reference has been supplied; Sakura Dark remains a
separate preserved theme.
Missing reference does not mean missing functionality: existing layouts and
features remain, with shared light controls. No new layout/feature is inferred.

Add Custom Entry now explicitly reuses the Edit Entry form by user approval;
it no longer needs a separate mockup. Its creation header and custom metadata
refresh explanation remain appropriate to adding an entry.

## Theme-wide shared implementation

`app/ui/manga_controls.py` styles visible buttons, tool buttons, sorting/select
dropdowns and search fields, including controls created when a workflow opens.
It reuses the existing master effects and restores prior local styles on Sakura.

- Light faces/dark text, raised rest state and recessed hover/press.
- Pink primary actions and existing destructive/status semantics.
- Consistent filters/focus without an extra blue ring.
- Raised dropdowns and inset search fields.
- Existing rail blur and calendar previews retained.

Effects are reused rather than stacked. Effect-bearing ancestors block a second
child effect, preventing blank labels. Large custom preview cards keep their
own anatomy. Page layouts, data and action callbacks are unchanged.
