import platform
from dataclasses import dataclass

from textual.binding import Binding, BindingType

from rovr.functions.config import config_setup, load_config

# Initialize the config once at import time
if "config" not in globals():
    global config, schema
    schema, config = load_config()
    config_setup()


@dataclass
class PreviewContainerTitles:
    image = "Image Preview"
    bat = "File Preview (bat)"
    file = "File Preview"
    folder = "Folder Preview"
    archive = "Archive Preview"


buttons_that_depend_on_path = [
    "#copy",
    "#cut",
    "#rename",
    "#delete",
    "#zip",
    "#copy_path",
]

ascii_logo = r"""
 ___ ___ _ _ ___
|  _| . | | |  _|
|_| |___|\_/|_|"""


class MaxPossible:
    @property
    def height(self) -> int:
        return 13 if config["interface"]["use_reactive_layout"] else 24

    @property
    def width(self) -> int:
        return 26 if config["interface"]["use_reactive_layout"] else 70


up_down_vindings: list[BindingType] = (
    [
        Binding(bind, "cursor_down", "Down", show=False)
        for bind in config["keybinds"]["down"]
    ]
    + [Binding(bind, "last", "Last", show=False) for bind in config["keybinds"]["end"]]
    + [
        Binding(bind, "select", "Select", show=False)
        for bind in config["keybinds"]["down_tree"]
    ]
)

vindings: list[BindingType] = (
    up_down_vindings
    + [
        Binding(bind, "first", "First", show=False)
        for bind in config["keybinds"]["home"]
    ]
    + [
        Binding(bind, "page_down", "Page Down", show=False)
        for bind in config["keybinds"]["page_down"]
    ]
    + [
        Binding(bind, "page_up", "Page Up", show=False)
        for bind in config["keybinds"]["page_up"]
    ]
    + [
        Binding(bind, "cursor_up", "Up", show=False)
        for bind in config["keybinds"]["up"]
    ]
)

os_type: str = platform.system()
