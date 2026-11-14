# qBittorrent and website search integration

> **9 November 2026 update:** Anime Vault now uses the built-in engine only.
> External-client setup/control described below is historical and removed.
> See [current setup and legacy queue recovery](BUILTIN_ONLY_DOWNLOADS.md).

Implemented 6 November 2026, on top of Phase 2. Existing library, matching,
organizing, history, Recycle Bin and API features are retained. No streaming
API, torrent engine or website scraper is added. The optional selected-site
Chrome extension is documented in the browser-capture follow-up below.

## How it works

1. Open **Settings > Downloads > Configure downloads**.
2. Enable the local qBittorrent connection. Enter its Web UI URL, username and
   password, choose the download destination, then **Test connection** and
   **Save settings**.
3. Open **Find / download…** on an anime's Details page, or **Find an episode /
   download…** in its episode-block page.
4. Review/edit the search title, release group, quality and optional episode.
   Search opens the configured website in the normal browser. Use absolute
   episode numbers for a continuing series; the app does not guess release
   numbering or select a torrent automatically.
5. Choose a release yourself. Copy its magnet link into Anime Vault, or choose
   its downloaded `.torrent` file, and click **Send selected torrent to
   qBittorrent**. This explicit handoff links the download to the selected anime.
6. By default the torrent starts paused: choose files and start it in qBittorrent.
   You can uncheck **Start paused** to start immediately. qBittorrent downloads/seeds
   the files. Anime Vault checks tracked downloads
   every 15 seconds while open. After completion and verification, it indexes
   the completed videos under that anime and refreshes the library.

**Browser capture option:** the selected-site Google Chrome extension can now
send a magnet click directly to Anime Vault without copying. See
[browser capture setup](BROWSER_MAGNET_CAPTURE.md). It only catches the chosen
website and leaves the global MAGNET handler unchanged.

Without that extension, a website's native magnet button can open
qBittorrent directly, but that bypasses Anime Vault's tracking handoff. This
manual handoff does not attach unrelated client jobs to an anime automatically.
Use the extension or magnet/file handoff above for automatic indexing.

## Your supplied search URL

Example: `https://nyaa.si/?q=%5BASW%5D+Kizoku+Tensei&f=0&c=0_0`

| Component | Meaning |
| --- | --- |
| `q` | Search text: `[ASW] Kizoku Tensei` |
| `%5B` / `%5D` | URL-encoded `[` / `]` |
| `+` | Space in the encoded query |
| `[ASW]` | Release-group tag in the query |
| `f=0` | No filter |
| `c=0_0` | All categories |

The default editable template is
`https://nyaa.si/?q={query}&f=0&c=0_0`. The query is built from editable group,
title, episode and quality fields, and URL-encoded once. Other website filters
are preserved. For another website, supply its actual search URL with `{query}`
in the search parameter. Only HTTP/HTTPS search links are accepted; placeholders
cannot change the destination hostname or execute commands.

## qBittorrent setup

In qBittorrent, open **Tools > Options > Web UI**, enable the Web UI, use a
loopback interface such as `127.0.0.1` and your chosen port (default suggested
address `http://127.0.0.1:8080`), and configure the Web UI username/password.
Keep authentication enabled. Anime Vault connects only to `localhost`,
`127.0.0.1` or `::1`; it does not enable the Web UI, alter firewall settings,
launch/elevate qBittorrent or create a public server.

qBittorrent authenticates through `/api/v2/auth/login` and a session cookie.
There is no newly generated Anime Vault API key. The password is saved using
Windows DPAPI encryption for the current Windows account. It is not stored in
plain text or embedded in the URL. Leave the password field blank to retain the
saved secret. After moving the app to another account/machine, re-enter it.
The app's existing `pywin32` dependency supplies DPAPI; there is no new dependency.

