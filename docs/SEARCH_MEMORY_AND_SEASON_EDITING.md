# Search memory and physical season editing

## Find Download Files

The app saves the edited search text for each library anime, along with the
selected title, source and season. Changes are saved after a short typing pause,
when searching, and when leaving the page. English, Romaji and Japanese title
choices remain available from the local cache.

**Confirm season / episodes** replaces the two duplicate confirmation buttons.
It accepts checked results or the highlighted result. Continuous numbering starts
unchecked on every new confirmation; enabling it does not change the series-wide
preference. After confirmation, use **Review selected downloads** to inspect the
existing review screen before starting transfers.

**Remember these alternate titles** records the confirmed title and numbering
association. For example, an encoder's episode 177 may mean local S2E7; its next
episode 178 can then match local S2E8. An encoder's S02 label can also be mapped to
local S1 when explicitly confirmed. Different encoder numbering patterns are
kept separate. Existing title-only aliases are recognized without a database
migration. Conflicting seasons, unknown episode coverage and unverified release
boundaries can still require confirmation.

## Stop completed downloads

Stop keeps a verified download marked Completed and detaches its native transfer
without removing files. Repeating Stop after detachment is harmless. If Stop is
clicked just before completion indexing finishes, verified completion is still
recorded correctly afterward.

## Physically move episodes into a season

1. Open the anime's details and select **Edit season**.
2. Edit season now opens the physical episode file list directly. The older
   label-only controls remain under **Edit release labels…**.
3. Check the indexed episode files, or choose **Select all files**. Use
   **Number selected episodes…** to assign consecutive local numbers in the
   displayed filename order when source numbers differ.
4. Choose a destination season button and select **Review move**. **Add season…**
   selects an existing season rather than creating a duplicate slot. If several
   real folders match the season, use **Choose destination season folder…**.
5. Read the destination and folder-creation notice, then select **Confirm move**.

Season buttons and default destinations now use `Season 01`, `Season 02`, etc.
An old `Season 1` path no longer becomes the default destination just because it
already exists. Selecting Season 01 reviews moving the selected files into
`Season 01`; it can combine files already there with selected files from the old
spelling. Filenames remain unchanged, and collisions still stop for review.
With empty-folder cleanup selected, the old directory is removed only after all
its contents have moved. Other files and unselected episodes stay untouched.
Previously interrupted moves retain their saved recovery destination.

The original filenames stay unchanged, including an old source prefix such as
S02E07. Database season and episode associations drive the displayed season after
the move. Only selected files move; other episodes stay in place. File identities
remain stable, and source watch-history records are retained for the reassigned
episodes. Existing season-label editing remains available separately.

Partial downloads cannot move. Existing filenames are not overwritten: a
collision stops the preview or operation for review. Moves use the existing
verified move/copy journal; interrupted plans are saved for retry when reopening
this flow. Empty source directories follow the reviewed cleanup checkbox below.
Moving some files from a completed pack keeps the remaining
files available to the Downloads/Organizer workflow.

The empty-folder cleanup checkbox now explicitly controls removal of empty old
season directories. The anime root, destination folder and nonempty directories
are retained. Empty local source entries are hidden, while provider metadata and
watch history remain stored.

For the confirmed Black Clover layout, the seven distinct files can be selected
in filename order, numbered starting at 1, and assigned to Season 2. This maps
ASW 172–175 to local episodes 1–4 and keeps Judas 5–7 as local episodes 5–7. The
release filenames remain intact inside Season 02.

## Leftovers and completed downloads

Removing an empty database entry that shares a folder with an active season
unlinks only that empty entry. It does not remove the live season directory or
its videos. Leave directory deletion unchecked for shared folders.

The completed-download move screen shows blocking reasons and supports an
explicit destination choice when both `Season 01` and `Season 1` exist. Use
**Refresh completed files** to recheck completion. **Select this anime’s episode
files to move…** also provides access to indexed files left in staging after a
completed queue record was cleared. Partial tracked downloads remain blocked.

Opening the editor checks existing paths. Strong, unique file signatures permit
verified external-move repairs. A different physical file is indexed separately;
it is never silently relinked by filename alone. Old identities and history are
retained, and season/episode changes require the user's reviewed confirmation.
