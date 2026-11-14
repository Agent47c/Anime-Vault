ANIMEVAULT - NEW FEATURES TO BE ADDED
======================================

This file contains the features that still need to be connected to the
PyQt5 application backend.

The HTML UI is a visual reference. Every button and control must be
connected to the appropriate Python service, SQLite query, filesystem
operation, AniList request, or FastAPI endpoint.

--------------------------------------------------
1. FLAT ANIME ROOT FOLDER DETECTION
--------------------------------------------------

Required behavior:

Detect this structure:

D:\Anime\Solo Leveling\01.mkv
D:\Anime\Solo Leveling\02.mkv
D:\Anime\Solo Leveling\03.mkv

Treat the direct video files as Season 1.

Supported video extensions:

.mp4
.mkv
.avi
.webm
.ts
.m4v
.mov

Rules:

- Do not require a Season 1 folder.
- Use the root folder name as the anime title.
- Use direct video files as Season 1.
- Detect episode numbers from file names.
- Display a preview before moving files.
- Do not silently merge files when both root files and Season folders exist.
- Display a warning for mixed season structures.

Suggested database fields:

flat_root_detected
flat_root_confirmed
detected_season_number
organization_status

--------------------------------------------------
2. MANUAL ANILIST REMATCH
--------------------------------------------------

Add a Rematch Anime button to the Anime Details dialog.

Required behavior:

- Search AniList by English title.
- Search AniList by Romaji title.
- Search AniList by Japanese title.
- Display poster, year, format, episode count, genres, and confidence.
- Allow the user to select a result.
- Change only the metadata link.
- Never rename the user's local folder automatically.
- Keep the original source folder name.
- Store the new AniList ID.
- Replace cached metadata and poster after confirmation.

Suggested fields:

source_folder_name
linked_anilist_id
display_title
romaji_title
native_title
metadata_match_confidence
metadata_last_updated

--------------------------------------------------
3. COMPACT LIBRARY VIEW
--------------------------------------------------

Add two library display modes:

Standard View:
- Large poster cards.
- Poster status badge.
- Rating.
- Disk size.
- Episode count.
- New and 18+ badges.

Compact View:
- Small thumbnail.
- English title.
- Romaji title.
- Episode count.
- Rating.
- Disk size.
- Watch status.
- Checkbox selection.

Requirements:

- Save the selected density using QSettings.
- Restore the density on application startup.
- Support multi-selection in both views.
- Show 20-30 anime entries on a wide monitor.

--------------------------------------------------
4. POTENTIAL RECLAIM FILTER
--------------------------------------------------

Add a Potential Reclaim filter in Library and Storage.

The filter should select titles where:

watch_status = "watched"
AND storage_state IN ("on_disk", "partial")
AND disk_size > 0

Display:

- Number of titles.
- Total possible reclaimable size.
- Last watched date.
- File path.
- Delete or review action.

Do not delete files immediately from the filter.

The user must go through the safe deletion flow.

--------------------------------------------------
5. DIRECT EPISODE LAUNCHER
--------------------------------------------------

Add Play Episode buttons to:

- Resume Last Session banner.
- Anime Details dialog.
- Season rows.
- Episode rows.
- Compact library cards.

Player options:

- Windows default application.
- VLC.
- MPV.
- MPC-HC.
- Local FastAPI streaming player.

Windows default player:

os.startfile(video_path)

Configured player:

subprocess.Popen([player_path, video_path])

Security requirements:

- Validate that the video exists.
- Validate that the video is inside a configured library root.
- Reject path traversal.
- Reject unapproved external paths.
- Log the last opened file.

--------------------------------------------------
6. WATCHED TXT IMPORTER
--------------------------------------------------

Add a watched list importer for TXT files.

Expected TXT format:

Solo Leveling
Bleach
Kimetsu no Yaiba
One Piece

Required import states:

matched
ambiguous
not_found
duplicate
ignored

Matching:

- Match English titles.
- Match Romaji titles.
- Match Japanese titles.
- Match aliases.
- Match folder names.
- Show confidence percentage.

Recommended confidence behavior:

90-100%:
Automatically matched.

70-89%:
Show review recommendation.

0-69%:
Require manual review.

Never create duplicate library entries.

--------------------------------------------------
7. MISSING EPISODE DETECTION
--------------------------------------------------

For each season:

- Detect episode numbers.
- Find missing episodes.
- Detect duplicate episode numbers.
- Detect files with no episode number.
- Detect zero-byte files.
- Detect unreadable files.

Example display:

Season 1
Episodes found: 10 / 12
Missing: 07, 11
Duplicates: 04
Unrecognized files: 2

