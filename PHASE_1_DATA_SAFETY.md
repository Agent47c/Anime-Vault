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
timestamp tracking has been added in this phase. A play event records a launch
request, not proof that the external player started or that an episode was watched
to completion. External players do not currently report completion back to the app.

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

## Complete change record

### Step 1.1: Stable identities and path reconciliation

- Added ten tables: `library_series`, `releases`, `season_releases`, `episodes`,
  `physical_files`, `file_locations`, `file_episodes`, `episode_history`,
  `repair_candidates` and `file_operations`. The relationship tables are separate
  persisted tables, not embedded JSON.
- Preserved the existing franchise/season tables and their notes, ratings,
  metadata, artwork filenames and UI connections. Existing series-level notes
  were not copied onto arbitrary episodes.
- Episode notes and history reference the episode ID. Last-played state stores
  an episode ID and preferred physical-file ID, with a compatibility path value.
- Changing a file's location does not recreate its episode or change its release.
- A replaced encoding gets a new physical-file identity; the same logical episode
  can retain its history and notes. Combined files can reference multiple episodes.
- Playback resolves stale paths only through completed move records. Details-page
  play actions reload current season inventory, and Open folder uses current data.
- If the last-played copy is recycled/replaced, Resume can select another available
  physical copy of that same episode instead of pointing permanently at the removed copy.
- Fixed Windows short/long path equivalence in identity keys and move reconciliation.
- Exact-title lookup no longer chooses the first result when multiple library rows
  match. Existing network matching remains conservative about ambiguous releases.
- External move discovery uses configured roots and existing signatures, including
  same-volume renames. It saves review candidates instead of silently reassigning
  history. Approval revalidates the candidate and refuses a target already claimed
  by another indexed file.
- Lazy episode discovery can register a newly found file under one unambiguous
  local release before recording play history. Ambiguous ownership requires refresh
  and review rather than assigning history to an arbitrary season.

### Step 1.2: Safe and recoverable operations

- Regular Organizer, consolidation and the One Piece rename script use the shared
  durable move service. The rename script retains its existing read-only handling.
- Preview signatures contain size and modification time. Complete previews are
  checked before execution and each file is checked again immediately before IO.
- Occupied destinations are never overwritten. Organizer's existing collision
  suffix behavior remains; consolidation retains its previewed collision names.
- Moves remain same-volume. Cross-volume copy/delete is rejected rather than
  silently degrading the operation's safety guarantees.
- Each intent includes source, target, file signature, timestamps, status and errors.
  A completed-file database commit happens before the progress callback reports it.
- In-process file operations and recovery are serialized to avoid a recovery thread
  interpreting another active operation's intent as an abandoned one.
- Interrupted rename recovery checks the full saved size/mtime/device/inode
  signature. A replacement file, conflicting destination or unavailable path stays
  in review; recovery neither deletes files nor invents a successful merge.
- Normal Organizer stops at its first execution failure, retaining unprocessed
  originals for a fresh preview. Failures are recorded and remain visible.
- Startup checks pending operations even with scheduled scans disabled. Refresh
  and Find missing files also reconcile them, using background workers.
- Recycle operations receive durable intents too. Inventory/availability and size
  summaries are updated after successful recycling; episode identities survive.
- Duplicate deletion still rechecks the keeper and selected copy with SHA-256.
  Windows recycling explicitly requires the modern backend; there is no fallback
  to `unlink`, permanent deletion, or the older Windows recycling implementation.
- Errors appear in refresh/Organizer status and tooltips. Original files remaining
  after a failure can be retried through a newly generated preview.

### Step 1.3: Release-aware numbering and gaps

- Stored original episode numbers independently of verified release numbers and
  their mapping source. Manual mappings survive subsequent folder scans.
- Stored numbering schemes (`ABSOLUTE`, `SEASON`, `UNVERIFIED`) and release states
  (`AIRED`, `UPCOMING`, `UNKNOWN`) separately.
- Explicit filename season tokens take precedence over a misplaced parent folder.
  S1E10 and S2E10 remain distinct even when placed in the same folder or encountered
  under a continuing-series setting.
- Continuing-series gap checks aggregate appropriate arc/root episodes. Explicit
  season-relative files are not silently used to fill absolute-numbering gaps.
- Verified part-relative mappings feed health/availability checks without renaming
  the physical files. Physical file counts remain distinct from contained episodes.
- Future release timestamps and not-yet-released seasons are excluded from missing
  reports. Total episode counts for airing releases no longer imply all have aired.
- The existing conservative internal-gap policy remains when boundaries are not
  verified. Unknown catalog information does not become an invented aired count.
- Episode browser filtering uses already-loaded rows; changing Aired/Upcoming/
  Release unknown does not start another filesystem scan.
- Conflicting ownership of a path is flagged by the lazy browser rather than
  assigning it to whichever season happens to be traversed first.

### Visible changes and preserved behavior

- Added the authorized release-state dropdown to the episode page.
- Find missing files shows an explicit repair confirmation with full source/target
  paths under Show Details; the default answer is No. Filename-only candidates stay
  unlinked, and conflicting candidates are not offered for batch approval.
- Duplicate confirmation and result text now say Recycle Bin rather than permanent
  deletion. Existing keeper review and confirmation controls remain.
- Added visible scan/file-operation review counts. Existing navigation, matching,
  grouping, storage, imports, backups, themes and player settings remain present.
