importScripts('logic.js');
importScripts('search.js');
const SCRIPT_ID = 'animevault-selected-site';
let configQueue = Promise.resolve();

async function getActiveSites() {
  const data = await chrome.storage.local.get(['sites', 'site', 'enabled']);
  let list = [];
  if (Array.isArray(data.sites) && data.sites.length) {
    list = data.sites;
  } else if (data.site) {
    list = [data.site];
  }
  const normalized = [];
  for (const s of list) {
    try { normalized.push(sourceOrigin(s)); } catch {}
  }
  return {sites: normalized, enabled: !!data.enabled};
}

function refreshScript() {
  configQueue = configQueue.catch(() => {}).then(applyScript);
  return configQueue;
}

async function applyScript() {
  const {sites, enabled} = await getActiveSites();
  const registered = await chrome.scripting.getRegisteredContentScripts({ids: [SCRIPT_ID]});
  if (registered.length) await chrome.scripting.unregisterContentScripts({ids: [SCRIPT_ID]});
  if (!enabled || !sites.length) return;
  const matches = [];
  for (const site of sites) {
    const match = sourceOrigin(site) + '/*';
    if (await chrome.permissions.contains({origins: [match]})) {
      matches.push(match);
    }
  }
  if (!matches.length) return;
  await chrome.scripting.registerContentScripts([{
    id: SCRIPT_ID, matches, js: ['capture.js'],
    runAt: 'document_start', allFrames: false, persistAcrossSessions: true
  }]);
}

chrome.runtime.onInstalled.addListener(() => refreshScript().catch(() => {}));
chrome.runtime.onStartup.addListener(() => refreshScript().catch(() => {}));
chrome.permissions.onRemoved.addListener(() => refreshScript().catch(() => {}));

chrome.runtime.onMessage.addListener((message, sender, respond) => {
  (async () => {
    if (message.action === 'configure' && sender.url === chrome.runtime.getURL('popup.html')) {
      await refreshScript(); connectBridge(); return {ok: true};
    }
    const {sites, enabled} = await getActiveSites();
    if (!enabled || !sites.length || !allowedSender(sender, sites) ||
        message.action !== 'capture' || !validMagnet(message.magnet)) {
      throw new Error('This click is not from your enabled website(s).');
    }
    const senderOrigin = sourceOrigin(sender.url);
    if (!await chrome.permissions.contains({origins: [senderOrigin + '/*']})) {
      throw new Error('Permission for this website was removed.');
    }
    const result = await chrome.runtime.sendNativeMessage('com.animevault.capture', {
      action: 'capture', site: senderOrigin, sites, magnet: message.magnet
    });
    if (!result || !result.ok) throw new Error(result?.error || 'Anime Vault could not receive the link.');
    return {ok: true};
  })().then(respond).catch(error => respond({ok: false, error: error.message}));
  return true;
});

let bridgePort = null;
let bridgeStarted = false;
let searching = false;

function connectBridge() {
  if (!chrome.runtime.connectNative) return;
  if (bridgePort) { sendHeartbeat(); return; }
  try {
    const port = chrome.runtime.connectNative('com.animevault.capture');
    bridgePort = port;
    bridgeStarted = false;
    port.onDisconnect.addListener(() => {
      void chrome.runtime.lastError;
      if (bridgePort === port) bridgePort = null;
      chrome.storage.local.set({bridgeStatus: 'Disconnected — open Anime Vault and reconnect in Settings.'});
    });
    port.onMessage.addListener(async message => {
      if (message.action === 'connected') {
        await chrome.storage.local.set({bridgeStatus: 'Connected to Anime Vault'});
      } else if (message.action === 'search') {
        await runSourceSearch(message, port);
      }
    });
    sendHeartbeat('connect');
  } catch { bridgePort = null; }
}

async function sendHeartbeat(action = 'heartbeat') {
  const {sites, enabled} = await getActiveSites();
  if (bridgePort && sites.length) {
    bridgePort.postMessage({
      action: bridgeStarted ? action : 'connect',
      site: sites[0],
      sites,
      enabled: !!enabled
    });
    bridgeStarted = true;
  }
}

async function runSourceSearch(message, port) {
  if (searching) {
    port.postMessage({action: 'search_result', id: message.id, error: 'Another source search is running. Retry shortly.'}); return;
  }
  let tab;
  let result;
  try {
    searching = true;
    const {sites, enabled} = await getActiveSites();
    const targetOrigin = sourceOrigin(message.url);
    if (!enabled || !sites.includes(targetOrigin) || !await chrome.permissions.contains({origins: [targetOrigin + '/*']})) {
      throw new Error('Enable this source website in the extension popup, then retry.');
    }
    tab = await chrome.tabs.create({url: message.url, active: false});
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => { chrome.tabs.onUpdated.removeListener(updated); reject(new Error('Source timed out. Open it in Chrome for any verification, then retry.')); }, 30000);
      function updated(id, change) {
        if (id === tab.id && change.status === 'complete') {
          clearTimeout(timeout); chrome.tabs.onUpdated.removeListener(updated); resolve();
        }
      }
      chrome.tabs.onUpdated.addListener(updated);
      chrome.tabs.get(tab.id).then(t => { if (t.status === 'complete') updated(tab.id, {status: 'complete'}); }).catch(error => {
        clearTimeout(timeout); chrome.tabs.onUpdated.removeListener(updated); reject(error);
      });
    });
    // A completed navigation can precede a site's asynchronously rendered results.
    // Retry extraction briefly, rechecking the permitted origin on every attempt.
    for (let attempt = 0; attempt < 9; attempt++) {
      const current = await chrome.tabs.get(tab.id);
      if (sourceOrigin(current.url) !== targetOrigin) throw new Error('Source redirected to a different website. Review it in Chrome.');
      const permission = await getActiveSites();
      if (!permission.enabled || !permission.sites.includes(targetOrigin) ||
          !await chrome.permissions.contains({origins: [targetOrigin + '/*']})) {
        throw new Error('Source permission changed during searching. Enable the selected site again, then retry.');
      }
      const response = await chrome.scripting.executeScript({target: {tabId: tab.id}, func: extractSourceResults});
      result = response[0]?.result || {error: 'The source returned no readable results. Open source in Chrome, then retry.'};
      if (!result.error || /verification is required|cannot bypass/i.test(result.error)) break;
      if (attempt < 8) await new Promise(resolve => setTimeout(resolve, 500));
    }
  } catch (error) { result = {error: error.message}; }
  finally {
    if (tab) await chrome.tabs.remove(tab.id).catch(() => {});
    searching = false;
  }
  const payload = {action: 'search_result', id: message.id, ...result};
  // Keep Chrome's native message below the host's strict 64 KiB boundary.
  if (payload.results) {
    payload.results = payload.results.slice(0, 60);
    while (new TextEncoder().encode(JSON.stringify(payload)).length > 60000 && payload.results.length) payload.results.pop();
  }
  try { port.postMessage(payload); } catch {}
}

if (chrome.alarms) {
  chrome.alarms.create('animevault-bridge', {periodInMinutes: 1});
  chrome.alarms.onAlarm.addListener(alarm => { if (alarm.name === 'animevault-bridge') connectBridge(); });
}
if (chrome.storage.onChanged) chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && (changes.site || changes.sites || changes.enabled)) connectBridge();
});
connectBridge();
