# Combined anime organizer

Sources: `E:\New Anime Seasons` and `E:\Seen Anime`.
Destination: `E:\Anime Library`.

The default command only creates a preview. It does not create the destination or move media:

```powershell
python "E:\Anime Details\organize_anime_library.py"
```

Review the resulting `moves.csv`, `summary.md`, and `plan.json` under `data\exports\consolidation-*`.
Rows with `review_reason` and unassigned root files are excluded from execution.
The current checked preview is `consolidation-20261103-203253-095046`.

Close the app and stop other organizers before applying the reviewed plan:

```powershell
python "E:\Anime Details\organize_anime_library.py" --apply "E:\Anime Details\data\exports\consolidation-20261103-203253-095046\plan.json"
```

The script prints the destination and asks you to type `MOVE`. Any other response cancels.
Windows may require an administrator terminal for inherited folder permissions.

The script backs up the database, validates source sizes and modification times, refuses existing targets,
and records operations in `move-journal.jsonl`. It stops on the first move failure and retains the
remaining source files. It does not remove source directories, delete duplicates, or change media contents.
Conflicting filenames receive a suffix, listed in the preview, to retain both versions.
Successfully moved files are indexed in the library and the destination becomes an additional library root.

For uncertain titles or releases, create an overrides JSON file with full source anime-folder paths:

```json
{
  "E:\\New Anime Seasons\\Example anime folder": {
    "series": "Example Anime",
    "release": "Season 02"
  }
}
```

Generate a fresh preview with `--overrides "E:\path\overrides.json"`.
Only use a release override when every video in that source anime folder belongs to that release.
Never reuse a plan after changing source files or after partially executing it; generate and review a fresh preview.
