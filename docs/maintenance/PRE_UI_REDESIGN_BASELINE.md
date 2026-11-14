# Source checkpoint before the next UI redesign

14 November 2026. Owner requested a direct GitHub update before providing the
next design screens and guidelines. Preserve the existing `v1.0.0` tag; this is
a source checkpoint on main, not a new tagged release or installer publication.

## Included changes

- Application source reports version 1.0.1; the independent Chrome extension is 1.2.0.
- Immediate propagation for Later, Not interested, Mute, Watched and ignore,
  Dismiss and Restore across the cached Library home and Updates views.
- Download completion/progress and seeding presentation; immediate readable
  transfer-rate controls; remembered maximized window state.
- PotPlayer playback integration; selected-release details, cached artwork and
  discovery pagination; mature-content preferences and password/recovery controls.
- Multi-source selected-site Chrome capture and updated popup/privacy information.
- Optional full-profile ZIP backups with optional artwork/thumbnail caches.
- Standalone/upgrade packaging source and master application artwork. Existing
  local installers remain local; personal/runtime content is not published.
- Organized reference folders, documentation history, feature/navigation guides,
  a recorded move manifest, and stronger regression-run completion verification.

## Verification and known limitations

The latest complete local run passed **539 Python tests** in 137.055 seconds,
compilation, and the regression completion guard. The extension has **18 passing
tests**. Publication hygiene checks inspect guarded secret patterns, excluded
runtime files, large artifacts and primary documentation links; they are not a
complete secret scan or security certification.

Retain the findings in the [14 November review](CODEBASE_REVIEW_2026-11-14.md):
forced shutdown durability, installer process termination scope, PotPlayer ctypes
ABI, inconsistent adult visibility checks, credential-update atomicity, and broad
settings invalidation. Passing current tests does not resolve these findings.
See also the [update-choice fix and test evidence](UPDATE_CHOICE_PROPAGATION_FIX.md).

## Next UI phase

The user will supply new UI screens and guidelines. Wait for those instructions
before changing layouts. Implement one screen at a time, preserve existing
functionality and navigation, and distinguish visual changes from feature changes.
The incoming guidelines determine which new features, if any, are authorized.

Design references: [design index](../../design/README.md).
Current feature destinations: [navigation map](../guides/All%20Feature%20and%20their%20Navigation.md).
