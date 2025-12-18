"""Pydantic models for rovr configuration."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class ClockConfig(BaseModel):
    """Clock configuration in the interface."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True, description="Show a clock in the tabs bar."
    )
    align: Literal["left", "right"] = Field(
        default="right",
        description="Align the clock to either the 'right' or 'left' of the tabs bar.",
    )


class PreviewTextConfig(BaseModel):
    """Preview text configuration."""

    model_config = ConfigDict(extra="forbid")

    error: str = Field(
        default="couldn't read this file! (¬_¬ )",
        description="If for any reason the file preview refused to show, this appears.",
    )
    binary: str = Field(
        default="the file does not use UTF-8, which isn't supported yet",
        description="If the current file cannot be read due to an encoding issue (ie not UTF8), it will display this message.",
    )
    start: str = Field(
        default=" ___ ___\n|  _| . |\n|_| |___|\n _ _ ___\n| | |  _|\n \\_/|_|\n",
        description="This is shown when the rovr starts up. You may see it for a split second, but it will never appear afterwards.",
    )
    empty: str = Field(
        default="bytes be gone (⌐■_■)",
        description="If the current file has no content, this is shown",
    )
    too_large: str = Field(
        default="this file is larger (but not larger than your mother)",
        description="If the file is too large (hard capped at < 1MB), the preview will refuse to render this file regardless of your memory size",
    )


class CompactModeConfig(BaseModel):
    """Compact mode configuration."""

    model_config = ConfigDict(extra="forbid")

    buttons: bool = Field(
        default=False,
        description="Whether to compact the buttons and path input to one line instead of three.",
    )
    panels: bool = Field(
        default=False,
        description="Whether to make the panels smaller to add more room for the file list itself",
    )


class InterfaceConfig(BaseModel):
    """Interface configuration."""

    model_config = ConfigDict(extra="forbid")

    tooltips: bool = Field(
        default=True,
        description="Show tooltips when your mouse is over a tooltip supported button.\nThis is not hot reloaded.",
    )
    nerd_font: bool = Field(
        default=False,
        description="Use nerd font for rendering icons instead of weird characters and stuff.\nNot properly hot-reloaded.",
    )
    use_reactive_layout: bool = Field(
        default=True,
        description="Hide certain elements based on the width and height of the terminal.",
    )
    show_progress_eta: bool = Field(
        default=False,
        description="When copying or deleting files, show an ETA for when the action will be completed.",
    )
    show_progress_percentage: bool = Field(
        default=False,
        description="When copying or deleting files, show a percentage of how much had been completed.",
    )
    truncate_progress_file_path: bool = Field(
        default=False,
        description="When the process container is using file paths, truncate the file path to only view the first and last names of the path.",
    )
    show_line_numbers: bool = Field(
        default=False,
        description="Add line numbers to the left gutter if you are viewing a text file.",
    )
    scrolloff: Annotated[int, Field(ge=0)] = Field(
        default=3,
        description="The number of files to keep above and below the cursor when moving through the file list.",
    )
    clock: ClockConfig = Field(default_factory=ClockConfig)
    preview_text: PreviewTextConfig = Field(default_factory=PreviewTextConfig)
    compact_mode: CompactModeConfig = Field(default_factory=CompactModeConfig)


class SettingsConfig(BaseModel):
    """Settings configuration."""

    model_config = ConfigDict(extra="forbid")

    show_hidden_files: bool = Field(
        default=False,
        description="Show hidden files and folders (those starting with a dot on Unix, or explicitly hidden on Windows/MacOS).",
    )
    use_recycle_bin: bool = Field(
        default=True,
        description="When deleting a file, allow moving the file to the recycle bin.",
    )
    copy_includes_metadata: bool = Field(
        default=True,
        description="When copying over a file, preserve metadata from the original file, such as creation and modification times.",
    )
    image_protocol: Literal["Auto", "TGP", "Sixel", "Halfcell", "Unicode"] = Field(
        default="Auto",
        description="The image protocol to use when displaying an image",
    )
    allow_tab_nav: bool = Field(
        default=False,
        description="Allow navigating the main app screen with `tab` and `shift+tab`",
    )
    append_new_tabs: bool = Field(
        default=True,
        description="Choose whether or not to append new tabs instead of inserting them.\n`true` => Append to the end of the tab list.\n`false` => Insert after the active tab.",
    )
    double_click_delay: float = Field(
        default=0.25,
        description="The delay between two consecutive clicks to enter into a directory, or open a file.",
    )
    drive_watcher_frequency: float = Field(
        default=3.0,
        description="How often (in seconds) to check for changes in mounted drives in the sidebar.",
    )


