from typing import Any, Literal, Required, TypedDict, Union

class RovrConfig(TypedDict, total=False):
    r"""Rovr Config."""

    interface: "_RovrConfigInterface"
    r""" Settings related to the user interface and experience """

    settings: "_RovrConfigSettings"
    r""" Settings related to behavior of file operations """

    metadata: "_RovrConfigMetadata"
    icons: "_RovrConfigIcons"
    r""" Custom icon configurations for files and folders """

    theme: "_RovrConfigTheme"
    keybinds: "_RovrConfigKeybinds"
    plugins: "_RovrConfigPlugins"

_OPENER_ONEOF1_ORPHAN_DEFAULT = True
r""" Default value of the field path 'opener oneof1 orphan' """

_OPENER_ONEOF1_SHELL_DEFAULT = True
r""" Default value of the field path 'opener oneof1 shell' """

_Opener = Union[str, "_OpenerOneof1"]
r""" Aggregation type: oneOf """

class _OpenerIf(TypedDict, total=False):
    cwd: list[str]
    r""" Only use this opener if the current working directory matches one (or more) of the glob patterns in this list (look at https://docs.python.org/3/library/fnmatch.html for more info) """

    os: "_OsIf"
    r""" Only use this setting if the operating system is one of the following (case insensitive) """

    directory: bool
    r""" Only use this opener if the selected item is a directory (set to true) or a file (set to false) (if unspecified, matches both files and directories) """

_OpenerOneof1 = TypedDict(
    "_OpenerOneof1",
    {
        # | Aggregation type: oneOf
        # |
        # | Required property
        "run": Required["_Run"],
        "if": "_OpenerIf",
        # | Whether to open the opener as an orphan process.
        # |
        # | default: True
        "orphan": bool,
        # | The name of the opener to show in the menu (currently unused)
        "name": str,
        # | Whether the command to run is a shell command that needs to be run in a shell (required if you want to do piping)
        # |
        # | default: True
        "shell": bool,
    },
    total=False,
)

_OsIf = list["_OsIfItem"]
r""" Only use this setting if the operating system is one of the following (case insensitive) """

_OsIfItem = Union["_OsIfItemAnyof0", str]
r""" Aggregation type: anyOf """

_OsIfItemAnyof0 = Literal["Windows"] | Literal["Linux"] | Literal["Darwin"]
_OSIFITEMANYOF0_WINDOWS: Literal["Windows"] = "Windows"
r"""The values for the '_OsIfItemAnyof0' enum"""
_OSIFITEMANYOF0_LINUX: Literal["Linux"] = "Linux"
r"""The values for the '_OsIfItemAnyof0' enum"""
_OSIFITEMANYOF0_DARWIN: Literal["Darwin"] = "Darwin"
r"""The values for the '_OsIfItemAnyof0' enum"""

_RIGHT_CLICK_ACTION_ONEOF1_SHELL_DEFAULT = False
r""" Default value of the field path 'right_click_action oneof1 shell' """

_ROVR_CONFIG_ICONS_FILES_DEFAULT: list[Any] = []
r""" Default value of the field path 'Rovr Config icons files' """

_ROVR_CONFIG_ICONS_FOLDERS_DEFAULT: list[Any] = []
r""" Default value of the field path 'Rovr Config icons folders' """

_ROVR_CONFIG_INTERFACE_ALLOW_TAB_NAV_DEFAULT = False
r""" Default value of the field path 'Rovr Config interface allow_tab_nav' """

_ROVR_CONFIG_INTERFACE_APPEND_NEW_TABS_DEFAULT = True
r""" Default value of the field path 'Rovr Config interface append_new_tabs' """

_ROVR_CONFIG_INTERFACE_CLOCK_ALIGN_DEFAULT = "right"
r""" Default value of the field path 'Rovr Config interface clock align' """

_ROVR_CONFIG_INTERFACE_CLOCK_ENABLED_DEFAULT = True
r""" Default value of the field path 'Rovr Config interface clock enabled' """

_ROVR_CONFIG_INTERFACE_COMPACT_MODE_BUTTONS_DEFAULT = True
r""" Default value of the field path 'Rovr Config interface compact_mode buttons' """

_ROVR_CONFIG_INTERFACE_COMPACT_MODE_PANELS_DEFAULT = False
r""" Default value of the field path 'Rovr Config interface compact_mode panels' """

_ROVR_CONFIG_INTERFACE_DOUBLE_CLICK_DELAY_DEFAULT = 0.25
r""" Default value of the field path 'Rovr Config interface double_click_delay' """

_ROVR_CONFIG_INTERFACE_DRIVE_WATCHER_FREQUENCY_DEFAULT = 3.0
r""" Default value of the field path 'Rovr Config interface drive_watcher_frequency' """

_ROVR_CONFIG_INTERFACE_FONT_PREVIEW_FONT_SIZE_DEFAULT = 40
r""" Default value of the field path 'Rovr Config interface font_preview font_size' """

_ROVR_CONFIG_INTERFACE_FONT_PREVIEW_MAX_SIZE_DEFAULT = [1000, 1000]
r""" Default value of the field path 'Rovr Config interface font_preview max_size' """

_ROVR_CONFIG_INTERFACE_IMAGE_VIEWER_MAX_SIZE_DEFAULT = [4000, 4000]
r""" Default value of the field path 'Rovr Config interface image_viewer max_size' """

_ROVR_CONFIG_INTERFACE_IMAGE_VIEWER_PROTOCOL_DEFAULT = "Auto"
r""" Default value of the field path 'Rovr Config interface image_viewer protocol' """

_ROVR_CONFIG_INTERFACE_IMAGE_VIEWER_RESAMPLING_DEFAULT = "nearest"
r""" Default value of the field path 'Rovr Config interface image_viewer resampling' """

_ROVR_CONFIG_INTERFACE_NERD_FONT_DEFAULT = False
r""" Default value of the field path 'Rovr Config interface nerd_font' """

_ROVR_CONFIG_INTERFACE_PREVIEW_TEXT_ERROR_DEFAULT = "couldn't read this file! (¬_¬ )"
r""" Default value of the field path 'Rovr Config interface preview_text error' """

_ROVR_CONFIG_INTERFACE_PREVIEW_TEXT_FONT_TEXT_DEFAULT = "abcdefghijklmnopqrstuvwxyz\nABCDEFGHIJKLMNOPQRSTUVWXYZ\noO08 iIlL1 g9qCQG a@ 5sS\n{} [==>  ] (*) <> ~-+ /\\\n"
r""" Default value of the field path 'Rovr Config interface preview_text font_text' """

_ROVR_CONFIG_INTERFACE_PREVIEW_TEXT_START_DEFAULT = (
    " ___ ___\n|  _| . |\n|_| |___|\n _ _ ___\n| | |  _|\n \\_/|_|\n"
)
r""" Default value of the field path 'Rovr Config interface preview_text start' """

_ROVR_CONFIG_INTERFACE_SCROLLOFF_DEFAULT = 3
r""" Default value of the field path 'Rovr Config interface scrolloff' """

_ROVR_CONFIG_INTERFACE_SHOW_HIDDEN_FILES_DEFAULT = False
r""" Default value of the field path 'Rovr Config interface show_hidden_files' """

_ROVR_CONFIG_INTERFACE_SHOW_LINE_NUMBERS_DEFAULT = False
r""" Default value of the field path 'Rovr Config interface show_line_numbers' """

_ROVR_CONFIG_INTERFACE_SHOW_PROGRESS_ETA_DEFAULT = False
r""" Default value of the field path 'Rovr Config interface show_progress_eta' """

_ROVR_CONFIG_INTERFACE_SHOW_PROGRESS_PERCENTAGE_DEFAULT = False
r""" Default value of the field path 'Rovr Config interface show_progress_percentage' """

_ROVR_CONFIG_INTERFACE_TOOLTIPS_DEFAULT = True
r""" Default value of the field path 'Rovr Config interface tooltips' """

