# TXT list presence and automatic import matching

Updated 9 November 2026.

## Both supplied files checked

| Source | Title lines | Already in library | Present, match review needed | Missing after check |
| --- | --- | --- | --- | --- |
| `E:\Anime Library\Deleted Seen Anime 1.txt` | 174 | 171 | 3 | 0 |
| `E:\Anime Library\Seen And Deleted Animes.txt` | 104 | 103 | 1 | 0 |
| Total list lines | 278 | 274 | 4 | 0 |

These are source-line counts, not 278 different anime. The two files overlap and
use both English and Romaji names. **Every listed line is now represented.**
Presence does not mean every title already has verified online metadata.

Three absent versions were added after a database backup:

- Fairy Tail (2018) Season 1 → confidently matched to AniList's **Fairy Tail Final Season**.
- Hunter x Hunter (2011) → confidently matched to its 2011 release.
- Fairy Tail (2009–2014) Seasons 1–8 → added as a custom entry needing review;
  a multi-season collection is not silently assigned to one release.

Four source lines still point to multiple existing records (three occurrences of
The God of High School Season 1 and one packaged Bleach listing). They are present,
but the importer reports the ambiguous match instead of creating another copy or
overriding earlier grouping decisions.

Backup before adding missing titles:
`E:\Anime Details\data\backups\library_backup_20261109_151344_9608b339.db`

Local, line-by-line reports (not intended for source publication):

- `E:\Anime Details\data\TXT_LIST_PRESENCE.md`
- `E:\Anime Details\data\text-list-presence.json`

The source TXT files were not edited. Existing local paths, notes, ratings and
watch status were compared with the backup and preserved. All pre-existing season
rows were retained unchanged. During the live check, seven existing records also
received metadata/title updates and eight season rows appeared outside this
missing-title addition. Those concurrent app changes were left intact; this audit
does not claim that the entire live database stayed frozen during the check.

## Import preview changes

- Existing anime are **shown**, not silently skipped when duplicate prevention is on.
- Four summary tiles: Already in library, Metadata matched, Need review, Not found.
- Filter: All titles, Already in library, New / needs match, Duplicate lines.
- Repeated lines remain visible as Duplicate line, unchecked and non-applicable.
- Already-linked entries are unchecked by default when duplicate prevention is on.
  Users can intentionally select an existing entry to update the chosen watch status.
- New saved option **Find metadata for existing unmatched titles** defaults on.
  Turning it off avoids online rematching of existing custom/unmatched entries.
- Online search runs in the import worker and supports cancellation. Merely viewing
  a preview does not change database metadata.
- Confident matches are selected according to the existing auto-select preference.
  Users click Apply to save. Ambiguous results require Choose match / review.
- Provider metadata, artwork and aliases can be added to an existing record without
  deleting its ID, moving seasons, replacing local paths, or overwriting notes/rating.
- A provider ID already owned by another record uses safe series grouping rather
  than deleting the imported local record.

## Python name cleanup and matching

- Number prefixes are handled by the existing numbered-list parser.
- Known uploader tags such as ASW, EMBER, Judas, Kayoanime and AnimeRG are removed
  for matching, together with resolution/codec/audio/batch packaging.
- Complete Series / Complete and episode-range packaging do not become series names.
- Meaningful years, season numbers, Japanese text and actual title numbers remain.
  `[Oshi no Ko]`, `86`, `91 Days` and `Pseudo Harem` are not stripped as release junk.
- Cached provider titles and synonyms help recognize existing anime without a new
  network search. This is not a fuzzy first-result lookup.
- Up to five provider candidates are checked against existing matching evidence:
  title, season/part, year and format. Close alternatives and conflicts veto automatic selection.
- Collections spanning several seasons remain review items instead of being linked
  to one arbitrary season.
- Confirmed TXT names are saved as persistent aliases tied to stable series identity
  and the current provider link. Thus a provider display-name change does not make
  the next import create another copy. Deleted/reused IDs or changed provider links
  invalidate stale aliases.
- Duplicate checks happen again at Apply time, including a provider link added by
  an earlier row in the same import.

## Use

Restart Anime Vault. Open Ctrl+I → Choose TXT file. Check **Already in library** to
inspect existing entries, or **New / needs match** to focus on unresolved names.
Keep Find metadata for existing unmatched titles on to find matching suggestions.
Review uncertain results and click Apply only for the changes you want saved.

The supplied lists do not need to be reimported just to add their missing titles:
the three absent entries have already been added safely.

## Implementation and validation

Changed/added: `app/core/text_import.py`, `import_matching.py`, `import_preview.py`,
`text_list_audit.py`, `entry_service.py`, `app/preferences.py`,
`app/ui/dialogs/watched_import_dialog.py`, `scripts/check_text_lists.py`,
`tests/test_import_presence.py`, and the existing import preference/parser tests.

Full validation passed **261 tests** in 42.640 seconds, including 12 new
presence/matching regressions. Scanner heartbeat maximum was 35.2 ms for the
500-file fixture. Compilation/whitespace checks passed, and the 560px import
drawer was rendered and visually checked. A live AniList check verified two of
the newly added versions; no uncertain collection mapping was applied.
