# Download completion, moves and Organizer synchronization

15 November 2026. No new folder exclusion rule was added.

## User flow

**Downloading → Download ready → Review and move → Organized in the library**

The torrent job owns its partial files. A file appearing on disk, or reaching its
allocated size, is not proof of completion. Ordinary neighbouring files retain
their existing scanner/organizer behaviour.

| Tracked state | Organizer behaviour |
| --- | --- |
| Downloading, restoring/checking or incomplete | Visible as Download not ready; cannot be selected or reviewed for movement |
| Verified completion | Download ready; Review opens the existing destination preview |
| Move in progress | Preserve saved inventory while affected paths are changing |
| Move interrupted or failed | Move needs review; allow the existing recovery/retry review |
| Move completed | Remove the old download row and update counts; retain final file paths and download history |

## What changed

- Shared per-file readiness checks use tracked ownership, verification and job
  state. A preallocated partial video is not treated as a finished local episode.
- Generic organization cannot move a tracked torrent file using an old folder
  proposal. Completed torrents use their linked anime's download review route.
- Ordinary scanning does not create a second anime from a torrent-job folder.
  Completed staging videos keep the anime link established by the download job;
  unrelated files in the watched parent still follow normal scanning.
- Local scan read/index/checkpoint work is coordinated with file moves. Network
  metadata fetching is outside that coordination; the GUI thread does not wait
  for the scan to finish.
- A scan captured before a move/readiness change cannot replace the newer
  Organizer preview or overwrite its saved cache.
- File movement marks the old scan location absent in the same transaction as
  the location update. Its old checkpoint is invalidated.
- Organizer reconciles its displayed download rows directly from current saved
  jobs. An older queued UI snapshot cannot bring a moved file back.
- Progress/rate changes alone do not invalidate Organizer or rebuild its rows.
  Meaningful readiness, ownership, movement and recovery changes do.

## Red-bin folder cleanup

Empty/missing folder rows in anime Details have a red-bin action beside Locate.
The confirmation defaults to cancelling. Removing the entry clears its stale
folder association and retains anime/release metadata and episode history.
Purely local detached folder rows are hidden; known provider releases remain.

The separate **Also delete the directory if it is empty** checkbox is off by
default. This uses a non-recursive empty-directory removal only. Videos,
nonempty directories, linked directories, active tracked downloads and library
roots are protected. No media file deletion is part of this action.

## Existing mechanisms retained

The proposal's seeding stop, verified cross-drive copy, operation recovery,
selected companion-file moves and no-overwrite policy already exist and were
retained. Collision recovery requests review; no automatic suffix/overwrite
feature was introduced. No new checksum feature or UI was added.

Windows long-path packaging is a separate concern, not solved by these changes.
This pass addresses completion state and stale scan/move records.

## Test in the app

1. Start one download and open Organizer while it is downloading: its row should
   say Download not ready, with Review and selection disabled.
2. Wait for verified completion: Review becomes available without rescanning.
3. Review the anime/season destination and move the completed files.
4. Confirm the files exist at the destination and that Organizer no longer shows
   the old completed-download row. Switch tabs and return to check persistence.
5. On an empty/missing season folder, try the red bin and Cancel first. Confirm
   removal separately; directory deletion requires the additional checkbox.

Automated regression coverage uses temporary media and databases, including a
scan/move concurrency test. No personal library files are moved during validation.

Validation: 614 full-suite checks passed. Final focused checks passed 8 readiness/
scan synchronization tests, 14 relocation/recovery tests and 5 stale-folder
cleanup tests, including preserving a video already recorded at a new location.
