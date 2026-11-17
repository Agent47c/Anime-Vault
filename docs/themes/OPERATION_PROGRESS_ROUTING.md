# Major operations and routine progress

16 November 2026. This supersedes the earlier blanket use of the large
Operation Progress card for foreground IO tasks.

## Large circular/bar card

Only explicit major action sites opt in:

| User action | Presentation |
|---|---|
| Organizer: Scan Now | Scanning library directories |
| Organizer: Find Missing Files | Finding missing files in library directories |
| Settings: Scan All Directories | Scanning library folders |
| Organizer: confirm individual/batch organization | Moving/organizing files |
| Merge Libraries: confirm actual move | Merging library files |
| Duplicate Review: scan duplicate files on drive | Checking duplicate files on drive |
| Duplicate Review: confirm duplicate deletion | Moving duplicate copies to the Recycle Bin |
| Storage: explicit Refresh Storage | Refreshing storage |
| Downloads: confirm moving completed files | Moving completed downloads to the library |
| Details → Edit Season: confirm actual move | Moving episodes between seasons |
| Confirm removal of indexed local video files | Moving files to the Recycle Bin |

Existing confirmation and Stop behavior is preserved. No move or deletion is
started by the indicator itself. Unknown totals show Working; percentages use
actual worker-reported counts. The Working label is smaller so it fits the ring.

## Bottom progress bar

Routine work does not construct a progress dialog. The existing bottom-edge bar
and footer message identify the active operation while navigation stays usable.
This includes tab-return refreshes, ordinary library/metadata refreshes, Details
and episode loading, saved-calendar loading, release searches, saved duplicate
results, watchlist parsing, backup/export/restore tasks, and move-preview reads.

The user explicitly chose **bottom-bar feedback for Generate Move Preview**;
the large screen appears only after confirming the real merge/move.

Overlapping task messages restore the previous active task when the newest one
finishes. Footer tasks survive disposal of their originating page until their
worker terminates, so changing pages cannot leave a stuck operation message.
An explicit major Storage request queued during a routine refresh retains its
major-operation presentation.

`watch(..., major=False)` and `io_task.start(..., major=False)` are quiet by
default. Future major actions must explicitly opt in at their execution site;
do not infer a popup from an operation taking more time or from a page opening.

## Footer and API status

For the Manga shell, the footer now contains:

- Current operation (Ready when idle).
- `Speed: …/s · Downloading: …`, using currently downloading jobs. Completed or
  seeding jobs are excluded from the downloading count and download speed.

The built-in downloader prefix, API text and free-space text are removed from
this footer. The indexed count stays in the Library's information area. Existing
storage views remain available. The old generic extra task-banner row is hidden
for this shell because the footer now carries its operation feedback.

A small status dot sits **beside the top-right menu button**, as approved:

- Red: unchecked, checking, offline or only one API verified.
- Green: both AniList and Jikan API checks succeeded.
- Tooltip: individual provider results. Clicking rechecks without blocking the
  GUI. Explicit metadata/internet sync also requests a check.

These are real API-response checks, not a fabricated combined status based only
on a TCP connection to AniList. Merely switching tabs does not launch API checks.
Other Sakura shell layouts remain preserved.

## Verification

All 698 tests and repository checks passed. Focused coverage includes routine
tasks creating no dialog, major worker lifecycle, page disposal without stuck
footer messages, queued Storage intent, API partial/verified states and correct
download counts. API tests use controlled responses and do not claim the live
services were checked during development. A temporary-data visual preview is
saved at `data/progress-routing-preview.png`; no personal files or database
records were changed.
