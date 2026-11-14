# Focused image-scaling freeze fix

Approved by the user during the audit on 12 November 2026. This is an explicit
exception to the earlier audit-only rule, not approval for other optimizations.

## Observed failure

Real process 20052, session `20052-1794478825431514200`, stayed open with Windows
Responding=False. The internal log stopped at 15:21:22 Asia/Karachi. Repeated
external native samples found:

- Worker 9248 owned the GIL while waiting in `QImage::smoothScaled`,
  `QImage::scaled` and `QSemaphore::acquire`.
- Its Python caller was `RefreshWorker.run -> cached_refresh_image`; that worker
  was resizing a cached image using `Qt.SmoothTransformation`.
- The GUI was in `VirtualPosters.sync`, submitting another Python image reader to
  `QThreadPool.globalInstance`, with native frames waiting for Python's GIL.
- Other readers, the logger and watchdog were also waiting for the GIL.

The saved function-only native capture is `audit.external_stack`, session
`18692-1794479281827504100`, target PID 20052, captured at 15:28:02 local time in
`audit_logs/profile.jsonl`. No local variables or full memory dump were saved.
Some private native symbols are approximate; exact Qt semaphore ownership is not
fully resolved. The native scaling/GIL blockage is confirmed; interaction with
Qt's shared rendering pool is the likely deadlock mechanism.

The user approved closing this frozen process after capture. Only PID 20052 was
terminated, after checking that it was Python with the Anime Vault window title.
No other Python application or media file was removed.

## Changes

1. `app/core/image_profiles.py:load_cached_image` accepts optional `max_size`.
   The bounded path decodes/downsizes through Pillow LANCZOS, then creates an
   owning RGBA QImage copy. It does not dispatch a Qt smooth-scaling operation
   from a Python image worker. Invalid/unsupported/unsafe-size images retain a
   null-image fallback. The default unbounded call remains available.
2. `app/ui/refresh.py:cached_refresh_image` requests the same 360x540 poster and
   1280x720 banner limits through that bounded decoder. The worker's
   `QImage.scaled(...SmoothTransformation)` call is removed. Existing version keys,
   cache hit handling and 128 MiB decoded-cache limit remain.
3. `app/ui/refresh.py:thumbnail_pool` owns a separate Qt pool with at most two
   Python image readers. It keeps these jobs out of Qt's native global rendering
   pool. Grid and list use the same bounded reader pool.
4. `app/ui/components/virtual_posters.py` and `virtual_library_list.py` submit
   `_Read` jobs to that pool. Slot rebinding, stale-image checks, selection,
   navigation, artwork links and the UI appearance are retained.

No schema, DB identity, watch history, download behavior, media path, feature or
UI-layout changes were made. Downscaled pixels are memory thumbnails; original
cached source images are not overwritten with thumbnails. Existing ICC metadata
repair behavior is retained. Verification used temporary copies, not real media.

## Regression coverage

`tests/test_thumbnail_deadlock.py` checks:

- Worker thumbnail loading never calls QImage.scaled.
- Poster/banner limits, aspect ratio, alpha and owning pixel lifetime survive.
- Small artwork is not enlarged; bad bytes yield a safe fallback.
- Source bytes remain unchanged for an ordinary image.
- The shared thumbnail pool is capped at two and differs from Qt's global pool.
- An isolated child process completes concurrent thumbnail loading and scrolling
  within a timeout; it uses generated artwork and a temporary DB.

`scripts/audit_image_stress.py` supplies that process-level regression. Without
`--synthetic`, it copies 32 artwork files to a temporary directory and exercises
128 fixture records with cold/warm scrolling. It never uses the real DB. With
profiling disabled it does not require the temporary instrumentation module.

Focused unit/UI suite: **17 passed**. Copied-artwork checks:

| Mode | Slots | Cold tour | Warm tour | >100 ms heartbeat delays | Maximum lateness |
|---|---:|---:|---:|---:|---:|
| Profiling off | 25 | 916.734 ms | 870.304 ms | 0 | 52.997 ms |
| Profiling on | 25 | 934.280 ms | 874.882 ms | 0 | 46.592 ms |

Tour durations include deliberate waits and must not be interpreted as frame time
or a before/after speedup. Profiled peak working set was 107,200,512 bytes. Its
JSONL evidence session is `13336-1794479560482805000`.
Full isolated validation (`python scripts/check.py`) passed compilation and
**all 464 tests in 100.819 seconds**. Its 500-file scanner heartbeat fixture
measured a 72.0 ms maximum. Output: `data/thumbnail-deadlock-validation.log`.
The user's real-library retest remains pending; isolated completion does not
guarantee every real HDD/workload is stall-free.