MetadataFieldType = Literal[
    "type", "permissions", "size", "modified", "accessed", "created", "hidden"
]


class MetadataConfig(BaseModel):
    """Metadata configuration."""

    model_config = ConfigDict(extra="forbid")

    fields: list[MetadataFieldType] = Field(
        default=[
            "type",
            "permissions",
            "size",
            "modified",
            "accessed",
            "created",
            "hidden",
        ],
        description="The order of the metadata tags that you want to see in the Metadata section.",
    )
    datetime_format: str = Field(
        default="%Y-%m-%d %H:%M",
        description="The datetime format for Metadata. Refer to https://docs.python.org/3/library/datetime.html#format-codes for more information.",
    )
    filesize_decimals: Annotated[int, Field(ge=0)] = Field(
        default=1,
        description="The number of decimals you want to see in the humanized file size",
    )
    filesize_suffix: Literal["decimal", "binary", "gnu"] = Field(
        default="decimal",
        description="The filesize suffix to follow.\n`decimal`: 1024 -> 1.024kB\n`binary`: 1024 -> 1KiB\n`gnu`: 1024 -> 1K",
    )


class IconMapping(BaseModel):
    """Icon mapping for files or folders."""

    pattern: str = Field(
        description="The glob pattern to match against the file name (e.g., '*.py', 'LICENSE').\nBoth the filename and glob will be forced to lowercase!"
    )
    icon: str = Field(description="The icon character to use.")
    color: str = Field(
        description="The color for the icon. Can be a named color or hex code."
    )


class IconsConfig(BaseModel):
    """Icons configuration."""

    model_config = ConfigDict(extra="forbid")

    files: list[IconMapping] = Field(
        default=[],
        description="Custom file icon mappings. Earlier entries have higher priority.",
    )
    folders: list[IconMapping] = Field(
        default=[],
        description="Custom folder icon mappings. Earlier entries have higher priority.",
    )


class ThemeConfig(BaseModel):
    """Theme configuration."""

    model_config = ConfigDict(extra="forbid")

    default: str = Field(
        default="nord",
        description="The default theme. Can be changed while in rovr, but it is not persistent.",
    )
    transparent: bool = Field(
        default=False, description="Use a transparent background."
    )


class BarGradient(BaseModel):
    """Bar gradient colors."""

    model_config = ConfigDict(extra="forbid")

    default: list[str] | None = Field(
        default=None,
        description="A list of hex codes, or named colors to use as the progress bar's gradient colors.",
    )
    error: list[str] | None = Field(
        default=None,
        description="A list of hex codes, or named colors to use as the progress bar's gradient colors **when it encountered an error**.",
    )


