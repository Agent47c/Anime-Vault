/* Pure checks shared by the Chrome extension and the no-network tests. */
function sourceOrigin(value) {
  const url = new URL(value);
  if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) {
    throw new Error('Enter an http/https website without credentials.');
  }
  return url.origin;
}
function validMagnet(value) {
  if (typeof value !== 'string' || value.length > 16000 || /[\r\n\0"]/.test(value)) return false;
  let url;
  try { url = new URL(value); } catch { return false; }
  return url.protocol === 'magnet:' && !url.host && !url.pathname && !url.hash &&
    url.searchParams.getAll('xt').some(xt =>
      /^urn:btih:(?:[a-f0-9]{40}|[a-z2-7]{32})$/i.test(xt) || /^urn:btmh:1220[a-f0-9]{64}$/i.test(xt));
}
function allowedSender(sender, site) {
  try {
    return sender.frameId === 0 && !!sender.tab &&
      sourceOrigin(sender.tab.url) === sourceOrigin(site) &&
      sourceOrigin(sender.url) === sourceOrigin(site);
  } catch { return false; }
}
if (typeof module !== 'undefined') module.exports = {sourceOrigin, validMagnet, allowedSender};
