from shutil import which
from typing import Literal, TypedDict

import textual_image.widget as timg
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, HorizontalGroup, VerticalGroup
from textual.screen import Screen
from textual.theme import BUILTIN_THEMES
from textual.widgets import Button, RadioButton, RadioSet, Select, Static, Switch


class Options(TypedDict):
    keybinds: Literal["sane", "vim"]
    theme: str
    plugins_rg: bool
    plugins_fd: bool
    plugins_bat: bool
    plugins_zoxide: bool
    plugins_poppler: bool
    plugins_file_one: bool


class Application(App, inherit_bindings=False):
    # dont need ctrl+c
    BINDINGS = [
        Binding(
            "ctrl+q",
            "quit",
            "Quit",
            tooltip="Quit the app and return to the command prompt.",
            show=False,
            priority=True,
        )
    ]
    CSS_PATH = ["first_launch.tcss"]

    HORIZONTAL_BREAKPOINTS = [(0, "-full"), (50, "-seventy-five"), (100, "-fifty")]

    def __init__(self) -> None:
        super().__init__(watch_css=True)
        self.user_options: Options = {
            "keybinds": "sane",
            "theme": "textual-dark",
            "plugins_rg": False,
            "plugins_fd": False,
            "plugins_bat": False,
            "plugins_zoxide": False,
            "plugins_poppler": False,
            "plugins_file_one": False,
        }

    def compose(self) -> ComposeResult:
        yield Static(classes="padding")
        yield Static("Welcome to [b][u]rovr[/][/]!")
        yield Static("Let's get you started!")
        yield Static(classes="padding")
        with Center(), RadioSet(id="theme"):
            yield from [RadioButton(theme, True, id=theme) for theme in BUILTIN_THEMES if theme != "textual-ansi"]
        yield Static(classes="padding")
        with Center(), RadioSet(id="keybinds"):
            yield RadioButton("Sane Keybinds (inspired by GUI tools)", value=True, id="sane", tooltip="taken from windows file explorer and other editors")
            yield RadioButton("Vi keybinds~ish", value=True, id="vi", tooltip="keybinds as close to vi as possible")
        yield Static(classes="padding")
        with Center(classes="plugins"):
            with HorizontalGroup():
                yield Switch(which("rg") is not None)
                yield Static("[u]rg[/] integration")
            with HorizontalGroup():
                yield Switch(which("fd") is not None)
                yield Static("[u]fd[/] integration")
            with HorizontalGroup():
                yield Switch(which("bat") is not None)
                yield Static("[u]bat[/] integration")
            with HorizontalGroup():
                yield Switch(which("pdftoppm") is not None)
                yield Static("[u]poppler[/] integration")
            with HorizontalGroup():
                yield Switch(which("zoxide") is not None)
                yield Static("[u]zoxide[/] integration")
            with HorizontalGroup():
                yield Switch(which("file") is not None)
                yield Static("[u]file(1)[/] integration")
        yield Static(classes="padding")
        with HorizontalGroup(id="hidden_files"):
            yield Switch(value=True, id="show_hidden_files")
            yield Static("Show hidden files by default")
        with HorizontalGroup(id="reactive_layout"):
            yield Switch(value=True, id="use_reactive_layout")
            yield Static("Use reactive layout (automatically disable certain UI elements at certain heights and widths)")
        with VerticalGroup(id="image_protocol"):
            yield Select((("Auto", "auto"), ("TGP/Kitty", "tgp"), ("Sixel", "sixel"), ("HalfCell", "halfcell"), ("Unicode (not recommended)", "unicode")), value="auto", id="image_protocol_select")


    def on_mount(self) -> None:
        self.query_one("#theme", RadioSet).border_title = "Choose a theme!"
        self.query_one("#theme", RadioSet).border_subtitle = "More coming soon\u2026"
        self.query_one("#keybinds", RadioSet).border_title = "Choose a Preset Keybind"
        self.query_one(".plugins", Center).border_title = "Plugins/Integrations"

    @on(RadioSet.Changed, "#theme")
    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        self.theme = event.pressed.id


Application().run()
