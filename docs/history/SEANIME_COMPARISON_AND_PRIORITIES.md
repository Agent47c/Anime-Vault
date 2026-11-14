# Anime Vault and Seanime: review and improvement priorities

Prepared 5 November 2026. This is a proposal for review, not an implementation plan or authorization to add features.

## Scope and confidence

- Anime Vault: comparison against the current local source, existing tests and previously reviewed workflows. An implemented feature is not a claim that every real-world edge case is resolved.
- Seanime: official README, public scanner source and three official screenshots. Seanime was not installed or exercised end to end. Screenshots illustrate selected layouts, not every current screen.
- The repositories and website can change. Unverified features are marked accordingly rather than assumed absent.
- Preserve Anime Vault's approved appearance and all existing controls. New features below require approval. No streaming server or streaming controls are proposed.

## Feature comparison

| Area | Seanime evidence | Anime Vault today | Implication |
|---|---|---|---|
| Local indexing | Flexible scanning; file and folder context | Multiple roots, nested releases, loose videos | Strengthen correctness before adding scope |
| Matching | Weighted title, season, part, year and format comparison | Automatic matching and manual release assignment | Improve ambiguous-match explanations and tests |
| Episode numbering | Separate hydration with absolute/part-relative normalization | Continuing-series inventory and conservative gaps | Preserve original numbers and explicit mappings |
| User corrections | Scanner supports locked/ignored files | Manual rematching, grouping and numbering choices | Verify corrections survive every refresh path |
| Missing drives | Shelving can retain locked records from unavailable roots | Path repair and storage-state tracking | Add explicit unavailable-drive handling if incomplete |
| Automatic scans | Watcher, delayed scan triggering and overlap prevention | Startup guards, local/internet refresh and scheduled scans | Consider a watcher only after reliable incremental reconciliation |
| Watching | AniList lists and playback-related features | Local statuses, ratings, notes, last-played file | Local watch history is not bidirectional AniList synchronization |
| Playback | Built-in libmpv client plus external players | External player launching and episode chooser | Keep external-player setup simple |
| Calendar | Release schedule | Week cards, hover previews and availability notices | Make release confidence and stale data clear |
| Downloads | Clients, debrid, torrent/online extensions and automation | Not implemented | Optional future expansion, low priority |
| Manga | Reader and sources | Not implemented | Separate product expansion, low priority |
| Mobile/remote | Companion apps and browser playback/transcoding | Windows desktop focus | Not needed for the current local-library objective |
| Offline | Documented offline mode | Cached metadata/artwork and local refresh | Test prolonged offline use and retry behavior |
| File organization | Equivalent merge/recovery workflow not established in this review | Previewed organization, consolidation, journals and path repair | Keep and harden our existing workflow |
| Duplicates | Equivalent hash review not established in this review | Season/release-scoped size and SHA-256 review | Distinguish identical copies from alternate encodes |
| Storage and deletion | Equivalent reclaim/recycle workflow not established | Storage summaries, reclaim review and normal Recycle Bin deletion | Audit every deletion entry point consistently |
| Import/export | Full equivalence not assessed | TXT import, manual/custom matches, backup, JSON/CSV | Preserve these existing features |
| Setup | Desktop distribution; optional service integrations | Source launch and an existing PyInstaller build script | Package and validate the actual end-user experience |

## Ranked improvements

Order reflects the user's history of moved files, incorrect grouping, One Piece numbering and HDD pauses. Effort is relative and requires a focused design before implementation.

