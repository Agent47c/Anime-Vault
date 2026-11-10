const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const {extractSourceResults} = require('../search.js');
const magnet = 'magnet:?xt=urn:btih:' + 'a'.repeat(40);

test('Nyaa rows become structured releases with seeders and quality', () => {
  const title = '[ASW] Example S02E11 [1080p]';
  const link = {classList: {contains: () => false}, getAttribute: () => title};
  const cells = ['', '', '', '1.2 GiB', '', '18', '2'].map(textContent => ({textContent}));
  const row = {querySelector: () => ({href: magnet}), querySelectorAll: query => query === 'td' ? cells : [link]};
  global.document = {querySelectorAll: () => [row], querySelector: q => q === 'table.torrent-list' ? {} : null};
  try {
    const result = extractSourceResults().results[0];
    assert.equal(result.title, title); assert.equal(result.size, '1.2 GiB');
    assert.equal(result.seeders, 18); assert.equal(result.group, 'ASW'); assert.equal(result.quality, '1080p');
  } finally { delete global.document; }
});

test('empty source results differ from a browser challenge/unreadable page', () => {
  global.document = {querySelectorAll: () => [], querySelector: q => q === 'table.torrent-list' ? {} : null};
  assert.deepEqual(extractSourceResults(), {results: []});
  global.document.querySelector = () => null;
  assert.match(extractSourceResults().error, /verification/);
  delete global.document;
});

function harness({permission = true, redirected = false, error = false, delayed = false} = {}) {
  const calls = [], messages = [];
  const context = vm.createContext({URL, console, setTimeout, clearTimeout, TextEncoder});
  context.importScripts = name => vm.runInContext(fs.readFileSync(path.join(__dirname, '..', name), 'utf8'), context);
  context.chrome = {
    storage: {local: {get: async () => ({enabled: true, site: 'https://nyaa.si'}), set: async () => {}}},
    permissions: {contains: async () => permission, onRemoved: {addListener() {}}},
    runtime: {onInstalled: {addListener() {}}, onStartup: {addListener() {}}, onMessage: {addListener() {}}},
    scripting: {executeScript: async () => {
      const pending = delayed && !calls.includes('extract');
      calls.push('extract');
      return [{result: pending ? {error: 'The source page has not provided readable torrent results.'} : {results: [{title: 'Example - 01', magnet}]}}];
    }},
    tabs: {
      create: async values => { calls.push(values); return {id: 1}; },
      get: async () => { if (error) throw new Error('Source unavailable'); return {status: 'complete', url: redirected ? 'https://other.example/' : 'https://nyaa.si/?q=Example'}; },
      remove: async id => { calls.push({removed: id}); },
      onUpdated: {addListener() {}, removeListener() {}}
    }
  };
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../background.js'), 'utf8'), context);
  return {calls, messages, search: url => context.runSourceSearch({id: 'search', url}, {postMessage: value => messages.push(value)})};
}

test('source search uses an inactive permitted tab and returns results to the app', async () => {
  const h = harness(); await h.search('https://nyaa.si/?q=Example');
  assert.equal(h.calls[0].active, false);
  assert.equal(h.messages[0].results[0].title, 'Example - 01');
  assert.equal(h.calls.at(-1).removed, 1);
});
test('wrong-origin and revoked permission searches never create tabs', async () => {
  for (const [options, url] of [[{}, 'https://nyaa.si.evil.example/'], [{permission: false}, 'https://nyaa.si/']]) {
    const h = harness(options); await h.search(url);
    assert.equal(h.calls.length, 0); assert.match(h.messages[0].error, /Enable/);
  }
});
test('source redirects cannot inject into a different website', async () => {
  const h = harness({redirected: true}); await h.search('https://nyaa.si/');
  assert.equal(h.calls.includes('extract'), false); assert.match(h.messages[0].error, /redirected/);
});
test('failed tab loading closes the temporary tab and gives retry feedback', async () => {
  const h = harness({error: true}); await h.search('https://nyaa.si/');
  assert.equal(h.calls.at(-1).removed, 1); assert.match(h.messages[0].error, /unavailable/);
});

test('an explicit no-results page without a table is an empty search, not a failed source', () => {
  global.document = {body: {innerText: 'No results found'}, querySelectorAll: () => [], querySelector: () => null};
  try { assert.deepEqual(extractSourceResults(), {results: []}); }
  finally { delete global.document; }
});

test('browser challenges give a verification instruction rather than empty results', () => {
  global.document = {title: 'Just a moment...', querySelector: () => null};
  try { assert.match(extractSourceResults().error, /verification is required/); }
  finally { delete global.document; }
});

test('rows without readable magnet links do not silently become a successful empty result', () => {
  const row = {querySelector: () => null};
  global.document = {querySelectorAll: () => [row], querySelector: () => null};
  try { assert.match(extractSourceResults().error, /no magnet links/); }
  finally { delete global.document; }
});

test('delayed source rendering is retried before returning results and closing its tab', async () => {
  const h = harness({delayed: true}); await h.search('https://nyaa.si/');
  assert.equal(h.calls.filter(c => c === 'extract').length, 2);
  assert.equal(h.messages[0].results[0].title, 'Example - 01');
  assert.equal(h.calls.at(-1).removed, 1);
});