_ROVR_CONFIG_INTERFACE_TRUNCATE_PROGRESS_FILE_PATH_DEFAULT = False
r""" Default value of the field path 'Rovr Config interface truncate_progress_file_path' """

_ROVR_CONFIG_INTERFACE_USE_REACTIVE_LAYOUT_DEFAULT = True
r""" Default value of the field path 'Rovr Config interface use_reactive_layout' """

_ROVR_CONFIG_METADATA_DATETIME_FORMAT_DEFAULT = "%Y-%m-%d %H:%M"
r""" Default value of the field path 'Rovr Config metadata datetime_format' """

_ROVR_CONFIG_METADATA_FIELDS_DEFAULT = [
    "type",
    "permissions",
    "size",
    "modified",
    "accessed",
    "created",
    "hidden",
    "mime",
]
r""" Default value of the field path 'Rovr Config metadata fields' """

_ROVR_CONFIG_METADATA_FILESIZE_DECIMALS_DEFAULT = 1
r""" Default value of the field path 'Rovr Config metadata filesize_decimals' """

_ROVR_CONFIG_METADATA_FILESIZE_SUFFIX_DEFAULT = "decimal"
r""" Default value of the field path 'Rovr Config metadata filesize_suffix' """

_ROVR_CONFIG_PLUGINS_BAT_ENABLED_DEFAULT = False
r""" Default value of the field path 'Rovr Config plugins bat enabled' """

_ROVR_CONFIG_PLUGINS_BAT_EXECUTABLE_DEFAULT = "bat"
r""" Default value of the field path 'Rovr Config plugins bat executable' """

_ROVR_CONFIG_PLUGINS_FD_DEFAULT_FILTER_TYPES_DEFAULT = ["file", "directory"]
r""" Default value of the field path 'Rovr Config plugins fd default_filter_types' """

_ROVR_CONFIG_PLUGINS_FD_ENABLED_DEFAULT = True
r""" Default value of the field path 'Rovr Config plugins fd enabled' """

_ROVR_CONFIG_PLUGINS_FD_EXECUTABLE_DEFAULT = "fd"
r""" Default value of the field path 'Rovr Config plugins fd executable' """

_ROVR_CONFIG_PLUGINS_FD_FOLLOW_SYMLINKS_DEFAULT = False
r""" Default value of the field path 'Rovr Config plugins fd follow_symlinks' """

_ROVR_CONFIG_PLUGINS_FD_KEYBINDS_DEFAULT = ["f"]
r""" Default value of the field path 'Rovr Config plugins fd keybinds' """

_ROVR_CONFIG_PLUGINS_FD_NO_IGNORE_PARENT_DEFAULT = False
r""" Default value of the field path 'Rovr Config plugins fd no_ignore_parent' """

_ROVR_CONFIG_PLUGINS_FD_RELATIVE_PATHS_DEFAULT = True
r""" Default value of the field path 'Rovr Config plugins fd relative_paths' """

_ROVR_CONFIG_PLUGINS_FD_SEARCH_HIDDEN_DEFAULT = False
r""" Default value of the field path 'Rovr Config plugins fd search_hidden' """

_ROVR_CONFIG_PLUGINS_FD_TIMEOUT_DEFAULT = 15
r""" Default value of the field path 'Rovr Config plugins fd timeout' """

_ROVR_CONFIG_PLUGINS_FILE_ONE_ENABLED_DEFAULT = False
r""" Default value of the field path 'Rovr Config plugins file_one enabled' """

_ROVR_CONFIG_PLUGINS_FILE_ONE_GET_DESCRIPTION_DEFAULT = True
r""" Default value of the field path 'Rovr Config plugins file_one get_description' """

_ROVR_CONFIG_PLUGINS_POPPLER_ENABLED_DEFAULT = True
r""" Default value of the field path 'Rovr Config plugins poppler enabled' """

_ROVR_CONFIG_PLUGINS_POPPLER_PDF_BATCH_SIZE_DEFAULT = 2
r""" Default value of the field path 'Rovr Config plugins poppler pdf_batch_size' """

_ROVR_CONFIG_PLUGINS_POPPLER_POPPLER_FOLDER_DEFAULT = "PATH"
r""" Default value of the field path 'Rovr Config plugins poppler poppler_folder' """

_ROVR_CONFIG_PLUGINS_POPPLER_THREADS_DEFAULT = 1
r""" Default value of the field path 'Rovr Config plugins poppler threads' """

_ROVR_CONFIG_PLUGINS_POPPLER_USE_PDFTOCAIRO_DEFAULT = False
r""" Default value of the field path 'Rovr Config plugins poppler use_pdftocairo' """

_ROVR_CONFIG_PLUGINS_RG_CASE_SENSITIVE_DEFAULT = True
r""" Default value of the field path 'Rovr Config plugins rg case_sensitive' """

_ROVR_CONFIG_PLUGINS_RG_ENABLED_DEFAULT = True
r""" Default value of the field path 'Rovr Config plugins rg enabled' """

_ROVR_CONFIG_PLUGINS_RG_EXECUTABLE_DEFAULT = "rg"
r""" Default value of the field path 'Rovr Config plugins rg executable' """

_ROVR_CONFIG_PLUGINS_RG_FOLLOW_SYMLINKS_DEFAULT = False
r""" Default value of the field path 'Rovr Config plugins rg follow_symlinks' """

_ROVR_CONFIG_PLUGINS_RG_KEYBINDS_DEFAULT = ["R"]
r""" Default value of the field path 'Rovr Config plugins rg keybinds' """

_ROVR_CONFIG_PLUGINS_RG_NO_IGNORE_PARENT_DEFAULT = False
r""" Default value of the field path 'Rovr Config plugins rg no_ignore_parent' """

_ROVR_CONFIG_PLUGINS_RG_SEARCH_HIDDEN_DEFAULT = False
r""" Default value of the field path 'Rovr Config plugins rg search_hidden' """

_ROVR_CONFIG_PLUGINS_RG_TIMEOUT_DEFAULT = 60
r""" Default value of the field path 'Rovr Config plugins rg timeout' """

_ROVR_CONFIG_PLUGINS_ZOXIDE_ENABLED_DEFAULT = True
r""" Default value of the field path 'Rovr Config plugins zoxide enabled' """

_ROVR_CONFIG_PLUGINS_ZOXIDE_KEYBINDS_DEFAULT = ["z"]
r""" Default value of the field path 'Rovr Config plugins zoxide keybinds' """

_ROVR_CONFIG_PLUGINS_ZOXIDE_SHOW_SCORES_DEFAULT = False
r""" Default value of the field path 'Rovr Config plugins zoxide show_scores' """

_ROVR_CONFIG_SETTINGS_COPY_INCLUDES_METADATA_DEFAULT = True
r""" Default value of the field path 'Rovr Config settings copy_includes_metadata' """

_ROVR_CONFIG_SETTINGS_DRIVE_EXCLUDE_DEFAULT: list[Any] = []
r""" Default value of the field path 'Rovr Config settings drive_exclude' """

_ROVR_CONFIG_SETTINGS_EDITOR_BULK_EDITOR_RENAME_SHOW_AS_MAPPING_DEFAULT = True
r""" Default value of the field path 'Rovr Config settings editor bulk_editor rename_show_as_mapping' """

_ROVR_CONFIG_SETTINGS_EDITOR_BULK_EDITOR_RUN_DEFAULT = "$EDITOR"
r""" Default value of the field path 'Rovr Config settings editor bulk_editor run' """

_ROVR_CONFIG_SETTINGS_EDITOR_BULK_EDITOR_SHELL_DEFAULT = False
r""" Default value of the field path 'Rovr Config settings editor bulk_editor shell' """

_ROVR_CONFIG_SETTINGS_EDITOR_FILE_ORPHAN_DEFAULT = True
r""" Default value of the field path 'Rovr Config settings editor file orphan' """

_ROVR_CONFIG_SETTINGS_EDITOR_FILE_RUN_DEFAULT = "$EDITOR"
r""" Default value of the field path 'Rovr Config settings editor file run' """

