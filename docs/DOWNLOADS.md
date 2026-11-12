# Built-in downloads: current setup

Anime Vault uses **libtorrent-rasterbar** through its own download engine. A separate qBittorrent application, Web UI or API key is not required. Historical integration documents remain for reference, but do not describe the current engine selection.

## Setup

1. Open **Settings → Downloads & Sources**, or **Downloads → Setup Guide**.
2. Choose the default download destination and configure optional transfer limits. Zero means unlimited.
3. Enable and save download preferences. Keep downloaded files separate from unrelated documents/media.
4. If using browser source search/capture, follow the [Chrome extension setup](../browser-extension/README.md). Permission applies to the selected website, not every site or the global Windows magnet handler.

## Find and confirm a release

Open a series and choose **Find Download Files**. Select the appropriate release/season; edit the search text or use a saved custom title when the encoder uses an alternate name. Search results can be selected and reviewed before downloading.

An uncertain match requires explicit confirmation of the anime, release type, season and episode assignment. A confirmed submission starts without requiring a second mandatory “Choose files first” step. The queue still exposes file-selection controls where applicable; do not confuse those controls with the old mandatory pause-before-download workflow.

Use Pause, Resume, Stop and Retry on the existing queue entry. **Clear completed** removes completed queue records and keeps files. Recycle Bin deletion is a separate, explicitly confirmed operation.

## Move completed files into the Library

**Downloads → Move completed to library** generates a reviewed move preview. It attempts to reuse the anime's existing Library/season folder. Review every destination, especially custom arcs and absolute-numbered series. Existing targets are not silently overwritten.

Two related issues are still open: completion indexing can ignore a manually confirmed assignment (**A02**), and one release split across staging/Library locations can appear as duplicate seasons (**A11**). See the [current audit](../WHOLE_APP_AUDIT_2026-11-12.md). The presence of a move button is not evidence that these issues are already fixed.

## Troubleshooting

| Symptom | Check |
|---|---|
| Source search requires browser verification | Open the chosen source in Chrome, complete its verification, then retry |
| No peers or transfer progress | Check torrent availability, connectivity, queue status and configured limits |
| Match uncertain | Confirm the actual anime/season/episode; do not assume similar filenames are sufficient |
| Destination unavailable | Reconnect the drive or select an accessible folder; review again before moving |
| Old external-client entry | Review legacy recovery guidance in [BUILTIN_ONLY_DOWNLOADS.md](../BUILTIN_ONLY_DOWNLOADS.md); external clients are no longer used for new submissions |

Transfer only material you have permission to access and share. Source availability and third-party verification requirements are outside the application's control.
