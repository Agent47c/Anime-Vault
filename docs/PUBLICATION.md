# Public source snapshot — 13 November 2026

This publication includes the current Python desktop application, Chrome-extension source, tests, bundled fonts/notices, retained HTML/screenshot design inputs and implementation/audit documentation. It is an owner-requested direct update to `main`; no pull request or force push is intended.

## Documentation changes

- A rewritten README with installation, first-run instructions, features, data/configuration behavior, limitations, validation and links to detailed guides.
- Six screenshots of the running Qt UI, captured from a temporary fictional library, and a reproducible generator.
- A current built-in download guide, documentation index, security-reporting instructions and bug-report template.
- A factual repository description and 20 relevant GitHub topics, with research sources in [DISCOVERABILITY.md](DISCOVERABILITY.md).
- A publication guard for high-confidence secret patterns, excluded runtime files, oversized artifacts and broken primary documentation links. This is not a complete security scanner.

## Validation

Before publication, `python scripts/check.py` passed **502 tests**, source compilation and the 500-file scanner heartbeat check. Maximum heartbeat gap was **60.1 ms** in that run. The two Chrome-extension test files passed **18 tests**. The publication check and screenshot rendering were also run. CI independently checks the pushed revision.

This is a source snapshot, not a newly certified stable release or installer. The original `v1.0.0` tag is preserved. Open findings in the [whole-app audit](../WHOLE_APP_AUDIT_2026-11-12.md), including scattered-location season counting, remain unresolved by this documentation/publication pass.

## Excluded material

Personal databases, `.env`, tokens/keys, watch-list TXT files, cached provider artwork, raw audit logs, crash dumps, torrent/resume state, downloaded media, virtual environments and build outputs are not part of the public snapshot. Local credential-manager helpers remain ignored. Screenshot titles, cover art, paths and transfer figures are fictional; screenshots are not evidence of live downloads.

## Audit reproduction tools

- `python scripts/audit_whole_app.py` reproduces the additional isolated edge-case observations; it uses a temporary database and an in-process API test client. It is intentionally diagnostic, not a passing regression test.
- `python scripts/audit_split_season.py` demonstrates one season split across two temporary locations.

Raw evidence logs stay local because diagnostic logs can contain private paths. See the audit report for recorded outcomes and limitations.