_ROVR_CONFIG_SETTINGS_EDITOR_FILE_SHELL_DEFAULT = False
r""" Default value of the field path 'Rovr Config settings editor file shell' """

_ROVR_CONFIG_SETTINGS_EDITOR_FOLDER_ORPHAN_DEFAULT = True
r""" Default value of the field path 'Rovr Config settings editor folder orphan' """

_ROVR_CONFIG_SETTINGS_EDITOR_FOLDER_RUN_DEFAULT = "$EDITOR"
r""" Default value of the field path 'Rovr Config settings editor folder run' """

_ROVR_CONFIG_SETTINGS_EDITOR_FOLDER_SHELL_DEFAULT = False
r""" Default value of the field path 'Rovr Config settings editor folder shell' """

_ROVR_CONFIG_SETTINGS_PREVIEW_RULES_DEFAULT = {
    "text/.*": "text",
    "application/(json|javascript|xml|raml\\+yaml)": "text",
    "application/x-(yaml|script|pem-file|subrip|typescript)": "text",
    "application/(mbox|ndjson|wine-extension-ini)": "text",
    "image/svg\\+xml": "resvg",
    "image/(avif|hei.|jxl)": "image",
    "image/.*": "image",
    "application/pdf": "pdf",
    "application/(zip|gzip|zstd|bzip2|vnd\\.rar)": "archive",
    "application/x-(xz|x-tar|x-gzip|x-bzip2|x-xz|x-rar|x-rar-compressed|x-7z-compressed)": "archive",
    "application/(rar|7z.*|tar|xz|bzip.*|lzma|compress|archive|cpio|arj|xar|ms-cab.*)": "archive",
    "application/(iso9660-image|qemu-disk|ms-wim|apple-diskimage)": "archive",
    "application/virtualbox-(vhd|vhdx)": "archive",
    "application/(debian.*-package|redhat-package-manager|rpm|android\\.package-archive)": "archive",
    "inode/directory": "folder",
    "font/.*": "font",
    "application/ms-opentype": "font",
    "application/font-.*": "font",
    "application/x-font-.*": "font",
}
r""" Default value of the field path 'Rovr Config settings preview_rules' """

_ROVR_CONFIG_SETTINGS_USE_RECYCLE_BIN_DEFAULT = True
r""" Default value of the field path 'Rovr Config settings use_recycle_bin' """

_ROVR_CONFIG_THEME_DEFAULT_DEFAULT = "nord"
r""" Default value of the field path 'Rovr Config theme default' """

_ROVR_CONFIG_THEME_PREVIEW_DEFAULT = "nord"
r""" Default value of the field path 'Rovr Config theme preview' """

_ROVR_CONFIG_THEME_TRANSPARENT_DEFAULT = False
r""" Default value of the field path 'Rovr Config theme transparent' """

_RightClickAction = Union["_RightClickActionOneof0", "_RightClickActionOneof1"]
r""" Aggregation type: oneOf """

_RightClickActionOneof0 = (
    Literal["rovr:copy"]
    | Literal["rovr:cut"]
    | Literal["rovr:paste"]
    | Literal["rovr:new"]
    | Literal["rovr:rename"]
    | Literal["rovr:delete"]
    | Literal["rovr:zip"]
    | Literal["rovr:unzip"]
    | Literal["system:copy_highlighted"]
    | Literal["system:copy_current_directory"]
    | Literal["system:copy_to_system_clip"]
)
_RIGHTCLICKACTIONONEOF0_ROVR_COLON_COPY: Literal["rovr:copy"] = "rovr:copy"
r"""The values for the '_RightClickActionOneof0' enum"""
_RIGHTCLICKACTIONONEOF0_ROVR_COLON_CUT: Literal["rovr:cut"] = "rovr:cut"
r"""The values for the '_RightClickActionOneof0' enum"""
_RIGHTCLICKACTIONONEOF0_ROVR_COLON_PASTE: Literal["rovr:paste"] = "rovr:paste"
r"""The values for the '_RightClickActionOneof0' enum"""
_RIGHTCLICKACTIONONEOF0_ROVR_COLON_NEW: Literal["rovr:new"] = "rovr:new"
r"""The values for the '_RightClickActionOneof0' enum"""
_RIGHTCLICKACTIONONEOF0_ROVR_COLON_RENAME: Literal["rovr:rename"] = "rovr:rename"
r"""The values for the '_RightClickActionOneof0' enum"""
_RIGHTCLICKACTIONONEOF0_ROVR_COLON_DELETE: Literal["rovr:delete"] = "rovr:delete"
r"""The values for the '_RightClickActionOneof0' enum"""
_RIGHTCLICKACTIONONEOF0_ROVR_COLON_ZIP: Literal["rovr:zip"] = "rovr:zip"
r"""The values for the '_RightClickActionOneof0' enum"""
_RIGHTCLICKACTIONONEOF0_ROVR_COLON_UNZIP: Literal["rovr:unzip"] = "rovr:unzip"
r"""The values for the '_RightClickActionOneof0' enum"""
_RIGHTCLICKACTIONONEOF0_SYSTEM_COLON_COPY_HIGHLIGHTED: Literal[
    "system:copy_highlighted"
] = "system:copy_highlighted"
r"""The values for the '_RightClickActionOneof0' enum"""
_RIGHTCLICKACTIONONEOF0_SYSTEM_COLON_COPY_CURRENT_DIRECTORY: Literal[
    "system:copy_current_directory"
] = "system:copy_current_directory"
r"""The values for the '_RightClickActionOneof0' enum"""
_RIGHTCLICKACTIONONEOF0_SYSTEM_COLON_COPY_TO_SYSTEM_CLIP: Literal[
    "system:copy_to_system_clip"
] = "system:copy_to_system_clip"
r"""The values for the '_RightClickActionOneof0' enum"""

class _RightClickActionOneof1(TypedDict, total=False):
    run: Required["_Run"]
    r"""
    Aggregation type: oneOf

    Required property
    """

    run_type: Required["_RightClickActionOneof1RunType"]
    r"""
    The way to run the command. `suspend` will suspend rovr until the command is finished, `background` will run the command in the background without suspending rovr, and `orphan` will run the command as an orphan process detached from rovr.

    Required property
    """

    shell: bool
    r"""
    Whether the command to run is a shell command that needs to be run in a shell (required if you want to do piping)

    default: False
    """

_RightClickActionOneof1RunType = (
    Literal["suspend"] | Literal["background"] | Literal["orphan"]
)
r""" The way to run the command. `suspend` will suspend rovr until the command is finished, `background` will run the command in the background without suspending rovr, and `orphan` will run the command as an orphan process detached from rovr. """
_RIGHTCLICKACTIONONEOF1RUNTYPE_SUSPEND: Literal["suspend"] = "suspend"
r"""The values for the 'The way to run the command. `suspend` will suspend rovr until the command is finished, `background` will run the command in the background without suspending rovr, and `orphan` will run the command as an orphan process detached from rovr' enum"""
_RIGHTCLICKACTIONONEOF1RUNTYPE_BACKGROUND: Literal["background"] = "background"
r"""The values for the 'The way to run the command. `suspend` will suspend rovr until the command is finished, `background` will run the command in the background without suspending rovr, and `orphan` will run the command as an orphan process detached from rovr' enum"""
_RIGHTCLICKACTIONONEOF1RUNTYPE_ORPHAN: Literal["orphan"] = "orphan"
r"""The values for the 'The way to run the command. `suspend` will suspend rovr until the command is finished, `background` will run the command in the background without suspending rovr, and `orphan` will run the command as an orphan process detached from rovr' enum"""

class _RightClickIf(TypedDict, total=False):
    path: list[str]
    r""" Only enable this menu item if the path matches one (or more) of the glob patterns in this list (look at https://docs.python.org/3/library/fnmatch.html for more info) """

    os: list["_RightClickIfOsItem"]
    r""" Only enable this menu item if the operating system is one of the following (case insensitive) """

    cwd: list[str]
    r""" Only enable this menu item if the current working directory matches one (or more) of the glob patterns in this list (look at https://docs.python.org/3/library/fnmatch.html for more info) """

    directory: bool
    r""" Only enable this menu item if the selected item is a directory (set to true) or a file (set to false) (if unspecified, matches both files and directories) """

