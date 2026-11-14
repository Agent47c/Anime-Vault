# Why Details displays Loading anime details

User report: opening every anime's Details is delayed, sometimes two seconds or
more. The amount varies by title. The initial investigation was diagnostic only.
The user subsequently approved removing the temporary styling cycle. The scoped
implementation and verification are recorded below; no database/media changes
were made.

## Confirmed shared cause

`app/ui/pages/detail_modal.py:DetailModal._reload_async` starts with a loading
label, prepares data in a worker and rebuilds the page through
`_build_ui_steps`. Repainting is disabled until the final build stage completes.
`done`/navigation dispose this Details page, so reopening constructs it again.

The builder assigns legacy inline styles to controls, then its final stage
iterates all child widgets and calls `setStyleSheet('')` before
`refresh_home_style` applies the shared final theme. With Qt style inheritance,
those individual resets trigger substantial repeated styling work. The loop
also performs required plain-text/object-name setup; that behavior must be
preserved in any later fix.

This is common to all anime. More season/release rows create more controls and
therefore more repeated style operations. The data worker is not the entire wait.

## Measurements

Existing real session `6748-1794480712744937600` contained four Details data
preparations of **62–68 ms**. The final styling event was approximately
0.53–0.70 seconds after page construction. The old log did not measure exact
first-presentation time, so it cannot independently verify the user's two-second
perception for those four openings.

New passive probe: `scripts/audit_detail_probe.py` creates a SQLite backup from a
read-only connection and copies only selected artwork into a temporary folder.
All DB/UI work uses that copy. It exercises the actual asynchronous Details
loader, times generator stages and stylesheet operations, then removes the
temporary copy. Network access and deferred episode indexing/previews are
excluded to isolate first-UI-build costs. No media files are moved or modified.

It selected four representative records and tested first/repeat opens. Default
100% text scale, 1450x900 offscreen window, instrumentation enabled. Results:

| Releases in displayed series | First / repeat Details loaded | Data preparation | Final UI stage | Child-style clearing |
|---|---|---|---|---|
| 1 (record 105) | 559 / 464 ms | 89 / 56 ms | 370 / 354 ms | 115 calls, 197 / 195 ms |
| 1 (record 1) | 518 / 494 ms | 68 / 60 ms | 389 / 380 ms | 116 calls, 219 / 211 ms |
| 4 (record 215) | 721 / 685 ms | 68 / 61 ms | 568 / 538 ms | 145 calls, 337 / 310 ms |
| 24 (record 53) | **1,976 / 1,950 ms** | 479 / 456 ms | **1,391 / 1,386 ms** | **390 calls, 798 / 785 ms** |

An earlier run without the per-setter timing measured the 24-release case at
**2,279 / 1,984 ms**. Both runs reproduce roughly two seconds on the shared
Details path. Differences between runs are normal; no speedup is inferred.

In the detailed run, season-table creation itself took approximately 5–14 ms for
one/four releases and 86–87 ms for 24 releases. Poster rendering took under
3 ms. The large case's final shared restyle took about 190 ms, in addition to the
roughly 0.8 seconds spent clearing child styles. These nested timings overlap
other stage totals and must not be added twice.

Evidence: `audit.detail_probe_result` records in `audit_logs/profile.jsonl`.
The log includes exact item IDs/counts and first/repeat visit labels. These are
copied-data, offscreen measurements, not a claim about every normal Windows
window, cold HDD state, larger text scale or concurrent background load.

## Interpretation and proposed focused change

**Confirmed / High:** repeated Details construction and per-child stylesheet
churn are significant GUI-thread costs. They explain why the delay exists for
every title and grows with release count. For the larger case, data preparation
also contributes about half a second. No evidence points to an internet request
as a requirement for initial Details rendering.

Recommended first change, pending user approval under the audit rules:

1. Construct Details controls with the final shared theme directly, rather than
   apply legacy per-control styles and clear them again.
2. Preserve all object names, plain-text safeguards, controls, actions and current
   visual appearance.
3. Repeat this same copied-data probe, UI regression checks and real-library
   opening test. Measure total loaded time and styling separately.

Do not immediately redesign the database, remove features or permanently retain
every Details page. Page/data reuse would require a separate invalidation and
resource-lifetime decision; it is not necessary to address the measured style
churn first. No specific speedup is promised before measurement.

## Approved implementation and measured result

Changes in `app/ui/pages/detail_modal.py`:

- Initialize Details using its existing final `detail_style.qss`.
- Remove 15 temporary stylesheet assignment statements from the active page
  builder/season table (rating-button loops previously repeated some assignments).
- Retain the child loop's plain-text safeguards and object-name setup. Clear
  styles only when a child actually has an independent style to remove; retain
  the final rating-button padding style.
- Assign rating properties at button creation, so final styling can resolve
  immediately. Keep rating sizing, values, signal connections and persistence.
- Avoid reapplying an identical root stylesheet. Theme/text-size changes still
  apply when the generated stylesheet changes.

No feature, action, DB query/identity, data-worker logic, playback behavior, page
reuse policy or navigation lifetime was changed.

Same copied-data probe, 100% scale and 1450x900, instrumentation enabled:

| Case | Before | After | Scope |
|---|---:|---:|---|
| One-release record 105, first open | 571 ms | 276 ms | End-to-end `loaded` signal |
| One-release record 105, repeat | 463 ms | About 0.2 seconds | Same fresh-page reopen |
| Four-release record 215 | About 0.68–0.72 seconds | About 0.29–0.32 seconds | First/repeat isolated probes |
| One Piece, 24 release rows, first | 2,014 ms | 1,000 ms | End-to-end `loaded` signal |
| One Piece, 24 release rows, repeat | 2,003 ms | 998 ms | Same fresh-page reopen |
| Child style resets, 24 release rows | 390 calls, about 0.8 seconds | 1 call, about 0.2 ms | Not including the final shared-theme work |
| Final shared restyle, 24 release rows | About 190–197 ms | About 3 ms | No identical stylesheet reset |

These are observations from this copied-data/offscreen fixture, not a universal
latency guarantee. The large case still has roughly half a second of data/coverage
preparation, which this styling-only fix intentionally leaves unchanged.

Before/after screenshots of all four cases were rendered and visually inspected.
Controls, artwork, colors, labels and feature access were retained. Final checks
show no horizontal page overflow. Minor rating-row layout settling and synopsis
scroll-handle differences exist; these are not claimed as pixel-identical renders.
Local images: `audit_logs/details-before-*.png`, `audit_logs/details-final-*.png`.

Regression coverage in `tests/test_detail_navigation_performance.py` verifies a
24-season page does not reset every child's stylesheet, identical theme refresh
does not reassign the root style, all season rows/rating controls remain, notes
are intact and the page has no horizontal scrollbar. The 27 focused Details/UI
tests passed. Final isolated validation passed compilation and **all 467 tests
in 98.153 seconds**. Output: `data/details-style-validation.log`. The pipeline's
500-file scanner heartbeat fixture measured a 46.1 ms maximum; this is separate
from the Details timings above. The profiler smoke fixture also passed three
consecutive standalone shutdown checks after explicit widget-tree cleanup.

The real-library user retest is pending. Restart the app before comparing so the
new Details builder is loaded.
