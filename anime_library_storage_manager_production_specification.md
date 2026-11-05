# Anime Library & Storage Manager — Production-Ready Specification (`v1.0.0`)

This document serves as the complete, locked-in engineering blueprint to build, test, and run the **Anime Library & Storage Manager** in Python (`main.py`), with an optional one-command conversion to `.exe` once all testing is complete.

---

## 1. Executive Summary & Core Philosophy

The **Anime Library & Storage Manager** solves four core problems for managing a 3 TB internal anime drive and personal streaming setup:

1. **Recognition & Romaji-to-English Resolution:** Most of your local folders use Japanese/Romaji names (`Ore dake Level Up na Ken`, `Kaifuku Jutsushi no Yarinaoshi`). The app queries AniList (including mature/18+ entries) and Jikan/MAL to display the **English Title** and **Poster Thumbnail** on the card, while showing the Romaji/Japanese names on hover (and seamlessly falling back to the Romaji title if an official English translation doesn't exist yet).
2. **Smart Auto-Folder & Season Organizer:** When scanning a selected root directory containing loose `.mp4`, `.mkv`, or other video files/folders, the app detects which files belong to the same anime and which season they belong to—giving you the option to **automatically organize and move them into clean `<Anime Name>/Season 1/` and `<Anime Name>/Season 2/` folders**.
3. **Proactive Sequel & Airing Tracker:** Automatically checks your library in the background on startup to flag any watched anime that has a new season, movie, or OVA announced or currently airing.
4. **Multi-Step Safe Disk Space Reclamation:** Lets you free up space on your 3 TB internal drive using a strict **2–3 step confirmation workflow** before permanently deleting video files—while keeping the anime, its poster, and its history in your library marked as **`"Watched, removed"`**.

---

## 2. Locked-In Production Rules (From Final 16 Questions)

| # | Feature Area | Locked-In Production Behavior |
| :--- | :--- | :--- |
| **1** | **Folder & Multi-Path Selection** | Users can select one or multiple root folders on the internal 3 TB drive where anime folders and loose `.mp4`/`.mkv` files are located. |
| **2** | **2–3 Step Deletion Confirmation** | Clicking **Delete** triggers a multi-step confirmation dialog: **Step 1:** Warns that files will be deleted from the drive and shows the exact folder path + GB size. **Step 2:** Asks to confirm permanent deletion from disk while keeping the `"Watched, removed"` record. **Step 3:** Final *"Delete Now"* execution button. |
| **3** | **Smart Auto-Season Folder Organizer** | During scanning, if the app detects loose video files or separate season folders for the same series (e.g., *Bleach* episodes or *Season 1* & *Season 2*), it can **automatically group and move those files into `<Anime Folder>/Season 1` and `<Anime Folder>/Season 2` subfolders**. Deleting a single season marks the card as **`Partially on Disk`** until all seasons are removed. |
| **4** | **Offline Mode & Last Streaming State** | If the internet is down on startup, the status bar displays **`Offline Mode`**, skips online API checks, and loads 100% of cached posters/data plus remembers the last opened streaming site state/URL before the app exited. |
| **5** | **Video File Tracking (`.mp4`, `.mkv`, etc.)** | The scanner indexes `.mp4`, `.mkv` (and secondary formats like `.avi`, `.webm`, `.ts`) and exposes their exact file paths via the local API so your streaming site can play episodes directly. |
| **6** | **Quit Confirmation (Tray vs. Exit)** | Clicking the window `X` button pops up a prompt asking: **"Minimize to System Tray (Keep Streaming API Running)"** or **"Exit Application Completely"**. |
| **7** | **Text File (`.txt`) Importer** | Parses one anime title per line (handling extra notes, season tags, or numbers automatically). |
| **8** | **Movies & OVAs Grouping** | Movies, OVAs, and Specials belonging to a franchise are grouped inside the **same Anime Details modal** under the Seasons/Relations list rather than cluttering the main grid with separate cards. |
| **9** | **Unfiltered Mature / Ecchi / 18+ Lookup** | AniList GraphQL queries do **not** filter out mature titles (`isAdult` filter omitted), ensuring shows like *Redo of Healer* (`Kaifuku Jutsushi no Yarinaoshi`) and uncensored OVAs resolve with full metadata and posters. |
| **10** | **Custom Entries & FFmpeg Frame Grab** | For any unmatched/custom anime, you can pick a custom image OR click **"Grab Thumbnail from Episode 1"** to auto-extract a poster frame from the `.mp4`/`.mkv` file. |
| **11** | **Sorting Options** | Defaults to **A–Z by English Title**, with instant sort dropdowns for **User Rating (Highest First)**, **Disk Size (Largest First)**, **Recently Added**, and **Watch Status**. |
| **12** | **Missing English Title Fallback** | Since local folders mostly have Romaji names and some entries on AniList lack an English title, the app automatically falls back to displaying the **Romaji title** on the card whenever `title_en` is empty, and allows manual title editing anytime. |
| **13** | **Internal Drive Storage** | Optimized for a fast local internal 3 TB drive (instant `shutil.disk_usage` and `os.scandir` metrics without external USB spin-up delays). |
| **14** | **Automatic Duplicate Merging** | If an anime is imported from your `.txt` watched list **and** is also found during the folder scan on your drive, both merge into a single franchise entry (`Watched` + `On Disk` with calculated GB size). |
| **15** | **Personal-First Local API** | Tailored strictly around your personal workflow and custom streaming site (no unnecessary multi-user clutter). |
| **16** | **Pure Python Execution (`main.py` -> `.exe`)** | Runs cleanly via `python main.py` during development and testing (no `.bat` or PowerShell wrappers needed), with a clean PyInstaller spec ready when you want to build a single `.exe`. |

---

## 3. Production Tech Stack

| Layer | Technology | Role |
| :--- | :--- | :--- |
| **Language** | **Python 3.12+** | Core runtime (`python main.py`). |
| **Desktop GUI** | **PyQt5** | Native Windows UI, system tray integration (`QSystemTrayIcon`), custom dark/light theme sync, and responsive poster grid. |
| **Database** | **SQLite 3 (WAL Mode)** | Local relational database (`data/library.db`) storing franchises, seasons, episode file paths, and last streaming state. |
| **Metadata APIs** | **AniList GraphQL API** + **Jikan v4 REST API** | Unfiltered search supporting Romaji folder matching, English title resolution, poster downloading, and sequel tree traversal. |
| **File & Season Organizer** | **`pathlib` + `shutil` + Regex Parser** | Detects episode numbers (`E01`, `- 01`, `S02E05`) and moves loose `.mp4`/`.mkv` files into structured `Anime Title/Season X/` subfolders. |
| **Streaming Site Bridge** | **FastAPI + Uvicorn** | Background daemon thread on `http://127.0.0.1:8765` serving JSON metadata, cached posters, and direct `.mp4`/`.mkv` file paths to your streaming site. |

---

## 4. Complete Database Schema (`app/db.py`)

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT
    -- Stores: 'last_streaming_url', 'last_active_franchise_id', 'window_geometry', 'default_sort'
);

