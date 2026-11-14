# Download retries, removal and library moves

Implemented 11 November 2026. Existing download, file selection, history and
library features remain available. No real library files were moved during
development or validation.

## What changed

### Retry keeps the transfer identity

- Native Retry reuses the same queue ID, torrent handle, destination and selected
  files. It clears the native error, rechecks existing pieces and resumes a
  confirmed selection. It does not submit a new queue entry.
- If files have not been chosen yet, Retry requests metadata/rechecking and tells
  the user to choose files. It does not silently select every file.
- An old external-client record converts to the built-in engine **in place**
  after confirmation. Its queue ID is retained. Its old external files stay
  untouched; native storage is isolated and requires file selection.
- Native preparation failures retain the original record and a retryable error.
- Existing duplicate queue entries are not automatically removed or combined.
  Use Remove queue entry on the unwanted record; its files remain on disk.

The native error reset uses libtorrent's documented
[torrent_handle API](https://www.libtorrent.org/reference-Torrent_Handle.html).

### Remove acts on the intended transfer

- Each row menu captures the transfer ID when opened. A timed queue refresh or
  selection change cannot redirect its Remove, Retry, Choose files, Open folder
  or Recycle Bin action to a different row.
- Remove cancels native tracking and removes the queue record after confirmation;
  it keeps downloaded files and library history. It does not invoke Pause or
  Choose files.
- Moving files to the Recycle Bin remains a separate confirmed action.

### Default location follows the main library

- When using the old default Downloads/AnimeVault destination, new transfers now
  stage under `<main library>/.animevault-downloads` in isolated job folders.
- The main library is the configured merge destination, or the sole watched root
  when exactly one root exists. The current installation has E:/Anime Library.
- Explicit custom download destinations and existing transfer destinations are
  preserved. With several roots and no preferred destination, select the main
  library first; the move preview explains this rather than guessing.
- The staging area is excluded from ordinary scanning. Only verified completed
  downloads enter the library inventory.

## Navigation: move completed downloads

**Downloads → Move completed to library → review source/destination table →
Move N files.** Opening the preview does not move anything.

- The preview includes verified completed transfers, including selected known
  accompanying files. Active transfers, unselected files, unknown files and
  already moved jobs are excluded.
- Files go under their linked anime's existing main-library folder where valid,
  otherwise a sanitized anime-name folder. Known seasons use the existing season
  folder or `Season NN`. An unknown season uses `Episodes` for continuing-series
  mode or `Unassigned episodes` for later review.
- Original filenames and relative torrent subfolders are preserved. This action
  does not infer a different release, rename episodes or reorganize every file
  already in the library.
- The native transfer is detached before moving; it cannot recreate files in its
  old staging folder. A moved job remains Completed, and Open folder opens its
  new anime folder. File selection/restarting from the old destination is blocked.
- Completed-file deletion after relocation goes through anime Details, where the
  actual library files can be reviewed.

## Safety and recovery

- All source/destination pairs are revalidated before the first move and again
  before each file. Occupied destinations, changed sources, linked paths and
  conflicting destinations remain visible for review; nothing is overwritten.
- Same-volume moves use the existing no-overwrite move journal. Cross-volume
  moves copy to an exclusive temporary destination, flush, compare SHA-256 hashes,
  publish without overwrite, verify again, then remove the source.
- Every completed file updates its physical location and preserves its stable
  file/episode identities, watch history and last-played references. Cross-drive
  intermediate inventories can represent files on both drives until finished.
- Queue intents and verified paths are saved after each file. Interrupted moves
  reconcile proven completed files and retry only the remainder. If both copies
  exist after an interrupted copy, neither is automatically deleted.
- Final completion updates the anime/group root and refreshes cached library
  views. Errors are retained per transfer and are retryable.
- Disk work runs in an app-owned worker. Stop after current file leaves the rest
  in place. Existing task/close protection recognizes this worker. A large
  cross-drive file may take time to finish copying and verifying before stopping.
- Empty staging directories are left intact. Files outside the verified selected
  inventory stay where they are.

## Changed implementation files

| File | Responsibility |
| --- | --- |
| app/core/builtin_torrents.py | Clear native error before rechecking same handle |
| app/core/download_queue.py | In-place legacy retry, native retry, moved-job guards |
| app/core/downloads.py | Main-library default, selected inventory, moved-file guard |
| app/core/download_library.py | Reviewed destinations, move intents and per-file recovery |
| app/core/file_operations.py | Verified cross-volume moves and location metadata updates |
| app/core/identity.py | Keep mixed-drive season inventories reachable during relocation |
| app/ui/pages/downloads_page.py | Stable row-menu targets and move-preview navigation |
| app/ui/dialogs/download_library_move.py | Preview, explicit confirmation, worker and stop control |
| tests/test_downloads.py | Updated in-place legacy retry assertions |
| tests/test_download_recovery_and_moves.py | Retry/removal/path/recovery/UI safety regressions |

## Validation

Focused modules: `test_downloads` (14), `test_download_recovery_and_moves` (11),
`test_data_safety` (27), `test_consolidation` (6), `test_transfer_screens` (8).
The 66 tests cover temporary-file moves, identity/history/last-played preservation,
destination collision, interrupted copy recovery, partial move resumption,
cross-drive path inventories, in-place retries, native call ordering, Remove,
menu selection races, custom destinations and unselected-file preservation.
The move preview is instantiated with temporary data and starts no worker until
confirmed. Native calls are mocked in these regressions; a live torrent/network
transfer was not performed. No claim is made that a full application test suite
or a live cross-drive transfer has been exercised.
