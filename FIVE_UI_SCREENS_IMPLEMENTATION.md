# Five UI screens and approved additions

Reference folder: `5 ui screen`. Its five screenshots and HTML files were
inspected. Existing navigation, metadata matching, grouping, inventory rules,
personal fields, download identity and deletion safeguards remain in use.

## Screens

1. **Rematch Anime Metadata** — existing full-page workflow, linked-entry panel,
   larger artwork, full release titles, provider aliases/year/format, synopsis
   excerpt, confidence pill and existing local-season/metadata-only mapping.
   Continuing shows remain exclusive; multi-release matches still require review.
2. **Broadcast & Release Updates** — premiere/synopsis panel, related releases,
   paginated episode table, local times, aired/scheduled state and local/pending
   availability. Release checks now reuse persistent saved results until the user
   clicks Check updates; see RELEASE_NEWS.md for cache and thumbnail behavior.
3. **Group seasons and arcs** — searchable poster list, checkable entries,
   highlighted main series, review and reset. The separate grouping confirmation
   from the previous UI pass remains intact.
4. **Episode coverage & franchise breakdown** — native report panels, per-season
   inventory, conservative gaps, repeated-number/unrecognized-file notes, movie
   catalogue exclusions and metrics. Unknown boundaries do not become a fabricated
   completion percentage. Report preparation runs in an IO worker.
5. **New anime releases** — responsive release-card grid, cached artwork loaded
   off-thread, recent/upcoming/announced discovery, sorting, pagination, release
   details and existing Import as Watching behavior.

The mockups' profile identifiers, daemon versions, fake latencies, example
completion/encoding data and connection guarantees are not copied as real data.
Global navigation retains the current app controls.

## Additions explicitly approved in chat

- **Auto-Grab** searches the configured source for the clicked aired episode.
  It requires an existing verified release/season link and a confirmation. It
  ignores uncertain matches and multi-episode results, chooses a verified exact
  single-episode match by available seed count, and reuses the current queue's
  duplicate/local-coverage revalidation. Already local/queued episodes are skipped.
  This is an explicit button action, not an unattended recurring download rule.
  If verification or source parsing fails, use Find Download Files for review.
- **Notify me** persists one reminder per release and episode. The running app
  checks due reminders every minute and requests a tray notification. Overdue
  reminders can be delivered after reopening. Anime Vault must be running; no
  Windows scheduled task or background service was installed.
- **Filter rules** are the broadcast selector: All, Aired, or Scheduled. Filtering
  reuses the loaded response instead of querying the provider again.
- **Export breakdown (.json)** saves the current coverage report using the
  existing file chooser and IO-worker pattern.
- **Discovery controls** add newest/earliest premiere order, English title order
  and an Announced-only query that also permits unknown premiere dates. Sorting
  is applied by AniList across the query, not just within the visible page.

Actual source downloads, OS tray delivery and provider artwork vary with configured
Chrome/source access and provider availability; they were not exercised against
the user's live downloads during this pass.

## Files

- `app/ui/five_screen_style.py`: shared scoped presentation and theme fallbacks.
- `app/ui/dialogs/rematch_dialog.py`, `app/ui/pages/group_series_page.py`:
  existing matching/grouping UI presentation.
- `app/ui/pages/release_news_page.py`: broadcast/discovery presentation and actions.
- `app/ui/pages/coverage_page.py`: report presentation and export.
- `app/core/release_news.py`: announced discovery and validated provider sorting.
- `app/core/release_actions.py`: reminders and conservative explicit Auto-Grab.
- `app/ui/main_window.py`: running-app reminder polling.

Five temporary-data offscreen previews were rendered and visually inspected.
Broadcast action widths and rematch indicators were corrected after inspection.
The complete validation pipeline passed 419 tests; follow-up targeted checks
passed after final plain-text and source-selection adjustments.

Audit implementation and remaining work: `AUDIT_FIXES_APPLIED.md`.