_RightClickIfOsItem = Union["_RightClickIfOsItemAnyof0", str]
r""" Aggregation type: anyOf """

_RightClickIfOsItemAnyof0 = Literal["Windows"] | Literal["Linux"] | Literal["Darwin"]
_RIGHTCLICKIFOSITEMANYOF0_WINDOWS: Literal["Windows"] = "Windows"
r"""The values for the '_RightClickIfOsItemAnyof0' enum"""
_RIGHTCLICKIFOSITEMANYOF0_LINUX: Literal["Linux"] = "Linux"
r"""The values for the '_RightClickIfOsItemAnyof0' enum"""
_RIGHTCLICKIFOSITEMANYOF0_DARWIN: Literal["Darwin"] = "Darwin"
r"""The values for the '_RightClickIfOsItemAnyof0' enum"""

# | oneOf:
# |   - required:
# |     - label
# |     - action
# |   - required:
# |     - label
# |     - options
_RightClickItem = TypedDict(
    "_RightClickItem",
    {
        # | Label to show in the context menu for this item
        "label": str,
        # | Aggregation type: oneOf
        "action": "_RightClickAction",
        "if": "_RightClickIf",
        # | Submenu items (only supported at the top level)
        "options": list["_RightClickItemOptionsItem"],
    },
    total=False,
)

_RightClickItemOptionsItem = TypedDict(
    "_RightClickItemOptionsItem",
    {
        # | Label to show in the context menu for this submenu item
        # |
        # | Required property
        "label": Required[str],
        # | Aggregation type: oneOf
        # |
        # | Required property
        "action": Required["_RightClickAction"],
        "if": "_RightClickIf",
    },
    total=False,
)

class _RovrConfigIcons(TypedDict, total=False):
    r"""Custom icon configurations for files and folders"""

    files: list["_RovrConfigIconsFilesItem"]
    r"""
    Custom file icon mappings. Earlier entries have higher priority.

    default:
      []
    """

    folders: list["_RovrConfigIconsFoldersItem"]
    r"""
    Custom folder icon mappings. Earlier entries have higher priority.

    default:
      []
    """

class _RovrConfigIconsFilesItem(TypedDict, total=False):
    pattern: Required[str]
    r"""
    The glob pattern to match against the file name (e.g., '*.py', 'LICENSE').
    Both the filename and glob will be forced to lowercase!

    Required property
    """

    icon: Required[str]
    r"""
    The icon character to use.

    Required property
    """

    color: Required[str]
    r"""
    The color for the icon. Can be a named color or hex code.

    Required property
    """

class _RovrConfigIconsFoldersItem(TypedDict, total=False):
    pattern: Required[str]
    r"""
    The glob pattern to match against the folder name (e.g., 'src', '.*').
    Both the folder name and glob will be forced to lowercase!

    Required property
    """

    icon: Required[str]
    r"""
    The icon character to use (should be a nerd font character)

    Required property
    """

    color: Required[str]
    r"""
    The color for the icon. Can be a named color or hex code

    Required property
    """

class _RovrConfigInterface(TypedDict, total=False):
    r"""Settings related to the user interface and experience"""

    tooltips: bool
    r"""
    Show tooltips when your mouse is over a tooltip supported button.
    This is not hot reloaded.

    default: True
    """

    nerd_font: bool
    r"""
    Use nerd font for rendering icons instead of weird characters and stuff.
    Not properly hot-reloaded.

    default: False
    """

    use_reactive_layout: bool
    r"""
    Hide certain elements based on the width and height of the terminal.

    default: True
    """

    show_progress_eta: bool
    r"""
    When copying or deleting files, show an ETA for when the action will be completed.

    default: False
    """

    show_progress_percentage: bool
    r"""
    When copying or deleting files, show a percentage of how much had been completed.

    default: False
    """

    truncate_progress_file_path: bool
    r"""
    When the process container is using file paths, truncate the file path to only view the first and last names of the path.

    default: False
    """

    show_line_numbers: bool
    r"""
    Add line numbers to the left gutter if you are viewing a text file.

    default: False
    """

    scrolloff: int
    r"""
    The number of files to keep above and below the cursor when moving through the file list.

    minimum: 0
    default: 3
    """

    show_hidden_files: bool
    r"""
    Show hidden files and folders (those starting with a dot on Unix, or explicitly hidden on Windows/MacOS).

    default: False
    """

    image_viewer: "_RovrConfigInterfaceImageViewer"
    r""" Settings related to the image viewer used in the preview sidebar """

    font_preview: "_RovrConfigInterfaceFontPreview"
    r""" Settings related to the font preview used in the preview sidebar """

    allow_tab_nav: bool
    r"""
    Allow navigating the main app screen with `tab` and `shift+tab`

    default: False
    """

    append_new_tabs: bool
    r"""
    Choose whether or not to append new tabs instead of inserting them.
    `true` => Append to the end of the tab list.
    `false` => Insert after the active tab.

    default: True
    """

    double_click_delay: int | float
    r"""
    The delay between two consecutive clicks to enter into a directory, or open a file.

    default: 0.25
    """

    drive_watcher_frequency: int | float
    r"""
    How often (in seconds) to check for changes in mounted drives in the sidebar.

    default: 3.0
    """

    clock: "_RovrConfigInterfaceClock"
    preview_text: "_RovrConfigInterfacePreviewText"
    compact_mode: "_RovrConfigInterfaceCompactMode"

class _RovrConfigInterfaceClock(TypedDict, total=False):
    enabled: bool
    r"""
    Show a clock in the tabs bar.

    default: True
    """

    align: "_RovrConfigInterfaceClockAlign"
    r"""
    Align the clock to either the 'right' or 'left' of the tabs bar.

    default: right
    """

_RovrConfigInterfaceClockAlign = Literal["left"] | Literal["right"]
r"""
Align the clock to either the 'right' or 'left' of the tabs bar.

default: right
"""
_ROVRCONFIGINTERFACECLOCKALIGN_LEFT: Literal["left"] = "left"
r"""The values for the 'Align the clock to either the 'right' or 'left' of the tabs bar' enum"""
_ROVRCONFIGINTERFACECLOCKALIGN_RIGHT: Literal["right"] = "right"
r"""The values for the 'Align the clock to either the 'right' or 'left' of the tabs bar' enum"""

class _RovrConfigInterfaceCompactMode(TypedDict, total=False):
    buttons: bool
    r"""
    Whether to compact the buttons and path input to one line instead of three.

    default: True
    """

    panels: bool
    r"""
    Whether to make the panels smaller to add more room for the file list itself

    default: False
    """

class _RovrConfigInterfaceFontPreview(TypedDict, total=False):
    r"""Settings related to the font preview used in the preview sidebar"""

    max_size: list["_RovrConfigInterfaceFontPreviewMaxSizeItem"]
    r"""
    The maximum size for the font preview. If the rendered font preview exceeds this size, it will be scaled down to fit within these dimensions while maintaining its aspect ratio.

    default:
      - 1000
      - 1000
    maxItems: 2
    minItems: 2
    """

    font_size: int
    r"""
    The font size to use when rendering font previews. This is only applicable when the font preview exceeds the maximum size specified in `max_size`.

    default: 40
    """

_RovrConfigInterfaceFontPreviewMaxSizeItem = int
r""" minimum: 1 """

class _RovrConfigInterfaceImageViewer(TypedDict, total=False):
    r"""Settings related to the image viewer used in the preview sidebar"""

    protocol: "_RovrConfigInterfaceImageViewerProtocol"
    r"""
    The image protocol to use when displaying an image

    default: Auto
    """

    max_size: list["_RovrConfigInterfaceImageViewerMaxSizeItem"]
    r"""
    The maximum size for the image viewer. If the image exceeds this size, it will be scaled down to fit within these dimensions while maintaining its aspect ratio.

    default:
      - 4000
      - 4000
    maxItems: 2
    minItems: 2
    """

    resampling: "_RovrConfigInterfaceImageViewerResampling"
    r"""
    The resampling method to use when resizing images. This is only applicable when the image exceeds the maximum size specified in `max_size`.

    default: nearest
    """

