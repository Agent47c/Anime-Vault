/* Only dynamically registered on the one permitted top-level website. */
(() => {
  if (globalThis.__animeVaultCapture) return;
  globalThis.__animeVaultCapture = true;
  let current = null;
  chrome.storage.local.get(['site', 'enabled']).then(config => { current = config; });
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== 'local') return;
    current = {...current};
    for (const key of ['site', 'enabled']) if (changes[key]) current[key] = changes[key].newValue;
  });
  function notice(message) {
    const box = document.createElement('div');
    box.textContent = message;
    Object.assign(box.style, {position: 'fixed', bottom: '24px', right: '24px', zIndex: '2147483647',
      maxWidth: '380px', padding: '14px 18px', borderRadius: '12px', color: '#f2f3f7',
      background: '#1c1f29', border: '1px solid #8b8cff', font: '14px sans-serif'});
    (document.body || document.documentElement).appendChild(box);
    setTimeout(() => box.remove(), 8000);
  }
  document.addEventListener('click', async event => {
    if (!event.isTrusted || event.button !== 0 || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
    const link = event.composedPath().find(node => node instanceof HTMLAnchorElement);
    if (!link || !link.href.toLowerCase().startsWith('magnet:?')) return;
    // Previously injected scripts can survive permission revocation until reload.
    // Check current settings before touching a browser navigation.
    if (!current?.enabled || current.site !== location.origin) return;
    // Cancellation must be synchronous, before the first await, or Chrome
    // would also launch the ordinary magnet handler for the same click.
    event.preventDefault();
    event.stopImmediatePropagation();
    try {
      const response = await chrome.runtime.sendMessage({action: 'capture', magnet: link.href});
      notice(response?.ok ? 'Sent to Anime Vault. Confirm the anime there.' :
        (response?.error || 'Capture failed. Open the Anime Vault extension to check setup.'));
    } catch {
      notice('Capture failed. Check the extension connection. You can still copy this magnet link.');
    }
  }, true);
})();
