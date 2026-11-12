# Anime Vault documentation

Start with the [project README](../README.md) for installation, screenshots and current capabilities.

## Using the application

| Task | Guide |
|---|---|
| Set up built-in downloads | [Current download guide](DOWNLOADS.md) |
| Connect the selected-site Chrome extension | [Extension setup](../browser-extension/README.md), [browser capture design](../BROWSER_MAGNET_CAPTURE.md) |
| Understand every feature and destination | [Feature/navigation map](../All%20Feature%20and%20their%20Navigation.md) |
| Organize folders | [Organizer usage](../ORGANIZER_USAGE.md) |
| Group and rematch seasons | [Series grouping](../SERIES_GROUPING_AND_REMATCH.md) |
| Review file moves from Downloads | [Download retry and library moves](../DOWNLOAD_RETRY_AND_LIBRARY_MOVES.md) |
| Understand episode/update timing | [Episode timing and progress](../UPDATE_DETAILS_EPISODE_TIMING_AND_PROGRESS.md) |
| Review new-anime discovery | [Release news implementation](../RELEASE_NEWS.md) |

## Reliability and development

- [Current audit: reproduced bugs, risks and acceptance checks](../WHOLE_APP_AUDIT_2026-11-12.md)
- [Phase 1: identities and recoverable file operations](../PHASE_1_DATA_SAFETY.md)
- [Phase 2: trustworthy scanning](../PHASE_2_TRUSTWORTHY_SCANNING.md)
- [Applied earlier audit fixes](../AUDIT_FIXES_APPLIED.md)
- [Changelog](../CHANGELOG.md)
- [Contribution and validation workflow](../CONTRIBUTING.md)
- [Security reporting](../SECURITY.md)
- [Repository discovery terms and sources](DISCOVERABILITY.md)

The root-level implementation notes and retained design folders document the evolution of the app. Older download notes may describe the retired external-client workflow; follow the current README and download guide for today's setup. An implementation note is not a claim that every edge case is resolved.

## Screenshot provenance

`screenshots/` contains actual PyQt renders generated with `python scripts/capture_readme.py`. All titles, abstract covers, paths and transfer statistics are fictional demo data. No real media is downloaded or played; no user's library database is opened. The generator requires the application's dependencies and bundled fonts, and uses a temporary database.