CREATE TABLE IF NOT EXISTS watched_directories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_path TEXT UNIQUE NOT NULL,
    auto_organize_seasons BOOLEAN DEFAULT 1,
    last_scanned_at DATETIME
);

CREATE TABLE IF NOT EXISTS franchises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anilist_id INTEGER UNIQUE,              -- Root Season 1 AniList ID (NULL if custom)
    mal_id INTEGER,
    display_title TEXT NOT NULL,            -- English title (or automatic Romaji fallback if English is null)
    title_en TEXT,                          -- Official English title
    title_romaji TEXT,                      -- Romaji title (matched against folders & shown on hover)
    title_native TEXT,                      -- Japanese Kanji/Kana title (shown on hover)
    synopsis TEXT DEFAULT '',
    genres TEXT DEFAULT '[]',               -- JSON array e.g. '["Action", "Fantasy", "Ecchi"]'
    is_adult BOOLEAN DEFAULT 0,             -- Supports mature anime like Redo of Healer
    cover_filename TEXT,                    -- Saved in data/covers/{id}.jpg
    watch_status TEXT DEFAULT 'WATCHED',    -- WATCHED, WATCHING, PLAN_TO_WATCH, DROPPED
    storage_state TEXT DEFAULT 'ON_DISK',   -- ON_DISK, PARTIALLY_ON_DISK, WATCHED_REMOVED, NOT_DOWNLOADED
    total_size_bytes INTEGER DEFAULT 0,
    user_rating INTEGER CHECK(user_rating IS NULL OR (user_rating BETWEEN 1 AND 10)),
    user_notes TEXT DEFAULT '',
    is_custom BOOLEAN DEFAULT 0,
    needs_review BOOLEAN DEFAULT 0,
    raw_import_name TEXT,
    has_new_update BOOLEAN DEFAULT 0,
    update_details TEXT,                    -- e.g. "Season 2 Announced (Not Yet Released)"
    root_folder_path TEXT,                  -- e.g. "D:\Anime\Bleach"
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_checked_at DATETIME
);