class CustomTheme(BaseModel):
    """Custom theme definition."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="A name for the theme. However, when the theme is available in the theme picker, it shows up as a hiphenated, lowercase version."
    )
    primary: str = Field(
        description="A hex code or named color to use as the primary color."
    )
    secondary: str = Field(
        description="A hex code or named color to use as the secondary color."
    )
    warning: str = Field(
        description="A hex code or named color to use as the warning color."
    )
    error: str = Field(
        description="A hex code or named color to use as the error color."
    )
    success: str = Field(
        description="A hex code or named color to use as the success color."
    )
    accent: str = Field(
        description="A hex code or named color to use as the accent color."
    )
    foreground: str = Field(
        description="A hex code or named color to use as the foreground color."
    )
    background: str = Field(
        description="A hex code or named color to use as the background color."
    )
    surface: str = Field(
        description="A hex code or named color to use as the surface color."
    )
    panel: str = Field(
        description="A hex code or named color to use as the panel color."
    )
    is_dark: bool = Field(description="Whether or not this theme is a dark type theme.")
    bar_gradient: BarGradient | None = Field(
        default=None, description="The gradient colors for the progress bar."
    )
    variables: dict[str, str] | None = Field(
        default=None,
        description="Extra variables to set unique to the theme.\nRefer to https://textual.textualize.io/guide/design/#additional-variables for more information.",
    )


# Keybind type alias
Keybind = list[str]


class ChangeSortOrderKeybinds(BaseModel):
    """Keybinds for changing sort order."""

    model_config = ConfigDict(extra="forbid")

    open_popup: Keybind | None = Field(
        default=None, description="Open the change sort order popup."
    )
    name: Keybind | None = Field(default=None, description="Sort by name.")
    extension: Keybind | None = Field(default=None, description="Sort by extension.")
    natural: Keybind | None = Field(
        default=None, description="Sort naturally (numbers first)."
    )
    size: Keybind | None = Field(default=None, description="Sort by size.")
    created: Keybind | None = Field(default=None, description="Sort by creation time.")
    modified: Keybind | None = Field(
        default=None, description="Sort by modification time."
    )
    descending: Keybind | None = Field(
        default=None, description="Toggle descending sort order."
    )


class DeleteFilesKeybinds(BaseModel):
    """Keybinds for delete confirmation screen."""

    model_config = ConfigDict(extra="forbid")

    trash: Keybind | None = Field(
        default=None,
        description="Confirm deletion and move files to the recycle bin.",
    )
    delete: Keybind | None = Field(
        default=None, description="Confirm deletion and permanently delete files."
    )
    cancel: Keybind | None = Field(
        default=None,
        description="Cancel deletion and go back to the main screen.",
    )


class FilenameConflictKeybinds(BaseModel):
    """Keybinds for handling filename conflicts."""

    model_config = ConfigDict(extra="forbid")

    overwrite: Keybind | None = Field(
        default=None,
        description="Overwrite the existing file with the new file.",
    )
    skip: Keybind | None = Field(
        default=None, description="Skip this file and do not copy/move it."
    )
    rename: Keybind | None = Field(
        default=None, description="Rename the new file being copied/moved."
    )
    cancel: Keybind | None = Field(
        default=None, description="Cancel the entire copy/move operation."
    )
    dont_ask_again: Keybind | None = Field(
        default=None,
        description="Apply the selected action to all future conflicts without asking again.",
    )


class FileInUseKeybinds(BaseModel):
    """Keybinds for handling file in use errors."""

    model_config = ConfigDict(extra="forbid")

    retry: Keybind | None = Field(
        default=None, description="Retry the operation on the file."
    )
    skip: Keybind | None = Field(
        default=None, description="Skip this file and do not copy/move it."
    )
    cancel: Keybind | None = Field(
        default=None, description="Cancel the entire copy/move operation."
    )
    dont_ask_again: Keybind | None = Field(
        default=None,
        description="Apply the selected action to all future 'file in use' errors without asking again.",
    )


class FilterModalKeybinds(BaseModel):
    """Keybinds for filter modals."""

    model_config = ConfigDict(extra="forbid")

    exit: Keybind | None = Field(
        default=None, description="Exit the modal without making a selection."
    )
    down: Keybind | None = Field(
        default=None, description="Move the selection down in the modal list."
    )
    up: Keybind | None = Field(
        default=None, description="Move the selection up in the modal list."
    )


class YesOrNoKeybinds(BaseModel):
    """Keybinds for yes/no confirmation modals."""

    model_config = ConfigDict(extra="forbid")

    yes: Keybind | None = Field(default=None, description="Confirm with 'yes'.")
    no: Keybind | None = Field(default=None, description="Decline with 'no'.")
    dont_ask_again: Keybind | None = Field(
        default=None,
        description="Apply the selected action to all future confirmations without asking again.",
    )


class KeybindsConfig(BaseModel):
    """Keybinds configuration."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    toggle_pin: Keybind | None = Field(
        default=None,
        description="Toggle the current folder in the Pinned Folder Sidebar.",
    )
    toggle_pinned_sidebar: Keybind | None = Field(
        default=None, description="Toggle viewing the pinned sidebar."
    )
    toggle_preview_sidebar: Keybind | None = Field(
        default=None, description="Toggle viewing the preview sidebar."
    )
    toggle_footer: Keybind | None = Field(
        default=None, description="Toggle viewing the footer."
    )
    toggle_menuwrapper: Keybind | None = Field(
        default=None, description="Toggle viewing the menu wrapper."
    )
    focus_toggle_pinned_sidebar: Keybind | None = Field(
        default=None,
        description="Toggle focus between pinned folder sidebar and file list.",
    )
    focus_file_list: Keybind | None = Field(
        default=None, description="Focus the file list."
    )
    focus_toggle_preview_sidebar: Keybind | None = Field(
        default=None,
        description="Focus toggle between preview sidebar and file list.",
    )
    focus_toggle_path_switcher: Keybind | None = Field(
        default=None,
        description="Focus toggle between path switcher and file list.",
    )
    focus_toggle_processes: Keybind | None = Field(
        default=None, description="Focus toggle the processes container."
    )
    focus_toggle_clipboard: Keybind | None = Field(
        default=None, description="Focus toggle the clipboard container."
    )
    focus_toggle_metadata: Keybind | None = Field(
        default=None, description="Focus toggle the metadata container."
    )
    focus_search: Keybind | None = Field(
        default=None, description="Focus the search bar."
    )
    copy_files: Keybind | None = Field(
        default=None,
        alias="copy",
        description="Copy the selected files in the file list to the clipboard.",
    )
    paste: Keybind | None = Field(
        default=None,
        description="Paste the selected files in the clipboard into the current directory.",
    )
    cut: Keybind | None = Field(
        default=None,
        description="Cut the selected files in the file list to the clipboard.",
    )
    delete: Keybind | None = Field(
        default=None, description="Delete the selected files in the file list."
    )
    rename: Keybind | None = Field(
        default=None,
        description="Rename the selected file in the file list to something else.",
    )
    new: Keybind | None = Field(
        default=None, description="Create a new item in the current directory."
    )
    toggle_all: Keybind | None = Field(
        default=None,
        description="Enter into select mode and select/unselect everything.",
    )
    zip: Keybind | None = Field(
        default=None, description="Create a zip archive from selected files."
    )
    unzip: Keybind | None = Field(
        default=None, description="Extract a selected zip archive."
    )
    copy_path: Keybind | None = Field(
        default=None,
        description="Copy the path of the item to the system clipboard.",
    )
    up: Keybind | None = Field(
        default=None, description="Go up the file list options."
    )
    down: Keybind | None = Field(
        default=None, description="Go down the file list options."
    )
    up_tree: Keybind | None = Field(default=None, description="Go up the file tree.")
    down_tree: Keybind | None = Field(
        default=None,
        description="Go down the file tree, or open the currently selected item.",
    )
    page_up: Keybind | None = Field(
        default=None, description="Go to the previous page of the file list."
    )
    page_down: Keybind | None = Field(
        default=None, description="Go to the next page of the file list."
    )
    home: Keybind | None = Field(
        default=None, description="Jump to the top of the file list."
    )
    end: Keybind | None = Field(
        default=None, description="Jump to the bottom of the file list."
    )
    hist_previous: Keybind | None = Field(
        default=None, description="Go back in history."
    )
    hist_next: Keybind | None = Field(
        default=None, description="Go forward in history."
    )
    toggle_visual: Keybind | None = Field(
        default=None, description="Enter or exit select/visual mode."
    )
    toggle_hidden_files: Keybind | None = Field(
        default=None,
        description="Toggle the visibility of hidden files (dot-prefixed on Unix, or flagged hidden on Windows/macOS).",
    )
    select_up: Keybind | None = Field(
        default=None,
        description="While in visual mode, extend the selection up.",
    )
    select_down: Keybind | None = Field(
        default=None,
        description="While in visual mode, extend the selection down.",
    )
    select_page_up: Keybind | None = Field(
        default=None,
        description="While in visual mode, extend the selection to the previous page.",
    )
    select_page_down: Keybind | None = Field(
        default=None,
        description="While in visual mode, extend the selection to the next page.",
    )
    select_home: Keybind | None = Field(
        default=None,
        description="While in visual mode, extend the selection to the first option.",
    )
    select_end: Keybind | None = Field(
        default=None,
        description="While in visual mode, extend the selection to the last option.",
    )
    tab_next: Keybind | None = Field(
        default=None, description="Go to the next tab, if it is available."
    )
    tab_previous: Keybind | None = Field(
        default=None, description="Go to the previous tab, if it is available."
    )
    tab_new: Keybind | None = Field(default=None, description="Create a new tab.")
    tab_close: Keybind | None = Field(
        default=None, description="Close the current tab."
    )
    preview_scroll_left: Keybind | None = Field(
        default=None, description="Temporarily unused."
    )
    preview_scroll_right: Keybind | None = Field(
        default=None, description="Temporarily unused."
    )
    preview_select_left: Keybind | None = Field(
        default=None, description="Temporarily unused."
    )
    preview_select_right: Keybind | None = Field(
        default=None, description="Temporarily unused."
    )
    show_keybinds: Keybind | None = Field(
        default=None,
        description="Show the keybinds list with all available keybinds.",
    )
    quit_app: Keybind | None = Field(
        default=None, description="Quit the application"
    )
    command_palette: str | None = Field(
        default=None,
        description="Launch Textual's mildly useful command palette (only one keybind is allowed!)",
    )
    suspend_app: Keybind | None = Field(
        default=None,
        description="Suspend the app's process, bringing you back to the terminal",
    )
    change_sort_order: ChangeSortOrderKeybinds | None = Field(
        default=None, description="Keybinds related to changing the sort order"
    )
    delete_files: DeleteFilesKeybinds | None = Field(
        default=None, description="Keybinds related to the delete confirmation screen"
    )
    filename_conflict: FilenameConflictKeybinds | None = Field(
        default=None,
        description="Keybinds related to handling a conflict with two files of the same name",
    )
    file_in_use: FileInUseKeybinds | None = Field(
        default=None,
        description="Keybinds related to handling a file that is in use by another process",
    )
    filter_modal: FilterModalKeybinds | None = Field(
        default=None,
        description="Keybinds related to selecting options in a modal screen (like FileSearch or ZDToDirectory)",
    )
    yes_or_no: YesOrNoKeybinds | None = Field(
        default=None, description="Keybinds related to yes/no confirmation modals"
    )