Add a Health status:

Healthy
Missing Episodes
Duplicate Episodes
Unreadable Files
Needs Metadata Review

--------------------------------------------------
8. MULTI-ROOT LIBRARY SUPPORT
--------------------------------------------------

Allow multiple library roots:

D:\Anime
E:\Anime Archive
F:\Completed Series

Requirements:

- Add and remove roots.
- Scan all roots in the background.
- Show the root path on each season.
- Prevent duplicate scanning of the same file.
- Normalize Windows paths.
- Handle disconnected drives gracefully.
- Display missing-root warnings.

--------------------------------------------------
9. EPISODE-LEVEL WATCH PROGRESS
--------------------------------------------------

Store:

anime_id
season_id
episode_number
playback_position
episode_duration
last_watched
is_completed

Resume should display:

Anime title
Season number
Episode number
Playback position
Remaining time

Example:

Solo Leveling
Season 1 · Episode 8
18 minutes remaining

--------------------------------------------------
10. SMART COLLECTIONS
--------------------------------------------------

Add dynamic collections:

- Currently Watching.
- Watched.
- Plan to Watch.
- Dropped.
- Potential Reclaim.
- Missing Episodes.
- Duplicate Files.
- Recently Added.
- Recently Watched.
- Currently Airing.
- Not Rated.
- Needs Metadata Review.
- Watched, Removed.

Collections should update automatically from SQLite.

--------------------------------------------------
11. BATCH ACTIONS
--------------------------------------------------

Add card selection checkboxes.

Batch actions:

- Mark Watched.
- Mark Watching.
- Add Rating.
- Change Collection.
- Rematch Metadata.
- Open Folder.
- Export Selected.
- Delete Files.
- Add Notes.
- Refresh Posters.

The Delete Files action must always use the safe deletion flow.

--------------------------------------------------
12. SAFE DELETION FLOW
--------------------------------------------------

Use three steps:

Step 1:
Review selected titles and exact disk size.

Step 2:
Confirm that database records will be retained.

Step 3:
Delete files and update the storage state.

After successful deletion:

storage_state = "watched_removed"
watch_status = "watched"
files_deleted = 1
deleted_at = current_time

Never delete database records unless the user specifically chooses
"Permanently Remove Library Record."

--------------------------------------------------
13. FILE INTEGRITY CHECKER
--------------------------------------------------

Scan for:

- Missing files.
- Zero-byte files.
- Corrupted or unreadable files.
- Duplicate episode numbers.
- Subtitle files without videos.
- Video files without metadata.
- Fonts without matching subtitles.
- Unsupported extensions.

Display results in Updates and Organizer.

--------------------------------------------------
14. METADATA CACHE MANAGER
--------------------------------------------------

Cache locally:

- AniList metadata.
- Posters.
- Cover images.
- Genre information.
- Relations.
- Season information.

Settings page should show:

Cached titles
Cached posters
Last update
Cache size

Actions:

- Refresh Metadata.
- Refresh Selected.
- Clear Poster Cache.
- Clear Metadata Cache.
- Rebuild Cache.

Offline Mode must use cached data.

--------------------------------------------------
15. BACKUP AND RESTORE
--------------------------------------------------

Support:

- JSON backup.
- CSV export.
- SQLite database backup.
- Poster cache backup.
- Configuration backup.

Before restoring:

- Create an automatic backup of the current database.
- Show title count.
- Show season count.
- Show watched progress count.
- Show notes count.
- Ask for confirmation.

Restore options:

- Replace current database.
- Import as additional records.
- Preview differences.

--------------------------------------------------
16. LOCAL FASTAPI SECURITY
--------------------------------------------------

The FastAPI server must:

- Bind only to 127.0.0.1.
- Validate all requested paths.
- Reject ../ traversal.
- Allow only configured library roots.
- Reject unsupported video extensions.
- Optionally require a local API token.
- Log requests.
- Expose server status in Settings.

Endpoints:

GET /api/library
GET /api/anime/{id}
GET /api/anime/{id}/seasons
GET /api/video/{episode_id}
GET /api/covers/{anilist_id}
GET /api/health

--------------------------------------------------
17. MEDIA PLAYER CONFIGURATION
--------------------------------------------------

Settings must support:

- Windows Default.
- VLC.
- MPV.
- MPC-HC.
- Custom player executable.

Allow:

- Browse for player.
- Detect installed players.
- Test player.
- Reset to Windows Default.

--------------------------------------------------
18. SMART SEASON PARSER
--------------------------------------------------

Recognize:

S01
S1
Season 2
2nd Season
Part II
Part 3
Cour 2
Roman numerals
Final Season
The Final Season