- No convenience features, streaming features, API routes or additional dependencies
  were added. `pywin32` and Send2Trash were already declared dependencies.

## Files changed and responsibility

| File | Change |
|---|---|
| `app/core/identity.py` | Schema/backfill, stable IDs, history, notes, release mappings, repair candidates, path compatibility and retained-copy resume |
| `app/core/file_operations.py` | Durable move/recycle intents, per-file database commits, serialization and recovery |
| `app/core/recycle_bin.py` | Recycle-only Windows adapter, refusing a legacy fallback |
| `app/db.py` | Run identity migration, register season inventory, refuse ambiguous title lookup |
| `app/config.py` | Save/resume playback through identities and completed move records |
| `app/core/scanner.py` | Synchronize file identities and honor explicit filename season numbers |
| `app/core/consolidation.py` | Shared move service, durable JSONL completion writes and identity-aware legacy repair |
| `app/core/organizer.py` | Preview signatures/preflight, shared moves, stop on failure, review-only external discovery |
| `app/core/loose.py` | Include preview signatures for loose files and sidecars |
| `app/core/duplicates.py` | Recycle verified copies, preserving identity/inventory and rechecking signatures |
| `app/core/recycle.py` | Normal deletion uses the shared journaled recycle service |
| `app/core/library_health.py` | Verified numbering in health checks; aired boundaries and mixed-numbering safeguards |
| `app/core/matching.py` | Bind explicit release matches without replacing episode IDs |
| `app/ui/refresh.py` | Background operation recovery and surfaced recovery errors |
| `app/ui/main_window.py` | Startup recovery independent of scan schedule and visible issue count |
| `app/ui/pages/detail_modal.py` | Reload playback inventory and index root fallback files before playback |
| `app/ui/pages/episode_page.py` | Identity-aware lazy discovery, ownership checks, verified availability and release-state filters |
| `app/ui/pages/organizer_page.py` | Candidate review/approval worker and visible operation-review state |
| `app/ui/pages/duplicate_page.py` | Recycle Bin confirmation/result wording |
| `organize_anime_library.py` | Initialize the migrated database for standalone execution |
| `standardize_one_piece.py` | Journaled renames and durable completion writes |
| `tests/test_data_safety.py` | 27 added acceptance/regression tests |
| `tests/test_matching.py` | Require review instead of automatic filename-only repair |
| `tests/test_organizer_permissions.py` | Inject permission failure at the shared move primitive |
| `CHANGELOG.md` | Unreleased Phase 1 entry |
| `PHASE_1_DATA_SAFETY.md` | This implementation and acceptance record |
| `README.md`, `CONTRIBUTING.md` | Link the phase record and require detailed future change records |

## Acceptance evidence

| Requested check | Automated evidence |
|---|---|
| Move keeps Play/Open folder/artwork/last-played aligned | `test_move_preserves_history_notes_release_artwork_and_all_path_consumers` |
| Manual moves retain history and require review | `test_manual_move_is_reviewed_and_keeps_episode_history`, `test_rescan_of_external_move_creates_candidate_without_relink` |
| Crash between rename and DB commit reconciles | `test_crash_between_rename_and_database_commit_is_reconciled_once`, `test_database_failure_after_rename_retains_recoverable_intent` |
| Partial merge commits each completed location | `test_interrupted_merge_updates_each_completed_file_immediately` |
| Permission errors stay retryable; targets survive | `test_permission_failure_is_visible_and_retryable`, `test_occupied_target_is_never_overwritten` |
| Changed preview moves nothing | `test_changed_preview_aborts_before_first_organizer_move` and existing consolidation test |
| Recycle failure retains originals | `test_recycle_failure_never_falls_back_to_permanent_delete`, `test_windows_recycling_does_not_use_legacy_fallback` |
| Split arcs/root files and future releases | `test_continuing_series_split_arcs_root_files_and_future_boundary` |
| Equal episode numbers from different seasons stay distinct | Both explicit-season tests and `test_season_one_and_two_episode_ten_have_distinct_identities` |
| Original numbers survive verified part-relative mapping | `test_verified_part_relative_mapping_drives_health_without_renaming` |
| Legacy migration backs up and is idempotent | `test_migration_backs_up_and_preserves_legacy_last_played` |
| Retained duplicate can resume the same episode | `test_recycling_last_played_duplicate_resumes_retained_episode_copy` |

Final code validation: **150 tests passed locally**, using `python scripts/check.py`.
GitHub Actions independently runs the Windows/Python 3.13 suite for the branch and
pull request. The CI links in the pull request are the authoritative run results.

## Remaining verification and limits

- No real power cut or forced drive disconnection during a live-library merge was
  performed. Those failures were simulated using disposable fixtures.
- A clean-machine installer, new player integrations and earlier Seanime-inspired
  convenience proposals are outside this phase.
- Same-volume fingerprint matching is not a cross-volume content-hash repair
  system. Unknown fingerprints and ambiguous candidates remain unresolved safely.
- Existing series notes and ratings are preserved at their original scope; an
  episode-note editor and actual watched-completion tracking remain outside scope.
- The version 1 baseline tag is unchanged. This work is published for review in
  [pull request #1](https://github.com/Agent47c/Anime-Vault/pull/1), rather than being
  merged into `main` automatically.
