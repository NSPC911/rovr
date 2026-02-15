from typing import Any, Literal, Required, TypedDict


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
    custom_theme: list["_RovrConfigCustomThemeItem"]
    keybinds: "_RovrConfigKeybinds"
    plugins: "_RovrConfigPlugins"


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


_ROVR_CONFIG_INTERFACE_IMAGE_PROTOCOL_DEFAULT = "Auto"
r""" Default value of the field path 'Rovr Config interface image_protocol' """


_ROVR_CONFIG_INTERFACE_MIME_RULES_DEFAULT = {
    "text/*": "text",
    "image/svg+xml": "resvg",
    "image/*": "image",
    "application/pdf": "pdf",
    "application/zip": "archive",
    "application/x-tar": "archive",
    "application/gzip": "archive",
    "application/x-bzip2": "archive",
    "application/x-xz": "archive",
    "application/x-rar": "archive",
    "application/x-7z-compressed": "archive",
    "inode/directory": "folder",
    "application/octet-stream": "remime",
}
r""" Default value of the field path 'Rovr Config interface mime_rules' """


_ROVR_CONFIG_INTERFACE_NERD_FONT_DEFAULT = False
r""" Default value of the field path 'Rovr Config interface nerd_font' """


_ROVR_CONFIG_INTERFACE_PREVIEW_TEXT_ERROR_DEFAULT = "couldn't read this file! (¬_¬ )"
r""" Default value of the field path 'Rovr Config interface preview_text error' """


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


_ROVR_CONFIG_PLUGINS_ZOXIDE_ENABLED_DEFAULT = True
r""" Default value of the field path 'Rovr Config plugins zoxide enabled' """


_ROVR_CONFIG_PLUGINS_ZOXIDE_KEYBINDS_DEFAULT = ["z"]
r""" Default value of the field path 'Rovr Config plugins zoxide keybinds' """


_ROVR_CONFIG_PLUGINS_ZOXIDE_SHOW_SCORES_DEFAULT = False
r""" Default value of the field path 'Rovr Config plugins zoxide show_scores' """


_ROVR_CONFIG_SETTINGS_BULK_RENAME_SHOW_AS_MAPPING_DEFAULT = True
r""" Default value of the field path 'Rovr Config settings bulk_rename show_as_mapping' """


_ROVR_CONFIG_SETTINGS_COPY_INCLUDES_METADATA_DEFAULT = True
r""" Default value of the field path 'Rovr Config settings copy_includes_metadata' """


_ROVR_CONFIG_SETTINGS_EDITOR_BULK_RENAME_RUN_DEFAULT = "$EDITOR"
r""" Default value of the field path 'Rovr Config settings editor bulk_rename run' """


_ROVR_CONFIG_SETTINGS_EDITOR_BULK_RENAME_SUSPEND_DEFAULT = True
r""" Default value of the field path 'Rovr Config settings editor bulk_rename suspend' """


_ROVR_CONFIG_SETTINGS_EDITOR_FILE_BLOCK_DEFAULT = False
r""" Default value of the field path 'Rovr Config settings editor file block' """


_ROVR_CONFIG_SETTINGS_EDITOR_FILE_RUN_DEFAULT = "$EDITOR"
r""" Default value of the field path 'Rovr Config settings editor file run' """


_ROVR_CONFIG_SETTINGS_EDITOR_FILE_SUSPEND_DEFAULT = True
r""" Default value of the field path 'Rovr Config settings editor file suspend' """


_ROVR_CONFIG_SETTINGS_EDITOR_FOLDER_BLOCK_DEFAULT = False
r""" Default value of the field path 'Rovr Config settings editor folder block' """


_ROVR_CONFIG_SETTINGS_EDITOR_FOLDER_RUN_DEFAULT = "$EDITOR"
r""" Default value of the field path 'Rovr Config settings editor folder run' """


_ROVR_CONFIG_SETTINGS_EDITOR_FOLDER_SUSPEND_DEFAULT = True
r""" Default value of the field path 'Rovr Config settings editor folder suspend' """


_ROVR_CONFIG_SETTINGS_EDITOR_OPEN_ALL_IN_EDITOR_DEFAULT = False
r""" Default value of the field path 'Rovr Config settings editor open_all_in_editor' """


_ROVR_CONFIG_SETTINGS_USE_RECYCLE_BIN_DEFAULT = True
r""" Default value of the field path 'Rovr Config settings use_recycle_bin' """


_ROVR_CONFIG_THEME_DEFAULT_DEFAULT = "nord"
r""" Default value of the field path 'Rovr Config theme default' """


_ROVR_CONFIG_THEME_PREVIEW_DEFAULT = "nord"
r""" Default value of the field path 'Rovr Config theme preview' """


_ROVR_CONFIG_THEME_TRANSPARENT_DEFAULT = False
r""" Default value of the field path 'Rovr Config theme transparent' """


