# Standalone Windows installer — 13 November 2026

## Delivered artifact

- `dist/installer/AnimeVault-Setup-1.0.0-windows-x64.exe`
- Size: **56,216,536 bytes** (about 56 MB / 53.6 MiB).
- SHA-256: `dd34ef534f9a766ebe6cf5c1ca533201ddbdc736086dee773c195ffff904bbc2`.
- The neighboring `.exe.sha256` identifies the exact setup file.
- The installer is **unsigned**. Windows can show an unknown-publisher/SmartScreen warning.

This artifact was rebuilt after the [download/discovery/backup fixes](DOWNLOAD_DISCOVERY_BACKUP_FIXES.md).
The previous setup is preserved as
`dist/installer/previous/AnimeVault-Setup-1.0.0-before-experience-fixes.exe`.
The rebuilt payload passed the standalone smoke check with Python removed from
PATH; see `data/experience-frozen-package-check.json` and
`data/experience-frozen-validation.log`. It was not installed on the user's PC.

This setup was compiled with the official **Inno Setup 7.1.1 x64** compiler. The
downloaded compiler's Authenticode signature was verified as valid, publisher
Pyrsys B.V. The application is bundled using **PyInstaller 6.22.3**, 64-bit Python
3.13, PyQt5 and libtorrent 2.0.15. Installing the finished app does not require
a separate Python or torrent-client installation.

## Data isolation

| Location | Purpose |
|---|---|
| `C:\Program Files\Anime Vault` | Installed program and immutable runtime/resources |
| `%LOCALAPPDATA%\AnimeVault` | Installed user's database, settings, artwork, logs and download-engine resume state |
| `E:\Anime Details\data` | Existing development data, not included or migrated by setup |

The setup contains no personal database, `.env`, watch list, downloaded media,
provider artwork cache or torrent state. Its input is the explicit bundled-resource
allowlist and built program files. Uninstall removes only installed program files
and shortcuts, leaving per-user data and media alone. Setup does not automatically
scan/import drives, configure Chrome, change URL handlers, or force-close the app.
Post-install application launch is unchecked by default.

Installed and source copies use independent database paths and lock files. An
existing source-app process was observed running separately during the build; it
was not closed. No exclusive, stable checksum attestation of that live database
is claimed. All application/restore tests were confined to temporary profiles;
the original database was not restored, replaced or bundled. Close the source
copy fully before your installed-app test to avoid competing API ports and media jobs.

## Implementation changes

- `app/paths.py`: separate bundled resources from per-user writable data; retain
  the source checkout's default data path. An explicit absolute environment
  override supports isolated build testing.
- `app/db.py`, `app/config.py`, `app/startup.py`, `app/audit_profile.py`: use the
  correct data/config/log locations in installed builds rather than Program Files
  or extraction directories. Database schema/business behavior stays intact.
- `app/startup.py`, `main.py`: hold the installed-application mutex for setup's
  orderly-close check; add an explicit temporary-profile `--self-test` mode before
  any ordinary configuration/logging/user-database consumer is imported.
- `app/core/builtin_torrents.py`: launch a separate **Qt-free native worker** in
  `engine/AnimeVaultTorrentHost.exe` for frozen builds. The original same-EXE worker
  crashed with native access violation because the GUI bundle runs Qt runtime
  hooks before dispatching command-line flags. The separate bundle passed real
  helper startup/save/close tests. Source-mode worker behavior stays the same.
- `app/core/chrome_bridge.py`: recover inherited binary pipe handles when the
  windowed EXE has no Python stdin/stdout. Preserve explicit error redaction and
  existing selected-site/extension authorization.
- `build_exe.py`, `requirements-build.txt`, `assets/app.ico`: reproducible two-bundle
  packaging, explicit resource allowlist, payload privacy guard, Windows metadata,
  multi-resolution icon, installer compilation and checksum output. Public certifi
  CA bundles are allowed; private-key/database/media files are rejected.
- `installer/AnimeVault.iss`: C-drive Program Files setup, elevation only for setup,
  optional desktop shortcut, Start menu entry, uninstaller and no user-data deletion.
- `app/packaging_checks.py`, `scripts/verify_windows_build.py`,
  `tests/test_installer_paths.py`: isolated source/frozen checks and regression tests.
- `docs/INSTALLER_GUIDE.md`, README and changelog: build, installation, data paths,
  backup/restore workflow, cache limitations and unsigned-build notes.

No new ordinary UI features were added, no existing UI feature was removed, and
no public torrent or live provider download was performed by the package checks.

## Verification

- **510 regression tests passed**, compilation passed; 125.9 seconds for the final
  suite. Scanner fixture maximum heartbeat gap: **45.3 ms** for 500 files.
- Actual frozen EXE: isolated first-run database and stable-identity tables exist.
- Temporary SQLite backup/restore retained the fixture note and rating.
- Bundled fonts, SVG controls, extension files and required notices exist.
- Actual separate libtorrent helper initializes and closes with public networking disabled.
- All six navigation tabs, Details and orderly shutdown passed in the packaged UI.
- Actual windowed Chrome host returns framed JSON and rejects an unregistered fixture caller.
- All packaged checks passed again with Python/virtual-environment directories
  removed from `PATH` and Python environment overrides removed.
- Payload privacy guard and source-publication hygiene check passed.
- Inno Setup compiled successfully; the final setup EXE and hash were generated.

The finished setup **was not installed on this PC**. Your real installation,
backup restoration, real-player playback and update/uninstall checks remain the
acceptance test requested. Open whole-app audit findings are not claimed fixed by
packaging. See [the installer guide](../INSTALLER_GUIDE.md) for the safe sequence.

Local evidence: `data/installer-final-validation.log`,
`data/frozen-package-check.json`, `data/frozen-verification.log` and
`data/installer-compiler.log`. These logs remain excluded from Git. No GitHub
release/upload or code push was performed during this installer task.
