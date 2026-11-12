# Details, Organizer, saved duplicate reviews and Home fixes

- Watch-status options now use the pointing-hand cursor.
- Organizer preview headers, proposed badges and Review buttons are centered.
  Content-sized columns reserve sufficient space. The actual clipping cause was
  global table-item padding reducing embedded-widget space by 28px; a scoped
  zero-padding rule fixes that without changing other tables.
- Duplicate scans no longer begin with an uncancellable identity inventory sync.
  Stop remains cooperative between files and during existing hash reads. No new
  hashing system was added and deletion retains its existing verification safeguards.
- Check duplicate files is now a dropdown: saved database results or a drive check.
  The last three completed reviews are retained in SQLite app state. Cancellation
  does not overwrite them. Loading saved results rechecks file locations and saved
  size/time/file identity signatures off the UI thread. Missing, moved or changed
  groups are listed for review and are not offered for deletion. The app does not
  guess a moved file's destination; run a drive scan after repairing paths.
- Synopsis scrolling explicitly uses AsNeeded. A rendered short synopsis has no
  scroll range; long content remains accessible.
- Searching hides the hero, broadcast schedule and new-release strip so All anime
  search results occupy the top of Home. Clearing search restores those sections.
- Settings → Appearance → New seasons and episodes selects placement above Hero,
  above Broadcast schedule or above All anime. Selection persists and applies immediately.
- Fairy Tail diagnosis: the manually grouped representative was an unmatched old
  entry with empty synopsis/artwork. Its matched group member already contained
  a 765-character synopsis and cached cover. Group cards now fill empty presentation
  fields from a matched member, preferring the same cached provider ID. IDs, file
  ownership, notes and history are unchanged. Artwork changes to any member reload
  the open group details. The existing Fairy Tail group resolves those cached fields
  in a read-only verification; no user records were rewritten.

Changed code: duplicates.py, series.py, duplicate_page.py, detail_modal.py,
organizer_page.py, organizer_style.py, library_page.py, settings_page.py and
main_window.py. Regression coverage: tests/test_requested_ui_fixes.py.

Validation: 59 targeted tests across requested fixes, Home, Organizer, settings,
download/settings polish, UI regressions and Details. Organizer was rendered and
visually inspected at 1280×900; the complete Download ready badge and Review button
fit their cells. Tests use temporary data; no actual media files were moved/deleted.
