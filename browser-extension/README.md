# Anime Vault selected-site magnet capture (Google Chrome)

This extension catches normal left-clicks on magnet links **only on the one
website you enable**. It does not change Windows MAGNET defaults, intercept
other websites, read browsing history or scrape search results.

## One-time setup

1. In Anime Vault, save your website search URL in Settings → Downloads. For
   your supplied source, keep `https://nyaa.si/?q={query}&f=0&c=0_0`.
2. Open `chrome://extensions`, enable Developer mode, choose **Load unpacked**,
   and select this `browser-extension` directory. The app's **Open Chrome
   extension folder** button shows its location.
3. Copy this extension's 32-character **ID** from its Chrome extension card.
4. In Anime Vault's Downloads drawer, paste the ID into **Chrome extension ID**
   and click **Connect selected-site Chrome extension**. This registers only a
   private Chrome Native Messaging host for your Windows account.
5. Open the extension popup. Enter `https://nyaa.si` (or the same website saved
   in Anime Vault), click **Enable on this website**, and approve that site's
   permission. Reload the website once.

Click a magnet on that site. Anime Vault opens a compact confirmation containing
the received torrent name, library anime selector and season selector. An exact,
unique title can be suggested; review it and click **Send to qBittorrent**.
No magnet copying/pasting is needed. Existing paused-download/file-selection
and completed-file indexing behavior still applies.

For Chrome to receive native messages, keep the Python installation and this
project in their registered locations. Reconnect the extension in the app after
moving the project, changing Python, or loading the extension from another path.
An installed/frozen build needs to include this extension folder separately for
the same manual Chrome setup; publishing a Web Store extension is not part of
this change.

## Disable or change the website

- **Disable capture** in the popup stops interception in already open pages;
  reload the page for a completely fresh state. Links then use your normal
  browser/Windows handler.
- Enable another website to replace the old one. The extension unregisters the
  previous content script and removes the old site's permission. Save the same
  website in Anime Vault as well; the app independently rejects other origins.
- Chrome's extension settings also let you remove its site access or disable/
  remove the extension. Your existing qBittorrent MAGNET association is unchanged.

## Permissions and limits

`optional_host_permissions` lets you choose a website; it does not grant access
to every website at installation. Actual capture uses one exact scheme/host
origin, the top-level tab only, and a trusted left-click. Modifier/middle clicks
keep their normal browser behavior. The host receives framed JSON over Chrome's
Native Messaging channel, not an HTTP listener or a global URL handler.

Only the extension ID explicitly connected in Anime Vault can use the native
host. Both the service worker and desktop host check the website. Links are
bounded/validated, queued durably and reviewed in the app before submission.
If the bridge fails, the extension shows a message instead of also starting an
untracked torrent. Disable capture to temporarily use your normal handler.

No live browser installation or torrent download is performed by the automated
tests. Local logic/content-script tests run with:

```text
node --test browser-extension/tests/capture.test.js
```
