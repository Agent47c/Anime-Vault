const siteInput = document.getElementById('site');
const status = document.getElementById('status');
chrome.storage.local.get(['site', 'enabled']).then(config => {
  if (config.site) siteInput.value = config.site;
  status.textContent = config.enabled ? 'Enabled for ' + config.site : 'Capture is disabled.';
});
document.getElementById('enable').addEventListener('click', async () => {
  try {
    const site = sourceOrigin(siteInput.value.trim());
    if (!await chrome.permissions.request({origins: [site + '/*']})) throw new Error('Website permission was not granted.');
    const old = await chrome.storage.local.get('site');
    await chrome.storage.local.set({site, enabled: true});
    const result = await chrome.runtime.sendMessage({action: 'configure'});
    if (!result?.ok) throw new Error(result?.error || 'Could not enable capture.');
    if (old.site && old.site !== site) await chrome.permissions.remove({origins: [old.site + '/*']});
    siteInput.value = site; status.textContent = 'Enabled for ' + site + '. Reload that website.';
  } catch (error) { status.textContent = error.message; }
});
document.getElementById('disable').addEventListener('click', async () => {
  await chrome.storage.local.set({enabled: false});
  const result = await chrome.runtime.sendMessage({action: 'configure'});
  status.textContent = result?.ok ? 'Disabled. Reload the website to restore normal links.' : result?.error;
});
