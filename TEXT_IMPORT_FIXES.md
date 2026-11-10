# Numbered TXT imports and duplicate cleanup

Updated 9 November 2026.

## What changed

- Watch-list numbering is removed before matching/saving: `1) Anime`, `2. Anime`,
  `[3] Anime`, `(4) Anime`, `5] Anime`, `6 - Anime`, `7: Anime`, `8 (Anime)`.
  Markdown bullets/check lists are supported; empty numbered items are ignored.
- Actual numeric titles such as `86`, `91 Days`, `2.5 Dimensional Seduction` and
  `3-gatsu no Lion` are preserved. Meaningful brackets/parentheses, years and
  season numbers are kept. TXT titles no longer pass through the release-filename
  cleaner, which could discard a whole parenthesized title.
- UTF-8 (including BOM), UTF-16 BOM and Windows-1252 lists are read without silent
  replacement decoding. Unsupported encodings produce a helpful error. Lists
  are bounded to 4 MB.
- Duplicate keys handle case, spacing, punctuation, smart apostrophes and Unicode.
  Japanese titles retain their letters instead of all becoming an empty key.
  Season 12 remains different from Seasons 1–2.
- Preview skips repeated list names and repeated matched provider identities when
  Ignore duplicate entries is enabled. Existing aliases are recognized.
- Apply rechecks identity at write time, so repeated rows, repeated imports and
  different names resolving to the same provider entry do not create extra records.
  Updating a matched entry preserves local paths, notes, artwork and rating.
- Ambiguous names shared by different provider releases require review; they are
  not silently assigned to the first result.
- The same decoding/title logic is used by watched import, TXT subscriptions and
  the existing core TXT importer. Ignoring duplicate preview rows remains a user
  preference; turning it off does not require creating duplicate database entities.

## Cleanup applied to this library

The saved library contained 449 records. A preview was generated against the two
provided text lists before applying a backed-up repair:

- **171** list-generated titles corrected.
- **176** duplicate cards consolidated through **155** explicit series groups.
- **449** original records retained; no database record or media file deleted.
- Identities, provider IDs, root paths, notes, ratings, watch status and season
  records were compared with the backup and verified unchanged.
- The grouped Library view contains **272** series cards after cleanup.
- A second repair preview reports **0** further title corrections and **0** new groups.

Database backup:
`E:\Anime Details\data\backups\library_backup_20261109_145620_eb9b74aa.db`

Detailed local report:
`E:\Anime Details\data\text-import-repair-report.json`

Grouping keeps every duplicate record's original user data and associations; it
does not physically merge/delete records or combine different episodes/files.
Conflicting provider identities and existing explicit grouping decisions are
protected. Provider-backed or manually renamed titles are not blindly overwritten.

Restart the app to load the corrected library and updated import code. The same
text lists do not need to be imported again just to repair these saved titles.

## Implementation and checks

- `app/core/parser.py`: TXT-specific list-prefix removal, preserved title content.
- `app/core/text_import.py`: shared decoding, Unicode duplicate identity and index.
- `app/ui/dialogs/watched_import_dialog.py`: correct previews and duplicate checks.
- `app/core/entry_service.py`: write-time deduplication and safe existing-entry updates.
- `app/core/import_lists.py`, `app/core/scanner.py`: shared TXT parsing/lookup.
- `app/core/import_repair.py`: conservative preview, backup, atomic revalidation,
  title repair and non-destructive grouping.
- `scripts/repair_text_imports.py`: preview by default; `--apply` backs up before repair.
- `tests/test_text_import.py`: 10 focused regressions.

Validation: the full isolated suite passed **249 tests** in 41.362 seconds. The
focused import/repair suite also passed all 10 tests after the final conservative
provider-conflict guard. Compilation and whitespace checks passed. Tests cover
numbered titles, real numeric names, encodings, Japanese identity, write-time
deduplication, preserved user data, stale-plan rejection and repair idempotence.
