from functools import lru_cache
from os import path

from rovr.variables.constants import config
from rovr.variables.maps import (
    ASCII_ICONS,
    ASCII_TOGGLE_BUTTON_ICONS,
    FILE_MAP,
    FILES_MAP,
    FOLDER_ICONS_WITH_FOLDER_SILHOUETTE,
    FOLDER_MAP,
    ICONS,
    TOGGLE_BUTTON_ICONS,
)


@lru_cache(maxsize=128)
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

            is_match = False
            if (
                match_type == "exact"
                and file_name == pattern
                or match_type == "endswith"
                and file_name.endswith(pattern)
            ):
                is_match = True

            if is_match:
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


@lru_cache(maxsize=128)
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

            is_match = False
            if (
                match_type == "exact"
                and folder_name == pattern
                or match_type == "endswith"
                and folder_name.endswith(pattern)
            ):
                is_match = True

            if is_match:
                preserve_folder_color = config.get("icons", {}).get(
                    "preserve_folder_color_for_non_folder_icons", False
                )

                if preserve_folder_color:
                    # For custom icons, we need to determine if they represent folder-like silhouettes
                    # Since we can't know for sure, we'll check if the pattern matches any known folder icons
                    # that have folder silhouettes
                    pattern_lower = pattern.lower()
                    if pattern_lower in FOLDER_ICONS_WITH_FOLDER_SILHOUETTE:
                        # Keep original custom color
                        return [custom_icon["icon"], custom_icon["color"]]
                    else:
                        # Use default folder color
                        default_color = ICONS["folder"]["default"][1]
                        return [custom_icon["icon"], default_color]
                else:
                    return [custom_icon["icon"], custom_icon["color"]]

    # Check for special folder types
    if folder_name in FOLDER_MAP:
        icon_key = FOLDER_MAP[folder_name]
        icon_info = ICONS["folder"].get(icon_key, ICONS["folder"]["default"])

        # Check if we should preserve folder color for non-folder-silhouette icons
        preserve_folder_color = config.get("icons", {}).get(
            "preserve_folder_color_for_non_folder_icons", False
        )

        if (
            preserve_folder_color
            and icon_key not in FOLDER_ICONS_WITH_FOLDER_SILHOUETTE
        ):
            # Use the icon from the themed folder but with default folder color
            default_color = ICONS["folder"]["default"][1]
            return [icon_info[0], default_color]
        else:
            # Use the original themed icon and color
            return icon_info
    else:
        return ICONS["folder"]["default"]


@lru_cache(maxsize=128)
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


@lru_cache(maxsize=128)
def get_toggle_button_icon(key: str) -> str:
    if not config["interface"]["nerd_font"]:
        return ASCII_TOGGLE_BUTTON_ICONS[key]
    else:
        return TOGGLE_BUTTON_ICONS[key]
