# Temporary audit instrumentation inventory

Branch: `codex/audit-instrumentation`, created from
`feature/selected-site-magnet-capture` on 12 November 2026.

The starting working tree already contained extensive modified and untracked app
files. Those predate this audit. This branch does **not** provide a clean committed
baseline of that work. Do not use reset, clean, or whole-file checkout to remove
the audit.

## Files touched by this audit

| File | Purpose |
|---|---|
| `main.py` | Guarded AUDIT blocks before imports and around QApplication creation/teardown |
| `chrome_magnet_host.py` | Guarded AUDIT block, no stdout logging |
| `builtin_torrent_host.py` | Guarded AUDIT block for helper-process timings |
| `.gitignore` | AUDIT block excludes local evidence from Git |
| `app/audit_profile.py` | Opt-in writer, wrappers, SQL timing, Qt watchdog and memory |
| `scripts/audit_inventory.py` | Read-only real DB counts and installed versions |
| `scripts/audit_smoke.py` | Temporary DB verification and deliberate artificial stall |
| `scripts/audit_session.py` | Read evidence and summarize timings |
| `scripts/audit_capture.py` | Function-only external stack capture to the same log |
| `scripts/audit_detail_probe.py` | Passive timing of Details on a DB/artwork copy |
| `tests/test_audit_instrumentation.py` | SQL/rollback/backup, redaction, disabled mode and native stdout tests |
| `audit_logs/CHANGES.md` | This inventory and removal procedure |
| `APP_AUDIT.md` | Phased working report |
| `AUDIT_CALLBACK_SIGNATURE_FIX.md` | Profiler slot-signature repair and latest findings |
| `DETAILS_LOADING_AUDIT.md` | Measured shared Details-build/style delay |

Measurements append to one file: `audit_logs/profile.jsonl`. Records contain UTC
timestamps, process/session/thread IDs, action, milliseconds and available counts.
No DB resets, real file moves/deletes or torrent submissions were performed by
the audit setup. A subsequent real-session freeze led to explicit user approval
for one focused fix; see the separate section below.

Qt memory sampling counts existing GC-tracked live QWidget Python wrappers,
excluding native-only internal widgets. It does not create native wrappers, force
garbage collection or keep widget references alive. A development teardown issue
with direct native-widget enumeration was caught in isolated checks; the final
instrumentation uses passive wrapper counting and explicit probe detachment.
Final isolated compilation and all 460 tests passed (96.308 seconds).

Later instrumentation repair: `app/audit_profile.py` now preserves real callback
signatures so PyQt retains signal argument trimming. `scripts/audit_smoke.py` and
`tests/test_audit_instrumentation.py` add profiled signal/search-click checks;
207 loaded wrapped signatures are verified. This changes instrumentation only.
Full isolated compilation and all 466 tests passed (101.206 seconds).

## User-approved exception: image freeze

Application files changed after explicit approval: `app/core/image_profiles.py`,
`app/ui/refresh.py`, `app/ui/components/virtual_posters.py`,
`app/ui/components/virtual_library_list.py`. Permanent regression files:
`tests/test_thumbnail_deadlock.py`, `scripts/audit_image_stress.py`.
Documentation: `THUMBNAIL_DEADLOCK_FIX.md`, `CHANGELOG.md`, and this working report.
These are **not** instrumentation to discard; removing the profiler must preserve
the approved fix and its regression tests.
After the fix, all 464 isolated tests passed in 100.819 seconds.

For diagnosis, py-spy 0.4.3 was installed locally under ignored
`audit_logs/tools`; no global Python package setup was changed. External captures
omit locals. Native captures may briefly pause a process. The user approved
closing only frozen process 20052 after the evidence was preserved.

## User-approved exception: Details styling

After reviewing the measured cause and proposed approach, the user approved
removing the redundant Details styling cycle. Application change:
`app/ui/pages/detail_modal.py`. Permanent regression addition:
`tests/test_detail_navigation_performance.py`. Preserve these approved changes
when removing instrumentation. `scripts/audit_detail_probe.py` gained optional
before/after screenshot rendering for verification; it remains removable audit
instrumentation. Details and measured results: `DETAILS_LOADING_AUDIT.md`.
The profiler's isolated smoke fixture also now disposes its widget tree while
QApplication is alive, rather than relying on interpreter teardown. This is
test-fixture cleanup, not a change to the real application's shutdown behavior.
Final Details validation: compilation and all 467 isolated tests passed in
98.153 seconds. Source audit hooks can still be removed independently of this
approved styling fix and its regression test.

## Launch and disable

Close any existing app instance, including the tray instance. In PowerShell:

```powershell
Set-Location 'E:\Anime Details'
$env:APP_PROFILE='1'
python .\main.py
```

The torrent helper inherits the switch. For Chrome's separately launched native
host to inherit it, completely exit Chrome and launch Chrome from that same
PowerShell session. We will do that in its own guided checklist. Do not change
Windows' permanent environment variables.

Disable for the next launch:

```powershell
Remove-Item Env:APP_PROFILE -ErrorAction SilentlyContinue
```

The running app must restart for disabling/removal to take effect.

## Exact safe removal

1. Gracefully close the profiled app, its helpers and Chrome's native connection.
2. Unset `APP_PROFILE` using the command above.
3. Remove **only** the marked AUDIT-START through AUDIT-END blocks in `main.py`,
   `chrome_magnet_host.py`, `builtin_torrent_host.py` and `.gitignore`.
4. Remove newly added `app/audit_profile.py`, `scripts/audit_inventory.py`,
   `scripts/audit_smoke.py`, `scripts/audit_session.py` and
   `scripts/audit_capture.py`, `scripts/audit_detail_probe.py` and
   `tests/test_audit_instrumentation.py` when no
   longer needed. The local `audit_logs/tools` utility may also be archived or
   removed. Preserve the approved image fix and its separate regression files.
5. Archive the report, this inventory and local evidence if desired. Keep the
   ignore block if retaining private logs.
6. Restart normally: `python .\main.py`. Without the switch no profiler is imported
   or installed by the entry points.

Switching branches alone does not discard uncommitted instrumentation. A
destructive Git discard command could erase the pre-existing work, so none is
recommended here.
