import asyncio
import shutil
from contextlib import suppress
from os import chdir, getcwd, listdir, path
from types import SimpleNamespace
from typing import Callable, Iterable

from textual import events, work
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.color import ColorParseError
from textual.containers import (
    HorizontalGroup,
    HorizontalScroll,
    Vertical,
    VerticalGroup,
)
from textual.content import Content
from textual.css.errors import StyleValueError
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import Input

from rovr.action_buttons import (
    CopyButton,
    CutButton,
    DeleteButton,
    NewItemButton,
    PasteButton,
    PathCopyButton,
    RenameItemButton,
    UnzipButton,
    ZipButton,
)
from rovr.core import (
    FileList,
    PinnedSidebar,
    PreviewContainer,
)
from rovr.footer import Clipboard, MetadataContainer, ProcessContainer
from rovr.functions import icons
from rovr.functions.path import decompress, ensure_existing_directory, normalise
from rovr.functions.themes import get_custom_themes
from rovr.header import HeaderArea
from rovr.navigation_widgets import (
    BackButton,
    ForwardButton,
    PathAutoCompleteInput,
    PathInput,
    UpButton,
)
from rovr.screens import DummyScreen, YesOrNo, ZDToDirectory
from rovr.screens.way_too_small import TerminalTooSmall
from rovr.search_container import SearchInput
from rovr.variables.constants import MaxPossible, config
from rovr.variables.maps import VAR_TO_DIR

