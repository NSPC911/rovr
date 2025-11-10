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
def get_icon_for_file(location: str) -> list:
    """
    Get the icon and color for a file based on its name or extension.

    Args:
        location (str): The name or path of the file.

    Returns:
        list: The icon and color for the file.
    """
    if not config["interface"]["nerd_font"]:
        return ASCII_ICONS["file"]["default"]
    file_name = path.basename(location).lower()

    # 0. Check for custom icons if configured
    if "icons" in config and "files" in config["icons"]:
        for custom_icon in config["icons"]["files"]:
            pattern = custom_icon["pattern"].lower()
            match_type = custom_icon.get("match_type", "exact")

            if (
                match_type == "exact"
                and file_name == pattern
                or match_type == "endswith"
                and file_name.endswith(pattern)
            ):
                return [custom_icon["icon"], custom_icon["color"]]

    # 1. Check for full filename match
    if file_name in FILES_MAP:
        icon_key = FILES_MAP[file_name]
        return ICONS["file"].get(icon_key, ICONS["file"]["default"])

    # 2. Check for extension match
    if "." in file_name:
        # This is for hidden files like `.gitignore`
        extension = "." + file_name.split(".")[-1]
        if extension in FILE_MAP:
            icon_key = FILE_MAP[extension]
            return ICONS["file"].get(icon_key, ICONS["file"]["default"])

    # 3. Default icon
    return ICONS["file"]["default"]


@lru_cache(maxsize=1024)
def get_icon_for_folder(location: str) -> list:
    """Get the icon and color for a folder based on its name.

    Args:
        location (str): The name or path of the folder.

    Returns:
        list: The icon and color for the folder.
    """
    folder_name = path.basename(location).lower()

    if not config["interface"]["nerd_font"]:
        return ASCII_ICONS["folder"].get(folder_name, ASCII_ICONS["folder"]["default"])

    # 0. Check for custom icons if configured
    if "icons" in config and "folders" in config["icons"]:
        for custom_icon in config["icons"]["folders"]:
            pattern = custom_icon["pattern"].lower()
            match_type = custom_icon.get("match_type", "exact")

            if (
                match_type == "exact"
                and folder_name == pattern
                or match_type == "endswith"
                and folder_name.endswith(pattern)
            ):
                return [custom_icon["icon"], custom_icon["color"]]

    # Check for special folder types
    if folder_name in FOLDER_MAP:
        icon_key = FOLDER_MAP[folder_name]
        return ICONS["folder"].get(icon_key, ICONS["folder"]["default"])
    else:
        return ICONS["folder"]["default"]


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
