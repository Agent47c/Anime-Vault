# Phase 1: Data safety and core identity

Implemented on `phase-1/data-safety-identities`, leaving the version 1 tag unchanged.

## Identity model and migration

`library_series` represents a series independently of its legacy franchise row.
`releases` represents a release independently of its local folders. `season_releases`
connects existing folder inventory rows to those release identities. `episodes`
stores original numbers, numbering scheme, verified release numbers, release state
and episode notes. `physical_files` and `file_locations` describe copies and their
current paths; `file_episodes` supports both alternate copies and combined-episode
files. `episode_history` references episode IDs, not filenames.

The migration preserves the existing tables and UI. Before backfilling an existing
inventory it uses SQLite's backup API to save a database under
`data/exports/migration-backups/`. Repeated initialization does not duplicate history.
Only the known legacy last-played item can be migrated into episode history;
earlier playback events were not recorded and cannot be reconstructed.

Existing title-level notes remain title-level notes. Episode notes have their own
storage API and are preserved through moves. No per-episode note editor or player
timestamp tracking has been added in this phase. A play event records a launch,
not proof that an episode was watched to completion.

## Moves and recovery

1. Revalidate the preview before moving anything. Changed previews are rejected.
2. Commit a `file_operations` intent using SQLite `synchronous=FULL`.
3. Perform a same-volume, non-overwriting move. There is no copy/delete fallback.
4. Commit file location, legacy playback/folder references and operation completion
   together before reporting the file as moved.
5. On reopening, a background refresh reconciles incomplete intents even when
   scheduled scanning is disabled. Missing source plus an exact destination file
   signature can complete the database update. Missing/conflicting/replaced files
   remain review issues; recovery never guesses by filename or repeats a move.

The older JSONL journals remain for auditing/compatibility. The new SQLite operation
log covers the filesystem/DB interruption window, including a rename completed
before its JSONL completion record was written. File operations are not a single
atomic transaction with SQLite, so recovery is deliberately explicit about this gap.

Remaining original files can be retried using a fresh Organizer/merge preview.
Errors remain in the operation log and are exposed through refresh/Organizer status.
An unavailable drive does not cause episode history to be removed.

## External moves

Organizer > Find missing files searches configured roots and presents repair
candidates. Known same-volume file signatures can be approved after reviewing paths.
Filename-only matches never automatically relink history. Files without a previous
fingerprint, cross-volume copies, or ambiguous matches require manual investigation;
the app does not pretend that equal names prove equal contents. Approved repairs
revalidate the candidate before changing the location.

## Duplicate deletion

Both the retained copy and selected duplicate are hashed again. The selected copy
goes through Send2Trash/OS Recycle Bin; failure retains the original and reports the
error. There is no fallback to permanent deletion. Episode records/history survive.
An interrupted Recycle Bin operation is left for review because absence alone
cannot prove recycling succeeded (a drive could be disconnected).

On Windows the adapter explicitly requires Send2Trash's modern pywin32 backend,
which uses the recycle-on-delete flag. Missing pywin32 is an error, not a reason
to fall back to the older deletion backend. Flag semantics are documented by
[Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifileoperation-setoperationflags).

## Episode numbering and release state

- S1E10 and S2E10 are distinct release/episode identities.
- Continuing series use absolute numbers across their local arc/root folders.
- Combined files link to each contained episode; alternate encodes are physical
  copies of a logical episode rather than new watch histories.
- Movies/specials do not fill gaps in a TV release.
- Explicit release mappings are stored separately from original filename numbers.
- Episode filters distinguish Aired, Upcoming and Release unknown using saved
  metadata and known timestamps. A local file alone does not prove it has aired.
- Airing-release totals and future folder boundaries are not treated as proof that
  every episode has already aired. Internal-gap detection remains conservative when
  boundaries are unverified, as previously requested.

## Validation and limits

`python scripts/check.py` runs the full suite using temporary files/databases.
The Phase 1 tests cover migration backups/idempotence, per-file commit during an
interrupted merge, simulated crash after rename, DB failure after rename, permission
retry, occupied targets, external-move review, different seasons with equal episode
numbers, combined files, replaced encodes, Recycle Bin failure and future-release gaps.

These tests simulate interruption; they do not claim that a real power cut, storage
controller failure, damaged filesystem or every removable-drive configuration has
been physically tested. Keep external backups. No tests operate on the real anime
library, and this implementation task does not migrate the user's live database.
