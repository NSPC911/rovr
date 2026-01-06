"""
Per-folder sort preferences storage and management.

Stores folder-specific sort preferences in a JSON file,
following the same pattern as pins.py for consistency.
"""

import os
from os import path
from typing import TypedDict, cast

import ujson

from rovr.variables.maps import VAR_TO_DIR

from .path import normalise


class FolderPrefDict(TypedDict):
    """Structure for a single folder's sort preferences."""

    sort_by: str
    sort_descending: bool


# Global storage for folder preferences
folder_prefs: dict[str, FolderPrefDict] = {}


def _get_prefs_file_path() -> str:
    """Get the path to the folder preferences file.
    Returns:
        str: The full path to the folder preferences JSON file.
    """
    return path.join(VAR_TO_DIR["CONFIG"], "folder_preferences.json")


def _expand_path(folder_path: str) -> str:
    """Expand $VAR variables in a path to actual values.
    Args:
        folder_path(str): The folder path with potential $VAR variables.
    Returns:
        str: The expanded folder path.
    """
    result = folder_path
    for var, dir_path_val in VAR_TO_DIR.items():
        result = result.replace(f"${var}", dir_path_val)
    return normalise(result)


def _collapse_path(folder_path: str) -> str:
    """Replace actual paths with $VAR variables for portability.
    Args:
        folder_path(str): The folder path to collapse.
    Returns:
        str: The collapsed folder path with $VAR variables."""
    result = normalise(folder_path)
    # Sort by length descending to replace longest matches first
    sorted_vars = sorted(VAR_TO_DIR.items(), key=lambda x: len(x[1]), reverse=True)
    for var, dir_path_val in sorted_vars:
        result = result.replace(dir_path_val, f"${var}")
    return result


def load_folder_prefs() -> dict[str, FolderPrefDict]:
    """
    Load folder preferences from the JSON file.

    Returns:
        dict: A dictionary mapping folder paths to their sort preferences.

    Raises:
        ValueError: If the preferences file is malformed.
    """
    global folder_prefs
    prefs_file = _get_prefs_file_path()

    # Ensure the config directory exists
    if not path.exists(VAR_TO_DIR["CONFIG"]):
        os.makedirs(VAR_TO_DIR["CONFIG"])

    # If file doesn't exist, return empty dict
    if not path.exists(prefs_file):
        folder_prefs = {}
        return folder_prefs

    try:
        with open(prefs_file, "r", encoding="utf-8") as f:
            loaded = ujson.load(f)
        if not isinstance(loaded, dict):
            raise ValueError("Invalid folder preferences format")

        # Expand variables in paths and validate structure
        expanded: dict[str, FolderPrefDict] = {}
        for folder_path, pref in loaded.items():
            if (
                isinstance(pref, dict)
                and "sort_by" in pref
                and "sort_descending" in pref
                and isinstance(pref["sort_by"], str)
                and isinstance(pref["sort_descending"], bool)
            ):
                expanded_path = _expand_path(folder_path)
                expanded[expanded_path] = cast(FolderPrefDict, pref)

        folder_prefs = expanded
    except (IOError, ValueError, ujson.JSONDecodeError):
        # On any error, reset to empty
        folder_prefs = {}

    return folder_prefs


def _save_folder_prefs() -> None:
    """Save folder preferences to the JSON file."""
    global folder_prefs
    prefs_file = _get_prefs_file_path()

    # Collapse paths for portability
    collapsed: dict[str, FolderPrefDict] = {}
    for folder_path, pref in folder_prefs.items():
        collapsed_path = _collapse_path(folder_path)
        collapsed[collapsed_path] = pref

    try:
        with open(prefs_file, "w", encoding="utf-8") as f:
            ujson.dump(collapsed, f, escape_forward_slashes=False, indent=2)
    except IOError:
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


def set_folder_pref(folder_path: str, sort_by: str, sort_descending: bool) -> None:
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
    _save_folder_prefs()


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
        _save_folder_prefs()


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
