# Approved compact modal refinements

16 November 2026. Applies the user's verdict on comparison screens 03, 05, 08
and Unlock Adult Anime (screen 31 in the audit inventory), plus Library hero
tone and discovery action sizing.

## Applied presentation

- Change Password and Unlock Adult Anime use a 480 px white face, rounded
  boundary, subtle watermark and compact content height.
- Exit Choice uses a 580 px face. The status well, raised choice cards,
  recommended badge and remembered-choice row follow the reference order.
- Confirm Series Grouping uses a 650 px face. It appears as a true modal overlay
  without replacing the underlying grouping page or its navigation history.
  Primary grouping badge, safety note and review checkbox retain their function.
- These widths are logical theme pixels before the existing accessibility text
  scale; external shadow padding adds 36 px to the window bounds. Long content
  can scroll when the parent window is too short.
- All four dialogs blur and tint one bounded snapshot of the parent window.
  The dialog itself stays sharp. The backdrop disappears on dismissal or
  destruction. No live page-level graphics blur effect is installed.
- Unlock includes a decorative lock icon; it does not reveal the password or
  add a new security mechanism. Existing masking, validation, recovery and save
  behavior remain in place.

## Library and discovery

The Library hero's pale middle/bottom fades are reduced slightly and the
artwork receives a subtle 8/255 dark tint. This reduces washout without changing
the cached image or the text-side layout. Brightness is a color/opacity value,
not a pixel dimension.

The discovery card's Details and Add actions have equal fixed widths and heights
for each pair. Width is calculated from both labels and updated after import,
so Already in Library / Added to Watching remains readable too.

## Evidence

Fresh temporary-data comparisons:

- Change Password (local artifact: `../../data/compact-modal-review/change-password-comparison.png`)
- Unlock (local artifact: `../../data/compact-modal-review/unlock-comparison.png`)
- Exit Choice (local artifact: `../../data/compact-modal-review/exit-choice-comparison.png`)
- Confirm Grouping (local artifact: `../../data/compact-modal-review/confirm-grouping-comparison.png`)
- All four comparisons (local artifact: `../../data/compact-modal-review/all-modal-comparisons.png`)

Reproduce with `scripts/capture_compact_modals.py`. No passwords were saved,
exit actions executed or real library records modified during the renders.
Focused tests cover bounded blur, dismissal cleanup, password masking, compact
sizes, grouping navigation/review protection and equal discovery controls.

Validation logs: five focused checks passed in
`data/compact-modal-focused-final.log`. The first 703-test full run passed
(`data/compact-modal-full-validation.log`); the final broad run had one
intermittent core scanner heartbeat assertion at 198.8 ms against 100 ms
(`data/compact-modal-final-validation.log`). All 17 scanner-module tests passed
in isolation with a 55.9 ms maximum heartbeat
(`data/compact-modal-scanner-recheck.log`). This test runs the core scanner
without constructing these dialogs. The assertion was not changed or skipped.

## Exit dialog input follow-up

The shared backdrop now ignores mouse input and focus. Compact dialogs use an
opaque native window with a cached matching crop of the blurred background, so
input does not depend on Windows layered-window alpha hit testing. The modal
is raised after its visual backdrop is installed. Rounded surfaces and shadows
remain unchanged. The reported failure was not reproducible with the offscreen
plugin, so native Windows checks were added to validation.

Nine focused tests passed with Qt's Windows platform plugin, including mouse
delivery through the dialog QWindow to both choice cards, radio indicators,
Remember my choice, Cancel and confirmation. A separate test uses `exec_()` to
cover the nested event loop used when closing the real app. Tests assert that
confirmation saves the chosen preference and cancellation saves nothing, using
temporary database fixtures only. Log: `data/compact-modal-windows-visible-tests.log`.
An initial experiment hiding all Windows test windows could not route QWindow
mouse events; rerunning with normal test-window visibility passed. These are
synthetic Qt mouse events, not physical cursor automation.

The full repository validation passed all 706 discovered tests and compilation
checks (`data/compact-modal-input-validation.log`). That run began before the
additional nested-loop test was added; all nine final focused tests, including
that test, passed separately on the Windows plugin.

## Black footer-strip follow-up

The backdrop is now captured while the dialog is hidden and retained only at
the existing bounded resolution. Capturing a visible owned window can include
its old position/footer in the snapshot. The matching background crop is also
rebuilt after native move/resize events, and the opaque dialog always paints
its full bounds, including newly exposed pixels. A Windows regression covers
the longer exit prompt with background downloads active, resizing/moving,
hidden-only capture and continued mouse operation. Fresh fixture renders show
one rounded dialog without the stale footer strip.

Local comparison artifacts are generated under ignored `data/`; they are not included in the public source snapshot.
