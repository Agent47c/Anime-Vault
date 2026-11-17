# Review: Anime World simplified download flow

Reviewed 16 November 2026 against the current source.
Source document: `anime-world-download-flow.md` supplied by the user.
Status: historical review. The user's subsequent decisions supersede the
recommendations below. See [approved implementation](../CONFIRMED_DOWNLOAD_FLOW.md):
preserve filenames with database assignments, no old-data migration, optional
completed movement, Replace/Skip/another-copy choices, remove Download Missing
Episodes, and Auto-Grab searches followed by user confirmation.

## Verdict

The shared-context / single-confirmation direction is useful. The most important
technical improvement is making the confirmed **per-file episode mapping** the
authority through completion and movement. Reducing screens alone will not fix
incorrect associations if completion still reconstructs them from filenames.

The proposal should not be implemented unchanged. It conflicts with approved
continuous numbering, manual completed-file movement and existing automatic
download features. Its suggested replacement schema is also narrower than the
app's existing identity/history model.

## Decisions required before implementation

| Plan change | Existing requirement / behaviour | Recommendation |
| --- | --- | --- |
| Always use season-relative numbering throughout the app | User explicitly requested keeping episode 177 as 177, with an independent destination season | Preserve continuous numbering as a valid mode. Offer an explicit, verified mapping to season-relative numbering; retain the original number |
| Automatically move files when the torrent finishes | Current approved flow is Download completed → user reviews → user moves | Keep manual movement by default. Automatic movement is a separate opt-in feature requiring approval |
| Remove Download Missing Episodes because it does nothing | `ReleaseSearchPage.missing`, `download_discovery.missing_plan` and `release_actions.auto_grab` are working paths; automatic download additions were approved earlier | Keep or relocate their functionality unless removal is explicitly approved. Do not call them dead controls |
| Replace an owned episode from confirmation | Current duplicate checks prevent accidental overlapping downloads; file moves never overwrite | Default to showing the existing file / cancelling. A replacement workflow needs explicit rules and approval |
| One locked anime for a torrent, but Naruto + Shippuden packs in the same torrent | Those are different group identities, not merely different season numbers | Keep anime fixed for normal downloads; multi-anime packs need explicit per-group identities and a separate advanced interaction |
| Automatically remap and merge existing episode 177 records | Existing absolute numbering may be intentional and valid, with history attached | No silent migration. Produce a preview, preserve IDs/history and apply only user-approved or previously verified mappings |

## What already exists and what would change

| Area | Current app | Plan review |
| --- | --- | --- |
| Search from Details, Updates and episode selection | Shared release-search entry exists, but several routes pass only the anime ID | Carry the exact local release and requested episode across routes; do not lose them in navigation |
| Known-anime confirmation | ConfirmCoverage already displays a fixed anime and editable per-release season/episode fields | Reuse it rather than creating another independent form |
| Search results and uncertainty confirmation | Match confirmation and a separate download review are both present | They can become one decision surface, retaining alias validation, overlap checks and final submission acknowledgement |
| Browser/pasted magnets | Existing anime picker and ingest flows are separate from source-search confirmation | Share the controller and assignment form. A known magnet does not need a mandatory search-page detour |
| Torrent metadata | Normal submissions fetch metadata through the built-in client | Packs need metadata/file inventory before file-level confirmation, with payload transfer held until confirmed; do not restore a mandatory second Choose Files gate for normal episodes |
| Job identity / retries | Stable tracked job IDs, torrent identities, durable submissions and retry-in-place already exist | Extend those records with per-file bindings; do not replace job IDs with an info-hash-only primary key |
| Completion | `_index_completed` indexes a verified file inventory, then `identity.sync_season` can derive episode numbers from filenames for newly registered files | This is the key gap: persist confirmed file-index/release/episode bindings and consume them at completion |
| Existing file mapping | Already registered physical files retain their established episode links | Extend that immutability to newly completed, explicitly confirmed files; use filename inference only for unconfirmed external imports |
| Logical episode identity | Existing `episodes` are unique by release and identity key; physical files link many-to-many through `file_episodes` | Preserve this model so alternate encodes and a file covering multiple episodes remain representable |
| Numbering | Original numbers, numbering scheme, release number, verification/source fields already exist | Add explicit mapping evidence/offset only where needed, without inventing a second parallel episode database |
| Custom query / aliases | Saved custom queries and alternate-title memory exist | Parameterized per-release templates and success/provider/style history would be an extension, not a rename |
| Missing coverage | Local/pending/missing episode keys and coverage views exist | Reuse these for result highlighting, with freshness checks against current jobs/files |
| Release schedules | Cached release/broadcast pages exist | A compact confirmation card is new UI. Reuse cache/services; show only known data |
| Completed-file movement | Reviewed source/target moves, identity updates and recovery exist | Reuse the move service and its manual default; do not bypass it in a new completion callback |
| Folder identity | Main-root selection, path normalization and existing-season reuse exist | A single resolver is useful, but AniList IDs alone cannot prevent path aliases or duplicate local roots |

