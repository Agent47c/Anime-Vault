const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const {sourceOrigin, validMagnet, allowedSender} = require('../logic.js');
const magnet = 'magnet:?xt=urn:btih:' + 'a'.repeat(40) + '&dn=Example';

test('only the exact chosen website and top-level tab are accepted', () => {
  const sender = {frameId: 0, tab: {url: 'https://nyaa.si/?q=test'}, url: 'https://nyaa.si/'};
  assert.equal(allowedSender(sender, 'https://nyaa.si'), true);
  assert.equal(allowedSender({...sender, frameId: 1}, 'https://nyaa.si'), false);
  assert.equal(allowedSender({...sender, url: 'https://other.example/'}, 'https://nyaa.si'), false);
  assert.equal(allowedSender({...sender, tab: {url: 'https://nyaa.si.evil.example/'}}, 'https://nyaa.si'), false);
  assert.equal(allowedSender(sender, 'http://nyaa.si'), false);
});
test('website normalization and magnet validation reject unsafe data', () => {
  assert.equal(sourceOrigin('https://nyaa.si/?q=anything'), 'https://nyaa.si');
  assert.throws(() => sourceOrigin('javascript:alert(1)'));
  assert.throws(() => sourceOrigin('https://user:password@example.org'));
  assert.throws(() => sourceOrigin('https://*'));
  assert.throws(() => sourceOrigin('https://*.example.org'));
  assert.equal(validMagnet(magnet), true);
  assert.equal(validMagnet('magnet:?xt=urn:btmh:1220' + 'a'.repeat(64)), true);
  assert.equal(validMagnet('https://example.org'), false);
  assert.equal(validMagnet(magnet + '\n'), false);
  assert.equal(validMagnet('magnet:?xt=urn:btih:short'), false);
});

async function contentHarness(config) {
  let click, settingsChanged;
  const messages = [];
  class Anchor { constructor(href) { this.href = href; } }
  const context = {
    HTMLAnchorElement: Anchor, location: {origin: 'https://nyaa.si'}, setTimeout: () => {},
    document: {addEventListener: (_, callback) => { click = callback; },
      createElement: () => ({style: {}, remove() {}}), body: {appendChild() {}}},
    chrome: {storage: {local: {get: async () => config}, onChanged: {addListener: cb => { settingsChanged = cb; }}},
      runtime: {sendMessage: async message => { messages.push(message); return {ok: true}; }}}
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../capture.js'), 'utf8'), context);
  await Promise.resolve();
  function event(overrides = {}) {
    return {isTrusted: true, button: 0, composedPath: () => [new Anchor(magnet)],
      prevented: false, preventDefault() { this.prevented = true; }, stopImmediatePropagation() {}, ...overrides};
  }
  return {click, event, messages, settingsChanged};
}
test('cancel the original magnet navigation before the async native handoff', async () => {
  const h = await contentHarness({site: 'https://nyaa.si', enabled: true});
  const event = h.event();
  const pending = h.click(event);
  assert.equal(event.prevented, true, 'preventDefault must happen synchronously');
  await pending;
  assert.equal(h.messages.length, 1);
  assert.equal(h.messages[0].magnet, magnet);
});
test('unselected websites and synthetic clicks keep their ordinary handler', async () => {
  const h = await contentHarness({site: 'https://other.example', enabled: true});
  const wrongSite = h.event(); await h.click(wrongSite);
  assert.equal(wrongSite.prevented, false);
  h.settingsChanged({site: {newValue: 'https://nyaa.si'}}, 'local');
  const synthetic = h.event({isTrusted: false}); await h.click(synthetic);
  assert.equal(synthetic.prevented, false);
  assert.equal(h.messages.length, 0);
});
test('disabling capture takes effect in an already open webpage', async () => {
  const h = await contentHarness({site: 'https://nyaa.si', enabled: true});
  h.settingsChanged({enabled: {newValue: false}}, 'local');
  const event = h.event(); await h.click(event);
  assert.equal(event.prevented, false);
  assert.equal(h.messages.length, 0);
});

function backgroundHarness(permission = true) {
  let listener;
  const calls = [], scripts = [];
  const context = vm.createContext({URL, console});
  context.importScripts = name => vm.runInContext(fs.readFileSync(path.join(__dirname, '..', name), 'utf8'), context);
  context.chrome = {
    storage: {local: {get: async () => ({enabled: true, site: 'https://nyaa.si'}), set: async () => {}}},
    permissions: {contains: async () => permission, onRemoved: {addListener() {}}},
    scripting: {getRegisteredContentScripts: async () => [],
      unregisterContentScripts: async () => { throw new Error('Cannot unregister a missing script'); },
      registerContentScripts: async values => { scripts.push(...values); }},
    runtime: {onInstalled: {addListener() {}}, onStartup: {addListener() {}},
      onMessage: {addListener: cb => { listener = cb; }},
      getURL: file => 'chrome-extension://connected/' + file,
      sendNativeMessage: async (host, message) => { calls.push({host, message}); return {ok: true}; }}
  };
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../background.js'), 'utf8'), context);
  const request = (message, sender) => new Promise(resolve => listener(message, sender, resolve));
  return {request, calls, scripts};
}
test('first-time setup registers one chosen site without unregistering a missing script', async () => {
  const h = backgroundHarness();
  const response = await h.request({action: 'configure'}, {url: 'chrome-extension://connected/popup.html'});
  assert.equal(response.ok, true);
  assert.equal(h.scripts.length, 1);
  assert.equal(h.scripts[0].matches.join(), 'https://nyaa.si/*');
  assert.equal(h.scripts[0].allFrames, false);
});
test('background rejects other sites before invoking the native app', async () => {
  const h = backgroundHarness();
  const response = await h.request({action: 'capture', magnet},
    {frameId: 0, tab: {url: 'https://other.example'}, url: 'https://other.example'});
  assert.equal(response.ok, false);
  assert.equal(h.calls.length, 0);
});
test('revoked site access blocks native handoff; granted access sends only the selected site', async () => {
  const sender = {frameId: 0, tab: {url: 'https://nyaa.si/'}, url: 'https://nyaa.si/'};
  const denied = backgroundHarness(false);
  assert.equal((await denied.request({action: 'capture', magnet}, sender)).ok, false);
  assert.equal(denied.calls.length, 0);
  const allowed = backgroundHarness(true);
  assert.equal((await allowed.request({action: 'capture', magnet}, sender)).ok, true);
  assert.equal(allowed.calls[0].host, 'com.animevault.capture');
  assert.equal(allowed.calls[0].message.site, 'https://nyaa.si');
});
