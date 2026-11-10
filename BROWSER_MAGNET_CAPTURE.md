# Selected-website browser magnet capture

Implemented 6 November 2026, following the user's clarification that catching
magnets must not replace the existing global browser/Windows handler.

## Behavior

- The optional Google Chrome Manifest V3 extension catches magnet clicks only
  on the single website chosen in its popup. The native app must have the same
  source website saved in Downloads. The supplied Nyaa source is supported.
- Windows' MAGNET association and qBittorrent's normal browser integration are
  untouched. There is no global magnet handler registration, Default Apps
  override, custom URL protocol, new HTTP server or new listening port.
- A native message carries the magnet to a durable app inbox. If Anime Vault is
  open, its existing window receives the link. If closed, the native host starts
  the app. A second GUI/API server is not started for an already-running app.
- A compact confirmation fills in the torrent name automatically. The user
  chooses/confirms the library anime and season, then sends the magnet through
  the existing qBittorrent integration. Exact unique titles may be suggested;
  weak/ambiguous names require selection. No download starts on receipt alone.
- Paused-start/file-selection preferences, isolated destinations, completion
  verification, stable series identities and automatic indexing are preserved.
- Manual magnet paste and `.torrent` selection remain available. `.torrent`
  download links, non-selected websites, frames and modifier/middle clicks are
  not intercepted by this extension.

## Setup

See [the extension setup instructions](browser-extension/README.md): load the
folder unpacked in Google Chrome, copy the extension ID into the app's Downloads
drawer, connect it, enable the chosen website in the popup, approve only that
site's permission and reload the page once. An extension-store release or silent
browser installation is not performed. No passwords or qBittorrent API cookies
are given to the extension.

Connecting the host writes only:

```text
HKCU\Software\Google\Chrome\NativeMessagingHosts\com.animevault.capture
data/chrome-bridge/host.json
data/chrome-bridge/host.cmd
```

The host manifest's `allowed_origins` contains exactly the connected Chrome
extension ID. Registration is a deliberate app button action; tests mock registry
writes. No real registry/browser settings were changed during development.

The fixed Windows launcher invokes the app's native-host script. Magnet data is
sent only over framed binary stdin JSON, never as a shell command argument. The
launcher supports source execution and the existing frozen app's dedicated
native-host startup mode; an actual packaged release remains separately testable.

## Scope and safety checks

1. Site permission is optional and requested for the selected site only. Dynamic
   content-script registration contains one site pattern and no subframes.
2. The content script requires a real user click. It checks cached current
   settings and prevents the original navigation synchronously before awaiting
   the native handoff. This prevents the same click also opening qBittorrent
   through the ordinary MAGNET handler.
3. The service worker checks the tab URL, sender URL, top-level frame, current
   enabled site and current host permission. It rejects synthetic/cross-site
   messages before calling the host. Disabling/switching sites updates already
   injected pages and removes the old script/permission.
4. The desktop host checks Chrome's caller extension origin and the website
   against the configured search source again. It accepts only the `capture`
   action and a validated BitTorrent magnet; it cannot execute arbitrary actions.
5. Native frames are limited to 64 KiB and magnet links to 16,000 characters.
   HTTP links, malformed info hashes, raw quotes/control characters and
   oversized messages are rejected. Responses do not echo tracker URLs or
   credentials. There is no native HTTP endpoint exposed to webpages.
6. Pending links are persisted in `data/magnet-inbox.sqlite`, limited to 32
   pending links and a bounded recent terminal audit. Rapid repeated links to
   the same torrent are deduplicated. Unreviewed links survive restarts.
7. Submissions retain a browser-origin idempotency key in the existing download
   job ledger. A confirmed repeat reuses its existing job; an uncertain API
   submission cannot be blindly added again. Startup recovers a submission
   interrupted before job creation and leaves existing jobs for reconciliation.
8. Inbox reads/writes, host registration and torrent submission run outside the
   GUI event loop. The app checks the small inbox every two seconds only after
   an extension is connected. It handles one confirmation at a time; other
   links queue behind it. Startup's existing single-instance lock and optional
   elevation remain in effect; no new server binds a port.

## Changed files

| File | Change |
| --- | --- |
| `browser-extension/manifest.json` | Chrome MV3, optional site access and native messaging |
| `browser-extension/logic.js` | Shared origin and magnet validation |
| `browser-extension/background.js` | Site-scoped script lifecycle, sender checks, native handoff |
| `browser-extension/capture.js` | Trusted-click interception, synchronous cancellation, feedback |
| `browser-extension/popup.html`, `popup.css`, `popup.js` | Site selection, opt-in permission and disable control |
| `browser-extension/README.md` | Installation, operation and troubleshooting |
| `browser-extension/tests/capture.test.js` | Selected-site and click behavior tests |
| `app/core/chrome_bridge.py` | Private native host registration, framing, caller/site checks and desktop wake-up |
| `chrome_magnet_host.py` | Source-mode host entry point |
| `app/core/magnet_capture.py` | Validation, bounded durable inbox, restart handling and title suggestions |
| `app/ui/magnet_capture.py` | Compact review drawer and worker-driven inbox pump |
| `app/core/downloads.py` | Browser submission identity and confirmed/unconfirmed retry protection |
| `app/ui/downloads.py` | Connect extension ID and open extension folder controls |
| `app/ui/main_window.py` | Own the opt-in inbox pump |
| `main.py` | Native-host fast path and quiet browser-initiated single-instance startup |
| `run_as_admin.py` | Preserve the trusted browser startup flag through optional elevation |
| `tests/test_magnet_capture.py` | Native host, registry boundaries, inbox, restart, idempotency and UI regressions |
| `DOWNLOAD_INTEGRATION.md`, `README.md`, `CHANGELOG.md`, this report | Updated workflow and complete change record |

## Validation and practical limits

`python scripts/check.py` compiles the source and runs isolated tests. The added
tests cover caller/site rejection, exact title suggestions, inbox bounds and
deduplication, interrupted submission recovery, length-prefixed Unicode JSON,
registry writes restricted to the Chrome host key, duplicate-API protection,
desktop launch arguments, and prefilling without downloading. The Python suite
also runs the Node extension tests when Node is installed; without it that one
test is explicitly skipped. Node is a development-test tool, not an app/browser
runtime dependency.

The Node tests exercise selected vs non-selected origins, top-level vs iframe
senders, URL validation, synchronous click cancellation, synthetic-click rejection
and disabling capture in an already-open page. Offscreen Qt checks the compact
review drawer. Existing download/scanner/file-safety regressions are retained.

Local validation: **202 Python tests passed**, including the Node extension
behavior check. The standalone extension suite now contains **8 passing tests**.

Automated tests do not install a Chrome extension, alter live browser/default-app
settings, use real qBittorrent credentials or submit a torrent. Live Chrome native
messaging and a real downloaded torrent require the user's one-time installation
and verification. Managed Chrome policies may disallow unpacked extensions or
native messaging. Browser restart/reloading the selected website may be needed
after installation or permission changes.

A user/site with another magnet format, renamed title or ambiguous season can
still require manual anime/season selection. This feature removes copying the
link; it does not guess an uncertain series or bypass the existing confirmation.

Official references used:

- [Chrome Native Messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)
- [Chrome scripting API](https://developer.chrome.com/docs/extensions/reference/api/scripting)
- [Chrome optional permission API](https://developer.chrome.com/docs/extensions/reference/api/permissions)
- [Google's Windows native-messaging sample](https://github.com/GoogleChrome/chrome-extensions-samples/tree/main/api-samples/nativeMessaging)
