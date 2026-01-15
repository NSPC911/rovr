import os
from asyncio import sleep
from importlib import resources
from importlib.metadata import PackageNotFoundError, version
from io import BytesIO
from shutil import which
from typing import Callable
from urllib import error, request

import textual_image.widget as timg
import tomli
from PIL import Image as PILImage
from PIL.Image import Image
from pygments.styles import get_all_styles
from rich.syntax import Syntax
from rich.text import Text
from textual import events, on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import (
    Center,
    Container,
    HorizontalGroup,
    ScrollableContainer,
    VerticalGroup,
)
from textual.css.query import NoMatches
from textual.screen import ModalScreen, Screen
from textual.theme import BUILTIN_THEMES
from textual.widgets import (
    Button,
    Input,
    RadioButton,
    RadioSet,
    Select,
    Static,
    Switch,
)

from rovr.variables.maps import VAR_TO_DIR

prot_to_timg: dict[str, Callable] = {
    "auto": timg.Image,
    "tgp": timg.TGPImage,
    "sixel": timg.SixelImage,
    "halfcell": timg.HalfcellImage,
    "unicode": timg.UnicodeImage,
}


prot_to_schema: dict[str, str] = {
    "auto": "Auto",
    "tgp": "TGP",
    "sixel": "Sixel",
    "halfcell": "Halfcell",
    "unicode": "Unicode",
}


try:
    schema_ref = f"refs/tags/v{version('rovr')}"
except PackageNotFoundError:
    schema_ref = "refs/heads/master"


def _escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


class DummyScreen(Screen[None]):
    def on_mount(self) -> None:
        self.dismiss()