# Plugin configs
class ZoxidePlugin(BaseModel):
    """Zoxide plugin configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True, description="Enable or disable zoxide travelling."
    )
    keybinds: Keybind | None = Field(
        default=None, description="The keybind to open the zoxide modal."
    )
    show_scores: bool = Field(
        default=False,
        description="Display zoxide frequency scores alongside directory paths.",
    )


class BatPlugin(BaseModel):
    """Bat plugin configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=False, description="Enable or disable bat for previewing files."
    )
    executable: str = Field(default="bat", description="The executable for bat.")


class EditorPlugin(BaseModel):
    """Editor plugin configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True, description="Enable opening a file in your editor."
    )
    file_executable: str = Field(default="nano", description="Open files in this app.")
    file_suspend: bool = Field(
        default=True,
        description="Suspend the app when editing a file. Useful for TUI editors, but not for something like VSCode or Notepad++.",
    )
    folder_executable: str = Field(
        default="code", description="Open folders in this app."
    )
    folder_suspend: bool = Field(
        default=True,
        description="Suspend the app when editing a folder. Useful for TUI editors, but not for something like VSCode or Notepad++.",
    )
    open_all_in_editor: bool = Field(
        default=False,
        description="Open all files in the configured editor, regardless of file encoding or type. When disabled, files that cannot be opened due to encoding issues will use the system's default application instead.",
    )
    keybinds: Keybind | None = Field(
        default=None, description="The keybind to launch your editor."
    )


FdFilterType = Literal[
    "file",
    "directory",
    "symlink",
    "executable",
    "empty",
    "socket",
    "pipe",
    "char-device",
    "block-device",
]


class FdPlugin(BaseModel):
    """Fd plugin configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True, description="Enable recursive file search using fd."
    )
    keybinds: Keybind | None = Field(
        default=None, description="The keybind to open the file search picker."
    )
    executable: str = Field(default="fd", description="fd executable name or path.")
    relative_paths: bool = Field(
        default=True,
        description="Whether to show as relative path or absolute path.",
    )
    follow_symlinks: bool = Field(
        default=False,
        description="Whether fd should follow symlinks when searching.",
    )
    no_ignore_parent: bool = Field(
        default=False,
        description="Don't use *ignore files from parent folders when searching.",
    )
    default_filter_types: list[FdFilterType] = Field(
        default=["file", "directory"],
        description="The default file types to show when using fd.",
    )


