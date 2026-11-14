# Anime Vault standalone Windows setup

## Installation and data locations

- Program: `C:\Program Files\Anime Vault\AnimeVault.exe`.
- Installed app's own database: `%LOCALAPPDATA%\AnimeVault\library.db`.
- Installed caches, settings, backups and logs: `%LOCALAPPDATA%\AnimeVault\`.
- Development copy: its existing `E:\Anime Details\data\` stays separate.

Setup installs bundled Python/Qt/native dependencies; you do not need to install
Python separately. Setup needs Windows administrator permission to write Program
Files. The installed app normally runs without elevation.

The installer contains no personal database, watch list, credentials, downloaded
media or artwork cache. It does not copy a database from the development checkout
and does not scan/import your drives during installation. The installed app starts
with an empty profile unless you have already used this installed version.

Uninstall removes the program and shortcuts, **not your per-user database/cache
or anime files**. Updating the program also preserves this profile. If an older
version of Anime Vault is running during an upgrade, Setup automatically signals
and shuts down running instances (`AnimeVault.exe` and `AnimeVaultTorrentHost.exe`)
so existing files can be replaced without access-denied errors.

## Your backup/restore test

1. In the development app, stop transfers and scans and finish pending edits.
   Open **Settings → Database & Backups → Create backup**. Record the generated
   `.db` file path. Do not remove or move the development database.
2. Close the development app completely (not just to the tray), then run the setup
   EXE and install Anime Vault. Closing the other copy avoids a local API port
   conflict or two clients operating on the same media/download jobs.
3. Launch the installed app from Start. Its first library should be empty. Open
   **Settings → Database & Backups → Restore backup** and choose your saved `.db`.
   Restore targets the installed profile only and keeps its normal safety backup.
4. Review the restored titles, watch status, ratings, notes and history. Test Open
   folder, Choose episode and Play against a few files you know are present.
5. Quit and reopen the installed app, then verify the restored state is retained.
   You can later reopen the source app; its own database remains independent.

The backup stores database records, not your video files. Restored media paths
still point to their original locations (for example on E:). A database-only backup
does not include the image cache; metadata/artwork may need to be fetched again
when online. Transfer records and saved folder preferences are restored too: review
them before enabling downloads or performing organization/deletion operations.
To transfer artwork and native download resume metadata too, enable **Full
app-state backup (ZIP)** in the backup settings. Optionally enable **Include
cached posters, banners and thumbnails**, then create the backup and select
the resulting `.zip` when restoring in the installed app. Cache backups can be
very large; the app warns before creation. Videos and application binaries are
excluded. Folder paths remain references to the original drives, not file copies.
Keep downloads stopped while switching between development and installed copies.
Backups contain private paths, history and download metadata; store them securely.
Restore validates the archive first and retains a safety backup.

Existing audit findings still apply; packaging does not fix split-location season
counts or all restore/concurrency edge cases. Restore only with background work
stopped, as described above. No automatic migration, destructive cleanup or app
installation is performed by the build checks.

## Build and verify

Use 64-bit Python 3.13 on Windows, install `requirements-build.txt` in an isolated
build virtual environment, and install the official Inno Setup compiler:

```powershell
python build_exe.py --installer --iscc "C:\path\to\ISCC.exe"
```

Output: `dist\installer\AnimeVault-Setup-1.0.0-windows-x64.exe`, plus a SHA-256 file.
The payload is a one-folder application inside a single setup EXE, avoiding
one-file extraction on every app launch. Resources are bundled separately from
writable user data.
The native download worker is bundled separately under `engine/` without Qt DLLs;
this prevents the GUI bundle's Qt runtime hooks from contaminating libtorrent.

Run the packaged smoke check without opening the installed/development profile:

```powershell
.\dist\AnimeVault\AnimeVault.exe --self-test "E:\Anime Details\data\package-check.json"
```

The check uses a temporary database and fictional records, validates backup/restore,
native helper startup with public networking disabled, resources, navigation and
Details. It does not install the app, register Chrome integration, access your
library or download public torrents. Read the JSON report and process exit code.

This build is unsigned unless a signing certificate is supplied separately.
Windows SmartScreen may show an unknown-publisher prompt. The setup hash identifies
the exact artifact; it is not a substitute for Authenticode signing. Final real-PC
installation and your restore/playback check remain your acceptance test.
