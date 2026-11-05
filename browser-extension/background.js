importScripts('logic.js');
const SCRIPT_ID = 'animevault-selected-site';
let configQueue = Promise.resolve();
function refreshScript() {
  configQueue = configQueue.catch(() => {}).then(applyScript);
  return configQueue;
}
async function applyScript() {
  const {site, enabled} = await chrome.storage.local.get(['site', 'enabled']);
  const registered = await chrome.scripting.getRegisteredContentScripts({ids: [SCRIPT_ID]});
  if (registered.length) await chrome.scripting.unregisterContentScripts({ids: [SCRIPT_ID]});
  if (!enabled || !site) return;
  const match = sourceOrigin(site) + '/*';
  if (!await chrome.permissions.contains({origins: [match]})) {
    await chrome.storage.local.set({enabled: false}); return;
  }
  await chrome.scripting.registerContentScripts([{
    id: SCRIPT_ID, matches: [match], js: ['capture.js'],
    runAt: 'document_start', allFrames: false, persistAcrossSessions: true
  }]);
}
chrome.runtime.onInstalled.addListener(() => refreshScript().catch(() => {}));
chrome.runtime.onStartup.addListener(() => refreshScript().catch(() => {}));
chrome.permissions.onRemoved.addListener(() => refreshScript().catch(() => {}));
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  (async () => {
    if (message.action === 'configure' && sender.url === chrome.runtime.getURL('popup.html')) {
      await refreshScript(); return {ok: true};
    }
    const {site, enabled} = await chrome.storage.local.get(['site', 'enabled']);
    if (!enabled || !site || !allowedSender(sender, site) ||
        message.action !== 'capture' || !validMagnet(message.magnet)) {
      throw new Error('This click is not from your enabled website.');
    }
    if (!await chrome.permissions.contains({origins: [sourceOrigin(site) + '/*']})) {
      throw new Error('Permission for this website was removed.');
    }
    const result = await chrome.runtime.sendNativeMessage('com.animevault.capture', {
      action: 'capture', site: sourceOrigin(site), magnet: message.magnet
    });
    if (!result || !result.ok) throw new Error(result?.error || 'Anime Vault could not receive the link.');
    return {ok: true};
  })().then(respond).catch(error => respond({ok: false, error: error.message}));
  return true;
});
