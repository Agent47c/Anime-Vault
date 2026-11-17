"""Shared naming policy for newly created season directories."""
from pathlib import Path
import re


def season_folder_name(number):
    number = int(number)
    if number < 1:
        raise ValueError('A season folder requires a positive season number.')
    return f'Season {number:02d}'


def existing_or_new_season_folder(root, number):
    """Choose the padded destination without renaming anything at inspection.

    A legacy Season 1 folder is a source, never the default target. Moving its
    files and removing it when empty requires the normal reviewed operation.
    """
    root = Path(root)
    canonical = root / season_folder_name(number)
    matches = [child for child in root.iterdir()
               if child.is_dir() and re.fullmatch(r'(?:season\s*|s)0*' + str(int(number)), child.name, re.I)] if root.is_dir() else []
    preferred = next((child for child in matches if child.name.casefold() == canonical.name.casefold()), None)
    if preferred:
        return preferred
    return canonical
