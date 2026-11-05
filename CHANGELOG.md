# Changelog

## Unreleased — Phase 1: Data Safety and Core Identity

- Added separately persisted series, release, episode and physical-file identities,
  episode-linked history/notes, verified number mappings and current file locations.
- Back up existing databases before identity migration; retain legacy season fields
  as a compatibility inventory rather than dropping existing user data.
- Journal each move durably and update references per file; reconcile interrupted
  moves on startup, with unresolved failures retained for review and retry.
- Require review for external-move repair candidates; never relink by filename alone.
- Route duplicate removal through the OS Recycle Bin with no permanent-delete fallback.
- Add release-state filtering to the episode browser and exclude future release
  boundaries from missing-episode reports.

## 1.0.0 — Version 1 — 2026-11-05

- Initial Git baseline of the existing Anime Vault application.
- Preserved library, episode, updates, organizer, merge, storage, import and settings workflows.
- Added shared local validation, a pre-push test hook and Windows GitHub Actions checks.
- Isolated the test runner from personal data with an initialized temporary database.
- Excluded private runtime data and documented development and release expectations.

This is a source baseline, not a claim that all proposed improvements or installer
acceptance checks are complete. Future work is listed separately in
`SEANIME_COMPARISON_AND_PRIORITIES.md`.