_RovrConfigInterfaceImageViewerMaxSizeItem = int
r""" minimum: 1 """

_RovrConfigInterfaceImageViewerProtocol = (
    Literal["Auto"]
    | Literal["TGP"]
    | Literal["Sixel"]
    | Literal["Halfcell"]
    | Literal["Unicode"]
)
r"""
The image protocol to use when displaying an image

default: Auto
"""
_ROVRCONFIGINTERFACEIMAGEVIEWERPROTOCOL_AUTO: Literal["Auto"] = "Auto"
r"""The values for the 'The image protocol to use when displaying an image' enum"""
_ROVRCONFIGINTERFACEIMAGEVIEWERPROTOCOL_TGP: Literal["TGP"] = "TGP"
r"""The values for the 'The image protocol to use when displaying an image' enum"""
_ROVRCONFIGINTERFACEIMAGEVIEWERPROTOCOL_SIXEL: Literal["Sixel"] = "Sixel"
r"""The values for the 'The image protocol to use when displaying an image' enum"""
_ROVRCONFIGINTERFACEIMAGEVIEWERPROTOCOL_HALFCELL: Literal["Halfcell"] = "Halfcell"
r"""The values for the 'The image protocol to use when displaying an image' enum"""
_ROVRCONFIGINTERFACEIMAGEVIEWERPROTOCOL_UNICODE: Literal["Unicode"] = "Unicode"
r"""The values for the 'The image protocol to use when displaying an image' enum"""

_RovrConfigInterfaceImageViewerResampling = (
    Literal["nearest"]
    | Literal["lanczos"]
    | Literal["bilinear"]
    | Literal["bicubic"]
    | Literal["box"]
    | Literal["hamming"]
)
r"""
The resampling method to use when resizing images. This is only applicable when the image exceeds the maximum size specified in `max_size`.

default: nearest
"""
_ROVRCONFIGINTERFACEIMAGEVIEWERRESAMPLING_NEAREST: Literal["nearest"] = "nearest"
r"""The values for the 'The resampling method to use when resizing images. This is only applicable when the image exceeds the maximum size specified in `max_size`' enum"""
_ROVRCONFIGINTERFACEIMAGEVIEWERRESAMPLING_LANCZOS: Literal["lanczos"] = "lanczos"
r"""The values for the 'The resampling method to use when resizing images. This is only applicable when the image exceeds the maximum size specified in `max_size`' enum"""
_ROVRCONFIGINTERFACEIMAGEVIEWERRESAMPLING_BILINEAR: Literal["bilinear"] = "bilinear"
r"""The values for the 'The resampling method to use when resizing images. This is only applicable when the image exceeds the maximum size specified in `max_size`' enum"""
_ROVRCONFIGINTERFACEIMAGEVIEWERRESAMPLING_BICUBIC: Literal["bicubic"] = "bicubic"
r"""The values for the 'The resampling method to use when resizing images. This is only applicable when the image exceeds the maximum size specified in `max_size`' enum"""
_ROVRCONFIGINTERFACEIMAGEVIEWERRESAMPLING_BOX: Literal["box"] = "box"
r"""The values for the 'The resampling method to use when resizing images. This is only applicable when the image exceeds the maximum size specified in `max_size`' enum"""
_ROVRCONFIGINTERFACEIMAGEVIEWERRESAMPLING_HAMMING: Literal["hamming"] = "hamming"
r"""The values for the 'The resampling method to use when resizing images. This is only applicable when the image exceeds the maximum size specified in `max_size`' enum"""

class _RovrConfigInterfacePreviewText(TypedDict, total=False):
    error: str
    r"""
    If for any reason the file preview refused to show, this appears.

    default: couldn't read this file! (¬_¬ )
    """

    start: str
    r"""
    This is shown when the rovr starts up. You may see it for a split second, but it will never appear afterwards. You cannot view this properly in this docs.

    default:  ___ ___
|  _| . |
|_| |___|
 _ _ ___
| | |  _|
 \_/|_|

    """

    font_text: str
    r"""
    When a font file is previewed, this text will be rendered in the font if possible.

    default: abcdefghijklmnopqrstuvwxyz
ABCDEFGHIJKLMNOPQRSTUVWXYZ
oO08 iIlL1 g9qCQG a@ 5sS
{} [==>  ] (*) <> ~-+ /\

    """

class _RovrConfigKeybinds(TypedDict, total=False):
    toggle_pin: list[str]
    toggle_pinned_sidebar: list[str]
    toggle_preview_sidebar: list[str]
    toggle_footer: list[str]
    toggle_menu_wrapper: list[str]
    focus_toggle_pinned_sidebar: list[str]
    focus_file_list: list[str]
    focus_toggle_preview_sidebar: list[str]
    focus_toggle_path_switcher: list[str]
    focus_toggle_processes: list[str]
    focus_toggle_clipboard: list[str]
    focus_toggle_metadata: list[str]
    focus_search: list[str]
    copy: list[str]
    paste: list[str]
    cut: list[str]
    delete: list[str]
    delete_files: "_RovrConfigKeybindsDeleteFiles"
    r""" Keybinds related to the delete confirmation screen """

    rename: list[str]
    new: list[str]
    bulk_create: list[str]
    toggle_all: list[str]
    zip: list[str]
    unzip: list[str]
    open_right_click_menu: list[str]
    extra_copy: "_RovrConfigKeybindsExtraCopy"
    r""" Keybinds related to extra copy options """

    up: list[str]
    down: list[str]
    up_tree: list[str]
    down_tree: list[str]
    bypass_up_tree: list[str]
    bypass_down_tree: list[str]
    page_up: list[str]
    page_down: list[str]
    home: list[str]
    end: list[str]
    hist_previous: list[str]
    hist_next: list[str]
    toggle_visual: list[str]
    toggle_hidden_files: list[str]
    toggle_select_item: list[str]
    select_up: list[str]
    select_down: list[str]
    select_page_up: list[str]
    select_page_down: list[str]
    select_home: list[str]
    select_end: list[str]
    tab_next: list[str]
    tab_previous: list[str]
    tab_new: list[str]
    tab_close: list[str]
    preview_scroll_left: list[str]
    preview_scroll_right: list[str]
    preview_select_right: list[str]
    preview_select_left: list[str]
    show_keybinds: list[str]
    change_sort_order: "_RovrConfigKeybindsChangeSortOrder"
    r""" Keybinds related to changing the sort order """

    quit_app: list[str]
    command_palette: str
    r"""
    Launch Textual's mildly useful command palette (only one keybind is allowed!)

    display_name: Launch command palette
    """

    suspend_process: list[str]
    open: list[str]
    open_editor: list[str]
    show_shell_screen: list[str]
    filename_conflict: "_RovrConfigKeybindsFilenameConflict"
    r""" Keybinds related to handling a conflict with two files of the same name """

    file_in_use: "_RovrConfigKeybindsFileInUse"
    r""" Keybinds related to handling a file that is in use by another process """

    filter_modal: "_RovrConfigKeybindsFilterModal"
    r""" Keybinds related to selecting options in a modal screen (like FileSearch or ZDToDirectory) """

    yes_or_no: "_RovrConfigKeybindsYesOrNo"
    r""" Keybinds related to yes/no confirmation modals """

    drag_and_drop: "_RovrConfigKeybindsDragAndDrop"
    r""" Keybinds related to the screen that appears after dropping a file """

class _RovrConfigKeybindsChangeSortOrder(TypedDict, total=False):
    r"""Keybinds related to changing the sort order"""

    open_popup: list[str]
    name: list[str]
    extension: list[str]
    natural: list[str]
    size: list[str]
    created: list[str]
    modified: list[str]
    descending: list[str]

