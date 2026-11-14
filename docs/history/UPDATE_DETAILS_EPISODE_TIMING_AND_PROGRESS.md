# Update details, episode timing and refresh progress

Implemented 12 November 2026.

## Open details

- Added **Open details** immediately beside **Refresh data** in View changes.
- Reuse the existing asynchronous Details page and navigation history. Back
  returns to the same update view. Refreshing can continue while viewing details.
- Preserve the primary series ID explicitly when a review covers several grouped
  entries, rather than relying on the order of a set of member IDs.

## Episode 20 versus episode 21

The checker was not adding one to the number. It copied AniList's
`nextAiringEpisode.episode` into an undated “airing soon” message. That field is
the **next** airing schedule, not the latest confirmed broadcast. See the
[official Media reference](https://docs.anilist.co/reference/object/media) and
[AiringSchedule reference](https://docs.anilist.co/reference/object/airingschedule).

A read-only check of the user's cached metadata/calendar found:

- Episode 20: 12 November 2026, 20:26 local time, already aired at inspection.
- Episode 21: 19 November 2026, 20:26 local time, the next scheduled broadcast.

Changes:

- New `app/core/episode_updates.py` identifies the latest aired episode and the
  earliest upcoming episode using actual saved timestamps for the same provider
  media ID. It never guesses the previous episode by subtracting one.
- Before episode 20's broadcast, a saved schedule for episode 20 takes precedence
  over a provider next-episode value already advanced to 21. After that broadcast,
  show episode 20 as aired and episode 21 as scheduled, with dates and local times.
- Missing broadcast times are labelled unverified. Future episodes are not called
  aired, missing downloads, or available files.
- Reuse the existing updater/publish/dismissal rules. Stable upcoming notification
  tokens remain compatible with previous dismissals; dated presentation distinguishes
  aired and scheduled entries. Aired rows also remain under the Episodes filter.
- Opening an update review can reconcile its old next-only message from existing
  cached metadata and schedule history in a worker, without an internet request.
  Existing dismissals are respected. Subsequent explicit metadata refreshes use
  the same timing logic.
- Update-card schedule presentation is cached with a per-anime signature; saved
  update dispositions retain that presentation data instead of losing dates.

## Bottom-edge loading bar

- Add a four-pixel themed progress bar at the bottom edge of the main app.
- Local Library refresh, internet sync and metadata update workers use their
  existing progress signals. Show indeterminate progress when no total is known,
  otherwise display actual reported current/total values.
- Keep the bar in the main shell so navigation does not hide it. Track overlapping
  refresh jobs separately; finishing one job does not hide another running job.
- Hide it after completion, failure or cancellation. Explicit **Refresh data**
  in View changes also participates. Keep the existing task banner and shutdown
  protections intact.

## Validation

- Added integration coverage for Open details placement, grouped identity and Back.
- Added cases for before/after-airing timestamps, unknown times, unrelated media
  IDs, cached correction without network calls, preserved dismissals and overlapping
  progress tasks.
- The focused run passed 37 tests. A read-only preview of the real cached entry
  showed “Episode 20 aired” and “Episode 21 scheduled” with the dates above; it did
  not alter the real database.
- Full validation log: `data/details-episode-timing-progress-validation.log`.
- Compilation and all 502 isolated tests passed in 127.846 seconds; the existing
  500-file scanner fixture recorded a maximum heartbeat delay of 40.5ms.
- Rendered and visually inspected the complete app at 1280×850 using a temporary
  database. Open details and Refresh data were beside each other. The bottom bar
  occupied `(0, 846, 1280, 4)` and the review showed episode 20 aired versus episode
  21 scheduled. The simulated progress preview did not run a real media scan.
