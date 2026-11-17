# Downloads and Organizer: current flow

## The three folder roles

| Role | Example | Purpose |
| --- | --- | --- |
| Main library root | `E:\Anime Library` | Parent folder containing the anime library |
| Download staging base | `E:\Anime Library\.animevault-downloads` | Temporary home of tracked torrent jobs; may instead be a separately configured folder |
| Anime/season destination | `E:\Anime Library\Black Clover\Season 1` | Final library location of a reviewed completed download |

Watched folders tell the scanner where to look. Several watched folders can
belong to one main library. They are not automatically separate destinations.

## Download stages

1. **Find Download Files:** search the configured source using the editable title.
   Searching only reads listings; it does not start a transfer.
2. **Confirm assignment:** link each selected release to the anime, its season
   folder and episode numbers. Continuous numbering and physical destination
   are independent. Episode 177 remains 177 unless the user edits it.
3. **Review and submit:** review the coverage/destination, confirm, and submit to
   the built-in libtorrent engine. Duplicate torrent identities and overlapping
   pending episodes are checked. Normal confirmed submission does not require
   another Choose Files step.
4. **Transfer:** download into an isolated per-job subfolder under staging.
   Isolation avoids different jobs writing into the same active directory.
5. **Complete and index:** verify the selected files' completion, paths and sizes,
   then record local videos against the linked anime. Completed means downloaded;
   it does not mean moved into the final library folder.
6. **Move to library:** Downloads > Move completed to library or Organizer's
   completed-download Review opens the source/destination preview. Only the
   explicit Move action relocates files.

Example:

```text
Before reviewed move:
E:\Anime Library\.animevault-downloads\Black Clover-<job-id>\Season 01\177.mkv

After reviewed move:
E:\Anime Library\Black Clover\Season 1\177.mkv
```

The original torrent filename is retained; `177.mkv` is illustrative. A unique
existing season folder is reused even before it is indexed. If several folders
match, the app requests review. It does not invent a season boundary or numbering
offset from folder names.

## Organizer stages

1. Scan configured watched folders and known anime locations.
2. Index discovered local files and prepare proposed season/folder assignments.
   Scanning updates inventory; it does not authorize physical file moves.
3. Treat known torrent staging as staging. Completed jobs use their saved anime
   identity instead of treating the staging folder itself as a new anime.
4. Show the proposals. Items are no longer automatically selected after scans
   or filter changes. Review lets the user examine an individual proposal.
5. For completed torrents, revalidate files and show the move-to-library preview.
   For ordinary folder organization, reject stale plans until scanned again.
6. On explicit confirmation, run the move worker with collision checks and a
   recovery journal. Do not overwrite an existing destination file. Keep file
   identity/history and database paths aligned with completed operations.

Files with unknown anime identity require review. Similar names alone are not
enough to move arbitrary videos into an anime's folder.

## Bugs identified in the root/folder flow

- The Merge destination could be shown without being saved. It used to be saved
  only when a preview finished. Completed-download review therefore could not
  see the choice. The destination is now saved immediately on selection or
  completion of editing.
- Main-root detection required exactly one watched-directory row. A main folder
  plus nested watched anime/staging folders could therefore be considered
  ambiguous. Nested watched folders are now collapsed; genuinely separate roots
  still require a main-root choice.
- A generic Open download folder action followed the selected transfer. Selecting
  Black Clover could open Black Clover's job folder, making it appear that the
  shared folder had changed. Opening a folder does not rename it. The global and
  selected-transfer actions now have separate explicit labels/routes.
- Saved default download paths could be replaced by an automatically derived
  path. An explicitly saved destination is now preserved.
- An unindexed `Season 1` could be overlooked and a new `Season 01` proposed.
  Preview now reuses the unique matching physical folder.
- Stale Organizer previews disabled completed-download Review even though that
  action performs its own fresh validation. That review route now remains usable.
- A first completed download can temporarily be the anime's only local location.
  A later move preview could mistake that staging location for the canonical anime
  folder, especially with a custom staging-directory name or another job folder.
  Preview now excludes the configured staging base and all tracked job roots when
  choosing an existing final anime/season folder. It also rejects targets inside
  staging rather than sending files from one torrent job into another.

Main library selection, staging configuration and per-anime file locations are
separate settings. Choosing one or opening a folder never moves files by itself.