| Rank | Improvement | Why / exact behavior | Acceptance check | Scope / effort |
|---|---|---|---|---|
| 1 | Stable identities and reliable path reconciliation | Keep series, release, episode and physical-file identity separate. A move changes a file's location without discarding watch history or changing the release. Do not auto-link ambiguous filename matches. | After an app-controlled move, Play, Open folder, artwork links and last-played references agree. Manual external moves produce confirmed repair candidates. | Backend hardening; large |
| 2 | Safe, recoverable file operations | Revalidate previews, prevent overwrites, record each completed move, update the database and recover after interruption. Audit duplicate removal separately: its current implementation uses permanent unlink, unlike normal Recycle Bin deletion. Propose consistent Recycle Bin handling subject to approval. | Interrupt a merge after several files; reopen and reconcile without losing files or reporting false success. Permissions failures remain visible and retryable. | Hardening; medium–large; deletion behavior change needs approval |
| 3 | Correct episode identity and release-aware gaps | Retain the filename number plus numbering scheme and verified release mapping. Aggregate the correct folders for continuing series. Separate aired, upcoming and unknown-release episodes. | One Piece with split arcs and root files reports only genuine gaps; S1E10 and S2E10 remain distinct; future episodes are never described as missing downloads. | Hardening; large |
| 4 | Persistent matching decisions and review of ambiguity | Combine filename, nearest meaningful folder, season/part, year and format. Keep confirmed user matches. Show unresolved items instead of silently choosing a weak match. | Dr. Stone S4 cannot silently become S1; a movie does not relabel the parent series; a local refresh preserves manual corrections. | Existing workflow hardening; medium–large; new review UI needs approval |
| 5 | Incremental indexing and unavailable-drive state | Compare saved inventories with local changes; process only changed files where possible. Differentiate offline/inaccessible roots from deleted files. Add a debounced watcher only if approved. | Unchanged startup makes no metadata requests; an unplugged drive preserves entries and history; reconnecting restores availability. | Hardening plus optional new watcher; medium–large |
| 6 | Responsive operations with measurable budgets | Keep file enumeration, hashing, API requests and disk writes off the UI thread. Bound workers for HDDs; cancel stale searches and ignore late results. | Measure event-loop stalls during sorting, theme changes, scans and hashing on representative large libraries. Target no recurring stalls over 100 ms; record hardware and worst cases. | Performance hardening; medium |
| 7 | Predictable metadata and artwork caching | Cache by provider identity and artwork version; show saved images immediately. Deduplicate requests, back off on errors and avoid retry loops when a provider has no banner. | Reopening the same cached anime requires no image download; switching heroes never shows another anime's image; a missing provider banner has a stable fallback. | Hardening; medium |
| 8 | Simple installer and persistent user data | Bundle the runtime, Qt plugins, fonts and assets. Store writable data independently of installed files; migrate existing data with backup. Admin remains optional. | Clean Windows account without Python can install, choose folders and play. Updates retain the database and cache. Test names with spaces/non-Latin characters and standard-user permissions. | Distribution work; medium–large |
| 9 | Clearer existing UI states | Present On disk, Partial, Unavailable drive, Missing and Upcoming consistently. Show a scan summary, useful failure messages and restrained primary actions. Keep all existing actions reachable. | Users can explain what needs attention without reading logs; no ambiguous success after zero files moved. | Presentation hardening; medium; new summaries need approval |
| 10 | First-run guidance and diagnostics | Propose a short folder/player/scan flow; optional diagnostics export with private paths/tokens redacted. Avoid asking for accounts or advanced tools for local use. | A first-time user reaches the library without a terminal, config-file editing or unnecessary setup choices. | New UX features; approval required; medium |
| 11 | Optional AniList progress synchronization | Useful for users with AniList accounts; requires explicit sign-in, conflict handling and an offline queue. | Local history is never overwritten silently; synchronization can be disabled. | New feature; approval required; large |
| 12 | Optional playback queue and verified resume position | Episode queues could improve binge watching. Exact timestamp resume needs player integration; last-launched file alone cannot prove how much was watched. | Resume uses a verified saved position when supported, otherwise clearly offers replay of the last file. | New feature; approval required; medium–large |

## UI insights from the inspected Seanime screenshots

These are visual observations and recommendations, not a usability test or a proposal to replace Anime Vault's design.

| Order | Observed pattern | Adaptation for Anime Vault | Permission |
|---|---|---|---|
| 1 | Prominent “Resolve unmatched (2)” action in the library screenshot | A compact Needs review count opening existing matching workflows, so unmatched files do not disappear into a large library | New entry point; approval needed |
| 2 | Small episode-progress overlays on posters | Optional “17 available” or “17 / 19 aired” badges using verified inventory; never label last-launched as watched progress | New displayed metric; approval needed |
| 3 | Large continuation cards with secondary episode information | Keep our hero composition, but simplify its subtitle to season/episode and move long release filenames into tooltips | Restyle existing data |
| 4 | Strong artwork-to-dark-background fade | Retain our readable scrim, bound title width and provide a deliberate fallback when artwork is unavailable | Existing UI refinement |
| 5 | Poster titles and secondary information have a stable hierarchy | Consistent two-line title area, aligned card bottoms and full-title tooltips in grid and list views | Existing UI refinement |
| 6 | A summary strip exposes library size/files/entries | Consider a small optional summary, using existing counts and sizes without additional disk scans | New presentation element; approval needed |
| 7 | Rich filters are separate from the poster content | Keep common filters visible; propose More filters for genre/year/format only if wanted. Preserve all current filters | New filters need approval |
| 8 | Continue watching can include several recent series | Optional recent-series row; keep the current main hero and its Resume action | New feature; approval needed |

Do not copy the entire interface: its icon-heavy navigation and many simultaneous filters serve a broader application. Keep Anime Vault's labelled sidebar and approved red/indigo design. Preserve keyboard access and visible click targets; hover previews must never be the only way to reach an action.

## Suggested review batches

1. Data safety: ranks 1–3. Verify file operations and episode identities before adding convenience features.
2. Trustworthy scanning: ranks 4–7. Preserve corrections, avoid unnecessary work and explain uncertainty.
3. Release readiness: rank 8 and the relevant parts of 9–10. Produce an easy clean-machine installation.
4. UI polish: existing UI refinements above; separately approve any new counts, filters or rows.
5. Optional expansion: ranks 11–12. Defer manga, torrent/debrid integration, plugins and remote streaming unless explicitly requested.

Already implemented foundations should be tested and strengthened, not rebuilt merely because they appear on this list. No application features or backend behavior were changed for this report.

## Evidence

- Official features and scope: https://github.com/5rahim/seanime#features
- Setup guide index: https://seanime.app/docs
- Matching implementation: https://github.com/5rahim/seanime/blob/main/internal/library/scanner/matcher.go
- Scan preservation and shelving: https://github.com/5rahim/seanime/blob/main/internal/library/scanner/scan.go
- Episode normalization: https://github.com/5rahim/seanime/blob/main/internal/library/scanner/hydrator.go
- Automatic scanning: https://github.com/5rahim/seanime/blob/main/internal/library/autoscanner/autoscanner.go
- Official UI screenshots inspected: https://seanime.app/ (main, scanner, discover/airings promotional images). The image linked as airings depicts discovery, so no claim about the calendar layout is inferred from it.
- Local: app/core/scanner.py, matching.py, series.py, library_health.py, organizer.py, consolidation.py, duplicates.py, recycle.py; app/ui/pages/library_page.py; app/config.py; build_exe.py; tests/.