class PopplerPlugin(BaseModel):
    """Poppler plugin configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True, description="Enable poppler for PDF previews.")
    threads: Annotated[int, Field(ge=1)] = Field(
        default=1, description="How many threads should poppler use?"
    )
    use_pdftocairo: bool = Field(
        default=False,
        description="Use pdftocairo instead of pdftoppm, may help performance",
    )
    poppler_folder: str = Field(
        default="",
        description="Path to the folder where Poppler-related binaries are located. Leave empty to use the system PATH.",
    )


PreviewType = Literal["text", "image", "pdf", "archive", "folder"]


class FileOnePlugin(BaseModel):
    """File(1) plugin configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable file(1) MIME type detection for preview selection. When enabled, rovr uses the `file` command to detect file types instead of relying solely on file extensions.",
    )
    mime_rules: dict[str, PreviewType] = Field(
        default={
            "text/*": "text",
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
        },
        description="Map MIME type patterns to preview types. Supports glob patterns (e.g., 'text/*' matches 'text/plain', 'text/html', etc.). Valid preview types: text, image, pdf, archive, folder.",
    )


class PluginsConfig(BaseModel):
    """Plugins configuration."""

    model_config = ConfigDict(extra="forbid")

    zoxide: ZoxidePlugin = Field(default_factory=ZoxidePlugin)
    bat: BatPlugin = Field(default_factory=BatPlugin)
    editor: EditorPlugin = Field(default_factory=EditorPlugin)
    fd: FdPlugin = Field(default_factory=FdPlugin)
    poppler: PopplerPlugin = Field(default_factory=PopplerPlugin)
    file_one: FileOnePlugin = Field(default_factory=FileOnePlugin)


class RovrConfig(BaseModel):
    """Main Rovr configuration model."""

    model_config = ConfigDict(extra="forbid")

    interface: InterfaceConfig = Field(default_factory=InterfaceConfig)
    settings: SettingsConfig = Field(default_factory=SettingsConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)
    icons: IconsConfig = Field(default_factory=IconsConfig)
    theme: ThemeConfig = Field(default_factory=ThemeConfig)
    custom_theme: list[CustomTheme] = Field(default=[])
    keybinds: KeybindsConfig = Field(default_factory=KeybindsConfig)
    plugins: PluginsConfig = Field(default_factory=PluginsConfig)
    mode: dict[str, dict] | None = Field(
        default=None,
        description="Define preset modes with config overrides. Use --mode <name> to activate.",
    )