class FinalStuff(ModalScreen[None]):
    def __init__(self) -> None:
        super().__init__()

    def compose(self) -> ComposeResult:
        with Container(classes="modal-wrapper"):
            yield Static("Done! You can now exit the app via the big red button!")
            yield Static(
                Text.from_markup(
                    "Make sure to [link=https://github.com/NSPC911/rovr][u]star the repo[/][/link] or [u][link=https://nspc911.github.io/rovr]visit the documentation[/link][/] for more information!"
                )
            )
            yield Static(classes="padding")
            yield Button("Bye!", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.exit(0)


class AskWrite(ModalScreen[bool]):
    def __init__(self, content: str) -> None:
        super().__init__()
        self.content = Syntax(
            content,
            "toml",
            theme="native",
            background_color="default",
            line_numbers=True,
        )

    def compose(self) -> ComposeResult:
        with Container(classes="modal-wrapper"):
            yield Static("Write config to disk?")
            yield Static(
                f"The following content will be written to [u]{os.path.realpath(f'{VAR_TO_DIR["CONFIG"]}/config.toml')}[/]:"
            )
            yield Static(classes="padding")
            with ScrollableContainer():
                yield Static(self.content, id="config-preview")
            with HorizontalGroup():
                yield Button("Ok!", id="yes", variant="success")
                yield Button("No.", id="no", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")


class FirstLaunchApp(App, inherit_bindings=False):
    AUTO_FOCUS = False

    # don't need ctrl+c
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

    HORIZONTAL_BREAKPOINTS = [(0, "-full"), (55, "-seventy-five"), (110, "-fifty")]

    ENABLE_COMMAND_PALETTE = False

    def __init__(self) -> None:
        super().__init__(watch_css=True)
        self.preview_image: Image | None = None
        self._wants_to_quit: bool = False

    def compose(self) -> ComposeResult:
        yield Static(classes="padding")
        yield Static(classes="padding")
        yield Static("Welcome to [b][u]rovr[/][/]!")
        yield Static("Let's get you started!")
        yield Static("[dim]Press [/]tab[dim] to navigate the options below.[/]")
        yield Static(classes="padding")
        with Center(), RadioSet(id="theme"):
            yield from [
                RadioButton(theme, value=True, id=theme)
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
                "Vim keybinds~ish",
                id="vim",
                tooltip="keybinds as close to vim as possible",
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
        with Center(classes="settings-editor"):
            with HorizontalGroup(id="settings-editor-file"):
                yield Input(value=os.environ.get("EDITOR", ""), id="editor_input")
                yield Static("File editor")
            with HorizontalGroup(id="settings-editor-folders"):
                yield Input(
                    value=os.environ.get("EDITOR", ""), id="editor_folders_input"
                )
                yield Static("Folder editor")
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
        with Center(classes="compact-things"):
            with HorizontalGroup(id="compact-buttons"):
                yield Switch(value=False, id="compact_buttons")
                yield Static("Use compact header")
            with HorizontalGroup(id="compact-panels"):
                yield Switch(value=False, id="compact_panels")
                yield Static("Use compact panels")
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
        self.query_one("#theme", RadioSet).border_subtitle = "More coming soon…"
        self.query_one("#keybinds", RadioSet).border_title = "Choose a Preset Keybind"
        self.query_one(".plugins", Center).border_title = "Plugins/Integrations"
        self.query_one("SelectCurrent").border_title = "Image Protocol"
        self.query_one(
            ".settings-editor", Center
        ).border_title = "Default editor when editing files"
        self.query_one(".compact-things", Center).border_title = "Compact Mode Options"
        popups = {
            "#plugins-rg": "Uses ripgrep to search all files for content quickly",
            "#plugins-fd": "Uses fd to quickly search for files and directories (and other weird path types)",
            "#plugins-bat": "Uses bat as an alternate previewer",
            "#plugins-zoxide": "Uses zoxide to zip around directories quickly",
            "#plugins-poppler": "Uses poppler-utils to preview PDF files",
            "#plugins-file": "Uses the file(1) command to get better file type information",
            "#compact-buttons": "Makes the header area a bit more compact (5 char tall instead of 7)",
            "#compact-panels": "Makes the panels take lesser size, for more center room",
        }
        for widget, desc in popups.items():
            self.query_one(widget).tooltip = desc
        worker = self._fetch_preview_image()
        try:
            await worker.wait()
            self.preview_image = worker.result
        except Exception:
            return
        if self.preview_image is not None:
            timg_image = prot_to_timg["auto"](
                self.preview_image,
            )
            self.query_one("#image_protocol", VerticalGroup).mount(timg_image)

    @work(thread=True)
    def _fetch_preview_image(self) -> Image | None:
        try:
            with request.urlopen(
                "https://github.com/Textualize/.github/assets/554369/037e6aa1-8527-44f3-958d-28841d975d40"
            ) as response:
                if response.getcode() == 200:
                    data = response.read()
                    return PILImage.open(BytesIO(data))
                else:
                    self.notify(
                        f"Failed to load preview image. Code: {response.getcode()}",
                        severity="error",
                    )
                    return None
        except error.URLError as exc:
            self.notify(
                f"Failed to load preview image. Could not connect to the internet.\n{exc}",
                title=type(exc).__name__,
                severity="error",
            )
            return None

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
        self.query_one("#theme", RadioSet).disabled = event.value
        self.query_one("#theme", RadioSet).tooltip = (
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

    @work
    @on(Button.Pressed, "#finish_setup")
    async def on_finish_setup_pressed(self, event: Button.Pressed) -> None:
        # get appropriate keybind
        with open(
            resources.files("rovr.config.keybinds")
            / f"{self.query_one('#keybinds', RadioSet).pressed_button.id}.toml",
            "r",
        ) as f:
            # hardcoding is my passion
            keybinds_sections: list[str] = f.read().split("\n# plugins\n")
            plugins = tomli.loads(keybinds_sections[1])
            keybinds: str = keybinds_sections[0]
            keybinds = "\n".join([
                line for line in keybinds.splitlines() if not line.startswith("#")
            ])
        # manually create toml file yipee (imagine using tomliw (one extra dependency smh))
        theme = self.query_one("#theme", RadioSet).pressed_button.id
        config_toml = f"""#:schema https://raw.githubusercontent.com/NSPC911/rovr/{schema_ref}/src/rovr/config/schema.json
[interface]
use_reactive_layout = {str(self.query_one("#use_reactive_layout", Switch).value).lower()}
show_hidden_files = {str(self.query_one("#show_hidden_files", Switch).value).lower()}
image_protocol = "{prot_to_schema[str(self.query_one("#image_protocol_select", Select).value)]}"
[interface.compact_mode]
buttons = {str(self.query_one("#compact_buttons", Switch).value).lower()}
panels = {str(self.query_one("#compact_panels", Switch).value).lower()}

[settings.editor]
open_all_in_editor = false

[settings.editor.file]
run = "{_escape_toml_string(self.query_one("#editor_input", Input).value)}"
block = false
suspend = true

[settings.editor.folder]
run = "{_escape_toml_string(self.query_one("#editor_folders_input", Input).value)}"
block = false
suspend = true

[theme]
default = "{theme}"
{f'preview = "{theme}"' if theme in list(get_all_styles()) else ""}
transparent = {str(self.query_one("#transparent_mode", Switch).value).lower()}
{keybinds}

[plugins.rg]
enabled = {str(self.query_one("#plugins-rg Switch", Switch).value).lower()}
keybinds = {plugins["plugins"]["rg"]["keybinds"]}

[plugins.fd]
enabled = {str(self.query_one("#plugins-fd Switch", Switch).value).lower()}
keybinds = {plugins["plugins"]["fd"]["keybinds"]}

[plugins.bat]
enabled = {str(self.query_one("#plugins-bat Switch", Switch).value).lower()}

[plugins.zoxide]
enabled = {str(self.query_one("#plugins-zoxide Switch", Switch).value).lower()}
keybinds = {plugins["plugins"]["zoxide"]["keybinds"]}

[plugins.poppler]
enabled = {str(self.query_one("#plugins-poppler Switch", Switch).value).lower()}

[plugins.file_one]
enabled = {str(self.query_one("#plugins-file Switch", Switch).value).lower()}"""
        # trust me it loads properly
        if await self.push_screen_wait(AskWrite(config_toml)):
            os.makedirs(VAR_TO_DIR["CONFIG"], exist_ok=True)
            with open(f"{VAR_TO_DIR['CONFIG']}/config.toml", "w") as f:
                f.write(config_toml)
            await self.push_screen_wait(FinalStuff())

    @work(exclusive=True)
    async def action_quit(self) -> None:
        if self._wants_to_quit:
            self.exit(1)
        self.notify(
            "You won't be able to do this again. Are you sure?\nYou will be using weird defaults.\n(Press Ctrl+q again)",
            severity="error",
        )
        self._wants_to_quit = True
        await sleep(3)
        self._wants_to_quit = False


if __name__ == "__main__":
    FirstLaunchApp().run()
