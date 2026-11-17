# Download confirmation and manual ingest

15 November 2026. Two new reference folders bring the supplied Manga count to 31.

- Confirm Selected Downloads styles the existing ConfirmCoverage form: a white
  confirmation canvas, release type/season, one pale card per selected release,
  episode inputs, alternate-title memory and the existing Confirm match action.
  Season zero retains its continuing/absolute meaning. Validation and callbacks
  remain unchanged; confirmation alone does not start a download.
- From Download Transfer Engine, only **Search & Auto Ingest** is used for the
  manual Add Magnet / Torrent route. It reuses the editable title, season,
  episode targeting, source URL, group/quality, seeding, website search, magnet
  input, torrent picker and submission handler. Configuration and queue widgets
  are retained internally for existing handlers but hidden in this presentation.
  Settings and Downloads retain their complete interfaces. No engine/extension/
  speed-limit or tracked-queue panels were copied into this screen.
- The redundant hidden queue timer is stopped while using this Manga form.
  The normal Downloads monitor remains available. Sakura presentation is intact.
- Fix native spinbox editors inheriting oversized search-field effects and
  minimum heights; their text remains visible inside the actual spin control.

Focused tests exercise distinct episode assignments, preservation of manual
input/configuration controls and isolation of Settings-only configuration.
Both screens were rendered with temporary data. Existing local transfer tests
require socket access; results are recorded in the changelog. No installer build
or personal database/media changes were performed.

The refreshed [reference inventory](MANGA_SCREEN_REFERENCE_INVENTORY.md) lists
remaining layouts, rather than repeating screens supplied in earlier batches.
