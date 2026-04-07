import sys
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from os import environ
from shutil import which
from typing import Literal, cast

from textual.binding import Binding

from rovr.classes.config import RovrConfig
from rovr.functions.config import load_config
from rovr.functions.utils import classproperty

# Initialize the config once at import time
if "config" not in globals():
    global config, schema
    schema, config = load_config()
else:
    config = globals()["config"]
    config = cast(RovrConfig, config)
    schema = globals()["schema"]


@cache
def file_one() -> str | None:
    # check for $ROVR_FILE_ONE
    if (
        "ROVR_FILE_ONE" in environ
        and (found := which(environ["ROVR_FILE_ONE"])) is not None
    ):
        return found
    # check for $YAZI_FILE_ONE
    if (
        "YAZI_FILE_ONE" in environ
        and (found := which(environ["YAZI_FILE_ONE"])) is not None
    ):
        return found
    # check for `file` existence
    return which("file")


if "log_name" not in globals():
    global log_name
    log_name = str(datetime.now()).replace(" ", "_").replace(":", "")
else:
    log_name = globals()["log_name"]


@dataclass
class PreviewContainerTitles:
    image = "Image Preview"
    bat = "File Preview (bat)"
    file = "File Preview"
    folder = "Folder Preview"
    archive = "Archive Preview"
    pdf = "PDF Preview"
    svg = "SVG Preview"
    font = "Font Preview"


buttons_that_depend_on_path = [
    "#copy",
    "#cut",
    "#rename",
    "#delete",
    "#zip",
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


scroll_bindings = (
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

bindings = (
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
    + [
        Binding(bind, "toggle_select_item", "Toggle Selection", show=False)
        for bind in config["keybinds"].get("toggle_select_item", [])
    ]
)

os_type = (
    "Windows"
    if sys.platform == "win32"
    else "Darwin"
    if sys.platform == "darwin"
    else sys.platform.capitalize()
)