## Corrections to the proposed rules

### Numbering and offsets

Do not assume every prequel relation contributes to a single linear episode
offset. A relation graph can include movies, specials, split releases, branches
and incomplete episode counts. The supplied Black Clover numbers are examples,
not verified mappings for migration.

Use a verified mapping belonging to the specific release. If there is no such
mapping, keep the detected number and show the ambiguity. A user-selected offset
can be remembered with its source and scope. Continuing series must remain
continuing series unless the user chooses a conversion.

Store original numbering and the confirmed logical identity separately. A
physical folder called Season 1 does not decide whether 177 means absolute
episode 177 or a season-relative episode.

### Confirmation versus payload filename

The proposed `Saving to: .../Episode 07` is misleading unless actual filename
renaming is approved. Show both:

- **Association:** Season 2, episode 7; original absolute number 177 if mapped.
- **Files:** actual staging and intended library paths, preserving the original
  torrent filename and relative companion-file paths.

Do not rename existing folders simply because the provider entry changed or
because an offset was edited.

### Airing data is guidance, not proof of a fake torrent

Cached provider data can be missing, stale or refer to a different release
schedule. Show known dates, timezone and freshness. Unknown is not Unreleased.
Do not extrapolate future weekly dates or mark every episode Released just
because a series is finished.

A schedule discrepancy can prompt a warning. Hard-blocking selection based
solely on that data can reject legitimate files and needs a separate decision.

### Search fallbacks

The plan says both "no auto-search" and "try three queries in order." Define
whether Try another query is a manual step or automatic fallback. Prefer editable
manual suggestions first; additional requests should be cancellable and should
not discard the user's custom query or provider selection.

Do not calculate an absolute-number suggestion from unverified season totals.
Save only a confirmed template; remember that an empty result can be temporary,
not evidence that the saved template is wrong.

### Context object

Use existing local IDs as the authority. AniList IDs are nullable external links,
not universal primary keys: custom/offline entries and grouped releases exist.
The context should support a local series ID, local release/season ID, optional
provider entry, an episode set/range, release type and numbering scheme.

Keep `source_screen` (Updates/Details/manual/magnet) separate from `provider`
(the search website). Pre-filled context is not yet a confirmed file mapping.

### Pack mapping

Persist `file_index → local release identity → episode identity/identities`.
A single aggregate episode list for the entire torrent cannot describe two
different seasons, combined-episode files and optional extras reliably.

Make range shortcuts convenience tools over the same explicit mappings. Unknown
extras must not become ordinary episodes. Keep selected subtitles/fonts with
their videos. Do not require a large pack checklist for a normal single episode.

### Data migration

Keep `library_series`, `releases`, `season_releases`, `episodes`, `physical_files`,
`file_locations`, `file_episodes` and `episode_history`. They already separate
logical episodes, physical versions and playback history.

The proposed `episodes(... file_path, status)` table cannot replace that model:
one episode can have multiple files, one file can cover multiple episodes, and
file paths change without changing episode identity.

Any migration must be additive and backed up, retain stable IDs, and be
idempotent. Unverified offsets/mappings should enter a review report, not a
destructive automatic conversion/merge.

## Recommended implementation order

1. Define the shared local context and preserve exact release/episode hints
   across Updates and Details routes. Keep existing download behaviour.
2. Persist and apply confirmed per-file mappings through the current job,
   completion, indexing and move services. Test mismatched filenames first.
3. Reuse the confirmation component for known and unknown-anime entry points;
   collapse duplicate steps only after preserving their validation/actions.
4. Add approved verified-numbering mapping controls; preserve continuous mode.
   Produce a migration preview without changing existing records automatically.
5. Extend saved templates and manual query fallbacks if approved.
6. Add approved pack/range mapping and explicit multi-release grouping.
7. Add the compact cached release-context card if approved.
8. Remove or relocate old controls only after a behaviour audit and user decision.

## Required acceptance checks

- Context is retained from every entry point, including a missing episode in Details.
- One final confirmation for a normal release; cancelling queues no payload.
- A misleading filename cannot override the confirmed per-file association.
- Continuous 177 remains 177 unless a verified/user-approved conversion is chosen.
- Absolute 177 and seasonal 7 deduplicate when their mapping is verified, without
  deleting alternate encodes or playback history.
- Movies, specials, combined-episode files, custom/offline entries and packs work.
- Metadata delay/cancellation does not start an unconfirmed payload transfer.
- Existing failed transfers retry in place rather than creating duplicate jobs.
- Ownership/readiness and stale scan/move protections remain intact.
- Existing physical files, folders and playback IDs survive any migration.

## Review boundary

Only the separate duplicate watched-path fix is implemented in this pass.
The flow redesign, automatic movement, numbering conversion, new schedule card,
template expansion, replacement workflow and database migration remain proposals.
