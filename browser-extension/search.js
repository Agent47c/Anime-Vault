/* Runs in an isolated world on the one permitted source tab. No page scripts. */
function extractSourceResults() {
  const pageText = (document.body?.innerText || document.body?.textContent || '').slice(0, 20000);
  const pageTitle = document.title || '';
  if (/just a moment|verify (?:you are|that you are) human|checking your browser|attention required|access denied/i.test(pageTitle) ||
      document.querySelector('#challenge-running, #challenge-form, .cf-turnstile, iframe[src*="challenges.cloudflare.com"]')) {
    return {error: 'Browser verification is required. Click Open source in Chrome, complete the website check, then click Search releases again. Anime Vault cannot bypass this check.'};
  }
  const rows = [...document.querySelectorAll('table.torrent-list tbody tr, table.torrent-list > tr')];
  const generic = !rows.length;
  const candidates = generic ? [...document.querySelectorAll('a[href^="magnet:"]')].map(a => a.closest('tr,article,li,.result') || a.parentElement) : rows;
  const results = [], seen = new Set();
  for (const row of candidates.slice(0, 100)) {
    const magnet = row.querySelector('a[href^="magnet:"]')?.href;
    if (!magnet || seen.has(magnet)) continue;
    seen.add(magnet);
    const cells = [...row.querySelectorAll('td')];
    const links = [...row.querySelectorAll('a[href*="/view/"]')].filter(a => !a.classList.contains('comments'));
    const title = (links.at(-1)?.getAttribute('title') || links.at(-1)?.textContent || row.querySelector('[title]')?.getAttribute('title') || row.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 300);
    results.push({title, magnet, size: generic ? '' : (cells[3]?.textContent || '').trim(),
      seeders: generic ? null : Number((cells[5]?.textContent || '').trim()),
      quality: title.match(/\b(480|720|1080|2160)p\b/i)?.[0] || '',
      group: title.match(/^\[([^\]]+)\]/)?.[1] || ''});
  }
  if (!results.length) {
    if (!rows.length && /\bno (?:results|torrents)(?: were)? found\b|\byour search did not match\b/i.test(pageText)) return {results: []};
    if (rows.length) return {error: 'The source loaded a results table, but no magnet links could be read. Open source in Chrome to inspect the results or use Paste magnet / torrent.'};
    if (!document.querySelector('table.torrent-list') && generic) {
      return {error: 'The source page has not provided readable torrent results. Click Open source in Chrome to check whether it loaded, requires verification, or uses an unsupported layout; then retry Search releases. You can also use Paste magnet / torrent.'};
    }
  }
  return {results};
}
if (typeof module !== 'undefined') module.exports = {extractSourceResults};