class _RovrConfigKeybindsDeleteFiles(TypedDict, total=False):
    r"""Keybinds related to the delete confirmation screen"""

    trash: list[str]
    delete: list[str]
    cancel: list[str]

class _RovrConfigKeybindsDragAndDrop(TypedDict, total=False):
    r"""Keybinds related to the screen that appears after dropping a file"""

    move: list[str]
    copy: list[str]
    cancel: list[str]

class _RovrConfigKeybindsExtraCopy(TypedDict, total=False):
    r"""Keybinds related to extra copy options"""

    open_popup: list[str]
    copy_to_rovr: list[str]
    copy_highlighted: list[str]
    copy_to_system_clip: list[str]
    copy_current_directory: list[str]

class _RovrConfigKeybindsFileInUse(TypedDict, total=False):
    r"""Keybinds related to handling a file that is in use by another process"""

    retry: list[str]
    skip: list[str]
    cancel: list[str]
    dont_ask_again: list[str]

class _RovrConfigKeybindsFilenameConflict(TypedDict, total=False):
    r"""Keybinds related to handling a conflict with two files of the same name"""

    overwrite: list[str]
    skip: list[str]
    rename: list[str]
    cancel: list[str]
    dont_ask_again: list[str]

class _RovrConfigKeybindsFilterModal(TypedDict, total=False):
    r"""Keybinds related to selecting options in a modal screen (like FileSearch or ZDToDirectory)"""

    exit: list[str]
    down: list[str]
    up: list[str]
    page_down: list[str]
    page_up: list[str]

class _RovrConfigKeybindsYesOrNo(TypedDict, total=False):
    r"""Keybinds related to yes/no confirmation modals"""

    yes: list[str]
    no: list[str]
    dont_ask_again: list[str]

class _RovrConfigMetadata(TypedDict, total=False):
    fields: list["_RovrConfigMetadataFieldsItem"]
    r"""
    The order of the metadata tags that you want to see in the Metadata section.

    default:
      - type
      - permissions
      - size
      - modified
      - accessed
      - created
      - hidden
      - mime
    uniqueItems: True
    """

    datetime_format: str
    r"""
    The datetime format for Metadata. Refer to https://docs.python.org/3/library/datetime.html#format-codes for more information.

    default: %Y-%m-%d %H:%M
    """

    filesize_decimals: int
    r"""
    The number of decimals you want to see in the humanized file size

    default: 1
    minimum: 0
    """

    filesize_suffix: "_RovrConfigMetadataFilesizeSuffix"
    r"""
    The filesize suffix to follow.
    `decimal`: 1024 -> 1.024kB
    `binary`: 1024 -> 1KiB
    `gnu`: 1024 -> 1K

    default: decimal
    """

_RovrConfigMetadataFieldsItem = (
    Literal["type"]
    | Literal["permissions"]
    | Literal["size"]
    | Literal["modified"]
    | Literal["accessed"]
    | Literal["created"]
    | Literal["hidden"]
    | Literal["mime"]
)
_ROVRCONFIGMETADATAFIELDSITEM_TYPE: Literal["type"] = "type"
r"""The values for the '_RovrConfigMetadataFieldsItem' enum"""
_ROVRCONFIGMETADATAFIELDSITEM_PERMISSIONS: Literal["permissions"] = "permissions"
r"""The values for the '_RovrConfigMetadataFieldsItem' enum"""
_ROVRCONFIGMETADATAFIELDSITEM_SIZE: Literal["size"] = "size"
r"""The values for the '_RovrConfigMetadataFieldsItem' enum"""
_ROVRCONFIGMETADATAFIELDSITEM_MODIFIED: Literal["modified"] = "modified"
r"""The values for the '_RovrConfigMetadataFieldsItem' enum"""
_ROVRCONFIGMETADATAFIELDSITEM_ACCESSED: Literal["accessed"] = "accessed"
r"""The values for the '_RovrConfigMetadataFieldsItem' enum"""
_ROVRCONFIGMETADATAFIELDSITEM_CREATED: Literal["created"] = "created"
r"""The values for the '_RovrConfigMetadataFieldsItem' enum"""
_ROVRCONFIGMETADATAFIELDSITEM_HIDDEN: Literal["hidden"] = "hidden"
r"""The values for the '_RovrConfigMetadataFieldsItem' enum"""
_ROVRCONFIGMETADATAFIELDSITEM_MIME: Literal["mime"] = "mime"
r"""The values for the '_RovrConfigMetadataFieldsItem' enum"""

_RovrConfigMetadataFilesizeSuffix = (
    Literal["decimal"] | Literal["binary"] | Literal["gnu"]
)
r"""
The filesize suffix to follow.
`decimal`: 1024 -> 1.024kB
`binary`: 1024 -> 1KiB
`gnu`: 1024 -> 1K

default: decimal
"""
_ROVRCONFIGMETADATAFILESIZESUFFIX_DECIMAL: Literal["decimal"] = "decimal"
r"""The values for the 'The filesize suffix to follow' enum"""
_ROVRCONFIGMETADATAFILESIZESUFFIX_BINARY: Literal["binary"] = "binary"
r"""The values for the 'The filesize suffix to follow' enum"""
_ROVRCONFIGMETADATAFILESIZESUFFIX_GNU: Literal["gnu"] = "gnu"
r"""The values for the 'The filesize suffix to follow' enum"""

class _RovrConfigPlugins(TypedDict, total=False):
    zoxide: "_RovrConfigPluginsZoxide"
    bat: "_RovrConfigPluginsBat"
    fd: "_RovrConfigPluginsFd"
    rg: "_RovrConfigPluginsRg"
    poppler: "_RovrConfigPluginsPoppler"
    file_one: "_RovrConfigPluginsFileOne"

class _RovrConfigPluginsBat(TypedDict, total=False):
    enabled: bool
    r"""
    Enable or disable bat for previewing files.

    default: False
    """

    executable: str
    r"""
    The executable for bat.

    default: bat
    """

class _RovrConfigPluginsFd(TypedDict, total=False):
    enabled: bool
    r"""
    Enable recursive file search using fd.

    default: True
    """

    keybinds: list[str]
    executable: str
    r"""
    fd executable name or path.

    default: fd
    """

    relative_paths: bool
    r"""
    Whether to show fd results as relative path or absolute path.

    default: True
    """

    follow_symlinks: bool
    r"""
    Whether fd should follow symlinks when searching.

    default: False
    """

    no_ignore_parent: bool
    r"""
    Don't use *ignore files from parent folders when searching.

    default: False
    """

    search_hidden: bool
    r"""
    Whether to include hidden files in fd results by default.

    default: False
    """

    timeout: int
    r"""
    The maximum time (in seconds) to wait for fd to return results before giving up.

    default: 15
    """

    default_filter_types: list["_RovrConfigPluginsFdDefaultFilterTypesItem"]
    r"""
    The default file types to show when using fd.

    default:
      - file
      - directory
    uniqueItems: True
    """