CREATE TABLE IF NOT EXISTS seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    franchise_id INTEGER NOT NULL,
    anilist_id INTEGER UNIQUE,
    season_number INTEGER DEFAULT 1,        -- 1, 2, 3... (0 for Movies/OVAs)
    relation_type TEXT DEFAULT 'SEASON',    -- SEASON, MOVIE, OVA, SPECIAL
    title_display TEXT NOT NULL,            -- English title with Romaji fallback
    title_romaji TEXT,
    episodes_total INTEGER,
    airing_status TEXT DEFAULT 'FINISHED',  -- FINISHED, RELEASING, NOT_YET_RELEASED
    next_airing_ep INTEGER,
    next_airing_at INTEGER,
    watch_status TEXT DEFAULT 'WATCHED',
    season_folder_path TEXT,                -- e.g. "D:\Anime\Bleach\Season 1"
    size_bytes INTEGER DEFAULT 0,
    video_files_json TEXT DEFAULT '[]',     -- JSON list of .mp4/.mkv filenames inside this season folder
    storage_state TEXT DEFAULT 'ON_DISK',   -- ON_DISK, WATCHED_REMOVED, NOT_DOWNLOADED
    FOREIGN KEY (franchise_id) REFERENCES franchises(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_franchises_display_title ON franchises(display_title COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_franchises_rating ON franchises(user_rating DESC);
CREATE INDEX IF NOT EXISTS idx_franchises_size ON franchises(total_size_bytes DESC);
```

---

## 5. Deep-Dive Module Specifications

### 5.1 Smart Auto-Folder & Season Organizer (`app/core/organizer.py`)
When you select a directory on your 3 TB drive, files are often messy—some episodes are loose `.mp4`/`.mkv` files in the root folder, or `Season 1` and `Season 2` folders are scattered separately.

1. **Detection Phase:**
   * Scans all `.mp4`, `.mkv`, `.avi`, and `.webm` files and subfolders.
   * Extracts the **Base Anime Name**, **Season Number** (`S01`, `Season 2`, `2nd Season`, `II`), and **Episode Number** (`E01`, `- 01v2`, `Ep 12`).
2. **Preview & Auto-Move Phase:**
   * Groups matching files under a single parent folder: `<Selected Root>/<Clean Anime Title>/`.
   * Creates structured subfolders:
     * `<Selected Root>/Bleach/Season 1/` (moves all Season 1 `.mp4`/`.mkv` files here)
     * `<Selected Root>/Bleach/Season 2/` (moves all Season 2 `.mp4`/`.mkv` files here)
     * `<Selected Root>/Bleach/Movies & OVAs/` (if applicable)
   * Updates `seasons.season_folder_path` and `seasons.video_files_json` in SQLite immediately so your streaming site always has the exact updated paths.

### 5.2 Unfiltered Romaji-Aware AniList Engine (`app/core/anilist_client.py`)
* **Unfiltered GraphQL Search:** Queries `Media(search: $query, type: ANIME)` **without** `isAdult: false` so mature/ecchi titles like *Redo of Healer* (`Kaifuku Jutsushi no Yarinaoshi`) are never blocked or hidden.
* **Romaji & English Dual Resolution:**
  * Since most of your folders are named in Romaji, AniList natively matches your Romaji folder name and returns `title.english`, `title.romaji`, and `title.native`.
  * **Display Rule:**
    ```python
    display_title = media["title"].get("english") or media["title"].get("romaji") or raw_folder_name
    ```
    This guarantees that if an anime has an English title, you see the English title; if an anime only has a Romaji title on AniList, the card displays the Romaji title cleanly without errors.
* **Movies & OVAs Inclusion:** Traverses `SEQUEL`, `PREQUEL`, and `SIDE_STORY` edges (filtering `format IN ['TV', 'TV_SHORT', 'MOVIE', 'OVA', 'ONA', 'SPECIAL']`) and inserts all of them into the `seasons` table under the same `franchise_id` so they appear neatly inside the Anime Details view.

### 5.3 Multi-Step Deletion Confirmation Workflow (`app/ui/dialogs/delete_confirm.py`)
To prevent accidental loss while giving you instant space reclamation on your 3 TB drive, clicking **Delete** on any season or franchise triggers a 3-stage safety flow:

* **Confirmation Step 1 (Overview & Warning):**
  * Shows the Anime Title, Season(s) selected, exact Windows folder path (`D:\Anime\...`), number of `.mp4`/`.mkv` files inside, and **exact GB to be freed** (e.g., `34.8 GB`).
  * Button: `"Proceed to Delete Check ->"` or `"Cancel"`.
* **Confirmation Step 2 (Record Preservation Verification):**
  * Displays a clear notice: *"This will permanently delete the video files from your 3 TB drive. Your library entry, poster thumbnail, rating, and 'Watched, removed' status WILL BE KEPT."*
  * Requires checking a confirmation box: `[x] Yes, permanently delete these video files from my drive.`
* **Confirmation Step 3 (Final Execution):**
  * Clicking the red **`"Confirm & Permanently Delete (Free 34.8 GB)"`** button deletes the video directory (`shutil.rmtree`), sets `size_bytes = 0`, updates `storage_state = 'WATCHED_REMOVED'` (or `'PARTIALLY_ON_DISK'` if other seasons remain), and refreshes the free-space bar immediately.

### 5.4 Offline Mode & Last Streaming Session Persistence (`app/core/state_manager.py`)
* **Startup Connectivity Check:** Performs a non-blocking 2-second ping to `https://graphql.anilist.co`.
  * If unreachable, switches the app into **`Offline Mode`** (amber status pill in the bottom bar) and skips the background update thread.
* **Streaming Session Memory:**
  * Whenever you open or stream an anime on your local streaming site (or launch an episode from the app), the app writes `last_streaming_url`, `last_franchise_id`, and `last_episode_path` into the `app_state` SQLite table.
  * When you reopen the app—even in **Offline Mode**—a **"Resume Last Session"** quick-bar at the top lets you jump right back to the last opened streaming site state or episode.

### 5.5 Quit Prompt: System Tray vs. Complete Exit (`app/ui/main_window.py`)
Overriding `closeEvent(self, event)` on the main PyQt5 window:
* When you click the top-right `X` button, a clean dialog asks:
  1. **`Minimize to System Tray`** — Hides the main window to the Windows system tray icon so the background FastAPI server (`localhost:8765`) stays alive for your streaming site.
  2. **`Exit Completely`** — Gracefully stops the FastAPI server thread, saves `app_state`, and closes the Python process.
  3. *(Optional checkbox)*: `"Remember my choice (changeable in Settings)"`.

---

## 6. Project File Structure (Pure Python — Ready to Code)

```text
anime-manager/
├── main.py                          # Run via: python main.py
├── build_exe.py                     # Run after all testing to compile AnimeManager.exe
├── requirements.txt                 # PyQt5, requests, fastapi, uvicorn, Pillow
├── data/
│   ├── library.db                   # SQLite database (WAL mode)
│   ├── covers/                      # Cached poster thumbnails ({franchise_id}.jpg)
│   └── exports/                     # Manual JSON & CSV backups
└── app/
    ├── __init__.py
    ├── db.py                        # Full SQLite schema, migrations, and queries
    ├── config.py                    # App state, theme registry reader, offline detector
    ├── core/
    │   ├── parser.py                # Cleans Romaji/English folder names & .txt lines
    │   ├── organizer.py             # Auto-moves .mp4/.mkv files into Anime/Season 1, Season 2 folders
    │   ├── anilist_client.py        # Unfiltered GraphQL client (TV + Movies + OVAs + 18+)
    │   ├── scanner.py               # Fast internal drive scanner & duplicate merger
    │   ├── updater.py               # Background QThread checking for new seasons on startup
    │   └── exporter.py              # Manual JSON / CSV backup generator
    ├── api/
    │   └── server.py                # Local API for your streaming site (titles, posters, .mp4/.mkv paths)
    └── ui/
        ├── main_window.py           # Sidebar, Offline Mode badge, Resume bar, Quit/Tray dialog
        ├── theme.py                 # Automatic Windows Dark/Light mode QSS
        ├── components/
        │   └── poster_card.py       # Poster + Display Title + Hover Tooltip (Romaji & Japanese)
        ├── dialogs/
        │   ├── delete_confirm.py    # 3-step permanent deletion safety modal
        │   └── custom_entry.py      # Manual anime creator + Episode 1 thumbnail grabber
        └── pages/
            ├── library_page.py      # Search bar, Sort (A-Z, Rating, Size, Added), Filters
            ├── detail_modal.py      # Synopsis, Genres, Rating/Notes, Seasons + Movies/OVAs list
            ├── organizer_page.py    # Preview & one-click organize loose files into Season 1/2 folders
            ├── updates_page.py      # New season & airing sequel alerts
            ├── storage_page.py      # 3 TB capacity bar, largest anime table, 3-step delete trigger
            └── settings_page.py     # Folder paths, .txt importer, JSON/CSV export
```

---

## 7. Ready to Build the Full Python Codebase

Everything in the specification is now 100% locked in around your workflow. 

To make sure the **Romaji Folder Parser (`parser.py`)** and **Auto-Season Organizer (`organizer.py`)** handle your exact naming patterns on the first run:
1. If you have **5–10 sample lines from your `.txt` file** and **5–10 folder/file names from your 3 TB drive**, paste them in your next message (or tell me to go ahead with standard anime folder/file patterns).
2. Let me know if you want me to generate the complete runnable Python files now so you can drop them straight into your IDE and run `python main.py`!