References: [qBittorrent WebUI API](https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-%28qBittorrent-5.0%29),
[supplied search page](https://nyaa.si/?q=%5BASW%5D+Kizoku+Tensei&f=0&c=0_0).
These pages were retrieved to verify the authentication and filter parameters.

## File and history safety

- Every submitted torrent receives a unique `AnimeVault-…` tag and an isolated
  subfolder under the chosen destination. Its root/season subfolder is saved in
  the durable job record. Existing library paths are not passed as an overwrite
  target, and automatic torrent management is disabled for this submission.
- This destination is download staging. Completed files remain there for
  seeding; automatic indexing does **not** move or rename them into the main
  consolidated library. The existing Organizer remains available for separately
  reviewed moves after the torrent client no longer needs those paths.
- Only explicitly tracked torrents are queried by their unique tags. The app
  never deletes torrents, removes data, changes unrelated downloads or pauses
  seeding. Individual file choices remain in qBittorrent's own UI.
- A completed job must have one matching torrent, the expected save path,
  selected files at 100%, readable video files and the expected sizes. Path
  traversal/outside-destination files are rejected. Hash-checking, moving,
  error/missing-file states and partial downloads are not indexed.
- Only the verified torrent file list enters indexing; unrelated/incomplete
  files in the same filesystem are not enumerated into that job's inventory.
  Existing library folders, notes and episode identities remain intact.
- Archives without completed videos require manual extraction/review. Unknown
  season numbering can still require the existing release-matching review.
- Submissions are journaled before the API request. A timeout leaves an
  **unconfirmed** job for reconciliation, rather than blindly submitting again.
  Missing torrents/path changes/permission failures remain visible for review.
- Indexed jobs persist and are not re-indexed on every poll/restart. Incomplete
  jobs resume monitoring when the app opens again. Closing Anime Vault does not
  stop the external qBittorrent download.
- Jobs also retain the Phase 1 stable series identity. Removing/merging an anime
  and reusing its numeric entry ID cannot attach an old download to a new series;
  the identity change requires review.

## Performance and implementation

Network requests, login, encrypted settings writes, torrent-file reads and
completed-file indexing run in app-owned IO workers. Monitoring never overlaps
itself, handles at most eight pending jobs per pass in least-recently-checked
order, and checks cancellation between jobs. Requests have bounded connect/read
timeouts (3/10 seconds). Existing shutdown handling waits for workers rather
than killing an indexing transaction. Monitoring is disabled by default, and
does not contact the client when there are no pending jobs.

| Changed file | Responsibility |
| --- | --- |
| `app/core/downloads.py` | Settings/DPAPI, query encoding, authenticated local client, submission journal, verified completion and idempotent indexing |
| `app/ui/downloads.py` | Themed setup/search/handoff drawer, progress list and background monitor |
| `app/ui/pages/settings_page.py` | Downloads configuration entry point |
| `app/ui/pages/detail_modal.py` | Anime-specific download entry point |
| `app/ui/pages/episode_page.py` | Download entry point from episode blocks |
| `app/ui/main_window.py` | Start monitoring and refresh the library after verified indexing |
| `tests/test_downloads.py` | Mocked-client integration, safety, persistence and DPAPI tests |
| `README.md`, `CHANGELOG.md`, this document | Setup instructions and full change record |

Settings and jobs use the existing `app_state` store (`downloads.settings` and
`downloads.jobs`), without dropping/changing identity tables or existing routes.

## Validation and limits

Run `python scripts/check.py`: isolated temporary databases/media and mocked
qBittorrent responses are used. Tests cover URL encoding/filter preservation,
loopback restrictions/session authentication, password encryption, fresh tagged
destinations, uncertain submission recovery, traversal/partial-file rejection,
completion-only indexing, restart idempotence, retained old folders/notes and
visible/retryable missing files. No real torrent is submitted by validation.

Validation result: **185 tests passed** locally, including the existing suite.

Offscreen Qt rendering checks the existing drawer design at 560×900. A real
connection/download still requires your local Web UI credentials and an explicitly
chosen torrent. No live download, real seeding relocation or website result
scraping has been tested or performed by the agent. Client/website availability
is not controlled by Anime Vault. Verified sizes and client completion status
are not an additional independent full-file SHA-256 audit.