_RovrConfigPluginsFdDefaultFilterTypesItem = (
    Literal["file"]
    | Literal["directory"]
    | Literal["symlink"]
    | Literal["executable"]
    | Literal["empty"]
    | Literal["socket"]
    | Literal["pipe"]
    | Literal["char-device"]
    | Literal["block-device"]
)
_ROVRCONFIGPLUGINSFDDEFAULTFILTERTYPESITEM_FILE: Literal["file"] = "file"
r"""The values for the '_RovrConfigPluginsFdDefaultFilterTypesItem' enum"""
_ROVRCONFIGPLUGINSFDDEFAULTFILTERTYPESITEM_DIRECTORY: Literal["directory"] = "directory"
r"""The values for the '_RovrConfigPluginsFdDefaultFilterTypesItem' enum"""
_ROVRCONFIGPLUGINSFDDEFAULTFILTERTYPESITEM_SYMLINK: Literal["symlink"] = "symlink"
r"""The values for the '_RovrConfigPluginsFdDefaultFilterTypesItem' enum"""
_ROVRCONFIGPLUGINSFDDEFAULTFILTERTYPESITEM_EXECUTABLE: Literal["executable"] = (
    "executable"
)
r"""The values for the '_RovrConfigPluginsFdDefaultFilterTypesItem' enum"""
_ROVRCONFIGPLUGINSFDDEFAULTFILTERTYPESITEM_EMPTY: Literal["empty"] = "empty"
r"""The values for the '_RovrConfigPluginsFdDefaultFilterTypesItem' enum"""
_ROVRCONFIGPLUGINSFDDEFAULTFILTERTYPESITEM_SOCKET: Literal["socket"] = "socket"
r"""The values for the '_RovrConfigPluginsFdDefaultFilterTypesItem' enum"""
_ROVRCONFIGPLUGINSFDDEFAULTFILTERTYPESITEM_PIPE: Literal["pipe"] = "pipe"
r"""The values for the '_RovrConfigPluginsFdDefaultFilterTypesItem' enum"""
_ROVRCONFIGPLUGINSFDDEFAULTFILTERTYPESITEM_CHAR_DEVICE: Literal["char-device"] = (
    "char-device"
)
r"""The values for the '_RovrConfigPluginsFdDefaultFilterTypesItem' enum"""
_ROVRCONFIGPLUGINSFDDEFAULTFILTERTYPESITEM_BLOCK_DEVICE: Literal["block-device"] = (
    "block-device"
)
r"""The values for the '_RovrConfigPluginsFdDefaultFilterTypesItem' enum"""

class _RovrConfigPluginsFileOne(TypedDict, total=False):
    enabled: bool
    r"""
    Enable secondary file(1) type detection if both puremagic and plaintext detection fails.

    default: False
    """

    get_description: bool
    r"""
    Use file(1) to get additional information of the file type.

    default: True
    """

class _RovrConfigPluginsPoppler(TypedDict, total=False):
    enabled: bool
    r"""
    Enable poppler for PDF previews.

    default: True
    """

    threads: int
    r"""
    How many threads should poppler use?

    default: 1
    minimum: 1
    """

    use_pdftocairo: bool
    r"""
    Use pdftocairo instead of pdftoppm, may help performance

    default: False
    """

    poppler_folder: str
    r"""
    Path to the folder where Poppler-related binaries are located. Leave empty to use the system PATH.

    default: PATH
    """

    pdf_batch_size: int
    r"""
    Number of PDF pages to load in each batch.

    default: 2
    minimum: 1
    """

class _RovrConfigPluginsRg(TypedDict, total=False):
    enabled: bool
    r"""
    Enable content searching using rg.

    default: True
    """

    keybinds: list[str]
    executable: str
    r"""
    rg executable name or path.

    default: rg
    """

    case_sensitive: bool
    r"""
    Whether the search should be case sensitive by default.

    default: True
    """

    follow_symlinks: bool
    r"""
    Whether rg should follow symlinks when searching.

    default: False
    """

    no_ignore_parent: bool
    r"""
    Don't use *ignore files from parent folders when searching.

    default: False
    """

    search_hidden: bool
    r"""
    Whether to search hidden files by default.

    default: False
    """

    timeout: int
    r"""
    The maximum time (in seconds) to wait for rg to return results before giving up.

    default: 60
    """

class _RovrConfigPluginsZoxide(TypedDict, total=False):
    enabled: bool
    r"""
    Enable or disable zoxide travelling.

    default: True
    """

    keybinds: list[str]
    show_scores: bool
    r"""
    Display zoxide frequency scores alongside directory paths.

    default: False
    """

class _RovrConfigSettings(TypedDict, total=False):
    r"""Settings related to behavior of file operations"""

    use_recycle_bin: bool
    r"""
    When deleting a file, allow moving the file to the recycle bin.

    default: True
    """

    right_click: list["_RightClickItem"]
    r""" Configuration for the right-click context menu. Fully replaces the default list. """

    copy_includes_metadata: bool
    r"""
    When copying over a file, preserve metadata from the original file, such as creation and modification times.

    default: True
    """

    editor: "_RovrConfigSettingsEditor"
    r""" Settings related to the editor used for different operations """

    preview_rules: dict[str, "_RovrConfigSettingsPreviewRulesAdditionalproperties"]
    r"""
    Map MIME type patterns to preview types. Uses regex patterns. Valid preview types: text, image, pdf, archive, folder, resvg, font, remime.
    -> Use 'remime' if you want a more accurate description from file(1)

    default:
      application/(debian.*-package|redhat-package-manager|rpm|android\.package-archive): archive
      application/(iso9660-image|qemu-disk|ms-wim|apple-diskimage): archive
      application/(json|javascript|xml|raml\+yaml): text
      application/(mbox|ndjson|wine-extension-ini): text
      application/(rar|7z.*|tar|xz|bzip.*|lzma|compress|archive|cpio|arj|xar|ms-cab.*): archive
      application/(zip|gzip|zstd|bzip2|vnd\.rar): archive
      application/font-.*: font
      application/ms-opentype: font
      application/pdf: pdf
      application/virtualbox-(vhd|vhdx): archive
      application/x-(xz|x-tar|x-gzip|x-bzip2|x-xz|x-rar|x-rar-compressed|x-7z-compressed): archive
      application/x-(yaml|script|pem-file|subrip|typescript): text
      application/x-font-.*: font
      font/.*: font
      image/(avif|hei.|jxl): image
      image/.*: image
      image/svg\+xml: resvg
      inode/directory: folder
      text/.*: text
    """

    openers: "_RovrConfigSettingsOpeners"
    r""" Openers to open files with, grouped by name and matched against file paths by glob pattern. """

    drive_exclude: list[str]
    r"""
    Glob patterns matched against mountpoint paths. Drives matching any pattern are hidden from the sidebar (e.g. '/run/media/*', 'D:/').

    default:
      []
    """

class _RovrConfigSettingsEditor(TypedDict, total=False):
    r"""Settings related to the editor used for different operations"""

    file: "_RovrConfigSettingsEditorFile"
    r""" Editor to use when opening a file """

    folder: "_RovrConfigSettingsEditorFolder"
    r""" Editor to use when opening a folder """

    bulk_editor: "_RovrConfigSettingsEditorBulkEditor"
    r""" Editor to use for bulk editing """

class _RovrConfigSettingsEditorBulkEditor(TypedDict, total=False):
    r"""Editor to use for bulk editing"""

    run: "_Run"
    r""" Aggregation type: oneOf """

    rename_show_as_mapping: bool
    r"""
    When doing a bulk rename, show as a mapping of `&lt;old&gt; ➔ &lt;new&gt;` instead of just showing only the new names

    default: True
    """

    shell: bool
    r"""
    Whether the command to run is a shell command that needs to be run in a shell (required if you want to do complicated things like piping in your editor command)

    default: False
    """

class _RovrConfigSettingsEditorFile(TypedDict, total=False):
    r"""Editor to use when opening a file"""

    run: Required["_Run"]
    r"""
    Aggregation type: oneOf

    Required property
    """

    orphan: Required[bool]
    r"""
    Whether to open the editor as an orphan process.

    default: True

    Required property
    """

    shell: bool
    r"""
    Whether the command to run is a shell command that needs to be run in a shell (required if you want to do complicated things like piping in your editor command)

    default: False
    """

class _RovrConfigSettingsEditorFolder(TypedDict, total=False):
    r"""Editor to use when opening a folder"""

    run: Required["_Run"]
    r"""
    Aggregation type: oneOf

    Required property
    """

    orphan: Required[bool]
    r"""
    Whether to open the editor as an orphan process.

    default: True

    Required property
    """

    shell: bool
    r"""
    Whether the command to run is a shell command that needs to be run in a shell (required if you want to do complicated things like piping in your editor command)

    default: False
    """