max_possible = MaxPossible()


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
    # higher index = higher priority
    CSS_PATH = ["style.tcss", path.join(VAR_TO_DIR["CONFIG"], "style.tcss")]
    # reactivity
    HORIZONTAL_BREAKPOINTS = (
        [(0, "-filelistonly"), (35, "-nopreview"), (70, "-all-horizontal")]
        if config["interface"]["use_reactive_layout"]
        else []
    )
    VERTICAL_BREAKPOINTS = (
        [
            (0, "-middle-only"),
            (16, "-nomenu-atall"),
            (19, "-nopath"),
            (24, "-all-vertical"),
        ]
        if config["interface"]["use_reactive_layout"]
        else []
    )

    def __init__(self, startup_path: str = "", *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.app_blurred = False
        self.startup_path = startup_path
        self.has_pushed_screen = False

    def compose(self) -> ComposeResult:
        print("Starting Rovr...")
        with Vertical(id="root"):
            yield HeaderArea(id="headerArea")
            with HorizontalScroll(id="menu"):
                yield CopyButton()
                yield CutButton()
                yield PasteButton()
                yield NewItemButton()
                yield RenameItemButton()
                yield DeleteButton()
                yield ZipButton()
                yield UnzipButton()
                yield PathCopyButton()
            with VerticalGroup(id="below_menu"):
                with HorizontalGroup():
                    yield BackButton()
                    yield ForwardButton()
                    yield UpButton()
                    path_switcher = PathInput()
                    yield path_switcher
                yield PathAutoCompleteInput(
                    target=path_switcher,
                )
            with HorizontalGroup(id="main"):
                with VerticalGroup(id="pinned_sidebar_container"):
                    yield SearchInput(
                        placeholder=f"({icons.get_icon('general', 'search')[0]}) Search"
                    )
                    yield PinnedSidebar(id="pinned_sidebar")
                with VerticalGroup(id="file_list_container"):
                    yield SearchInput(
                        placeholder=f"({icons.get_icon('general', 'search')[0]}) Search something..."
                    )
                    yield FileList(
                        id="file_list",
                        name="File List",
                        classes="file-list",
                    )
                yield PreviewContainer(
                    id="preview_sidebar",
                )
            with HorizontalGroup(id="footer"):
                yield ProcessContainer()
                yield MetadataContainer(id="metadata")
                yield Clipboard(id="clipboard")

    def on_mount(self) -> None:
        # border titles
        self.query_one("#menu").border_title = "Options"
        self.query_one("#menu").can_focus = False
        self.query_one("#below_menu").border_title = "Directory Actions"
        self.query_one("#pinned_sidebar_container").border_title = "Sidebar"
        self.query_one("#file_list_container").border_title = "Files"
        self.query_one("#processes").border_title = "Processes"
        self.query_one("#metadata").border_title = "Metadata"
        self.query_one("#clipboard").border_title = "Clipboard"
        # themes
        try:
            for theme in get_custom_themes():
                self.register_theme(theme)
            parse_failed = False
        except ColorParseError as e:
            parse_failed = True
            exception = e
        if parse_failed:
            self.exit(
                return_code=1,
                message=Content.from_markup(
                    f"[underline ansi_red]Config Error[/]\n[bold ansi_cyan]custom_themes.bar_gradient[/]: {exception}"
                ),
            )
            return
        self.theme = config["theme"]["default"]
        self.ansi_color = config["theme"]["transparent"]
        # tooltips
        if config["interface"]["tooltips"]:
            self.query_one("#back").tooltip = "Go back in history"
            self.query_one("#forward").tooltip = "Go forward in history"
            self.query_one("#up").tooltip = "Go up the directory tree"
        self.tabWidget = self.query_one("Tabline")

        # Change to startup directory. This also calls update_file_list()
        # causing the file_list to get populated
        self.cd(
            directory=path.abspath(self.startup_path),
            focus_on=path.basename(self.startup_path),
        )
        self.query_one("#file_list").focus()
        # start mini watcher
        self.watch_for_changes_and_update()

    @work
    async def action_focus_next(self) -> None:
        if config["settings"]["allow_tab_nav"]:
            super().action_focus_next()

    @work
    async def action_focus_previous(self) -> None:
        if config["settings"]["allow_tab_nav"]:
            super().action_focus_previous()

    async def on_key(self, event: events.Key) -> None:
        # Not really sure why this can happen, but I will still handle this
        if self.focused is None or not self.focused.id:
            return
        # Make sure that key binds don't break
        match event.key:
            # placeholder, not yet existing
            case "escape" if "search" in self.focused.id:
                match self.focused.id:
                    case "search_file_list":
                        self.query_one("#file_list").focus()
                    case "search_pinned_sidebar":
                        self.query_one("#pinned_sidebar").focus()
                return
            # backspace is used by default bindings to head up in history
            # so just avoid it
            case "backspace" if (
                type(self.focused) is Input or "search" in self.focused.id
            ):
                return
            # focus toggle pinned sidebar
            case key if key in config["keybinds"]["focus_toggle_pinned_sidebar"]:
                if (
                    self.focused.id == "pinned_sidebar"
                    or "hide" in self.query_one("#pinned_sidebar_container").classes
                ):
                    self.query_one("#file_list").focus()
                elif self.query_one("#pinned_sidebar_container").display:
                    self.query_one("#pinned_sidebar").focus()
            # Focus file list from anywhere except input
            case key if key in config["keybinds"]["focus_file_list"]:
                self.query_one("#file_list").focus()
            # Focus toggle preview sidebar
            case key if key in config["keybinds"]["focus_toggle_preview_sidebar"]:
                if (
                    self.focused.id == "preview_sidebar"
                    or self.focused.parent.id == "preview_sidebar"
                    or "hide" in self.query_one("#preview_sidebar").classes
                ):
                    self.query_one("#file_list").focus()
                elif self.query_one(PreviewContainer).display:
                    with suppress(NoMatches):
                        self.query_one("PreviewContainer > *").focus()
                else:
                    self.query_one("#file_list").focus()
            # Focus path switcher
            case key if key in config["keybinds"]["focus_toggle_path_switcher"]:
                self.query_one("#path_switcher").focus()
            # Focus processes
            case key if key in config["keybinds"]["focus_toggle_processes"]:
                if (
                    self.focused.id == "processes"
                    or "hide" in self.query_one("#processes").classes
                ):
                    self.query_one("#file_list").focus()
                elif self.query_one("#footer").display:
                    self.query_one("#processes").focus()
            # Focus metadata
            case key if key in config["keybinds"]["focus_toggle_metadata"]:
                if self.focused.id == "metadata":
                    self.query_one("#file_list").focus()
                elif self.query_one("#footer").display:
                    self.query_one("#metadata").focus()
            # Focus clipboard
            case key if key in config["keybinds"]["focus_toggle_clipboard"]:
                if self.focused.id == "clipboard":
                    self.query_one("#file_list").focus()
                elif self.query_one("#footer").display:
                    self.query_one("#clipboard").focus()
            # Toggle hiding panels
            case key if key in config["keybinds"]["toggle_pinned_sidebar"]:
                self.query_one("#file_list").focus()
                if self.query_one("#pinned_sidebar_container").display:
                    self.query_one("#pinned_sidebar_container").add_class("hide")
                else:
                    self.query_one("#pinned_sidebar_container").remove_class("hide")
            case key if key in config["keybinds"]["toggle_preview_sidebar"]:
                self.query_one("#file_list").focus()
                if self.query_one(PreviewContainer).display:
                    self.query_one(PreviewContainer).add_class("hide")
                else:
                    self.query_one(PreviewContainer).remove_class("hide")
            case key if key in config["keybinds"]["toggle_footer"]:
                self.query_one("#file_list").focus()
                if self.query_one("#footer").display:
                    self.query_one("#footer").add_class("hide")
                else:
                    self.query_one("#footer").remove_class("hide")
            case key if (
                key in config["keybinds"]["tab_next"]
                and self.tabWidget.active_tab is not None
            ):
                self.tabWidget.action_next_tab()
            case key if (
                self.tabWidget.active_tab is not None
                and key in config["keybinds"]["tab_previous"]
            ):
                self.tabWidget.action_previous_tab()
            case key if key in config["keybinds"]["tab_new"]:
                await self.tabWidget.add_tab(after=self.tabWidget.active_tab)
            case key if (
                self.tabWidget.tab_count > 1 and key in config["keybinds"]["tab_close"]
            ):
                await self.tabWidget.remove_tab(self.tabWidget.active_tab)
            # zoxide
            case key if (
                config["plugins"]["zoxide"]["enabled"]
                and event.key in config["plugins"]["zoxide"]["keybinds"]
            ):
                if shutil.which("zoxide") is None:
                    self.notify(
                        "Zoxide is not installed or not in PATH.",
                        title="Zoxide",
                        severity="error",
                    )

                def on_response(response: str) -> None:
                    """Handle the response from the ZDToDirectory dialog."""
                    if response:
                        pathinput = self.query_one(PathInput)
                        pathinput.value = decompress(response).replace(path.sep, "/")
                        pathinput.on_input_submitted(
                            SimpleNamespace(value=pathinput.value)
                        )

                self.push_screen(ZDToDirectory(), on_response)
            # zen mode
            case key if (
                config["plugins"]["zen_mode"]["enabled"]
                and key in config["plugins"]["zen_mode"]["keybinds"]
            ):
                if "zen" in self.classes:
                    self.remove_class("zen")
                else:
                    self.add_class("zen")
            # toggle hidden files
            case key if key in config["keybinds"]["toggle_hidden_files"]:
                file_list = self.query_one("#file_list")
                await file_list.toggle_hidden_files()

    def on_app_blur(self, event: events.AppBlur) -> None:
        self.app_blurred = True

    def on_app_focus(self, event: events.AppFocus) -> None:
        self.app_blurred = False

    @work
    async def action_quit(self) -> None:
        process_container = self.query_one(ProcessContainer)
        if len(process_container.query("ProgressBarContainer")) != len(
            process_container.query(".done")
        ) + len(process_container.query(".error")) and not await self.push_screen_wait(
            YesOrNo(
                f"{len(process_container.query('ProgressBarContainer')) - len(process_container.query('.done')) - len(process_container.query('.error'))}"
                + " processes are still running!\nAre you sure you want to quit?",
                border_title="Quit [teal]rovr[/teal]",
            )
        ):
            return
        if config["settings"]["cd_on_quit"]:
            with open(
                path.join(VAR_TO_DIR["CONFIG"], "rovr_quit_cd_path"), "w"
            ) as file:
                file.write(getcwd())
                print(getcwd())
        self.exit()

    def cd(
        self,
        directory: str,
        add_to_history: bool = True,
        focus_on: str | None = None,
        callback: Callable | None = None,
    ) -> None:
        # Makes sure `directory` is a directory, or chdir will fail with exception
        directory = ensure_existing_directory(directory)

        if normalise(getcwd()) == normalise(directory):
            add_to_history = False
        else:
            chdir(directory)

        self.query_one("#file_list").update_file_list(
            add_to_session=add_to_history, focus_on=focus_on
        )
        if callback:
            self.call_later(callback)

    @work
    async def watch_for_changes_and_update(self) -> None:
        self._cwd = getcwd()
        self._items = listdir(self._cwd)
        while True:
            await asyncio.sleep(1)
            new_cwd = getcwd()
            try:
                new_cwd_items = listdir(new_cwd)
            except PermissionError:
                continue
            if self._cwd != new_cwd:
                self._cwd = new_cwd
                self._items = listdir(self._cwd)
            elif self._items != new_cwd_items:
                self.cd(self._cwd)
                self._items = new_cwd_items

    @work
    async def on_resize(self, event: events.Resize) -> None:
        if (
            event.size.height < max_possible.height
            or event.size.width < max_possible.width
        ) and not self.has_pushed_screen:
            self.has_pushed_screen = True
            await self.push_screen_wait(TerminalTooSmall())
            self.has_pushed_screen = False

    async def _on_css_change(self) -> None:
        try:
            await super()._on_css_change()
            if self._css_has_errors:
                self.notify(
                    "Errors were found in the TCSS!",
                    title="Stylesheet Watcher",
                    severity="error",
                )
            else:
                self.notify(
                    "TCSS reloaded successfully!",
                    title="Stylesheet Watcher",
                    severity="information",
                )
        except StyleValueError as exc:
            self.notify(
                f"Errors were found in the TCSS!\n{exc}",
                title="Stylesheet Watcher",
                severity="error",
            )

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        if not self.ansi_color:
            yield SystemCommand(
                "Change theme",
                "Change the current theme",
                self.action_change_theme,
            )
        yield SystemCommand(
            "Quit the application",
            "Quit the application as soon as possible",
            self.action_quit,
        )

        # # the HelpPanel will need some fixes.
        # if screen.query("HelpPanel"):
        #     yield SystemCommand(
        #         "Hide keys and help panel",
        #         "Hide the keys and widget help panel",
        #         self.action_hide_help_panel,
        #     )
        # else:
        #     yield SystemCommand(
        #         "Show keys and help panel",
        #         "Show help for the focused widget and a summary of available keys",
        #         self.action_show_help_panel,
        #     )

        if screen.maximized is not None:
            yield SystemCommand(
                "Minimize",
                "Minimize the widget and restore to normal size",
                screen.action_minimize,
            )
        elif screen.focused is not None and screen.focused.allow_maximize:
            yield SystemCommand(
                "Maximize", "Maximize the focused widget", screen.action_maximize
            )

        yield SystemCommand(
            "Save screenshot",
            "Save an SVG 'screenshot' of the current screen",
            lambda: self.set_timer(0.1, self.deliver_screenshot),
        )

        if self.ansi_color:
            yield SystemCommand(
                "Disable Transparent Theme",
                "Go back to an opaque background.",
                lambda: self.set_timer(0.1, self._toggle_transparency),
            )
        else:
            yield SystemCommand(
                "Enable Transparent Theme",
                "Have a transparent background.",
                lambda: self.set_timer(0.1, self._toggle_transparency),
            )

    @work
    async def _toggle_transparency(self) -> None:
        self.ansi_color = not self.ansi_color
        await self.push_screen_wait(DummyScreen())


app = Application(watch_css=True)