class _RovrConfigCustomThemeItem(TypedDict, total=False):
    name: Required[str]
    r"""
    A name for the theme. However, when the theme is available in the theme picker, it shows up as a hyphenated, lowercase version.

    Required property
    """

    primary: Required[str]
    r"""
    A hex code or named color to use as the primary color. Refer to https://textual.textualize.io/css_types/color/#named-colors for the named colors.

    Required property
    """

    secondary: Required[str]
    r"""
    A hex code or named color to use as the secondary color. Refer to https://textual.textualize.io/css_types/color/#named-colors for the named colors.

    Required property
    """

    warning: Required[str]
    r"""
    A hex code or named color to use as the warning color. Refer to https://textual.textualize.io/css_types/color/#named-colors for the named colors.

    Required property
    """

    error: Required[str]
    r"""
    A hex code or named color to use as the error color. Refer to https://textual.textualize.io/css_types/color/#named-colors for the named colors.

    Required property
    """

    success: Required[str]
    r"""
    A hex code or named color to use as the success color. Refer to https://textual.textualize.io/css_types/color/#named-colors for the named colors.

    Required property
    """

    accent: Required[str]
    r"""
    A hex code or named color to use as the accent color. Refer to https://textual.textualize.io/css_types/color/#named-colors for the named colors.

    Required property
    """

    foreground: Required[str]
    r"""
    A hex code or named color to use as the foreground color. Refer to https://textual.textualize.io/css_types/color/#named-colors for the named colors.

    Required property
    """

    background: Required[str]
    r"""
    A hex code or named color to use as the background color. Refer to https://textual.textualize.io/css_types/color/#named-colors for the named colors.

    Required property
    """

    surface: Required[str]
    r"""
    A hex code or named color to use as the surface color. Refer to https://textual.textualize.io/css_types/color/#named-colors for the named colors.

    Required property
    """

    panel: Required[str]
    r"""
    A hex code or named color to use as the panel color. Refer to https://textual.textualize.io/css_types/color/#named-colors for the named colors.

    Required property
    """

    bar_gradient: "_RovrConfigCustomThemeItemBarGradient"
    r""" The gradient colors for the progress bar. """

    is_dark: Required[bool]
    r"""
    Whether or not this theme is a dark type theme.

    Required property
    """

    variables: dict[str, Any]
    r"""
    Extra variables to set unique to the theme.
    Refer to https://textual.textualize.io/guide/design/#additional-variables for more information.
    """


class _RovrConfigCustomThemeItemBarGradient(TypedDict, total=False):
    r"""The gradient colors for the progress bar."""

    default: list[Any]
    r""" A list of hex codes, or named colors to use as the progress bar's gradient colors. Refer to https://textual.textualize.io/css_types/color/#named-colors for the named colors. """

    error: list[Any]
    r""" A list of hex codes, or named colors to use as the progress bar's gradient colors **when it encountered an error**. Refer to https://textual.textualize.io/css_types/color/#named-colors for the named colors. """


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

    image_protocol: "_RovrConfigInterfaceImageProtocol"
    r"""
    The image protocol to use when displaying an image

    default: Auto
    """

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
    mime_rules: dict[str, "_RovrConfigInterfaceMimeRulesAdditionalproperties"]
    r"""
    Map MIME type patterns to preview types. Supports glob patterns (e.g., 'text/*' matches 'text/plain', 'text/html', etc.). Valid preview types: text, image, pdf, archive, folder, remime.
    -> Use 'remime' if you want a more accurate description from file(1)

    default:
      application/gzip: archive
      application/octet-stream: remime
      application/pdf: pdf
      application/x-7z-compressed: archive
      application/x-bzip2: archive
      application/x-rar: archive
      application/x-tar: archive
      application/x-xz: archive
      application/zip: archive
      image/*: image
      image/svg+xml: resvg
      inode/directory: folder
      text/*: text
    """


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


