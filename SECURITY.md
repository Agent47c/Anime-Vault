# Security and data-safety reporting

Anime Vault is under active development. The [current audit](WHOLE_APP_AUDIT_2026-11-12.md) includes unresolved issues; the repository does not claim production certification or a completed security review.

## Reporting

For a vulnerability, use GitHub's **Security → Advisories → Report a vulnerability** when private reporting is available. If it is unavailable, contact the repository owner through an available private channel before sharing exploit details publicly. Do not put tokens, personal databases, private paths or unpublished exploit details in a public issue.

For an ordinary reproducible bug, use the issue template with a redacted traceback, Windows/Python version, affected operation and a minimal fictional example.

## Operational guidance

- Keep the existing local API bound to loopback. Configure an access token where appropriate; do not expose it to the LAN/internet while audit hardening remains open.
- Keep credentials in local settings/environment only. Do not commit `.env`, database files, resume state, private watch lists or logs.
- Review move/deletion previews and maintain a full SQLite backup before large file operations. Metadata exports do not contain every database table.
- Browser-extension access should remain restricted to the explicitly selected website.
- Test fixes using temporary fixtures before working with real media.

The original `v1.0.0` tag is a historical baseline. There is no separate supported security-maintenance branch or published response-time commitment at present.
