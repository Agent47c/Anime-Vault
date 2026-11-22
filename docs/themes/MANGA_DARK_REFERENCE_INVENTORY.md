# Manga Brutalism Dark reference inventory

The supplied Main Screen (Dark Theme) is the visual authority for the dark
variant. Its original 1591 × 1600 screenshot, HTML and design notes are
preserved together. [Archived main screen](../../design/references/manga-brutalism-dark/main-v1)

The shared dark palette uses charcoal surfaces, warm gray text, muted pink
secondary text and hot pink primary actions. The existing Manga shell,
raised and recessed controls, and modal layouts carry those materials into
other screens. Settings retains the existing categories and actions.

The selected Library filter uses the original white face, dark text and dark
count badge from the main screen.

## Supplied references

There are 33 screen folders with PNG and HTML files. Several are alternate
views of the same workflow.

| Area | Supplied screens |
| --- | --- |
| Library | Main Screen, Anime Details, Edit Anime Entry, Rematch Anime Metadata, Choose Episode, Edit Season Numbers, Group Seasons and Arcs, Confirm Series Grouping, Episode Coverage |
| Updates | Updates, Broadcast and Release Updates, Full Calendar, New Anime Releases, Genre/Theme Filters, View Changes examples for Overlord and The Rising of the Shield Hero |
| Downloads | Downloads and Transfers, Add Magnet transfer engine panel, Find Download Files, Confirm/Review Downloads, Confirm Selected Downloads, Five-Step Setup, Move Completed Downloads |
| Organizer and storage | Organize and File Management, Merge Libraries, Review Duplicate Files, Storage |
| Settings and dialogs | Settings, Import Watched List, Unlock Adult Anime, Change Password, Close Anime Vault, Operation Progress |

Storage has usable HTML but its PNG is blank. Operation Progress is visually
dark despite the folder name ending in `light_theme`. Add Custom Entry shares
the Edit Entry layout, as previously requested.

## Dedicated dark references still needed

The existing screens inherit the shared dark treatment in the meantime.

- Library list view and its bulk selection toolbar.
- Organizer per-file review, missing-file/path repair and ambiguous scan match review.
- Move Episodes Between Seasons. This is separate from moving completed downloads.
- Torrent file picker, browser Magnet Received dialog and duplicate download choices.
- Duplicate file Inspect dialog and the confirmation before recycling copies.
- Remove anime, local-file deletion and other destructive confirmations.
- Initial password setup and security-question recovery.
- Backup and restore confirmation, restart prompt, and shared alerts.
- Vault Navigator, anime right-click menu and the playback dropdown.
- API JSON inspector.

The Chrome extension and Windows installer are separate surfaces. Dedicated
Manga Dark mockups for those surfaces were absent from this set.

## Verification

Reviewed the supplied screenshots as a set and rendered the Library, Updates,
Downloads, Organizer, Storage and Settings with temporary data. Also rendered
Close Anime Vault, Unlock, Change Password, Duplicate Review, New Anime Releases
and Move Completed Downloads. The app switched through both Sakura modes and
both Manga modes without restarting. These checks cover the shared materials
and representative layouts. Individual screenshots of every workflow state,
display scale and populated dataset are still pending.
