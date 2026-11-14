# Release news and anime timelines

Navigation:

- Library → anime Details → **Check release updates**.
- Updates → **New episode updates** selects the existing episode category.
- Updates → **New anime releases** opens discovery.
- Discovery → **Release details** opens that anime's timeline.
- Timeline → related prequel/sequel → **Release details**.

Discovery offers releases from the past 30 days or upcoming premieres within
90 days, with Previous/Next pagination. This is premiere-date discovery, not a
general news feed or every new episode. Existing Updates filters/actions remain.

Timelines show the anime synopsis, first official release date, provider status,
related prequel/sequel premiere dates, and paginated published episode schedules.
Dates/times use the computer's timezone. Future items say Scheduled, past items
say Aired, and unknown date components remain question marks. Historical schedules
can be incomplete; episodes or weekly dates are never extrapolated.

**Import as Watching** creates a metadata-only library entry and release record,
marks it Watching and publishes an Update card. No folders/files are created.
Existing provider IDs return Already in library without overwriting watch status,
notes, files or manual season mappings. Artwork uses the existing artwork loader.

Implementation reuses navigation, IOTask, AniList pacing/cancellation, transfer
panels/theme, FlowLayout, database helpers, artwork loader and change notifications.
No startup discovery request is added. Network requests and imports run in workers;
closed/stale page callbacks are ignored. Opening discovery, changing its filters
and navigating saved discovery pages use persistent SQLite results only.
Results do not expire after an hour or become unreachable on a new calendar day.
For discovery, only **Check updates** makes a release API request. An uncached filter/page explains
that it must be fetched first; it does not imply nonexistent saved data is available.
Failed refreshes show the last saved results with a warning and retain their original
last-checked time. Compatible older date-keyed entries are reused automatically.
Adult-content preferences still apply to cached discovery results.

Clicking **Release details** is an explicit request for that selected anime: a
missing timeline/page is fetched automatically in the background and cached.
Later visits reuse the saved timeline; Check updates refreshes it manually.
No extra click is needed on the first visit. Selection uses the clicked provider
ID, and the local-season lookup connection closes immediately after reading.

Release thumbnails reuse the existing provider/URL-version artwork cache on disk
(`data/covers`, indexed by `artwork_assets`). Opening a saved page loads images in a
worker without network access, including when a thumbnail is missing. A successful
explicit Check updates may fetch missing/new-version images, with the existing
deduplication, image validation and retry backoff. Existing valid images are reused.

Files: `app/core/release_news.py`, `app/ui/pages/release_news_page.py`, Details
and Updates navigation hooks, `tests/test_release_news.py`.

Validation: 3 release-news tests and 12 transfer-screen regressions passed.
Checks cover caching/failure retention, duplicate imports, Watching/no-files state,
announced status and aired/scheduled rendering. Compilation passed. Live provider
responses were not exercised in this pass.

Cache repair validation: 32 targeted release-news, release-addition and trustworthy
scanning tests passed. Tests cover first-open/no-cache behavior, explicit fetch/save,
reopening across calendar days, old cache-key migration, timeout fallback, and disk
thumbnail reuse with no repeat download. Provider responses are mocked; a successful
online check is needed before a never-fetched filter/page can have saved results.

API references: https://docs.anilist.co/reference/object/airingschedule and
https://docs.anilist.co/reference/object/media . AniList only guarantees future
airing data; historical completeness is not assumed.

## Issues Found & Fixed

- **GraphQL `FuzzyDateInt` type mismatch (`app/core/release_news.py`)**:
  `discover()` declared `$from:Int` and `$to:Int` instead of `FuzzyDateInt` for
  `startDate_greater` / `startDate_lesser`, causing AniList to reject live
  New anime releases queries with HTTP 400 Bad Request. Fixed by declaring
  `$from:FuzzyDateInt` and `$to:FuzzyDateInt`.
- **Month-boundary date arithmetic (`app/core/release_news.py`)**:
  `int(lower.strftime('%Y%m%d')) - 1` produced invalid calendar day `00` on
  the 1st of a month (e.g. `20261100`); replaced with `(lower - timedelta(days=1))`.
- **Hidden GraphQL/HTTP failure causes (`app/core/anilist_client.py`,
  `app/core/release_news.py`)**: `_graphql_request()` previously discarded
  HTTP 400/429/GraphQL error messages and returned bare `None`, causing `cached()`
  to always show the same generic failure text. Added per-thread `last_error()`
  diagnostics (preserving the `None` return contract) and surfaced the reason
  inside `cached()`, plus safe handling for corrupted cache JSON and offline mode.
- **Nullable response guards (`app/core/release_news.py`,
  `app/ui/pages/release_news_page.py`)**: Guarded nullable `Page`, `media`,
  `pageInfo`, `relations`, and `airingSchedules` fields before rendering.
