# Profiling callback signature crash

## User-visible failure

Clicking Search releases while `APP_PROFILE=1` raised
`TypeError: ReleaseSearchPage.search() takes 1 positional argument but 2 were given`.
Real session: `14700-1794480166778843100`, at 15:44:18 on 12 November 2026
(Asia/Karachi). The profiler recorded that TypeError; a successful search was not
recorded. This was introduced by the instrumentation, not the search service.

## Cause and fix

PyQt normally inspects the actual callable's code-level positional argument count
and drops excess signal arguments for a slot that accepts fewer arguments.
`clicked(bool)` can therefore connect directly to `search(self)`.

The original profiler used `measured(*args, **kwargs)`. `functools.wraps` restored
metadata but not its code-level argument count, so the extra checked boolean
reached the original zero-argument bound method and crashed.

`app/audit_profile.py:signature_proxy` now creates a forwarding function with the
same actual positional, positional-only, keyword-only and variadic parameters.
Default objects are restored directly, not represented or evaluated as source.
Annotations/metadata are copied. The original timing/error wrapper remains behind
this forwarding signature. Direct invalid calls still raise TypeError; errors
are not swallowed or retried.

This repair applies to all profiler-wrapped callbacks, not only Search. No search
behavior, network policy, DB handling, matching, download submission, UI feature
or visual styling was changed.

## Verification

- `tests/test_audit_instrumentation.py` verifies real code arity, parameter kinds,
  default identity, keyword binding, return values and invalid-call behavior.
- `scripts/audit_smoke.py --signals` uses a temporary DB with networking disabled.
  It exercises `QPushButton.clicked`, `QAction.triggered`, dropdown index changes,
  checkbox toggles, text changes and Return, with zero/one/variadic handlers.
- It clicks the actual `ReleaseSearchPage.search_button` with profiling active,
  mocks only source IO, waits for its worker and confirms results arrive without
  a crash. No real download or external search is submitted.
- It checks **207 loaded profiler-wrapped callable signatures** against their
  originals, covering more than the single reported callback.
- All 8 focused instrumentation tests passed. Full isolated validation passed
  compilation and **all 466 tests in 101.206 seconds**. Output:
  `data/audit-slot-signature-validation.log`.

## Other measured findings — not silently fixed

Latest real session `14700-1794480166778843100`:

| Finding | Evidence | Interpretation |
|---|---|---|
| Startup Storage refresh | 3,255.656 ms, GUI thread | Confirmed startup blocker |
| MainWindow construction / first event-loop turn | 7,340.623 / 8,222.458 ms | Significant startup delay; nested durations are not additive |
| Download-search page construction | 548.523 ms, GUI thread | A separate page-opening stall, not this TypeError |
| Detail page restyling | Up to 227.387 ms, GUI thread | Exceeds the desired 100 ms budget |
| Background full refreshes | 7 completed; maximum 9,225.787 ms | Worker work; slow completion and repeated workload, not proof of GUI blocking by itself |
| Tab queued return | 11 switches; maximum 248.574 ms | Some switches still exceed 100 ms |
| Peak sampled process working set | 679,358,464 bytes, about 648 MiB | High transient memory; no established leak from this short run |
| Malformed JSONL records | 19 across the entire audit file, not just this session | Instrumentation evidence loss; excluded from summaries; concurrent append safety needs review |

The earlier session also captured Organizer styling at 1,113.481 ms and the
native image/GIL freeze already addressed in THUMBNAIL_DEADLOCK_FIX.md. Do not
claim a before/after speedup from these different sessions/workloads.

The callback crash was reproduced and fixed. Remaining performance findings stay
in APP_AUDIT.md for review under the phased audit rules.
