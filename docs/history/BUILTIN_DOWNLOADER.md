# Built-in libtorrent downloader

> **9 November 2026 update:** Anime Vault now uses the built-in engine only.
> External-client setup/control described below is historical and removed.
> See [current setup and legacy queue recovery](BUILTIN_ONLY_DOWNLOADS.md).

## Use it

1. Open **Settings → Configure downloads** (or Find / download on an anime).
2. Select **Built-in downloader**, check **Enable downloads**, choose the download
   destination, then **Save settings**. No qBittorrent login or Web UI is needed.
3. Leave **Choose files before starting downloads** enabled to review the files.
   Magnet metadata is fetched first; payload files stay unselected until approval.
4. Use the existing website search and Chrome extension, paste a magnet, or choose
   a local `.torrent`. Browser capture still requires confirmation of anime/season.
5. In **Tracked downloads**, highlight the new transfer and click **Files**. Once
   its metadata is available, select the files and click **Start selected files**.
6. The list shows progress, state, download/upload speeds and an estimated remaining
   time when a transfer rate is available. **Pause**, **Resume** and **Cancel** act
   on the highlighted built-in transfer. Cancel always keeps downloaded files.

With the file-review option off, adding a torrent explicitly approves all its files
and starts payload download after metadata/path validation. The default remains on.
Source installations need `python -m pip install -r requirements.txt`; libtorrent
2.0.15 is pinned and was tested on Windows x64 / Python 3.13.

## Existing features and settings

- qBittorrent remains available and remains the default for existing installations.
  Switching engines only affects new downloads; it does not migrate external jobs.
- Existing qBittorrent jobs continue to use their saved tags and completion checks.
  External-client transfers are still controlled in qBittorrent.
- Browser capture stays limited to the chosen website, without changing Windows'
  global magnet handler. It now hands off to whichever engine is selected.
- Download destination, source query, release group, quality, season assignment,
  encrypted qBittorrent credentials, and library completion indexing are preserved.
- Built-in upload/download limits are in KiB/s; zero means unlimited. Limits also
  apply to local-network peers. Completed seeding is optional and defaults off.
- Minimizing to tray keeps transfers running. Fully exiting saves native resume
  state and stops the built-in engine; reopening restores uncancelled jobs when
  downloads are enabled. Disabling downloads stops the native engine.
- File selection uses a virtual list rather than one checkbox widget per file.
  Selection cannot be changed after a transfer has already been indexed.

## Architecture and recovery

`app/core/builtin_torrents.py` contains a libtorrent adapter and an `EngineClient`.
The client starts the app-owned `builtin_torrent_host.py` helper using private
stdin/stdout pipes. This is an internal component, not another installed app or a
local HTTP API. No browser page can address this private pipe. The process is
started lazily, only for built-in work, with no visible console window.

Native sessions and torrent parsing stay out of the Qt process. Tests encountered
a Windows native access violation when native libtorrent sessions shared the Qt
process; isolating the engine avoids losing the library window on native failure.
Helper failures become visible download errors. Restart the app to restore jobs
from the durable torrent identity and source/resume state.

Jobs remain in SQLite's existing `downloads.jobs` app state. Each records its
engine, stable series ID, destination, torrent identity, reviewed file indices,
desired paused/running/cancelled state, and whether completion was indexed. New
jobs and user choices are committed before applying native operations.

Native `.torrent` and `.resume` files are stored under `data/builtin-downloads/`.
Writes use a temporary file, flush/fsync and atomic replacement. Resume state is
requested periodically (30 seconds while polling) and flushed on graceful exit.
The original `.torrent` or magnet remains available if resume data is absent or
invalid, allowing libtorrent to recheck the actual downloaded pieces. GUI crashes
close the private pipe; the helper attempts a final resume-state save on EOF.
Power loss may require piece rechecking; cached progress is never proof that a
download is complete.

Exit uses the existing app-owned IO worker and shutdown timer. The interface keeps
responding while native resume data is saved. New download/inbox work is blocked
during shutdown. The helper is bounded by response and shutdown timeouts.

## File safety

- Every new torrent has its own fresh UUID-based subfolder in the chosen destination.
- Torrent paths, Windows reserved names, duplicate case-insensitive filenames and
  symlinks are checked before enabling payload transfers. Large file inventories
  are bounded. Magnets fetch metadata in upload-only mode until validation.
- File selection is durable and completion decisions use the saved selection,
  avoiding races with asynchronous native priority updates.
- Hash checking, active downloads and native disk errors block completion indexing.
  Selected files must be complete, present, correctly sized, and inside the reviewed
  destination. Only verified selected video paths enter the existing scanner.
- Series identity is revalidated before indexing. Notes, watch history, existing
  folders and files remain intact. Cancelling never requests native `delete_files`.
- Interrupted/failed submissions remain tracked. Browser-origin retries are
  idempotent, and duplicate active torrent identities are rejected.
- The helper's peer port is chosen dynamically. It does not request router UPnP or
  NAT-PMP mappings. As with other torrent clients, connectivity depends on peers,
  trackers, the Windows firewall and the network.

## Files changed

- `app/core/builtin_torrents.py`: private process client, native engine, safe
  metadata/file handling, rate/seeding settings, resume persistence and shutdown.
- `builtin_torrent_host.py`: bounded length-framed private worker commands.
- `app/core/downloads.py`: engine selection, durable built-in jobs/actions,
  completion verification shared with qBittorrent, and coordinated shutdown.
- `app/ui/downloads.py`: engine settings, live transfer controls and virtual file
  selection drawer. qBittorrent-only fields remain available when selected.
- `app/ui/magnet_capture.py`: engine-aware confirmation and status wording.
- `app/ui/main_window.py`: native download exit information and worker shutdown.
- `app/ui/theme.py`: file-selection list styling using existing theme tokens.
- `main.py`: early helper entry point before GUI imports for packaged execution.
- `requirements.txt`: pinned native dependency.
- `build_exe.py`: collect libtorrent, the helper and license notice.
- `tests/test_builtin_downloads.py`, `scripts/check_builtin_engine.py`: regression
  checks and a generated loopback-only native transfer/restart check.
- `third_party/libtorrent-LICENSE.txt`: upstream redistribution notices.
- README and CHANGELOG: usage and changes.

## Validation and remaining limits

Tests cover native file selection, pause/resume, cancellation keeping files,
duplicate prevention, bad paths, confirmed completion, helper failure, engine
selection UI and a 10,000-row virtual file model. A real generated local-peer
transfer is interrupted partway, restarted, completed and byte-compared; the
unselected episode remains excluded. No real library files or public torrents
are used. Visual checks cover the settings and file-selection drawers.

Validation result: all 216 application tests passed, including the real native
loopback test. Scanner heartbeat remained at 35 ms in the existing 500-file
performance check. This heartbeat measurement is not a blanket guarantee for all
network conditions or native disk workloads.

The source-mode Windows implementation has been exercised. Build configuration
is prepared, but the packaged EXE still needs its own clean-machine test before
release. Browser search and file downloads are not site scrapers, subscriptions
or automatic downloading of newly aired episodes. Existing qBittorrent transfers
are not imported into libtorrent. The app itself must remain running (including
in the tray) for native transfers to continue.

References: https://www.libtorrent.org/manual-ref.html and
https://pypi.org/project/libtorrent/2.0.15/ .
