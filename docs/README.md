# Anime Vault documentation

Start with the [project README](../README.md) for installation, screenshots and current capabilities.

## Using the application

| Task | Guide |
|---|---|
| Set up built-in downloads | [Current download guide](DOWNLOADS.md) |
| Connect the selected-site Chrome extension | [Extension setup](../browser-extension/README.md), [browser capture design](history/BROWSER_MAGNET_CAPTURE.md) |
| Understand every feature and destination | [Feature/navigation map](guides/All%20Feature%20and%20their%20Navigation.md) |
| Organize folders | [Organizer usage](guides/ORGANIZER_USAGE.md) |
| Group and rematch seasons | [Series grouping](history/SERIES_GROUPING_AND_REMATCH.md) |
| Review file moves from Downloads | [Download retry and library moves](history/DOWNLOAD_RETRY_AND_LIBRARY_MOVES.md) |
| Understand episode/update timing | [Episode timing and progress](history/UPDATE_DETAILS_EPISODE_TIMING_AND_PROGRESS.md) |
| Review new-anime discovery | [Release news implementation](history/RELEASE_NEWS.md) |

## Reliability and development

- [Current audit: reproduced bugs, risks and acceptance checks](history/WHOLE_APP_AUDIT_2026-11-12.md)
- [Phase 1: identities and recoverable file operations](history/PHASE_1_DATA_SAFETY.md)
- [Phase 2: trustworthy scanning](history/PHASE_2_TRUSTWORTHY_SCANNING.md)
- [Applied earlier audit fixes](history/AUDIT_FIXES_APPLIED.md)
- [Changelog](../CHANGELOG.md)
- [Contribution and validation workflow](../CONTRIBUTING.md)
- [Security reporting](../SECURITY.md)
- [Repository discovery terms and sources](DISCOVERABILITY.md)

Implementation notes now live in [history](history/README.md), UI references in the
[design index](../design/README.md), and product/backlog notes in `planning/`.
See the [14 November code review and organization report](maintenance/CODEBASE_REVIEW_2026-11-14.md)
for verified recent changes, remaining risks and the proposed UI work order.
Older notes may describe the retired external-client workflow; follow the current
README and download guide for today's setup. Historical reports are not proof
that every edge case in the current app is resolved.

## Screenshot provenance

`screenshots/` contains actual PyQt renders generated with `python scripts/capture_readme.py`. All titles, abstract covers, paths and transfer statistics are fictional demo data. No real media is downloaded or played; no user's library database is opened. The generator requires the application's dependencies and bundled fonts, and uses a temporary database.
