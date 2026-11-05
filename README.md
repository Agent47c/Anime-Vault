# Anime Vault

**Version 1 — v1.0.0** is the baseline before the next improvement cycle.

A Windows desktop anime library and storage manager built with Python 3.13,
PyQt5 and SQLite. Metadata comes from AniList and Jikan.

## Existing features

- Series library with seasons/arcs, metadata, cached artwork and manual rematching.
- Episode browser, local availability checks and external-player launching.
- Release calendar, update review and persistent update preferences.
- Previewed folder organization, multi-root consolidation and path repair.
- Storage review, duplicate-file checking and confirmed file removal.
- Watched TXT import, custom entries, ratings, notes, backups and JSON/CSV export.
- Theme, accessibility, media-player and application-behavior settings.

## Run from source

Use Windows and Python 3.13:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Choose your own library roots in the app. The repository does not include a
personal database, watch lists, credentials or cached media. `.env.example`
documents optional configuration; normal use does not require editing it.
An external video player is needed to play files. FFmpeg is optional for
episode-frame artwork extraction. Administrator mode is optional.

The current source also starts a local FastAPI service. This baseline preserves
existing behavior; it does not add streaming setup screens.

## Validate before pushing

```powershell
python scripts/check.py
```

This compiles the Python source and runs the full unittest suite with Qt's
offscreen platform and a fresh temporary database, independent of your library.
It does not replace manual Windows visual testing.

Enable the included local push guard once per clone:

```powershell
git config core.hooksPath .githooks
```

The guard runs the same command before every push and stops on failure.
GitHub Actions independently runs it on pushes and pull requests.
Local hooks can be bypassed; repository branch protection is required to enforce
passing CI before merges. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Development and versions

- Preserve the `v1.0.0` Git tag as the original version 1 baseline.
- Make improvements on feature/fix branches and review pull requests into `main`.
- Update the changelog and version for subsequent releases.
- Preview file operations and back up your database before testing against real media.

The existing `build_exe.py` is a packaging starting point. A clean-machine-tested
installer is not supplied by this baseline. This repository is Windows-focused;
other operating systems are not currently validated by CI.

## Reference documents

- [Version history](CHANGELOG.md)
- [Organizer usage](ORGANIZER_USAGE.md)
- [Proposed improvement priorities](SEANIME_COMPARISON_AND_PRIORITIES.md)
- [Phase 1 implementation and complete change record](PHASE_1_DATA_SAFETY.md)
- `anime-vault-ui/` contains design reference HTML, not the Python application's runtime.