Recognize episode patterns:

E01
Ep 01
Episode 01
- 01
01
01v2
01-02

The parser must not mistake years, resolutions, or audio channels
for episode numbers.

--------------------------------------------------
19. DRAG AND DROP
--------------------------------------------------

Support drag and drop for:

- Anime folders into Organizer.
- TXT files into Watched Import.
- Video files into Organizer.
- Video files into an Anime Details dialog.
- Poster images into Custom Poster.

Show an explicit preview before moving or importing files.

--------------------------------------------------
20. CUSTOM OVERRIDES
--------------------------------------------------

Allow users to override:

- Display title.
- Short title.
- Poster.
- Notes.
- Genres.
- Collection.
- Rating.

Keep original AniList metadata available.

Add:

Reset Title
Reset Poster
Reset Metadata
Reset All Overrides

--------------------------------------------------
21. KEYBOARD SHORTCUTS
--------------------------------------------------

Ctrl + K:
Focus global search.

Ctrl + F:
Focus Library search.

Ctrl + R:
Refresh metadata.

Ctrl + I:
Open watched TXT importer.

Ctrl + O:
Open Organizer.

Space:
Play selected item.

Delete:
Open safe deletion flow.

Escape:
Close modal or drawer.

Ctrl + Shift + B:
Create database backup.

--------------------------------------------------
22. SYSTEM TRAY
--------------------------------------------------

Tray menu:

- Restore.
- Toggle Server.
- Start Scan.
- Open Settings.
- Pause Metadata Updates.
- Exit Completely.

Close behavior:

- Minimize to tray.
- Exit completely.
- Remember choice.

Store close preference using QSettings.

--------------------------------------------------
23. ACCESSIBILITY
--------------------------------------------------

Add:

- Larger text mode.
- High contrast mode.
- Reduced motion mode.
- Keyboard focus indicators.
- Tooltips on icon buttons.
- Accessible names for all controls.
- Screen reader-friendly labels.
- Color-independent status labels.

Do not use color as the only status indicator.

--------------------------------------------------
24. DATABASE TABLES
--------------------------------------------------

Recommended tables:

anime
seasons
episodes
files
collections
watch_progress
notes
metadata_cache
poster_cache
library_roots
scan_history
organizer_jobs
backup_history
settings
import_jobs
rematch_history

Important anime fields:

id
anilist_id
display_title
english_title
romaji_title
native_title
source_folder_name
custom_title
custom_poster
watch_status
storage_state
rating
notes
is_18_plus
created_at
updated_at
last_watched

--------------------------------------------------
25. PYQT5 PAGE STRUCTURE
--------------------------------------------------

QMainWindow
|
|-- SidebarWidget
|   |-- Navigation buttons
|   |-- Collections
|   |-- Drive card
|   |-- API status
|
|-- TopBarWidget
|   |-- Global search
|   |-- Offline badge
|   |-- Theme button
|   |-- Notification button
|
|-- QStackedWidget
|   |-- LibraryPage
|   |-- UpdatesPage
|   |-- OrganizerPage
|   |-- StoragePage
|   |-- SettingsPage
|
|-- StatusBarWidget
|
|-- AnimeDetailsDialog
|-- RematchDialog
|-- WatchedImportDialog
|-- SafeDeleteDialog
|-- PlayerSelectionDialog
|-- BackupRestoreDialog

--------------------------------------------------
26. PYQT5 WORKER THREADS
--------------------------------------------------

Use QThread or QRunnable for:

- AniList requests.
- Folder scanning.
- File integrity checking.
- Poster downloading.
- Metadata cache updates.
- Organizer preview generation.
- Organizer execution.
- Storage calculation.
- Backup creation.
- TXT matching.
- Video file validation.

The UI must never freeze during these operations.

--------------------------------------------------
27. IMPLEMENTATION PRIORITY
--------------------------------------------------

Priority 1:

1. Flat root folder detection.
2. Potential Reclaim filter.
3. Direct episode launcher.
4. Compact library view.
5. Manual metadata rematch.
6. Watched TXT importer.

Priority 2:

7. Missing episode detection.
8. Duplicate episode detection.
9. Multi-root library support.
10. Episode-level watch progress.
11. Safe deletion flow.
12. File integrity scanner.

Priority 3:

13. Smart collections.
14. Batch operations.
15. Metadata cache manager.
16. Backup restore preview.
17. Custom poster and title overrides.
18. Drag and drop.

Priority 4:

19. Accessibility settings.
20. Local API token.
21. Scheduled metadata updates.
22. Advanced player detection.
23. Advanced keyboard shortcuts.
24. Scan history and job history.