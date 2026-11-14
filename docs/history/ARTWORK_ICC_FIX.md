# Repeated Qt ICC warnings

Implemented 11 November 2026.

## Finding

An audit decoded all 865 files in `data/covers`. Four files generated
`qt.gui.icc: fromIccProfile: failed minimal tag size sanity`: three posters and
one banner. Each contained a short ICC copyright text tag (11 bytes) that Qt
rejects. Loading the same artwork repeatedly produced repeated terminal lines.
The image data itself decoded successfully.

## Fix

- `app/core/image_profiles.py` conservatively extends the short copyright tag
  into its existing zero padding, to the minimum 12 bytes. It checks segment
  bounds, ICC header/table bounds and overlap with other tags first. Unrecognised
  or unsafe structures are left unchanged rather than guessed at.
- Existing valid profiles are retained. No JPEG recompression occurs, no colour
  transform tag is modified and JPEG scan bytes remain unchanged. A profile ID
  is cleared to indicate no checksum is supplied after the metadata correction.
- `app/core/anilist_client.py` repairs incoming artwork before Qt validation and
  writing the cache, and checks existing ready artwork through the repaired loader.
- `app/ui/refresh.py` uses the loader in its background refresh worker. Repairs
  write through a unique temporary file and atomic replacement. Concurrent cache
  changes are checked before replacement; an unwritable cache can still render
  the cleaned in-memory image. Repeated references decode once per refresh.
- Qt's logging rules/message handler are unchanged in the application. Other Qt
  warnings remain visible; this fix addresses the malformed metadata itself.

## Local repair

Four cached files were repaired, after saving their original bytes in
`data/backups/artwork_profiles_20261111_014944`:

- `anilist-112667-cover-a5f68948ce86b8d4e7fed478.jpg`
- `anilist-126546-cover-89e13bf4f31fc1c7deae5c74.jpg`
- `anilist-136707-cover-492ceefe71eee9ab79d4394c.jpg`
- `anilist-179689-banner-a6f2687b2fd0bf14963e3d4b.jpg`

Pillow decoded pixels were compared before/after and were identical. No anime
files, database links or user artwork originals outside the cache were modified.
Local report: `data/icc-repair-report.json`.

## Tests

`tests/test_image_profiles.py`: four passing regressions cover unchanged pixels
and JPEG scan bytes, idempotence, valid/truncated/unrecognised inputs, split ICC
segments, atomic cache loading, absence of the specific Qt warning after repair,
and sanitization before download cache writes.

After repair, the cache audit decoded 892 current files with **zero Qt warnings**.
Final `python data/phase2_validate.py`: **295 tests passed**, compile/check steps
passed, exit code 0. Scanner heartbeat maximum: 40.0 ms for 500 files.

## Follow-up: unsupported printer profile class `70727472`

A later download added a banner with a different profile problem:
`Unsupported ICC profile class 70727472`. The hexadecimal class bytes spell
`prtr`, a printer/output profile which this Qt image decoder cannot use.
This was not a repeat of the short copyright-tag defect.

The cache audit located it in
`anilist-20789-banner-7941d7b01f72565534aa08d2.jpg`. Its original bytes were backed
up in `data/backups/artwork_profiles_20261111_020643`.

The shared JPEG sanitizer now removes the complete ICC APP2 segment sequence
when a complete, recognised ICC header declares the `prtr` class. It does not
pretend the profile is a monitor profile or apply a colour conversion Qt did not
previously support. Other JPEG metadata, compressed scan data and decoded pixels
are retained. Supported and unrecognised non-printer classes are left unchanged.
The existing download/cache worker hooks automatically use this expanded check.

The banner's decoded pixels were compared before/after and were identical. A new
audit decoded all **967 current artwork files with zero warnings**. No application
logging rules were changed. Report: `data/icc-printer-repair-report.json`.

All **six image-profile tests passed**. The two additional regressions cover
printer profiles split across multiple segments, unchanged scan/pixel data,
preservation of other APP2 metadata, idempotence and retaining non-printer classes.
The 295-test full-suite result above records the earlier copyright-tag repair;
this follow-up was verified with the six focused tests and the full cache audit.
