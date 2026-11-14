const sitesList = document.getElementById('sites-list');
const newSiteInput = document.getElementById('new-site');
const addBtn = document.getElementById('add-btn');
const enableBtn = document.getElementById('enable');
const disableBtn = document.getElementById('disable');
const status = document.getElementById('status');

let configuredSites = [];
let captureEnabled = false;

async function loadConfig() {
  const config = await chrome.storage.local.get(['sites', 'site', 'enabled', 'bridgeStatus']);
  captureEnabled = !!config.enabled;
  if (Array.isArray(config.sites) && config.sites.length) {
    configuredSites = config.sites;
  } else if (config.site) {
    configuredSites = [config.site];
  } else {
    configuredSites = ['https://nyaa.si', 'https://sukebei.nyaa.si'];
    await chrome.storage.local.set({sites: configuredSites});
  }
  renderSites();
  updateStatus(config.bridgeStatus);
}

function updateStatus(bridgeStatus) {
  if (!captureEnabled) {
    status.textContent = 'Capture is disabled. ' + (bridgeStatus || 'Open Anime Vault to connect.');
  } else if (!configuredSites.length) {
    status.textContent = 'No websites enabled. Add at least one website above.';
  } else {
    status.textContent = `Capture enabled for ${configuredSites.length} website(s). ` + (bridgeStatus || 'Connected to Anime Vault.');
  }
}

function renderSites() {
  sitesList.innerHTML = '';
  if (!configuredSites.length) {
    const emptyLi = document.createElement('li');
    emptyLi.className = 'site-item';
    emptyLi.innerHTML = '<span class="site-origin" style="color:var(--muted)">No websites added yet.</span>';
    sitesList.appendChild(emptyLi);
    return;
  }

  configuredSites.forEach(site => {
    const li = document.createElement('li');
    li.className = 'site-item';

    const span = document.createElement('span');
    span.className = 'site-origin';
    span.textContent = site;
    li.appendChild(span);

    const removeBtn = document.createElement('button');
    removeBtn.className = 'remove-btn';
    removeBtn.type = 'button';
    removeBtn.textContent = 'Remove';
    removeBtn.addEventListener('click', async () => {
      await removeSite(site);
    });
    li.appendChild(removeBtn);

    sitesList.appendChild(li);
  });
}

async function addSite(urlValue) {
  try {
    const origin = sourceOrigin(urlValue.trim());
    if (configuredSites.includes(origin)) {
      status.textContent = `${origin} is already in the list.`;
      return;
    }
    const granted = await chrome.permissions.request({origins: [origin + '/*']});
    if (!granted) throw new Error(`Permission for ${origin} was not granted.`);

    configuredSites.push(origin);
    await chrome.storage.local.set({sites: configuredSites, site: configuredSites[0]});
    renderSites();
    newSiteInput.value = '';

    if (captureEnabled) {
      await chrome.runtime.sendMessage({action: 'configure'});
      status.textContent = `Added ${origin}. Reload that website.`;
    } else {
      status.textContent = `Added ${origin}. Click "Enable capture on all websites" to activate.`;
    }
  } catch (error) {
    status.textContent = error.message;
  }
}

async function removeSite(site) {
  try {
    configuredSites = configuredSites.filter(s => s !== site);
    await chrome.storage.local.set({sites: configuredSites, site: configuredSites[0] || ''});
    renderSites();
    try {
      await chrome.permissions.remove({origins: [site + '/*']});
    } catch {}
    if (captureEnabled) {
      await chrome.runtime.sendMessage({action: 'configure'});
    }
    updateStatus();
  } catch (error) {
    status.textContent = error.message;
  }
}

addBtn.addEventListener('click', () => {
  if (newSiteInput.value.trim()) {
    addSite(newSiteInput.value);
  }
});

newSiteInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    if (newSiteInput.value.trim()) addSite(newSiteInput.value);
  }
});

document.querySelectorAll('.chip-btn').forEach(chip => {
  chip.addEventListener('click', () => {
    const url = chip.getAttribute('data-url');
    if (url) addSite(url);
  });
});

enableBtn.addEventListener('click', async () => {
  try {
    if (!configuredSites.length) {
      throw new Error('Add at least one website before enabling capture.');
    }
    const origins = configuredSites.map(s => sourceOrigin(s) + '/*');
    const granted = await chrome.permissions.request({origins});
    if (!granted) throw new Error('Permission for one or more websites was not granted.');

    captureEnabled = true;
    await chrome.storage.local.set({sites: configuredSites, site: configuredSites[0], enabled: true});
    const result = await chrome.runtime.sendMessage({action: 'configure'});
    if (!result?.ok) throw new Error(result?.error || 'Could not enable capture.');
    updateStatus();
    status.textContent = `Enabled for ${configuredSites.length} website(s). Reload open tabs to activate.`;
  } catch (error) {
    status.textContent = error.message;
  }
});

disableBtn.addEventListener('click', async () => {
  try {
    captureEnabled = false;
    await chrome.storage.local.set({enabled: false});
    const result = await chrome.runtime.sendMessage({action: 'configure'});
    updateStatus();
    status.textContent = result?.ok ? 'Capture disabled. Normal magnet handlers restored.' : result?.error;
  } catch (error) {
    status.textContent = error.message;
  }
});

loadConfig();
