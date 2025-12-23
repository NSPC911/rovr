import platform
from dataclasses import dataclass
from os import environ
from shutil import which
from typing import Literal, TypeAlias

from textual.binding import Binding, BindingType

from rovr.functions.config import config_setup, load_config
from rovr.functions.utils import classproperty

# Initialize the config once at import time
if "config" not in globals():
    global config, schema
    schema, config = load_config()
    config_setup()
else:
    config = globals()["config"]
    schema = globals()["schema"]


if "file_executable" not in globals():
    global file_executable
    # check for $ROVR_FILE_ONE
    if (  # noqa: SIM114
        "ROVR_FILE_ONE" in environ
        and (found := which(environ["ROVR_FILE_ONE"])) is not None
    ):
        file_executable = found
    # check for $YAZI_FILE_ONE
    elif (  # noqa: SIM114
        "YAZI_FILE_ONE" in environ
        and (found := which(environ["YAZI_FILE_ONE"])) is not None
    ):
        file_executable = found
    # check for `file` existence
    elif (found := which("file")) is not None:
        file_executable = found
    else:
        file_executable = None
else:
    file_executable = globals()["file_executable"]


@dataclass
class PreviewContainerTitles:
    image = "Image Preview"
    bat = "File Preview (bat)"
    file = "File Preview"
    folder = "Folder Preview"
    archive = "Archive Preview"
    pdf = "PDF Preview"


buttons_that_depend_on_path = [
    "#copy",
    "#cut",
    "#rename",
    "#delete",
    "#zip",
    "#copy_path",
]

ascii_logo = r"""
╭───╮╭───╮╭╮  ╭╮╭───╮
│ ╭─╯│ ╷ ││╰╮╭╯││ ╭─╯
│ │  │ ╵ │╰╮╰╯╭╯│ │
╰─╯  ╰───╯ ╰──╯ ╰─╯"""


class MaxPossible:
    @classproperty
    def height(self) -> Literal[13, 24]:
        return 13 if config["interface"]["use_reactive_layout"] else 24

    @classproperty
    def width(self) -> Literal[26, 70]:
        return 26 if config["interface"]["use_reactive_layout"] else 70


scroll_vindings: list[BindingType] = (
    [
        Binding(bind, "scroll_down", "Scroll Down", show=False)
        for bind in config["keybinds"]["down"]
    ]
    + [
        Binding(bind, "scroll_up", "Scroll Up", show=False)
        for bind in config["keybinds"]["up"]
    ]
    + [
        Binding(bind, action="scroll_page_up", description="Scroll Page Up", show=False)
        for bind in config["keybinds"]["page_up"]
    ]
    + [
        Binding(
            bind, action="scroll_page_down", description="Scroll Page Down", show=False
        )
        for bind in config["keybinds"]["page_down"]
    ]
    + [
        Binding(bind, "scroll_home", "Scroll First", show=False)
        for bind in config["keybinds"]["home"]
    ]
    + [
        Binding(bind, "scroll_end", "Scroll End", show=False)
        for bind in config["keybinds"]["end"]
    ]
)

vindings: list[BindingType] = (
    [
        Binding(bind, "cursor_down", "Down", show=False)
        for bind in config["keybinds"]["down"]
    ]
    + [
        Binding(bind, "cursor_up", "Up", show=False)
        for bind in config["keybinds"]["up"]
    ]
    + [
        Binding(bind, "first", "First", show=False)
        for bind in config["keybinds"]["home"]
    ]
    + [Binding(bind, "last", "Last", show=False) for bind in config["keybinds"]["end"]]
    + [
        Binding(bind, "page_down", "Page Down", show=False)
        for bind in config["keybinds"]["page_down"]
    ]
    + [
        Binding(bind, "page_up", "Page Up", show=False)
        for bind in config["keybinds"]["page_up"]
    ]
    + [
        Binding(bind, "select", "Select", show=False)
        for bind in config["keybinds"]["down_tree"]
    ]
)

os_type: str = platform.system()

SortByOptions: TypeAlias = Literal[
    "name", "size", "modified", "created", "extension", "natural"
]
