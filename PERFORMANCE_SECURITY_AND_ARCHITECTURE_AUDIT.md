# Performance, Security, and Architecture Audit

This document provides a detailed code-level audit of performance bottlenecks, security findings, and architectural improvements across **Anime Library & Storage Manager (`Anime Vault`)**. Every entry documents:

1. **Issue & Exact Location** (modules, symbols, line numbers)
2. **Cause** (the exact mechanism in code)
3. **Effect on the App** (observable user and runtime impact)
4. **Changes / Repair** (actionable implementation steps and existing test constraints to preserve)
5. **Effect on the System** (performance, memory, threading, safety, and maintenance outcomes after repair)

> **Scope Note:** All findings below were verified by direct static inspection of the codebase on branch `feature/selected-site-magnet-capture`.

---

## Quick Summary Matrix

| ID | Category | Severity / Impact | Primary Files | Core Symptom / Risk |
| :--- | :--- | :--- | :--- | :--- |
| **PERF-01** | Performance | **Critical** | `detail_modal.py`, `main_window.py`, `refresh.py` | Every note keystroke, rating click, and status change triggers sync DB writes + full-library rebuild cascades |
| **PERF-02** | Performance | **High** | `detail_modal.py` | Every rating click re-parses the full modal QSS stylesheet and unpolishes/re-polishes all 10 rating buttons twice |
| **PERF-03** | Performance | **High** | `rematch_dialog.py`, `matching.py`, `detail_data.py`, `custom_entry.py`, `anilist_client.py` | Double full-DB `:memory:` backups, sequential 0.7s rate-limited API hops, sync art download, and full UI teardown on rematch/rename |
| **PERF-04** | Performance | **High** | `library_page.py` | Batch watch-status updates loop synchronous SQLite commits on the GUI thread, followed by duplicate sync + async refreshes |
| **PERF-05** | Performance | **Critical** | `main_window.py`, `refresh.py`, `db.py` | Switching to a dirty tab copies all of `library.db` to `:memory:`, decodes every cover & banner image into RAM, and re-runs `disk_snapshot()` on the GUI thread |
| **PERF-06** | Performance | **High** | `storage_page.py` | Synchronous N+1 season queries, duplicate `episode_inventory()`, sync image scaling, and 6 `setCellWidget()` wrappers per row on open/refresh |
| **PERF-07** | Performance | **Medium** | `db.py`, `library_page.py`, `navigation.py`, `settings_page.py`, `theme_scopes.py` | Per-connection WAL/PRAGMA overhead, missing SQL indexes, 3× `get_all_franchises()` calls in calendar refresh, `previous.grab()` screenshot on drawer open, sync keystroke write in Settings |
| **PERF-08** | Performance | **High** | `library_page.py`, `home_poster.py`, `organizer_page.py`, `organizer_style.py` | Unvirtualized `HomePosterCard` widget trees in `QScrollArea`, `setCellWidget()` bloat in `compact_table`, and keystroke table teardown/rebuilds in `OrganizerPage` |
| **PERF-09** | Performance | **Medium** | `library_page.py`, `smooth_scroll.py`, `wheel_routing.py`, `downloads_page.py`, `transfer_row.py` | Uncached procedural canvas loops in `HeroResumeCard.paintEvent`, full `beginResetModel()` resets every 2.5s in Downloads, and animation/wheel-filter overhead during scroll |
| **SEC-01** | Security | **High** | `app/api/server.py`, `app/config.py`, `.env.example` | `API_ACCESS_TOKEN` is never enforced; `CORSMiddleware` allows `allow_origins=["*"]` + `allow_credentials=True`; cover route lacks `relative_to` check; local file paths leak in JSON |
| **SEC-02** | Security | **High** | `app/db.py`, `app/api/server.py`, `app/core/entry_service.py` | Live `/api/library?sort_order=...` SQL `ORDER BY` injection plus unwhitelisted dynamic SQL column names in `update_franchise_field`, `update_season_field`, `save_entry` |
| **SEC-03** | Security | **Medium** | `app/core/playback.py`, `app/config.py`, `app/ui/pages/settings_page.py` | VLC `--http-password` exposed on CLI `argv`; unvalidated custom player executable path; shared tempdir Unix socket path in non-Windows fallback |
| **SEC-04** | Security | **Medium** | `app/ui/components/poster_card.py`, `app/ui/pages/detail_modal.py`, `app/core/exporter.py` | Unescaped genres in HTML tooltip (`<br>` triggers Qt rich text), inconsistent `Qt.PlainText` on labels, and CSV formula injection in `export_csv()` |
| **SEC-05** | Security / Hardening | **Low** | `app/core/anilist_client.py`, `app/core/chrome_bridge.py`, `app/core/downloads.py` | Unbounded `resp.content` buffering without `https://` scheme or byte limit in `_download_artwork()`; `.cmd` batch launcher for Chrome native host; plain `http://` accepted in source URL templates |
| **ARCH-01** | Architecture | **Medium** | `detail_modal.py`, `organizer_page.py`, `updates_page.py`, `main_window.py`, `storage_page.py` | Coexisting inline legacy QSS vs. Twilight Sakura wrapper stylesheets; `StoragePage` still uses legacy top header + sidebar instead of `HomeHeader` |

---

## Part 1 — Performance Issues

### PERF-01: Un-debounced Keystroke DB Writes & Full-Library Rebuild Cascade on Edits

- **Location**:
  - `app/ui/pages/detail_modal.py`: `_change_watch_status` (`L815-818`), `_set_rating` (`L1395-1431`), `_save_notes` (`L1434-1437`), `notes_edit.textChanged` connection (`L600`)
  - `app/ui/main_window.py`: `_on_data_updated` (`L863-866`), `_start_refresh` (`L868-908`), `_apply_refresh_snapshot` (`L891-908`), `_finish_refresh` (`L925-935`), `_refresh_dirty_page` (`L840-843`)
  - `app/ui/refresh.py`: `RefreshWorker.run` (`L59-122`)

- **Cause**:
  1. `self.notes_edit.textChanged.connect(self._save_notes)` fires synchronously on **every single character typed or deleted** in Notes (zero debounce).
  2. `_save_notes()`, `_change_watch_status()`, and `_set_rating()` all call `db.update_franchise_field(self.franchise_id, ...)` **on the GUI thread** (opening a fresh SQLite connection, running 3 `PRAGMA` statements, executing `UPDATE franchises`, committing to disk, and closing the connection) and immediately emit `self.data_changed.emit()`.
  3. `MainWindow._on_data_updated()` reacts to `data_changed` by reloading all filesystem watchers (`self._library_watchers.reload()`), marking all three content pages (`library_page`, `storage_page`, `updates_page`) dirty, and launching `RefreshWorker`.
  4. `RefreshWorker.run()` backs up the entire SQLite database into `:memory:` (`source.backup(memory)`), runs `recover_operations()`, executes `disk_snapshot()`, decodes **every cover and banner file for every franchise in the library** via `load_cached_image()`, rebuilds `LibraryIndex` (including union-find `build_groups()`), and computes `build_facts()` across all seasons.
  5. Rapid edits set `self._refresh_pending = True` (`main_window.py:871-873`), chaining a second `RefreshWorker` as soon as the first completes (`L933-934`). Furthermore, because `DetailModal` is the active widget on `stacked_widget`, `library_page` stays marked in `_dirty_pages` (`L901-906`), so clicking `Back` triggers `stacked_widget.currentChanged` -> `_refresh_dirty_page()`, running **another** full `RefreshWorker` when returning to Home.

