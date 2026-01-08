from io import BytesIO
from shutil import which
from typing import Callable, Literal, TypedDict

import aiohttp
import textual_image.widget as timg
from PIL import Image as PILImage
from PIL.Image import Image
from textual import events, on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, HorizontalGroup, VerticalGroup
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.theme import BUILTIN_THEMES
from textual.widgets import Button, RadioButton, RadioSet, Select, Static, Switch

prot_to_timg: dict[str, Callable] = {
    "auto": timg.Image,
    "tgp": timg.TGPImage,
    "sixel": timg.SixelImage,
    "halfcell": timg.HalfcellImage,
    "unicode": timg.UnicodeImage,
}


class DummyScreen(Screen[None]):
    def on_mount(self) -> None:
        self.dismiss()


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
        self.preview_image: Image | None = None

    def compose(self) -> ComposeResult:
        yield Static(classes="padding")
        yield Static(classes="padding")
        yield Static("Welcome to [b][u]rovr[/][/]!")
        yield Static("Let's get you started!")
        yield Static(classes="padding")
        with Center(), RadioSet(id="theme"):
            yield from [
                RadioButton(theme, True, id=theme)
                for theme in BUILTIN_THEMES
                if theme != "textual-ansi"
            ]
        yield Static(classes="padding")
        with HorizontalGroup(id="transparent"):
            yield Switch(value=False, id="transparent_mode")
            yield Static("Enable transparent mode")
        yield Static(classes="padding")
        with Center(), RadioSet(id="keybinds"):
            yield RadioButton(
                "Sane Keybinds (inspired by GUI tools)",
                value=True,
                id="sane",
                tooltip="taken from windows file explorer and other editors",
            )
            yield RadioButton(
                "Vi keybinds~ish",
                value=True,
                id="vi",
                tooltip="keybinds as close to vi as possible",
            )
        yield Static(classes="padding")
        with Center(classes="plugins"):
            with HorizontalGroup(id="plugins-rg"):
                yield Switch(which("rg") is not None)
                yield Static("[u]rg[/] integration")
            with HorizontalGroup(id="plugins-fd"):
                yield Switch(which("fd") is not None)
                yield Static("[u]fd[/] integration")
            with HorizontalGroup(id="plugins-bat"):
                yield Switch(which("bat") is not None)
                yield Static("[u]bat[/] integration")
            with HorizontalGroup(id="plugins-poppler"):
                yield Switch(which("pdftoppm") is not None)
                yield Static("[u]poppler[/] integration")
            with HorizontalGroup(id="plugins-zoxide"):
                yield Switch(which("zoxide") is not None)
                yield Static("[u]zoxide[/] integration")
            with HorizontalGroup(id="plugins-file"):
                yield Switch(which("file") is not None)
                yield Static("[u]file(1)[/] integration")
        yield Static(classes="padding")
        with HorizontalGroup(id="hidden_files"):
            yield Switch(value=False, id="show_hidden_files")
            yield Static("Show hidden files by default")
        with HorizontalGroup(id="reactive_layout"):
            yield Switch(value=True, id="use_reactive_layout")
            yield Static(
                "Use reactive layout (automatically disable certain UI elements at certain heights and widths)"
            )
        yield Static(classes="padding")
        with VerticalGroup(id="image_protocol"):
            yield Select(
                (
                    ("Auto", "auto"),
                    ("TGP/Kitty (might be broken)", "tgp"),
                    ("Sixel", "sixel"),
                    ("HalfCell", "halfcell"),
                    ("Unicode (not recommended)", "unicode"),
                ),
                value="auto",
                id="image_protocol_select",
                allow_blank=False,
            )
        yield Static(classes="padding")
        yield Button("Finish Setup", id="finish_setup", variant="success")
        yield Static(classes="padding")
        yield Static(classes="padding")

    @work
    async def on_mount(self) -> None:
        self.query_one("#theme", RadioSet).border_title = "Choose a theme!"
        self.query_one("#theme", RadioSet).border_subtitle = "More coming soon\u2026"
        self.query_one("#keybinds", RadioSet).border_title = "Choose a Preset Keybind"
        self.query_one(".plugins", Center).border_title = "Plugins/Integrations"
        self.query_one("SelectCurrent").border_title = "Image Protocol"
        plugins = {
            "rg": "Uses ripgrep to search all files for content quickly",
            "fd": "Uses fd to quickly search for files and directories (and other weird path types)",
            "bat": "Uses bat as an alternate previewer",
            "zoxide": "Uses zoxide to zip around directories quickly",
            "poppler": "Uses poppler-utils to preview PDF files",
            "file": "Uses the file(1) command to get better file type information",
        }
        for plugin, desc in plugins.items():
            self.query_one(f"#plugins-{plugin}", HorizontalGroup).tooltip = desc
        self.query_one("#image_protocol", VerticalGroup).mount()
        # call aiohttp and pull https://github.com/Textualize/.github/assets/554369/037e6aa1-8527-44f3-958d-28841d975d40 into a PIL object
        async with aiohttp.ClientSession() as session:  # noqa: SIM117
            async with session.get(
                "https://github.com/Textualize/.github/assets/554369/037e6aa1-8527-44f3-958d-28841d975d40"
            ) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    self.preview_image = PILImage.open(BytesIO(data))
                    timg_image = prot_to_timg["auto"](
                        self.preview_image,
                    )
                    self.query_one("#image_protocol", VerticalGroup).mount(timg_image)
                else:
                    self.preview_image = None
                    self.notify(
                        f"Failed to load preview image. Code: {resp.status}",
                        severity="error",
                    )

    @on(RadioSet.Changed, "#theme")
    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        self.theme = event.pressed.id

    def on_click(self, event: events.Click) -> None:
        try:
            if event.widget != self.query_one("SelectOverlay"):
                self.query_one(Select).expanded = False
        except NoMatches:
            return

    @on(Switch.Changed, "#transparent_mode")
    def on_transparent_mode_changed(self, event: Switch.Changed) -> None:
        self.ansi_color = event.value
        self.query_one(RadioSet).disabled = event.value
        self.query_one(RadioSet).tooltip = (
            "Disabled when transparent mode is enabled" if event.value else None
        )
        self._toggle_transparency()

    @on(Select.Changed, "#image_protocol_select")
    def on_image_protocol_select_changed(self, event: Select.Changed) -> None:
        protocol = event.value
        if self.preview_image is not None:
            timg_image = prot_to_timg[protocol](  # ty: ignore
                self.preview_image,
            )
            container = self.query_one("#image_protocol", VerticalGroup)
            # remove old image
            for child in container.children:
                if not isinstance(child, Select):
                    child.remove()
            container.mount(timg_image)

    @work
    async def _toggle_transparency(self) -> None:
        await self.push_screen_wait(DummyScreen())


Application().run()
