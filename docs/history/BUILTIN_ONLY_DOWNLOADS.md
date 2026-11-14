# Anime Vault downloads — built-in engine only

Updated 9 November 2026.

## What caused the reported failure

The saved failed transfer was owned by the old qBittorrent integration. Its Web UI
login endpoint returned HTTP 404. Selecting the built-in engine did not change the
engine attached to that existing queue record.

Anime Vault now uses its own libtorrent-backed engine exclusively. There is no
qBittorrent Web UI connection, username/password form, engine choice for external
clients, login request, queue polling or external torrent-control request.

The native engine remains in a separate helper process to avoid loading its
native networking runtime into the PyQt GUI process. It is an app-owned helper,
not a requirement to install a separate torrent application.

## Start a new download

1. Restart Anime Vault after updating its code.
2. Open Settings → Downloads & Sources. Enable downloads, select your destination
   and save. Check Anime Vault engine verifies the native helper can start.
3. Open an anime → Find Download Files, or add a magnet/local `.torrent` through
   the existing manual download flow.
4. Review and confirm the release and target anime/season.
5. If Choose files before starting downloads is enabled, open Downloads, select
   the transfer, then Choose files once torrent metadata is available. Select
   the wanted files and apply; this starts the selected payload.
6. Keep the app open or minimized to tray. Exiting completely saves native resume
   data and stops its transfers. Verified completed videos are indexed normally.

Fetching metadata requires reachable peers or another supported metadata source.
An empty swarm, unavailable tracker, firewall restriction or browser-verification
failure is not resolved by switching engines. Source search and torrent transfer
are separate stages, with separate error states.

## Recover an old external-client entry

Old queue records and existing files are preserved. They are never polled through
the retired client or silently treated as built-in downloads.

- Select the old failed entry in Downloads and click Retry.
- Confirm creation of an Anime Vault transfer in a new isolated folder.
- If the old transfer is running in another application, stop it there first.
  Anime Vault no longer controls that external application.
- The original saved magnet or `.torrent` is submitted to the native engine.
  The original entry remains stopped as an audit record. Existing files stay put.
- Choose files on the new entry when metadata is ready if file selection is on.
- Repeated Retry on the old entry is blocked once a replacement was created;
  use the new queue entry instead.
- If the original source was not saved, the app asks you to add it again manually.
- Failures before submission keep the original entry reviewable/retryable.
- Failed native attachment retains the source and episode mapping in the new job
  so it can be recovered without blindly submitting a duplicate.

Completed historical entries are not automatically redownloaded. Removing a
queue entry still keeps files; recycling files remains a separate confirmation.
Old partial-file locations stay excluded from ordinary auto-import scans.

## Settings migration

Saved engine preferences are read as builtin, including older qBittorrent values.
Destination, enabled flag, source URLs, query preferences, speed limits, seeding
and file-selection preferences are retained. Retired credentials are not exposed
in the new settings and are removed from the download settings record on Save.
Saving does not launch an old failed download without a Retry confirmation.

## Changed implementation

- `app/core/downloads.py`: native-only settings, submission, polling and helper
  checks; durable source/episode metadata before attachment; uncertain-submit guard.
- `app/core/download_queue.py`: safe explicit retry of legacy jobs, local-only
  history removal, no external API control or file-inventory requests.
- `app/ui/downloads.py`, `app/ui/download_setup.py`: built-in-only configuration
  and setup; remove external connection/credential fields.
- `app/ui/magnet_capture.py`: native submission labels and file-selection guidance.
- `app/ui/pages/downloads_page.py`: legacy Retry confirmation and actionable file guidance.
- `app/core/builtin_torrents.py`: native-only recovery/error copy.
- Download, browser capture, UI and end-to-end tests updated to exercise the native
  flow and explicitly reject any external-client HTTP request.
- README, changelog and feature/navigation inventory updated for this decision.

Validation: `python data/phase2_validate.py` passed **239 tests** in 46.452 seconds,
including native loopback transfer/resume, completed-file indexing, failed-attachment
recovery, legacy-entry retry, no-external-HTTP assertions and 18 Chrome JavaScript
checks through the test wrappers. The 500-file scanner heartbeat measured 40.1 ms
maximum in this run. Compilation passed. These are isolated test measurements,
not a guarantee that every public swarm has peers or every network permits traffic.
No public torrent or user media is downloaded, moved or deleted by the suite.
