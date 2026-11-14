# Codebase review and workspace organization — 14 November 2026

## Scope and evidence

Reviewed the current changelog, working-tree diff from Git HEAD, new source/tests,
Chrome-extension changes, installer source and existing setup artifacts. This
checkout contains uncommitted work from several sessions; a Git diff alone cannot
attribute every line to one author or prove when it changed.

This pass organizes references and documentation, repairs paths, and improves test
verification. It does not redesign screens or change the production app's shutdown,
authentication, playback, download or installer behavior. Personal databases,
media, caches and existing installers stay in their current locations.

## Changes found

| Area | What is present now | Verification limits |
|---|---|---|
| Versions | App is 1.0.1; Chrome extension is independently versioned 1.2.0 | A matching source version does not prove a setup contains the newest source |
| Downloads | Completed/seeding progress normalization; blue completed, orange seeding, coral active; separate Seeding state/filter counts | Indexed records and native rechecking are handled separately; real restored transfers were not started here |
| Playback | PotPlayer IPC adapter, per-process window lookup, millisecond conversion, `/new` and `/seek=` integration | Existing tests mock IPC; native ABI issues below remain |
| Installer | Master icon used in build/window/tray; matching installer AppId; restart-replacement and process cleanup | Both 1.0.0 and 1.0.1 setup files exist; neither was run in this pass |
| Exit | Immediate hide, shutdown watchdog and several hard process exits | This reduces lingering windows but introduces durability/test risks below |
| Adult visibility | Password setup/change/unlock, three-question recovery, restart locking, DB/library/discovery gating | This is a local visibility lock, not database encryption or an OS parental-control boundary |
| Chrome | Multiple configured sources, optional per-origin permissions, revised popup/capture/bridge, 1.2.0 manifest | Existing 18 tests cover selected logic, not every Chrome permission or reconnect lifecycle |
| Earlier retained work | Immediate rate limits, maximized geometry, cached release discovery/details, optional ZIP profile backup | These predate this review and are included in the working tree |

The latest changelog documents 1.0.1 downloads, PotPlayer, installer and exit work.
It does not yet describe the adult-lock and multi-site extension additions.

## Prioritized findings to resolve before another release

### P1 — Hard exit can interrupt durable operations

`app/ui/main_window.py` schedules `os._exit(0)` after 2.5 seconds and also exits
directly in several close paths. `_finish_pending_exit` stops waiting after a
bounded tick count. If a slow drive, restore, file move or torrent state save is
still working, the process can terminate before it finishes. The new exit tests
verify that hard exit was requested; they do not establish crash-safe persistence.
Next: cooperative cancellation, explicit durable-operation completion and a
user-visible timeout path, tested in child processes with slow/failing storage.

### P1 — Installer kills processes by name

`installer/AnimeVault.iss` uses `taskkill /F /T /IM` and calls it during setup
initialization, before the installation is confirmed. This can terminate another
copy with the same name, including ongoing work, rather than only the target
installation. Next: graceful target-path/PID-specific shutdown; request permission
for force termination only after an explicit upgrade action.

### P1 — PotPlayer native result buffer is not pointer-sized

`app/core/potplayer.py:send` allocates `wintypes.DWORD` and does not declare ctypes
argument/return signatures. Microsoft's API expects a `PDWORD_PTR` result and
pointer-sized handles. On a 64-bit build this risks incorrect results or memory
overwrite. Timeout/failure also returns zero, indistinguishable from valid zero
playback position. Next: declare the complete ABI with a pointer-sized result,
propagate timeout, and test a native fixture plus app-launched PotPlayer.
[Microsoft API signature](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendmessagetimeoutw).

### P1 — Adult lock is not enforced uniformly at rendering boundaries

Discovery requests use both `is_adult_unlocked()` and the mature preference, but
`ReleaseNewsPage.render` checks only the preference for selected media, related
releases and discovery rows. Cached/in-flight adult data can therefore bypass the
new lock at that boundary when the preference stays enabled. `db.get_all_franchises`
also defaults to including adult records if visibility evaluation raises.
Next: one fail-closed visibility policy applied to cache, API, model and render
boundaries, plus a regression that locks while results are in flight.

### P2 — Password setup mutates state before validating recovery questions

`adult_content.set_password` writes the new salt/hash before validating all three
answers; invalid recovery input can leave a changed password after reporting
failure. Salt/hash/questions are separate state writes. `_hash_secret` case-folds
passwords as well as answers, making passwords case-insensitive. Hashing is also
called synchronously by dialog handlers. Next: validate first, commit credentials
atomically, preserve password case, and move hashing off the GUI thread without
breaking existing stored credentials.

### P2 — Settings changes still rebuild broad library state

`MainWindow._apply_settings_preferences` refreshes the library and metrics for
every settings change. This is a likely source of avoidable latency when changing
unrelated preferences. Next: compare changed preference keys, invalidate only the
affected models, and measure real event-loop stalls before refactoring.

## Verification integrity issue corrected in this pass

The first `scripts/check.py` run returned success after approximately 190 tests,
without a unittest final summary. A delayed exit-test callback called the real
`os._exit(0)` after its mock had ended. The checker accepted that zero exit code.
Consequently the old 526-pass claim cannot be established from that run.

The exit test now captures its watchdog rather than leaving a live termination
callback and avoids starting unrelated shutdown workers. The regression runner
writes a completion record only after the discovered suite finishes. The checker
requires the expected count, actual count and success flag; premature zero-exit
termination now fails verification. Two regressions cover this guard.

The corrected complete run passed **535 Python tests** in 134.419 seconds with
the completion record verified, compilation checks passed, and **18 Chrome
extension tests** passed. The first publication hygiene/link check also passed;
it is a focused pattern/path check, not a comprehensive security certification.
Logs: `data/workspace-review-final-validation.log`,
`data/workspace-extension-check.log`, `data/workspace-publication-final.log`.
The deliberate incomplete-run guard regression prints an expected ERROR message
inside the otherwise successful full-suite log; it asserts that this case fails.

## Workspace organization

- 22 supplied design folders plus legacy `ui.html` are under `design/references/`.
- 53 existing root-level implementation/audit notes moved to `docs/history/`.
- Feature navigation and organizer usage moved to `docs/guides/`.
- Product specification and backlog moved to `docs/planning/`.
- Historical generated previews moved to ignored `design/previews/`.
- Personal TXT import lists and the extension signing key moved under ignored
  `data/import-lists/` and `data/private/`. The packaged CRX moved to ignored
  `dist/browser-extension/`; the unrelated external installer to ignored
  `tools/external-installers/`.
- Runtime entry points and root CLI tools remain stable. The build's master-icon
  reference was updated; the runtime icon still resides in `assets/app.ico`.
- All 165 file contents were checksum-verified immediately after moving.
  Markdown links were subsequently repaired in ten documents. The move manifest
  records source/destination paths and original hashes.

[Move manifest](workspace-organization-2026-11-14.json) ·
[Design index](../../design/README.md) · [Documentation index](../README.md)

## Suggested order for the next UI work

1. Resolve the P1 safety/ABI/visibility findings and verify them before repackaging.
2. Establish one reusable page header, breadcrumb and action-row component; preserve
   tab navigation memory and existing features.
3. Review Library/calendar/Details against the retained references one screen at a
   time; capture before/after renders at 100%, 125% and 150% scale.
4. Reuse the existing virtualized transfer/episode/poster delegates and async image
   cache. Measure page switching and scrolling rather than adding more effects.
5. Update the feature/navigation map and release notes only after behavior is
   verified. Ask before adding features from old mockups.
