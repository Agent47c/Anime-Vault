# Release update tracking correction — 15 November 2026

## Confirmed causes

The saved Black Clover record contained a releasing sequel with its own next
episode and timestamp. Its generic “Season 2 — Currently Airing” announcement
was in dismissed updates, not Later. The checker emitted that same announcement
on each refresh and checked episode events only for the original series. A
season-level dismissal therefore left no new episode notification to display.

The release overview also constructed an “Import as Watching” button
unconditionally. Its background lookup already knew some releases were in the
library, but the hero ignored that information. Import itself checked only the
top-level franchise provider ID, missing releases linked as seasons.

## Changes

- `app/core/updater.py`: produce separately dismissible episode events for
  related airing releases, with the release title in each event. Check explicitly
  linked release IDs during an existing online refresh, deduplicating requests.
  Do not turn metadata-only not-downloaded seasons into owned-file exclusions.
  Preserve pending updates if a linked release cannot be checked.
- `app/core/release_calendar.py`: retain dated next-episode observations from
  sequel/side-story/spin-off metadata as well as the root, without guessing an
  episode number or weekly schedule.
- `app/ui/update_release_dates.py`: format the correct related release's
  timestamp for qualified episode notices.
- `app/core/release_news.py`: use exact franchise and season provider identities
  to recognize existing entries; avoid duplicate imports and preserve their data.
- `app/ui/pages/release_news_page.py`: both discovery and release overview use
  that lookup before displaying import actions. Existing entries say “Already in
  library” and disable duplicate import immediately.

Dismissed announcements stay dismissed. Later, Not interested and Mute choices
are retained. New episodes have their own event text; dismissing episode 7 does
not suppress episode 8. Announced episodes are not labeled aired. No title-based
matching, database reset, media move, or installer build is involved.

## Validation and use

Six targeted regressions cover dismissal/new episode progression, mute, linked
seasons, announcements, persisted schedules, failure preservation, exact import
identity and the initial release-hero button. The existing release-news tests
also pass. Tests use temporary databases and mocked provider responses.
Full project validation passed **554 tests**; publication and whitespace checks
also passed. No new provider requests run merely to decide an import label.

Use **Refresh metadata** or **Refresh and sync with internet** to fetch and
publish current episode events. Local refresh does not contact AniList. Existing
provider timestamps determine whether an event is aired, scheduled or unverified.