- **Effect on the App**:
  - Typing a 40-character note generates 40 synchronous SQLite disk transactions on the UI thread, 40 watcher reloads, and multiple chained whole-library DB backups + whole-library image decodes.
  - Clicking a rating pill (`1–10`) or changing Watch Status feels sluggish immediately and causes noticeable delay when returning to the Library tab.

- **Changes / Repair**:
  1. **Debounce Notes & offload single-row writes**:
     - Attach `notes_edit.textChanged` to a `450 ms` single-shot `QTimer` (`_notes_timer`); flush any pending unsaved note text cleanly inside `DetailModal.done()` / `hide()` if dirty.
     - Execute single-field DB updates (`_set_rating`, `_change_watch_status`, debounced `_save_notes`) through an `IOTask` (or serialized single-writer queue) rather than committing on the Qt GUI thread.
  2. **Introduce granular mutation events (`franchise_updated(int fid, dict fields)`)**:
     - Distinguish lightweight metadata edits (`user_rating`, `watch_status`, `user_notes`, `display_title`) from structural changes (disk scans, deletes, rematches, consolidation moves).
     - Emit a targeted update signal handled by a lightweight `MainWindow._on_franchise_updated(fid, fields)` method that patches only the affected entry in:
       - `library_page._library_index` (`by_id` + matching series group aggregate `user_rating`/`watch_status`),
       - the pooled `HomePosterCard` / `compact_table` row / `HeroResumeCard` if displayed,
       - sidebar `coll_counts` delta and `storage_page` watch-status/reclaim summary (marking only `storage_page` dirty if needed, without dirtying `library_page` when already patched in-place).
     - Do **not** reload `LibraryWatchers` or launch `RefreshWorker` for rating, status, or note changes.
  3. **Test contracts to preserve**: `test_detail_navigation_performance.py` checks async loading/disposal and non-blocking UI heartbeats; `test_ui_regressions.py:116-117` calls `dialog._set_rating(10)` synchronously in unit tests — ensure either `_set_rating` persists cleanly before modal tests assert (or tests flush/wait cleanly while still offloading runtime commits cleanly, or keep fast write + async notify). Verify whether existing tests check `dialog.data_changed` on `_set_rating`/`_change_watch_status` before altering signal emission behavior (keeping `data_changed` emitting or bridging cleanly to scoped refresh handler).

- **Effect on the System**:
  - Rating clicks, status toggles, and typing in Notes drop from O(N_franchises × disk_backup × image_decode) work to O(1) background single-row updates with zero UI frame drops.
  - Returning from `DetailModal` to `LibraryPage` becomes instant because `library_page` stays clean and up-to-date in memory.
  - Requires careful flush-on-close logic for the Notes debounce timer so rapid close (`Esc` / `Back`) never drops typed notes.

---

### PERF-02: Redundant Full-Modal QSS Reparse on Every Rating Click

- **Location**:
  - `app/ui/pages/detail_modal.py`: rating button creation (`L527-567`), `refresh_home_style` (`L690-709`), `_set_rating` (`L1395-1431`)

- **Cause**:
  - During `_build_ui_steps`, `L535-563` assigns verbose inline gradient/border QSS to all 10 rating buttons, which `L687` promptly clears (`widget.setStyleSheet('')`), and `refresh_home_style()` (`L703-709`) replaces with `button.setStyleSheet('padding: 0;')` and property `detailRating=True`, `rated=(number <= rating)`.
  - However, `_set_rating()` (`L1399-1431`) still runs legacy code that constructs multi-line `setStyleSheet(...)` strings for all 10 buttons **and immediately calls `self.refresh_home_style()` (`L1430`)**, which re-generates `detail_style.qss()`, re-applies `self.setStyleSheet(qss())` to the entire `DetailModal` widget tree (and child `DetailEpisodes`), and then loops over all 10 buttons again overriding the stylesheets it just set (`padding: 0;` + `unpolish()`/`polish()`).

- **Effect on the App**:
  - Every click on a rating button triggers a full Qt stylesheet cascade recalculation across the entire `DetailModal` (including buttons, tables, `FlowLayout` pills, and episode lists), causing visible UI click stutter.