_RovrConfigInterfaceImageProtocol = (
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
_ROVRCONFIGINTERFACEIMAGEPROTOCOL_AUTO: Literal["Auto"] = "Auto"
r"""The values for the 'The image protocol to use when displaying an image' enum"""
_ROVRCONFIGINTERFACEIMAGEPROTOCOL_TGP: Literal["TGP"] = "TGP"
r"""The values for the 'The image protocol to use when displaying an image' enum"""
_ROVRCONFIGINTERFACEIMAGEPROTOCOL_SIXEL: Literal["Sixel"] = "Sixel"
r"""The values for the 'The image protocol to use when displaying an image' enum"""
_ROVRCONFIGINTERFACEIMAGEPROTOCOL_HALFCELL: Literal["Halfcell"] = "Halfcell"
r"""The values for the 'The image protocol to use when displaying an image' enum"""
_ROVRCONFIGINTERFACEIMAGEPROTOCOL_UNICODE: Literal["Unicode"] = "Unicode"
r"""The values for the 'The image protocol to use when displaying an image' enum"""


_RovrConfigInterfaceMimeRulesAdditionalproperties = (
    Literal["text"]
    | Literal["image"]
    | Literal["pdf"]
    | Literal["archive"]
    | Literal["folder"]
    | Literal["remime"]
    | Literal["resvg"]
)
_ROVRCONFIGINTERFACEMIMERULESADDITIONALPROPERTIES_TEXT: Literal["text"] = "text"
r"""The values for the '_RovrConfigInterfaceMimeRulesAdditionalproperties' enum"""
_ROVRCONFIGINTERFACEMIMERULESADDITIONALPROPERTIES_IMAGE: Literal["image"] = "image"
r"""The values for the '_RovrConfigInterfaceMimeRulesAdditionalproperties' enum"""
_ROVRCONFIGINTERFACEMIMERULESADDITIONALPROPERTIES_PDF: Literal["pdf"] = "pdf"
r"""The values for the '_RovrConfigInterfaceMimeRulesAdditionalproperties' enum"""
_ROVRCONFIGINTERFACEMIMERULESADDITIONALPROPERTIES_ARCHIVE: Literal["archive"] = (
    "archive"
)
r"""The values for the '_RovrConfigInterfaceMimeRulesAdditionalproperties' enum"""
_ROVRCONFIGINTERFACEMIMERULESADDITIONALPROPERTIES_FOLDER: Literal["folder"] = "folder"
r"""The values for the '_RovrConfigInterfaceMimeRulesAdditionalproperties' enum"""
_ROVRCONFIGINTERFACEMIMERULESADDITIONALPROPERTIES_REMIME: Literal["remime"] = "remime"
r"""The values for the '_RovrConfigInterfaceMimeRulesAdditionalproperties' enum"""
_ROVRCONFIGINTERFACEMIMERULESADDITIONALPROPERTIES_RESVG: Literal["resvg"] = "resvg"
r"""The values for the '_RovrConfigInterfaceMimeRulesAdditionalproperties' enum"""


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


class _RovrConfigKeybinds(TypedDict, total=False):
    toggle_pin: list[str]
    toggle_pinned_sidebar: list[str]
    toggle_preview_sidebar: list[str]
    toggle_footer: list[str]
    toggle_menuwrapper: list[str]
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
    toggle_all: list[str]
    zip: list[str]
    unzip: list[str]
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

    suspend_app: list[str]
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


class _RovrConfigKeybindsExtraCopy(TypedDict, total=False):
    r"""Keybinds related to extra copy options"""

    open_popup: list[str]
    copy_to_rovr: list[str]
    copy_single_path: list[str]
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

    copy_includes_metadata: bool
    r"""
    When copying over a file, preserve metadata from the original file, such as creation and modification times.

    default: True
    """

    bulk_rename: "_RovrConfigSettingsBulkRename"
    editor: "_RovrConfigSettingsEditor"
    r""" Settings related to the editor used for different operations """


class _RovrConfigSettingsBulkRename(TypedDict, total=False):
    show_as_mapping: bool
    r"""
    Show as a mapping of `<old> ➔ <new>` instead of just `<old>`

    default: True
    """


class _RovrConfigSettingsEditor(TypedDict, total=False):
    r"""Settings related to the editor used for different operations"""

    file: "_RovrConfigSettingsEditorFile"
    r""" Editor to use when opening a file """

    folder: "_RovrConfigSettingsEditorFolder"
    r""" Editor to use when opening a folder """

    bulk_rename: "_RovrConfigSettingsEditorBulkRename"
    r""" Editor to use for bulk renaming """

    open_all_in_editor: bool
    r"""
    Open all in the configured editor, regardless of file encoding or type. When disabled, it opens them in the system configured editor.

    default: False
    """


class _RovrConfigSettingsEditorBulkRename(TypedDict, total=False):
    r"""Editor to use for bulk renaming"""

    run: str
    r"""
    Editor to use for bulk renaming

    default: $EDITOR
    """

    suspend: bool
    r"""
    Suspend (hide) rovr until the editor closes

    default: True
    """


class _RovrConfigSettingsEditorFile(TypedDict, total=False):
    r"""Editor to use when opening a file"""

    run: str
    r"""
    Editor to use when opening a file

    default: $EDITOR
    """

    block: bool
    r"""
    Block rovr until the editor closes

    default: False
    """

    suspend: bool
    r"""
    Suspend (hide) rovr until the editor closes. Will block regardless.

    default: True
    """


class _RovrConfigSettingsEditorFolder(TypedDict, total=False):
    r"""Editor to use when opening a folder"""

    run: str
    r"""
    Editor to use when opening a folder

    default: $EDITOR
    """

    block: bool
    r"""
    Block rovr until the editor closes

    default: False
    """

    suspend: bool
    r"""
    Suspend (hide) rovr until the editor closes. Will block regardless.

    default: True
    """


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