class _RovrConfigSettingsOpeners(TypedDict, total=False):
    r"""Openers to open files with, grouped by name and matched against file paths by glob pattern."""

    groups: dict[str, list["_Opener"]]
    r""" Named groups of openers. Each group is a list that can contain a mix of strings and objects, tried in order until one succeeds. Referenced by name from `match`. """

    match: dict[str, list[str]]
    r""" Map glob patterns (matched against the file's path) to one or more group names defined in `groups`. If multiple groups match, they are tried in order. """

_RovrConfigSettingsPreviewRulesAdditionalproperties = (
    Literal["text"]
    | Literal["image"]
    | Literal["pdf"]
    | Literal["archive"]
    | Literal["folder"]
    | Literal["remime"]
    | Literal["resvg"]
    | Literal["font"]
)
_ROVRCONFIGSETTINGSPREVIEWRULESADDITIONALPROPERTIES_TEXT: Literal["text"] = "text"
r"""The values for the '_RovrConfigSettingsPreviewRulesAdditionalproperties' enum"""
_ROVRCONFIGSETTINGSPREVIEWRULESADDITIONALPROPERTIES_IMAGE: Literal["image"] = "image"
r"""The values for the '_RovrConfigSettingsPreviewRulesAdditionalproperties' enum"""
_ROVRCONFIGSETTINGSPREVIEWRULESADDITIONALPROPERTIES_PDF: Literal["pdf"] = "pdf"
r"""The values for the '_RovrConfigSettingsPreviewRulesAdditionalproperties' enum"""
_ROVRCONFIGSETTINGSPREVIEWRULESADDITIONALPROPERTIES_ARCHIVE: Literal["archive"] = (
    "archive"
)
r"""The values for the '_RovrConfigSettingsPreviewRulesAdditionalproperties' enum"""
_ROVRCONFIGSETTINGSPREVIEWRULESADDITIONALPROPERTIES_FOLDER: Literal["folder"] = "folder"
r"""The values for the '_RovrConfigSettingsPreviewRulesAdditionalproperties' enum"""
_ROVRCONFIGSETTINGSPREVIEWRULESADDITIONALPROPERTIES_REMIME: Literal["remime"] = "remime"
r"""The values for the '_RovrConfigSettingsPreviewRulesAdditionalproperties' enum"""
_ROVRCONFIGSETTINGSPREVIEWRULESADDITIONALPROPERTIES_RESVG: Literal["resvg"] = "resvg"
r"""The values for the '_RovrConfigSettingsPreviewRulesAdditionalproperties' enum"""
_ROVRCONFIGSETTINGSPREVIEWRULESADDITIONALPROPERTIES_FONT: Literal["font"] = "font"
r"""The values for the '_RovrConfigSettingsPreviewRulesAdditionalproperties' enum"""

class _RovrConfigTheme(TypedDict, total=False):
    default: str
    r"""
    The default theme. Can be changed while in rovr, but it is not persistent.

    default: nord
    """

    preview: "_RovrConfigThemePreview"
    r"""
    The theme to use when previewing files in the preview sidebar.

    default: nord
    """

    transparent: bool
    r"""
    Use a transparent background.

    default: False
    """

_RovrConfigThemePreview = (
    Literal["abap"]
    | Literal["algol"]
    | Literal["algol_nu"]
    | Literal["arduino"]
    | Literal["autumn"]
    | Literal["bw"]
    | Literal["borland"]
    | Literal["coffee"]
    | Literal["colorful"]
    | Literal["default"]
    | Literal["dracula"]
    | Literal["emacs"]
    | Literal["friendly_grayscale"]
    | Literal["friendly"]
    | Literal["fruity"]
    | Literal["github-dark"]
    | Literal["gruvbox-dark"]
    | Literal["gruvbox-light"]
    | Literal["igor"]
    | Literal["inkpot"]
    | Literal["lightbulb"]
    | Literal["lilypond"]
    | Literal["lovelace"]
    | Literal["manni"]
    | Literal["material"]
    | Literal["monokai"]
    | Literal["murphy"]
    | Literal["native"]
    | Literal["nord-darker"]
    | Literal["nord"]
    | Literal["one-dark"]
    | Literal["paraiso-dark"]
    | Literal["paraiso-light"]
    | Literal["pastie"]
    | Literal["perldoc"]
    | Literal["rainbow_dash"]
    | Literal["rrt"]
    | Literal["sas"]
    | Literal["solarized-dark"]
    | Literal["solarized-light"]
    | Literal["staroffice"]
    | Literal["stata-dark"]
    | Literal["stata-light"]
    | Literal["tango"]
    | Literal["trac"]
    | Literal["vim"]
    | Literal["vs"]
    | Literal["xcode"]
    | Literal["zenburn"]
)
r"""
The theme to use when previewing files in the preview sidebar.

default: nord
"""
_ROVRCONFIGTHEMEPREVIEW_ABAP: Literal["abap"] = "abap"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_ALGOL: Literal["algol"] = "algol"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_ALGOL_NU: Literal["algol_nu"] = "algol_nu"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_ARDUINO: Literal["arduino"] = "arduino"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_AUTUMN: Literal["autumn"] = "autumn"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_BW: Literal["bw"] = "bw"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_BORLAND: Literal["borland"] = "borland"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_COFFEE: Literal["coffee"] = "coffee"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_COLORFUL: Literal["colorful"] = "colorful"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_DEFAULT: Literal["default"] = "default"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_DRACULA: Literal["dracula"] = "dracula"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_EMACS: Literal["emacs"] = "emacs"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_FRIENDLY_GRAYSCALE: Literal["friendly_grayscale"] = (
    "friendly_grayscale"
)
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_FRIENDLY: Literal["friendly"] = "friendly"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_FRUITY: Literal["fruity"] = "fruity"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_GITHUB_DARK: Literal["github-dark"] = "github-dark"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_GRUVBOX_DARK: Literal["gruvbox-dark"] = "gruvbox-dark"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_GRUVBOX_LIGHT: Literal["gruvbox-light"] = "gruvbox-light"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_IGOR: Literal["igor"] = "igor"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_INKPOT: Literal["inkpot"] = "inkpot"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_LIGHTBULB: Literal["lightbulb"] = "lightbulb"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_LILYPOND: Literal["lilypond"] = "lilypond"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_LOVELACE: Literal["lovelace"] = "lovelace"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_MANNI: Literal["manni"] = "manni"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_MATERIAL: Literal["material"] = "material"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_MONOKAI: Literal["monokai"] = "monokai"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_MURPHY: Literal["murphy"] = "murphy"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_NATIVE: Literal["native"] = "native"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_NORD_DARKER: Literal["nord-darker"] = "nord-darker"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_NORD: Literal["nord"] = "nord"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_ONE_DARK: Literal["one-dark"] = "one-dark"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_PARAISO_DARK: Literal["paraiso-dark"] = "paraiso-dark"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_PARAISO_LIGHT: Literal["paraiso-light"] = "paraiso-light"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_PASTIE: Literal["pastie"] = "pastie"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_PERLDOC: Literal["perldoc"] = "perldoc"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_RAINBOW_DASH: Literal["rainbow_dash"] = "rainbow_dash"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_RRT: Literal["rrt"] = "rrt"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_SAS: Literal["sas"] = "sas"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_SOLARIZED_DARK: Literal["solarized-dark"] = "solarized-dark"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_SOLARIZED_LIGHT: Literal["solarized-light"] = "solarized-light"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_STAROFFICE: Literal["staroffice"] = "staroffice"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_STATA_DARK: Literal["stata-dark"] = "stata-dark"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_STATA_LIGHT: Literal["stata-light"] = "stata-light"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_TANGO: Literal["tango"] = "tango"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_TRAC: Literal["trac"] = "trac"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_VIM: Literal["vim"] = "vim"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_VS: Literal["vs"] = "vs"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_XCODE: Literal["xcode"] = "xcode"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""
_ROVRCONFIGTHEMEPREVIEW_ZENBURN: Literal["zenburn"] = "zenburn"
r"""The values for the 'The theme to use when previewing files in the preview sidebar' enum"""

_Run = Union[str, "_RunOneof1"]
r""" Aggregation type: oneOf """

_RunOneof1 = list[str]
r""" minItems: 1 """