- **Changes / Repair**:
  1. Remove the redundant loop of multi-line `btn.setStyleSheet(...)` calls inside `_build_ui_steps` (`L534-563`) and `_set_rating` (`L1399-1429`), as well as the `self.refresh_home_style()` call at `L1430`.
  2. Set `btn.setProperty('detailRating', True)` and `btn.setStyleSheet('padding: 0;')` once during setup (which directly satisfies `test_ui_regressions.py:118`: `self.assertIn("padding: 0", button.styleSheet())`).
  3. Inside `_set_rating()`, only update `self._update_rating_title_text(rating)` and toggle `btn.setProperty('rated', num <= rating)` + `unpolish(btn)` / `polish(btn)` on the 10 buttons (and make `_update_rating_title_text` stop assigning conflicting inline QSS that clashes with `refresh_home_style`'s amber mono header at `L702`).

- **Effect on the System**:
  - Eliminates full-dialog QSS re-parsing on rating changes while preserving exact visual appearance and all existing button-geometry / stylesheet assertions in `tests/test_ui_regressions.py` and `tests/test_detail_screen.py`.

---

### PERF-03: Double Full-Database `:memory:` Backup, Sequential API Hops, and Widget Teardown on Edit / Rematch

- **Location**:
  - `app/core/matching.py`: `series_root` (`L26-41`), `apply_release_match` (`L60-149`)
  - `app/core/anilist_client.py`: `_rate_limit` (`L51-59`), `download_cover` / `download_banner` (`L297-345`)
  - `app/ui/dialogs/rematch_dialog.py`: `_start_apply` (`L374-425`)
  - `app/ui/dialogs/custom_entry.py`: `_save` / `_saved` (`L272-308`)
  - `app/ui/detail_data.py`: `prepare_details` (`L12-35`)
  - `app/ui/pages/detail_modal.py`: `_reload_async` (`L111-159`), `_build_ui_steps` (`L684-688`), `_edit_entry` (`L1468-1474`)

- **Cause**:
  1. **Serialized sequential provider lookups**: `apply_release_match()` calls `series_root()` up to 12 `PREQUEL` hops sequentially, plus additional hops if `additional` seasons are passed. Each `get_anime_by_id()` acquires `_request_lock` in `anilist_client._rate_limit()` and sleeps inside the lock for `_MIN_INTERVAL = 0.7s`, blocking both rematch progress and background `ArtworkLoader` / `UpdaterThread` calls. It then sequentially downloads both cover and banner (`timeout=15`) *before* committing the rematch.
  2. **Whole-DB `:memory:` copy per single-anime open/reload**: `DetailModal._reload_async()` calls `prepare_details(fid)`, which calls `source.backup(memory)` to copy the **entire SQLite DB** (`franchises`, `seasons`, `episodes`, `physical_files`, `scan_files`, `app_state`, etc.) just to read 1 series and its seasons.
  3. **Full widget destruction + double cascade**: `_reload_async(notify=True)` deletes every widget in `DetailModal`, reconstructs the entire layout from scratch (`_build_ui_steps` + clearing `setStyleSheet('')` on all children + `refresh_home_style()` + respawning `EpisodeWorker`), and then emits `data_changed` (`L148`) -> triggering a full `RefreshWorker` (`L863`). For `CustomEntryDialog`, `_save` emits `entry_saved` (`main_window.py:798` -> `RefreshWorker` #1) when invoked directly or inside `DetailModal`, where `DetailModal._edit_entry` calls `_reload_async(notify=True)` (launching `prepare_details` DB backup + widget rebuild + `RefreshWorker` #2, plus another `RefreshWorker` on closing back to Library!).

- **Effect on the App**:
  - Rematching takes seconds of network + disk latency followed by a visible teardown/rebuild blink inside `DetailModal` and multi-second background/tab-return lag across the app.
  - Renaming an anime title or toggling folder/display fields rebuilds the entire modal and backs up the database multiple times unnecessarily.

- **Changes / Repair**:
  1. **Eliminate full-DB `backup(memory)` in `prepare_details(fid)`**: Replace `source.backup(memory)` in `app/ui/detail_data.py` with targeted read-only `SELECT` queries into a tiny `:memory:` table subset—or better, a dedicated read-only snapshot connection / direct off-thread data dictionary `{franchise, seasons, continuous, coverage, poster, resume}` (`DetailModal` already has `_prepared_resume` and preloaded fields; only `_build_ui_steps` internals that still touch `db.*` need data injected). Keep `data['snapshot']['connection']` compatible with `test_detail_navigation_performance.py:64-83` (or update the test alongside the simplification).
  2. **Optimize `matching.series_root()` & non-blocking artwork**:
     - Check cached provider records (`franchises.metadata_json`, `series_relation_cache`) before firing live `get_anime_by_id()` requests in `series_root()`, and release `_request_lock` in `anilist_client._rate_limit()` during `_wait()` if possible (reserving a time-slot timestamp atomically under the lock instead of sleeping while holding the lock, reducing contention while preserving `0.7s` pacing).
     - After writing `franchises` metadata in `apply_release_match()`, commit and return immediately when artwork isn't already locally cached (letting `ArtworkLoader` fetch cover/banner asynchronously and fire `DetailModal._metadata_changed`), updating only the cover label pixmap instead of tearing down the entire modal UI on `_metadata_changed` (`detail_modal.py:999-1002`)!
  3. **In-place header/text refresh on rename & single scoped invalidation**:
     - When `CustomEntryDialog` edits only title/notes/status/rating/cover without changing `root_folder_path`, update existing `DetailModal` labels/poster in place instead of full teardown (`clear(old); sip.delete(old)`), and emit one granular update instead of double `entry_saved` + `data_changed` cascades.

- **Effect on the System**:
  - Drastically lowers rematch and title-edit latency (bounded by minimal DB queries and single-shot AniList hops only when uncached); removes UI flicker in `DetailModal` when artwork downloads complete; keeps DB isolation guarantees clean.

---

### PERF-04: Synchronous Batch Loops on the GUI Thread

- **Location**:
  - `app/ui/pages/library_page.py`: `_batch_mark_watched` (`L1157-1162`), `_batch_mark_watching` (`L1164-1169`)

- **Cause**:
  - Loops `for fid in self.selected_fids: db.update_franchise_field(fid, "watch_status", ...)` on the GUI thread—opening, PRAGMA-configuring, committing, and closing N separate SQLite connections synchronously.
  - Immediately executes synchronous `self.refresh()` (re-reading `LibraryIndex`, re-running `_refresh_airing_week()` with 3× `get_all_franchises()`, rebuilding release cards, reflowing grid), and then emits `self.data_changed.emit()`, which launches `RefreshWorker` right after.

- **Effect on the App**:
  - Multi-selecting 20+ anime and clicking "Mark Watched" / "Mark Watching" freezes the window while performing N SQLite fsyncs, a full synchronous `LibraryPage.refresh()`, and then an asynchronous full-library `RefreshWorker` pass.

- **Changes / Repair**:
  1. Add `db.update_franchises_field_batch(fids, field, value)` executing one parameterized `UPDATE franchises SET ... WHERE id IN (...)` inside a single SQLite transaction.
  2. Run the batch update inside `IOTask`, then patch the selected records in `_library_index`, update card/table badges & sidebar counts directly without calling synchronous `self.refresh()` + full `RefreshWorker`.

- **Effect on the System**:
  - Batch updates execute in a single transaction off the UI thread and render instantaneously regardless of selection size.

---

### PERF-05: Heavy Full-Library Snapshot & Whole-Library Artwork Decoding on Dirty Tab Switches

- **Location**:
  - `app/ui/main_window.py`: `currentChanged` connection (`L256`), `_refresh_dirty_page` (`L840-843`), `_on_data_updated` (`L863-866`), `_apply_refresh_snapshot` (`L891-908`), `_refresh_metrics` (`L942-984`)
  - `app/ui/refresh.py`: `RefreshWorker.run` (`L59-122`), `refresh_pixmap` (`L30-35`), `refresh_image_exists` (`L37-41`)

- **Cause**:
  1. Whenever `library_page`, `storage_page`, or `updates_page` is marked dirty in `_dirty_pages`, clicking that tab invokes `_refresh_dirty_page()` -> `_start_refresh(allow_network=False)`.
  2. Inside `RefreshWorker.run()` (`refresh.py:92-115`), **on every refresh regardless of which page opened or whether artwork changed**, it:
     - copies the entire SQLite database via `source.backup(memory)`,
     - runs `disk_snapshot()`,
     - executes `SELECT cover_filename, banner_filename FROM franchises` and loads + JPEG-repairs + decodes **every single cover and banner image in the entire library into uncompressed `QImage`s in RAM** (`L100-115`),
     - constructs `LibraryIndex()` (including `build_groups()` union-find) and computes `build_facts()`.
  3. On completion, `MainWindow._refresh_metrics()` (`L942-984`) runs on the GUI thread, calling `db.get_library_stats()` (up to 8 queries + Python JSON parsing of `seasons.video_files_json` for all rows), `db.get_series_library()`, `db.get_all_franchises()` again, and **another synchronous `disk_snapshot()` (`L971`)** — even though `RefreshWorker` already computed `snapshot['disk']`!

- **Effect on the App**:
  - Switching between `Library`, `Updates`, and `Storage` after any edit stalls with high disk read, CPU JPEG decoding, RAM spikes (holding all decoded full-res covers + banners simultaneously), and synchronous `shutil.disk_usage()` calls on potentially slow/USB/network drives on the GUI thread.

- **Changes / Repair**:
  1. **Replace full-library upfront `QImage` decoding with a bounded, scaled LRU cache**:
     - Stop iterating and decoding every cover & wide banner in `RefreshWorker.run()`. Instead, compute lightweight file metadata (`image_versions` via `(mtime_ns, size)`) or load images lazily into a bounded LRU cache keyed by `(norm_path, mtime_ns, size, target_width, target_height, dpr)` on demand via worker threads. *(Maintain `snapshot["images"]` compatibility where tested in `test_refresh.py` / `test_ui_regressions.py` via a lazy cache dict wrapper if accessed directly, or populate lazily.)*
  2. **Reuse `snapshot` metrics in `_refresh_metrics()`**:
     - Use `snapshot["disk"]` (already returned by `disk_snapshot()` in `RefreshWorker`) via `disk_snapshot()`'s existing/snapshot integration instead of calling `shutil.disk_usage` a second time on the GUI thread.
     - Pass precomputed `stats` and `franchises` counts from `RefreshWorker` / `LibraryIndex` so `_refresh_metrics()` does zero extra SQLite queries or JSON parsing on the GUI thread.
  3. **Targeted page dirtying**: Track *why* a page is dirty instead of unconditionally invalidating `StoragePage`, `UpdatesPage`, and `LibraryPage` together.

- **Effect on the System**:
  - Cuts RAM consumption drastically on large libraries with high-resolution covers/banners; cuts tab-switch latency and eliminates GUI-thread `disk_usage` stalls while keeping offline/snapshot read safety intact (`test_refresh.py:19-40`).

---

### PERF-06: `StoragePage` Synchronous N+1 Queries, Sync Cover Scaling, and Dense Cell Widgets

- **Location**:
  - `app/ui/pages/storage_page.py`: `refresh` (`L236-286`), `_health` (`L288-303`), `_text_cell` (`L305-315`), `_create_title_cell` (`L317-337`), `rescan_btn` (`L135`)

- **Cause**:
  - `StoragePage.refresh()` runs synchronously on the GUI thread (both on dirty page switches and on clicking "Refresh storage").
  - Performs N+1 SQL queries: fetches all franchises (`L254`), then loops over every on-disk entry calling `db.get_seasons_for_franchise(record["id"])` (`L258`) and calling `db.uses_continuous_episodes(record)` **twice per row** inside `_health` (`L290`, `L292` — making up to 3×N separate SQLite connections with 3 PRAGMAs each).
  - Synchronously decodes/scales cover pixmaps using `Qt.SmoothTransformation` (`L326`).
  - Populates **all 6 columns per row with `QTableWidget.setCellWidget()`** containing nested layouts/widgets (`L266-283`), then calls `resizeColumnsToContents()` (`L284`).

- **Effect on the App**:
  - Switching to or refreshing the `Storage` tab stutters proportionally to library size (`3N` DB connections + sync thumbnail `SmoothTransformation` + hundreds of child widgets + column resizing recalculation).

- **Changes / Repair**:
  1. **Batch DB load in `IOTask`**: Fetch all active seasons in one query (`SELECT * FROM seasons`), all `continuous_episodes:*` overrides in one prefix query, and disk stats in an `IOTask` (or reuse `RefreshWorker`'s `snapshot`), passing prepared plain row dicts into `StoragePage`.
  2. **Eliminate unnecessary `setCellWidget()`**: Render columns 1–4 (`Seasons/files/size`, `Watch status`, `Health` pill, `Potential reclaim`) directly via standard `QTableWidgetItem` / lightweight `QStyledItemDelegate` (preserving objectNames/properties or text accessibility) instead of per-cell `QWidget` + `QHBoxLayout` + `QLabel` trees. Cache `36×54` scaled thumbnails in a shared thumbnail cache.

- **Effect on the System**:
  - Turns `StoragePage` opening/refresh into a non-blocking single-query load and reduces table widget count by ~70% per row.

---

### PERF-07: Connection / PRAGMA Overhead, Missing Indexes, Calendar Triple-Query, Modal Grab, & Keystroke Settings Saves

- **Location**:
  - `app/db.py`: `get_connection` (`L141-152`), schema indexes (`L129-135`), `get_all_franchises` (`L323`), `get_library_stats` (`L618-681`), `get_series_library` (`L870-878`), `get_series_seasons` (`L896-906`)
  - `app/ui/pages/library_page.py`: `_refresh_airing_week` (`L748-785`), `refresh` (`L809-821`)
  - `app/ui/navigation.py`: `navigate` (`L37-41`)
  - `app/ui/pages/settings_page.py`: `custom_path_edit` (`L258`)
  - `app/ui/theme_scopes.py`: `ThemeScopes` / `scale_inline` (`L7-68`)

- **Cause**:
  1. **DB connection + 3 PRAGMA churn**: Every `db.get_connection()` call creates a brand-new `sqlite3.connect(DB_PATH)` and executes `PRAGMA journal_mode = WAL`, `PRAGMA synchronous = NORMAL`, and `PRAGMA foreign_keys = ON`. `get_series_library()` calls `get_all_franchises()` twice (`db.py:875-876`), and `get_all_franchises()` opens a connection *and* calls `get_state('library.removed_ids')` (`L323`) opening a second connection inside it. `get_series_seasons()` queries `get_franchise` + `get_seasons_for_franchise` inside a `for member_id` loop (`L901-903`). `get_library_stats()` runs up to 8 SQL queries and `json.loads()` on every `seasons.video_files_json` row.
  2. **Missing SQLite indexes**: Only `franchises(display_title COLLATE NOCASE)`, `franchises(user_rating DESC)`, `franchises(total_size_bytes DESC)`, `episode_history(episode_id, played_at)`, `physical_files(season_id)`, and `scan_files(root_id, scope)` are indexed (`db.py:129-134`, `identity.py:65-66`, `scan_state.py:26`). Frequent lookups on `seasons(franchise_id)`, `seasons(next_airing_at)`, `franchises(storage_state)`, and `franchises(has_new_update)` perform table scans.
  3. **Calendar & Release Strip redundancy**: `LibraryPage._refresh_airing_week()` calls `db.get_all_franchises()` **three separate times** (`L753`, `L765`, `L784`) plus two queries on `seasons`. `LibraryPage.refresh()` also destroys and recreates every `PosterCard` inside `release_layout` (`L809-821`) on every refresh even when unchanged.
  4. **Modal screenshot grab**: `navigate()` captures the entire previous page bitmap (`previous.grab()`) on the CPU via `QPainter`/widget rendering every time a drawer or centered dialog opens (`navigation.py:40`).
  5. **Settings keystroke write**: `settings_page.py:258` saves `set_custom_player_path` directly to SQLite on every keystroke in `custom_path_edit`.
  6. **Global `QEvent.Show` styling filter**: `ThemeScopes.eventFilter` (`theme_scopes.py:63-68`) intercepts every widget `Show` event and runs regex `re.sub` scaling unless `animevaultOwnScaledStyle` is set.

- **Effect on the App**:
  - Cumulative micro-stutters on opening dialogs, navigating tabs, typing paths in Settings, and refreshing Home calendar/release strips.

- **Changes / Repair**:
  1. Configure `PRAGMA journal_mode = WAL` once in `db.init_db()`, reuse thread-local connections in `db.get_connection()` (with `PRAGMA busy_timeout = 5000`, falling back safely cleanly when `DB_PATH` is patched in tests via `(DB_PATH, threading.get_ident())` cache key!), and keep `_SnapshotConnection` unchanged for `refresh_view`.
  2. Add indexes in `db.init_db()`: `idx_seasons_franchise_id ON seasons(franchise_id)`, `idx_seasons_next_airing ON seasons(next_airing_at)`, `idx_franchises_storage_state ON franchises(storage_state)`, `idx_franchises_has_update ON franchises(has_new_update)`.
  3. Collapse `get_all_franchises()` subquery for hidden IDs (via `WHERE id NOT IN (...)` or 1 cached read), replace the 8-query `get_library_stats()` block with 1 aggregated `SELECT` + SQL `json_array_length(COALESCE(video_files_json, '[]'))` (or single cursor pass), batch `get_series_seasons()` via `WHERE franchise_id IN (...)`, and fetch `franchises` **once** inside `_refresh_airing_week()` (and reuse `_card_pool` / signature check for `release_layout`).
  4. Replace `previous.grab()` in `navigate()` with a simple translucent scrim overlay (`QWidget` / `background: rgba(0, 0, 0, 158)`) stacked above `previous` (without taking a full-window software snapshot), or cache cleanly only if truly needed.
  5. Change `custom_path_edit.textChanged` to `editingFinished` (or a short debounce).

- **Effect on the System**:
  - Cuts SQLite connection creation overhead by an order of magnitude across every workflow (carefully keying connection reuse by resolved `str(db.DB_PATH)` so unit tests that `patch.object(db, 'DB_PATH', ...)` never read a stale DB handle!). Removes modal-open raster grab hitches.

---

### PERF-08: Unvirtualized Grid Widgets, Compact `setCellWidget()` Tables, & Keystroke Organizer Rebuilds

- **Location**:
  - `app/ui/pages/library_page.py`: `views_stack`, `_render_grid` (`L888-932`), `_reflow_grid` (`L934-957`), `_build_compact_rows` (`L1011-1115`)
  - `app/ui/components/home_poster.py` (`L25-85`) & `app/ui/components/poster_card.py` (`L70-369`)
  - `app/ui/pages/organizer_page.py`: `search_filter.textChanged` (`L755`), `_switch_tab` (`L1131-1137`), `_render_table` (`L1182-1320`)
  - `app/ui/organizer_style.py`: `style_cells` (`L36-44`)

- **Cause**:
  1. **No viewport virtualization in Library Grid**: Every anime in `LibraryPage` is an active `HomePosterCard` `QWidget` inside `QGridLayout` inside `SmoothScrollArea`. Each card nests multiple containers, a `QProgressBar`, 3 independently styled `QLabel`s (using per-card inline `setStyleSheet` in `HomePosterCard.restyle()` at `home_poster.py:52-57` and `update_facts()` at `L95` instead of shared parent selectors!), a hover `QPropertyAnimation`, and rich HTML tooltips.
  2. **Heavy `QTableWidget` row construction**:
     - `LibraryPage._build_compact_rows()` creates 5 `setCellWidget()` containers + `QCheckBox` + `ElidedLabel` + `QPushButton` per library item upfront (even for filtered-out/off-screen rows) and calls `pix.scaled(40, 58, ..., SmoothTransformation)` synchronously (`L1043`).
     - `OrganizerPage._render_table()` rebuilds all `setCellWidget()` columns from scratch on **every keystroke in `search_filter`** (`L755`) and tab switch (`L1137`), including setting inline QSS strings per badge and then invoking `organizer_style.style_cells(self)` (`L1320`), which loops over every row × 4 columns × every child widget clearing stylesheets again!

- **Effect on the App**:
  - Scrolling the Library page slows down as collection count grows (hundreds/thousands of widgets translated/repainted per scroll animation tick).
  - Typing in Organizer's "Filter anime..." box or switching Organizer tabs freezes noticeably on large folders.

- **Changes / Repair**:
  1. **Immediate low-risk improvements (keeping existing tests 100% intact)**:
     - **`HomePosterCard` optimization**: Move per-widget `setStyleSheet(...)` rules out of every card instance into shared selectors under `QWidget#home_library` in `app/ui/home_style.py` (`[homePoster='true'] QLabel#...`), pre-cache scaled cover pixmaps by target pixel size `(width*dpr, height*dpr)`, avoid running `_lift` hover animations when scrolling is active, and skip `update_title()` when width hasn't changed. *(Preserves `page._cards` identity contracts tested in `test_performance_paths.py:32-39`, `test_ui_regressions.py:93-100`, and `test_home_screen.py:66-112`.)*
     - **`OrganizerPage` quick win**: Keep all rows built once per scan/tab or lazily populated, move badge coloring to dynamic properties (`[badgeTone='...']` in `organizer_style.py`) instead of inline QSS + `style_cells()` clearing loops, and filter by `table.setRowHidden(row, ...)` with a `150 ms` search debounce instead of destroying/rebuilding the whole table per keystroke!
  2. **Long-term architectural fix (Virtualization)**:
     - Migrate `LibraryPage` Grid/Compact views and `OrganizerPage.table` to model/delegate views (`QListView` in `IconMode` with `UniformItemSizes` / `QTableView` + `QStyledItemDelegate`, matching `DownloadsPage` / `TransferDelegate` and `DetailEpisodes`), updating test suites (`test_home_screen.py`, `test_performance_paths.py`, `test_ui_regressions.py`, `test_three_reference_screens.py`, `test_requested_ui_fixes.py`) to interact via model/delegate methods.

- **Effect on the System**:
  - Phase 1 optimizations deliver faster Organizer typing/tab switches and lower Library card QSS/memory overhead immediately without breaking any regression tests. Full model/delegate virtualization guarantees constant O(visible_viewport) memory & 60 FPS scroll even with 5,000+ entries.

---

### PERF-09: Uncached Procedural Painting in `HeroResumeCard`, Animation/Wheel Overhead, & Downloads Model Resets

- **Location**:
  - `app/ui/pages/library_page.py`: `HeroResumeCard.paintEvent` (`L158-206`)
  - `app/ui/components/smooth_scroll.py`: `SmoothScrollArea` (`L7-40`)
  - `app/ui/components/wheel_routing.py`: `WheelRouting` (`L7-42`)
  - `app/ui/pages/downloads_page.py`: `timer` (`L105`), `loaded` (`L165-167`), `render` (`L168-179`)
  - `app/ui/components/transfer_row.py`: `TransferDelegate.paint` (`L21-41`)

- **Cause**:
  1. `HeroResumeCard.paintEvent` executes dozens of vector draw operations on every repaint (gradient background, scaled banner, radial gradient glow, diagonal scanlines `for x in range(0, w + h, 28)`, linear dark fade, 300px Kanji text, and double semicircular arcs `for x in range(-18, w, 36)`).
  2. `DownloadsPage` polls every `2500ms`; whenever any transfer's downloaded bytes, speed, ETA, or progress changes, `self.items == items` fails (`L166`), and `render()` calls `beginResetModel()` / `endResetModel()` (`L172`), discarding view state and re-applying `selectRow()`. Meanwhile `TransferDelegate.paint()` constructs two `QFont` objects, queries `colors()`, and recomputes `coverage_label()`/`format_bytes()` per cell paint.
  3. `SmoothScrollArea` triggers 160ms scrollbar animations redrawing large widget subtrees; global `WheelRouting` intercepts every `QEvent.Wheel` across the app walking parent chains and synthesizing `QWheelEvent` objects.

- **Effect on the App**:
  - Scrolling past or back onto the Hero card forces expensive Python paint loops per frame.
  - Viewing active transfers resets the Downloads table model every 2.5s (flickering/resetting row scroll/selection edge cases) and wastes CPU formatting strings per paint.

- **Changes / Repair**:
  1. Cache `HeroResumeCard`'s painted background (gradients, scaled banner, scanlines, Kanji, arcs) into an offscreen `QPixmap` keyed by `(w, h, banner_cache_key, theme, decorated, dpr)`; `paintEvent` simply runs `painter.drawPixmap(0, 0, self._cached_surface)`.
  2. In `DownloadsPage.render()`: when filtered row IDs/order haven't changed, update `self.model.rows` in-place and emit `self.model.dataChanged.emit(...)` instead of `beginResetModel()`/`endResetModel()`, falling back to reset only when row count or ID ordering changes.
  3. Cache `QFont` instances and palette tokens in `TransferDelegate`, and compute formatted ETA/coverage/rate strings inside `QueueModel` or once per item refresh.

- **Effect on the System**:
  - Reduces `HeroResumeCard` repaint cost to a single GPU/raster blit; eliminates periodic full model resets in `DownloadsPage` while preserving row selection (`test_transfer_screens.py`).

---

## Part 2 — Security Issues & Hardening

### SEC-01: Unenforced `API_ACCESS_TOKEN`, Wide-Open CORS (`*` + Credentials), & Path Leak in Local FastAPI Server

- **Severity**: **High**
- **Location**:
  - `app/api/server.py`: `CORSMiddleware` (`L32-38`), endpoints (`L45-205`), `get_cover` (`L124-135`)
  - `app/config.py`: `LOCAL_API_HOST`, `LOCAL_API_PORT`, `API_ACCESS_TOKEN` (`L54-56`)
  - `.env.example` (`L11-16`)

- **Cause**:
  1. `app/config.py` reads `API_ACCESS_TOKEN` (documented in `.env.example` as *"Optional API Access Token for Local Streaming API"*), **but `app/api/server.py` never imports or enforces `API_ACCESS_TOKEN` anywhere**.
  2. `CORSMiddleware` is configured with `allow_origins=["*"]`, `allow_credentials=True`, `allow_methods=["*"]`, and `allow_headers=["*"]` (`server.py:32-38`).
  3. `get_cover()` (`L131-135`) joins `COVERS_DIR / franchise["cover_filename"]` directly without checking `resolve().relative_to(COVERS_DIR.resolve())` (unlike `serve_video()` at `L156-163`, which validates path containment and rejects `..`).
  4. `/api/library`, `/api/franchise/{id}`, `/api/franchise/{id}/seasons`, and `/api/updates` serialize and return full database rows containing sensitive local machine paths (`root_folder_path`, `season_folder_path`, `scan_root`) and private user notes/ratings.

- **Effect on the App**:
  - **Cross-site localhost data exfiltration**: Any malicious website visited in a browser while Anime Vault is open can issue `fetch("http://127.0.0.1:8765/api/library")`, `/api/stats`, `/api/cover/{id}`, or `/api/video/{season_id}/{filename}` and read the user's entire anime collection, personal notes, ratings, local Windows usernames/drive structure (`C:\Users\...`), and video streams.
  - **False sense of security on LAN**: Configuring `LOCAL_API_HOST=0.0.0.0` alongside `API_ACCESS_TOKEN=...` exposes the library and local video files unauthenticated to the entire LAN/Wi-Fi network because the token is ignored.
  - Note: Also creates an active SQLite read path exposed externally via `server.py:45-60` (see **SEC-02**).

- **Changes / Repair**:
  1. **Enforce `API_ACCESS_TOKEN`**:
     - Add an ASGI/FastAPI dependency or HTTP middleware checking `Authorization: Bearer <token>` (or `X-API-Token` / optional short-lived signed/query capability for `<video>`/`<img>` tags if a local streaming site uses direct media URLs) via `secrets.compare_digest` whenever `API_ACCESS_TOKEN` is non-empty.
     - Automatically generate or require a non-empty `API_ACCESS_TOKEN` if `LOCAL_API_HOST` is not a loopback address (`127.0.0.1`, `::1`, `localhost`).
  2. **Lock down CORS**:
     - Remove `allow_origins=["*"]` with `allow_credentials=True`. Configure `ALLOWED_API_ORIGINS` (defaulting to disabled/empty list `[]` unless explicitly configured by the user) and restrict `allow_methods=["GET"]`.
  3. **Path containment & payload minimization**:
     - In `get_cover()`, resolve `COVERS_DIR` and `cover_path`, verify `cover_path.relative_to(COVERS_DIR.resolve())`, and reject invalid filenames cleanly.
     - Strip internal filesystem path fields (`root_folder_path`, `season_folder_path`, `scan_root`) from external HTTP API responses (keep them inside `franchise_payload()` only when explicitly requested by the in-process desktop JSON inspector, or gate behind authentication).

- **Effect on the System**:
  - Prevents browser-based cross-origin exfiltration and unauthenticated LAN access without affecting the in-process Desktop JSON Inspector (`DetailModal._show_api_json`, which calls `franchise_payload()` directly in Python).
  - External local-streaming frontends using the HTTP API will need an explicit configured origin (`ALLOWED_API_ORIGINS`) and token header when `API_ACCESS_TOKEN` is set (and will no longer rely on raw Windows disk paths).

---

### SEC-02: Live HTTP-to-SQL `ORDER BY` Injection & Unwhitelisted SQL Identifiers

- **Severity**: **High**
- **Location**:
  - `app/api/server.py`: `get_library` (`L45-60`)
  - `app/db.py`: `get_all_franchises` (`L352`), `update_franchise_field` (`L366-371`), `update_season_field` (`L592-596`), `get_series_library` (`L875-876`)
  - `app/core/entry_service.py`: `save_entry` (`L46-48`)

- **Cause**:
  1. **Reachable via HTTP right now**: `/api/library` accepts query parameter `sort_order: str = Query("ASC")` (`server.py:48`), passes it verbatim into `db.get_series_library(sort_order=sort_order)` (`server.py:56`), which passes it verbatim into `db.get_all_franchises(..., sort_order=...)` (`db.py:875`), which interpolates it directly into SQL: `query += f" ORDER BY {col} {sort_order}"` (`db.py:352`).
  2. `db.update_franchise_field(fid, field, value)` executes `f"UPDATE franchises SET {field} = ? WHERE id = ?"` (`db.py:369`), `db.update_season_field(sid, field, value)` executes `f"UPDATE seasons SET {field} = ? WHERE id = ?"` (`db.py:594`), and `entry_service.save_entry` interpolates `data.keys()` into `UPDATE franchises SET ...` (`entry_service.py:47-48`) with no column allowlists.

- **Effect on the App**:
  - **Exploitable Blind SQL Injection via localhost/CORS**: Because `server.py` also enables wildcard CORS (SEC-01), any webpage or local client calling `GET /api/library?sort_order=ASC,(CASE WHEN (...) THEN 1 ELSE (SELECT ...) END)` injects arbitrary expressions into `sqlite3.Connection.execute()`, leaking `app_state` keys (e.g., `downloads.settings`, `chrome.capture_extension`, `series_overrides`), timing side-channels, or triggering errors. *(Multi-statement `; DROP` is blocked by `sqlite3.Connection.execute`, so data exfiltration via expressions/subqueries in `ORDER BY` is the primary risk.)*
  - Any future API/script/UI caller passing an untrusted `field` string to `update_franchise_field` or `update_season_field` would similarly trigger SQL column/syntax injection.

- **Changes / Repair**:
  1. Immediately normalize `sort_order` in `db.get_all_franchises()` (and validate with `Query(..., pattern="^(?i)(ASC|DESC)$")` in `server.py`):
     `order_dir = "DESC" if str(sort_order).upper() == "DESC" else "ASC"`
  2. Define explicit `frozenset` column allowlists in `app/db.py`:
     - `_FRANCHISE_FIELDS` checked in `update_franchise_field()` and `entry_service.save_entry()`
     - `_SEASON_FIELDS` checked in `update_season_field()`
     Raise `ValueError` immediately if a disallowed identifier is passed.

- **Effect on the System**:
  - Closes live HTTP-to-SQL injection completely and hardens the persistence API against future bugs with zero performance cost or breakage for valid callers.

---

### SEC-03: VLC HTTP Password Exposed in CLI `argv`, Unvalidated Custom Player Path, & Shared Temp Socket Path

- **Severity**: **Medium**
- **Location**:
  - `app/core/playback.py`: `Session.__init__` (`L91-101`)
  - `app/config.py`: `launch_video_file` (`L229-249`)
  - `app/ui/pages/settings_page.py`: `custom_path_edit` (`L256-259`, `L448-455`)

- **Cause**:
  1. When using VLC, `playback.py:94` appends `'--http-password=' + self.password` directly to `subprocess.Popen` arguments.
  2. When using a `"custom"` player, `config.py:229-232` runs `subprocess.Popen([custom, str(path)])` for any file passing `os.path.isfile(custom)` without validating extension (e.g., `.exe`), dangerous script extensions (`.bat`, `.cmd`, `.vbs`, `.ps1`), or user verification.
  3. On non-Windows platforms, MPV IPC socket is placed in shared `tempfile.gettempdir()` (`playback.py:98`) rather than a private `0o700` directory.

- **Effect on the App**:
  - Any same-user process inspecting process command lines on Windows (e.g., WMI / Task Manager / diagnostic loggers) can read VLC's HTTP password and issue VLC HTTP control requests on `127.0.0.1:<port>`.
  - A manually edited DB setting (`custom_player_path`) or accidental script selection executes arbitrary binaries/scripts when playing an episode.

- **Changes / Repair**:
  1. Restrict `custom_player_path` execution in `launch_video_file()` to resolved `.exe` files on Windows (rejecting scripts/shortcuts) and warn/confirm in Settings when saving a non-executable path.
  2. On POSIX systems, store the MPV socket inside a dedicated `0o700` subdirectory (`DATA_DIR` or `tempfile.mkdtemp(prefix="animevault-")`) with cleanup.
  3. Evaluate VLC `--rc-host` / stdin or ephemeral config approaches vs. CLI `--http-password` (note `tests/test_home_screen.py:137` inspects `vlc.arguments` for `'--http-host=127.0.0.1'` and `'--start-time='`; keep MPV documented as the cleaner pipe-IPC option).

- **Effect on the System**:
  - Tightens local IPC and binary execution hygiene without changing normal VLC/MPV playback or breaking `test_home_screen.py`.

---

### SEC-04: Unescaped Tooltip HTML Segment, Inconsistent `Qt.PlainText`, & CSV Formula Injection

- **Severity**: **Medium**
- **Location**:
  - `app/ui/components/poster_card.py`: `_setup_tooltip` (`L327-348`)
  - `app/ui/pages/detail_modal.py`: `title_lbl` (`L360`), `sub_lbl` (`L372`), `t_lbl` (`L1143`)
  - `app/core/exporter.py`: `export_csv` (`L67-82`)

- **Cause**:
  1. `PosterCard._setup_tooltip()` escapes `title_en`, `title_romaji`, and `title_native` via `html.escape()`, **but interpolates `', '.join(genre_list[:4])` unescaped** (`L344`) inside a rich-text HTML tooltip (`<br>` triggers Qt rich-text parsing).
  2. Several data-bound `QLabel`s in `DetailModal` (`title_lbl`, `sub_lbl`, `t_lbl`) rely on Qt's default `Qt.AutoText` rather than explicitly calling `setTextFormat(Qt.PlainText)`.
  3. `export_csv()` (`exporter.py:67-82`) writes `display_title`, `title_*`, `genres`, `user_notes`, and `root_folder_path` straight to CSV without checking leading formula characters (`=`, `+`, `-`, `@`, `\t`, `\r`).

- **Effect on the App**:
  - Untrusted metadata from custom entries, provider overrides, or local folder names containing `<...>` tags can alter Qt label/tooltip rendering (`QTextDocument`).
  - Opening exported CSV files in Microsoft Excel or LibreOffice Calc can execute embedded spreadsheet formulas if any title, note, or folder path begins with `=`, `+`, `-`, or `@`.

- **Changes / Repair**:
  1. Wrap each genre entry in `escape(str(g))` in `PosterCard._setup_tooltip()`.
  2. Audit all DB/API/filename-populated `QLabel`s in `DetailModal` (and remaining pages) and set `.setTextFormat(Qt.PlainText)`.
  3. Add a small `_csv_safe(value)` sanitizer in `exporter.py` prefixing leading `=`, `+`, `-`, `@`, `\t`, `\r` characters with `'` (single quote) for text columns.

- **Effect on the System**:
  - Eliminates rich-text markup injection in UI widgets and formula injection in CSV exports with zero impact on JSON exports or normal ASCII/Unicode titles.

---

### SEC-05: Unbounded Artwork Download, Batch Wrapper for Native Messaging, & `http://` Source Templates

- **Severity**: **Low (Hardening)**
- **Location**:
  - `app/core/anilist_client.py`: `_download_artwork` (`L347-375`)
  - `app/core/chrome_bridge.py`: `register` (`L29-56`)
  - `app/core/downloads.py`: `validate_url` (`L38-46`)

- **Cause**:
  1. `_download_artwork()` performs `requests.get(url, timeout=15)` and reads `resp.content` entirely into memory without verifying `https://` scheme or bounding payload size (unlike `player_icons.py:30-34`, which streams with a strict 1 MB cap).
  2. `chrome_bridge.register()` points Chrome's Native Messaging manifest at `data/chrome-bridge/host.cmd`, invoking `cmd.exe` (`%*`), whereas `chrome_bridge.py` (`L40-41`) explicitly notes external input arrives over framed stdin JSON rather than CLI args.
  3. `downloads.validate_url()` permits plain `http://` templates in search sources (`L40`).

- **Effect on the App**:
  - If `ANILIST_GRAPHQL_URL` is customized/compromised or a malicious image URL is returned, `_download_artwork` could allocate unbounded RAM or follow non-HTTPS links.
  - Invoking `host.cmd` introduces `cmd.exe` batch quoting semantics unnecessarily (especially if `ROOT` ever contains special batch characters like `&`, `%`, `^`).

- **Changes / Repair**:
  1. In `_download_artwork()`, enforce `urlsplit(url).scheme == 'https'` (or http/https strict check with HTTPS preferred), inspect `Content-Length` if present, and enforce a max byte limit (e.g., 16 MB) — ensuring mocked `Response` objects in `tests/test_ui_regressions.py:159-167` (which only expose `.content` + `raise_for_status()`) continue to pass without relying exclusively on `iter_content()`.
  2. Validate `ROOT` / executable path characters rigorously in `chrome_bridge.register()`, or point the Native Messaging manifest directly to a standalone launcher executable in frozen builds instead of `.cmd`.
  3. Surface a clear UI warning (or disallow plaintext `http://` unless loopback) for external download search sources in Settings.

- **Effect on the System**:
  - Caps worst-case image-download memory allocation, preserves all existing artwork download tests, and reduces Windows shell surface.

*(Positive security baseline already in place and should be preserved: `magnet_capture.validate()` checks BitTorrent `urn:btih`/`urn:btmh` and rejects `\r\n\x00"`; `chrome_bridge` restricts Chrome callers to one saved 32-char extension ID and user-enabled origin; `builtin_torrents.safe_files()` rejects path traversal, symlinks, Windows reserved device names, and case-insensitive collisions while running `libtorrent` in `upload_mode` until approved; `file_operations.py` verifies file signatures and routes all deletions strictly to the Windows Recycle Bin.)*

---

## Part 3 — Architecture & Maintainability Advice

### ARCH-01: Unify Dual Styling Layers & Complete `StoragePage` Shell Alignment

- **Location**:
  - `app/ui/pages/detail_modal.py` (`L90-96, L268-343, L535-563, L684-688`)
  - `app/ui/pages/organizer_page.py` (`L1144-1320`), `app/ui/organizer_style.py` (`L36-88`)
  - `app/ui/pages/updates_page.py` (`L79-90, L207-208`)
  - `app/ui/main_window.py`: `_update_nav_selection` (`L702-724`)
  - `app/ui/pages/storage_page.py`

- **Cause**:
  - Newer "Twilight Sakura" UI modules (`home_style.py`, `detail_style.py`, `organizer_style.py`, `settings_style.py`, `transfer_style.py`) wrap older baseline widgets programmatically and clear legacy inline stylesheets at runtime (`widget.setStyleSheet('')`).
  - Simultaneously, `MainWindow._update_nav_selection()` still swaps back to the legacy `top_header` + `sidebar` only when index `3` (`StoragePage`) is active (`shared = active_index in (0, 1, 2, 4, 5)` at `main_window.py:705`), while all other 5 pages use the capsule `HomeHeader`.

- **Effect on the App**:
  - Increases QSS churn and subtle conflicts (e.g., `_set_rating` setting inline styles later wiped by `refresh_home_style()`, or `scale_inline` regex matching inline styles before wrapper opt-out).
  - Switching to `Storage` causes an abrupt visual shell shift (header swap + sidebar appearing) and double geometry relayout.

- **Changes / Repair**:
  1. Strip dead inline `setStyleSheet(...)` blocks directly at widget construction once equivalent `objectName` / property selectors exist in `*_style.py`, deleting the runtime `for widget in self.findChildren(QWidget): widget.setStyleSheet('')` passes.
  2. Create a clean Twilight Sakura style/header integration for `StoragePage` (`storage_style.py` + `animevaultOwnScaledStyle = True`) and include index `3` in `HomeHeader`'s `shared` tabs so all 6 tabs share one consistent navigation shell.
  3. Add regression assertions in `tests/test_performance_paths.py` verifying that rating, watch status, and note edits patch state without invoking `RefreshWorker` or `sqlite3.Connection.backup`, and add security unit tests for `app/api/server.py` (CORS headers, `API_ACCESS_TOKEN` enforcement, `sort_order` SQL-injection rejection, cover path traversal rejection) and `app/db.py` column allowlists.

- **Effect on the System**:
  - Eliminates layout jumps when visiting `Storage`, removes wasted runtime stylesheet cleanup loops, and locks in performance and security invariants against regressions.

---

## Part 4 — Recommended Implementation Roadmap

| Phase | Included Items | Why This Order | Verification Target |
| :--- | :--- | :--- | :--- |
| **Phase 1: Immediate Security & Edit-Lag Quick Wins** | **SEC-02**, **SEC-01**, **SEC-04**, **PERF-01**, **PERF-02** | Highest impact with minimal refactoring risk: closes live HTTP SQLi & CORS leaks, stops keystroke DB freezes, stops full-library rebuild cascades on rating/status/notes edits, and removes full-modal QSS reparsing. | `python scripts/check.py` + new tests for `/api/library` auth/CORS/SQLi, debounced notes flush, and no `RefreshWorker` on rating/status edits |
| **Phase 2: Database, Tab-Switch & Rematch Optimization** | **PERF-03**, **PERF-04**, **PERF-05**, **PERF-06**, **PERF-07**, **SEC-03**, **SEC-05** | Eliminates tab-switch stalls (`RefreshWorker` lazy image cache, `StoragePage` async bulk load), speeds up rematching (`series_root` cache + async art), adds SQLite indexes/WAL tuning, and closes local hardening gaps. | `python scripts/check.py` (especially `test_refresh.py`, `test_detail_navigation_performance.py`, `test_performance_paths.py`, `test_ui_regressions.py`) |
| **Phase 3: Rendering, Virtualization & Architecture Polish** | **PERF-08**, **PERF-09**, **ARCH-01** | Converts heavy `HeroResumeCard` paint loops to cached pixmaps, switches `DownloadsPage` to incremental `dataChanged`, virtualizes Library/Organizer views to model/delegate architecture, and unifies `StoragePage` + QSS layers. | `python scripts/check.py` + manual Windows GUI verification at `dark`/`light`, `1.0` and `1.3` text scales (`CONTRIBUTING.md`) |
