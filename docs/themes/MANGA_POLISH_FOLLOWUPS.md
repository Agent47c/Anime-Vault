# Manga UI polish and download numbering

Date: 15 November 2026. The main Library remains the shared design authority.
This supersedes the earlier staged taxonomy panel and update-action layout.

## Download assignment

- The checkbox is labelled **Continuous episode numbering**.
- Every selected release has its own **Season / folder** and **Episode number(s)** fields.
- A continuous episode keeps its number independently of the destination: episode
  177 assigned to Season 1 is stored as `EPISODE:ABS:177`, with destination season 1.
- With continuous numbering off, season 2 episode 6 is `EPISODE:S2:6`.
  Season 1 episode 6 and season 2 episode 6 can coexist; two assignments to the
  same absolute episode cannot.
- Each file shows a live folder/numbering explanation. Original torrent file names
  are preserved. Editing the association does not rename a physical video.
- Numbering preference is remembered for the anime on successful confirmation.
  Invalid input and duplicate assignments do not save that preference.
- Source season-relative numbers are never converted to absolute numbers using
  guessed season lengths. Users can supply the correct number explicitly.
- Continuous aliases are stored independently of the physical destination season.
- Visible release titles in this form no longer repeat themselves in tooltips.

## Organizer

- A scan or filter-tab change no longer selects every proposed move automatically.
  Select all stays synchronized with the actual selection.
- Season and folder, Merge, and Duplicate tabs share the main raised/inset material.
  The active tab looks recessed; inactive tabs remain raised.
- File count, proposed season/status, and Review have separately sized columns.
  Text width and display scale determine minimum widths; shadow space stays inside
  the action cell rather than overlapping the status cell.
- Cached completed-download rows can open Review even when the general preview is
  stale. Their move preview revalidates sources and destinations asynchronously.
  Ordinary stale organization plans still require a scan before execution.
- Completed downloads keep the linked anime identity. Review uses the existing
  completed-download move dialog, not generic staging-folder organization.
- Move preview reuses a unique physical `Season 2` folder even if the scanner has
  not registered it yet, instead of creating a second `Season 02` folder.
  Multiple matching folders produce a review message rather than a guessed target.
- Existing scan indexing handles local videos absent from the database. Unknown
  anime identity is not permission to guess an anime or move unrelated files.
- Preview does not move files. Confirmed moves retain existing collision checks,
  file identity/history updates, recovery journals and stop behaviour.

### Main root versus staging and anime folders

The main library root is now saved as `library.main_root` as soon as an existing
destination selector or its edited path is committed. Older `merge_destination`
preferences remain a fallback. Generating a merge preview also saves that choice.
The previous implementation saved it only after preview generation, while the UI
could display an unsaved default path. It also required exactly one watched row,
so nested watched directories could incorrectly make a single library ambiguous.

Fallback root detection now collapses nested watched folders and excludes the
reserved staging directory. Separate unrelated roots still require an explicit
choice. An explicitly saved download destination is no longer silently rewritten
when it happens to equal the default path.

Downloads has distinct actions for **Open downloads folder** (the shared staging
base) and **Open selected download folder** (that transfer's files). Per-row folder
actions remain scoped to their transfer. Previously the generic label followed
the selected anime, which could make opening Black Clover appear to change the
shared downloads folder. Opening a folder does not rename it or move its contents.

Move preview excludes the configured staging base and every tracked job root from
canonical anime/season locations, including custom staging names. It rejects a
move target inside staging rather than using an older torrent's subfolder.

## Shared alerts

`app/ui/components/message_boxes.py` provides the shared alert component.
App errors, information messages and confirmations use it, including playback
failures, settings, imports, file operations and startup information.

Rendered example: [shared light alert](previews/shared-alert-light.png).

- Consistent theme colours, heading, symbol, readable message and explicit buttons.
- OK remains visible during hover and press; native graphics-effect source capture
  is excluded from alert buttons.
- Standard return values and button roles remain intact, including custom removal
  buttons, Cancel defaults, No defaults and keyboard activation.
- Existing Show Details path-repair review remains available before approval.
- Manga, Sakura Light and Sakura Dark styling can change while a dialog is open.
- The path-repair error itself remains a valid protection: styling does not bypass
  the requirement to repair missing/changed paths before playback.

An isolated native Qt QMessageBox also crashed under this environment's headless
platform, without Anime Vault imported. The shared app dialog uses QDialog rather
than that native QMessageBox rendering path. Tests exercise the actual app dialog.

## Other reported UI corrections

| Area | Applied correction |
| --- | --- |
| Updates | Spaced shadowed cards; Find Download primary; View changes/Later secondary; More retains Not interested/Mute/Watched and ignore/Dismiss; red trash Remove |
| View changes | Shadowed release rows with Find release search icon and Ignore |
| Discovery | Uniform shadowed cards, plain descriptions, readable Details and Add actions; no empty banner placeholder |
| Genres/themes | Immediate boxed popovers; outside-click dismissal; no staged Clear/Cancel/Apply panel |
| Dropdowns | Drawn chevrons replace unsupported font glyphs; native combo boxes exclude graphics effects |
| Playback | Separate rounded main/arrow controls with a gap; clipped control rendering prevents square corner bleed |
| Completed transfers | Inset icon surface; active downloads retain raised icon surface |
| Add download | Shared themed anime picker replaces the native item prompt with blank hover rendering |
| Import list | Centred Choose TXT file; readable native dropdown arrows |
| Setup | Existing five steps, actual numbered status cells, shadowed cards and compact controls; no fake success/integrity claims |
| Download review | Payload cards and coverage/destination section retain the existing confirmation gate and matching route |
| Home updates strip | Wheel input moves horizontally; row height accommodates cards; no inner vertical wheel movement |
| Exit | Remember my choice is visible above choices; checkbox/radio contrast and dialog size corrected |
| Theme switching | Cached update/discovery cards refresh their family-specific material; setup restores Sakura button layout policies |

No CRC/SHA badges, profile features or other declined functionality were added.
Existing Settings options and section boundaries are retained.

## Verification and limits

Rendered the main screen, Updates/Details/Edit/Rematch, the twelve workflow batch,
the twelve additional screens, shared alert normal/pressed states, multi-file
assignment, Organizer and exit with temporary data. Existing master controls
take precedence over conflicting decorative elements in page references.

Regression coverage includes exact episode identity, per-file season assignment,
duplicate rejection, submission context, unregistered season folders, stale
Organizer review, selection state, theme restoration, alert hover/press and
confirmation/detail results. The combined regression suite passed 601 tests.
After the final custom-staging guard, all 14 download relocation/recovery checks
passed, including the new cross-job staging regression.

These are rendered fixture checks, not a claim of pixel equality at every Windows
scale or with every possible provider title. Actual provider artwork and text
change wrapping. Native OS file pickers remain OS-managed. No live media was
moved, no personal database was edited, and no installer was built for these checks.

The current reference inventory remains in MANGA_SCREEN_REFERENCE_INVENTORY.md.
Missing dedicated layouts keep existing functionality with shared theme controls.
