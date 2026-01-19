import fnmatch
from functools import lru_cache
from os import path

from rovr.variables.constants import config
from rovr.variables.maps import (
    ASCII_ICONS,
    ASCII_TOGGLE_BUTTON_ICONS,
    FILE_MAP,
    FILES_MAP,
    FOLDER_MAP,
    ICONS,
    TOGGLE_BUTTON_ICONS,
)


@lru_cache(maxsize=1024)
def get_icon_for_file(location: str) -> list[str]:
    """
    Get the icon and color for a file based on its name or extension.

    Args:
        location (str): The name or path of the file.

    Returns:
        list: The icon and color for the file.
    """
    if not config["interface"]["nerd_font"]:
        return ASCII_ICONS["file"]["default"]

    # 0. check junction/symlink
    if path.islink(location):
        return ICONS["general"]["symlink"]

    file_name = path.basename(location).lower()

    # 1. Check for custom icons if configured
    if "icons" in config and "files" in config["icons"]:
        for custom_icon in config["icons"]["files"]:
            pattern = custom_icon["pattern"].lower()
            if fnmatch.fnmatch(file_name, pattern):
                return [custom_icon["icon"], custom_icon["color"]]

    # 2. Check for full filename match
    if file_name in FILES_MAP:
        icon_key = FILES_MAP[file_name]
        return ICONS["file"].get(icon_key, ICONS["file"]["default"])

    # 3. Check for extension match
    if "." in file_name:
        # This is for hidden files like `.gitignore`
        extension = "." + file_name.split(".")[-1]
        if extension in FILE_MAP:
            icon_key = FILE_MAP[extension]
            return ICONS["file"].get(icon_key, ICONS["file"]["default"])

    # 4. Default icon
    return ICONS["file"]["default"]


@lru_cache(maxsize=1024)
def get_icon_for_folder(location: str) -> list[str]:
    """Get the icon and color for a folder based on its name.

    Args:
        location (str): The name or path of the folder.

    Returns:
        list: The icon and color for the folder.
    """
    if not config["interface"]["nerd_font"]:
        return ASCII_ICONS["folder"]["default"]

    # 0. check junction/symlink
    if path.islink(location) or path.isjunction(location):
        return ICONS["general"]["symlink"]

    folder_name = path.basename(location).lower()

    # 1. Check for custom icons if configured
    if "icons" in config and "folders" in config["icons"]:
        for custom_icon in config["icons"]["folders"]:
            pattern = custom_icon["pattern"].lower()
            if fnmatch.fnmatch(folder_name, pattern):
                return [custom_icon["icon"], custom_icon["color"]]

    # 2. Check for special folder types
    if folder_name in FOLDER_MAP:
        icon_key = FOLDER_MAP[folder_name]
        return ICONS["folder"].get(icon_key, ICONS["folder"]["default"])

    # 3. Default icon
    return ICONS["folder"]["default"]


def get_icon_smart(location: str) -> list[str]:
    """Get the icon and color for a file or folder based on its path.

    Args:
        location (str): The path of the file or folder.

    Returns:
        list: The icon and color for the file or folder.
    """
    if path.isdir(location):
        return get_icon_for_folder(location)
    else:
        return get_icon_for_file(location)


@lru_cache(maxsize=1024)
def get_icon(outer_key: str, inner_key: str) -> list:
    """Get an icon from double keys.
    Args:
        outer_key (str): The category name (general/folder/file)
        inner_key (str): The icon's name

    Returns:
        list[str,str]: The icon and color for the icon
    """
    if not config["interface"]["nerd_font"]:
        return ASCII_ICONS.get(outer_key, {"empty": None}).get(inner_key, " ")
    else:
        return ICONS[outer_key][inner_key]


@lru_cache(maxsize=1024)
def get_toggle_button_icon(key: str) -> str:
    if not config["interface"]["nerd_font"]:
        return ASCII_TOGGLE_BUTTON_ICONS[key]
    else:
        return TOGGLE_BUTTON_ICONS[key]
