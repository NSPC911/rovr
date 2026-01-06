import os
from os import path
from typing import TypedDict, cast

import ujson

from rovr.variables.constants import SortByOptions
from rovr.variables.maps import VAR_TO_DIR

from .path import normalise


class FolderPrefDict(TypedDict):
    sort_by: str
    sort_descending: bool


folder_prefs: dict[str, FolderPrefDict] = {}


def load_folder_prefs() -> dict[str, FolderPrefDict]:
    """
    Load folder preferences from the JSON file.

    Returns:
        dict: A dictionary mapping folder paths to their sort preferences.
    """
    global folder_prefs
    prefs_file = path.join(VAR_TO_DIR["CONFIG"], "folder_preferences.json")

    os.makedirs(VAR_TO_DIR["CONFIG"], exist_ok=True)

    if not path.exists(prefs_file):
        folder_prefs = {}
        return folder_prefs

    try:
        with open(prefs_file, "r", encoding="utf-8") as f:
            loaded = ujson.load(f)
        if not isinstance(loaded, dict):
            # some stupid people will do some stupid things
            loaded = {}

        # validate structure
        expanded: dict[str, FolderPrefDict] = {}
        for folder_path, pref in loaded.items():
            if (
                isinstance(pref, dict)
                and "sort_by" in pref
                and "sort_descending" in pref
                and isinstance(pref["sort_by"], str)
                and isinstance(pref["sort_descending"], bool)
            ):
                for var, dir_path_val in VAR_TO_DIR.items():
                    folder_path = folder_path.replace(f"${var}", dir_path_val)
                expanded[folder_path] = cast(FolderPrefDict, pref)

        folder_prefs = expanded
    except (IOError, ValueError, ujson.JSONDecodeError):
        folder_prefs = {}

    return folder_prefs


def save_folder_prefs() -> None:
    """Save folder preferences to the JSON file."""
    global folder_prefs
    prefs_file = path.join(VAR_TO_DIR["CONFIG"], "folder_preferences.json")
    sorted_vars = sorted(VAR_TO_DIR.items(), key=lambda x: len(x[1]), reverse=True)

    collapsed: dict[str, FolderPrefDict] = {}
    for folder_path, pref in folder_prefs.items():
        folder_path = normalise(folder_path)
        for var, dir_path_val in sorted_vars:
            folder_path = folder_path.replace(dir_path_val, f"${var}")
        collapsed[folder_path] = pref

    try:
        with open(prefs_file, "w", encoding="utf-8") as f:
            ujson.dump(collapsed, f, escape_forward_slashes=False, indent=2)
    except (IOError, OSError):
        # something beyond our control
        pass


def get_folder_pref(folder_path: str) -> FolderPrefDict | None:
    """
    Get the sort preference for a specific folder.

    Args:
        folder_path: The path to the folder.

    Returns:
        FolderPrefDict if a custom preference exists, None otherwise.
    """
    normalised = normalise(folder_path)
    return folder_prefs.get(normalised)


def set_folder_pref(folder_path: str, sort_by: SortByOptions, sort_descending: bool) -> None:
    """
    Set the sort preference for a specific folder.

    Args:
        folder_path: The path to the folder.
        sort_by: The sort method (name, size, modified, created, extension, natural).
        sort_descending: Whether to sort in descending order.
    """
    global folder_prefs
    normalised = normalise(folder_path)
    folder_prefs[normalised] = FolderPrefDict(
        sort_by=sort_by, sort_descending=sort_descending
    )
    save_folder_prefs()


def remove_folder_pref(folder_path: str) -> None:
    """
    Remove the sort preference for a specific folder.

    Args:
        folder_path: The path to the folder.
    """
    global folder_prefs
    normalised = normalise(folder_path)
    if normalised in folder_prefs:
        del folder_prefs[normalised]
        save_folder_prefs()


def has_folder_pref(folder_path: str) -> bool:
    """
    Check if a folder has a custom sort preference.

    Args:
        folder_path: The path to the folder.

    Returns:
        True if the folder has a custom preference, False otherwise.
    """
    normalised = normalise(folder_path)
    return normalised in folder_prefs
