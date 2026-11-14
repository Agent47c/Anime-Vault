# Anime Vault privacy and data use

Anime Vault stores its library database, watch state, ratings, notes, media paths,
download records, settings and caches locally. There is no added analytics,
advertising SDK or Anime Vault cloud-library upload in this application.

Metadata lookups contact AniList and Jikan; artwork downloads contact provider
image servers. Queries/identifiers and ordinary network information such as your
IP address are therefore visible to those services. User-selected download source
searches contact the configured website. Approved torrent transfers communicate
with trackers/peers and can reveal your IP address to them. Third-party services
operate under their own policies; local storage does not mean zero network use.

The optional Chrome extension stores the selected website, enabled state and
connection status in local extension storage. It reads release links on the
explicitly permitted source, relays selected magnet links/search results through
native messaging, and may open a temporary inactive source-search tab. It does not
collect browsing history or inspect unrelated websites. See its bundled
[privacy page](browser-extension/privacy.html) and review Chrome permissions.

SQLite backups include all database state. Optional full-profile backups add
download resume metadata and, when selected, image caches. They do not include
anime videos, executable code, .env API tokens or machine-specific Chrome bridge
registration. Backups may contain private paths, notes and source/transfer details;
keep them private. Logs and diagnostic evidence may contain private paths too.

An existing local API bridge serves library/media information to local clients.
Keep it bound to loopback and configure authentication as appropriate. This policy
does not claim that all outstanding security-audit findings have been resolved.
