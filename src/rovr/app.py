import asyncio
import shutil
from contextlib import suppress
from os import chdir, getcwd, path
from types import SimpleNamespace
from typing import Callable, Iterable

from textual import events, on, work
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
from rovr.core.file_list import FileListRightClickOptionList
from rovr.footer import Clipboard, MetadataContainer, ProcessContainer
from rovr.functions import icons
from rovr.functions.path import (
    decompress,
    ensure_existing_directory,
    get_filtered_dir_names,
    normalise,
)
from rovr.functions.themes import get_custom_themes
from rovr.header import HeaderArea
from rovr.navigation_widgets import (
    BackButton,
    ForwardButton,
    PathAutoCompleteInput,
    PathInput,
    UpButton,
)
from rovr.screens import DummyScreen, FileSearch, Keybinds, YesOrNo, ZDToDirectory
from rovr.screens.way_too_small import TerminalTooSmall
from rovr.search_container import SearchInput
from rovr.variables.constants import MaxPossible, config
from rovr.variables.maps import VAR_TO_DIR

max_possible = MaxPossible()


class Application(App, inherit_bindings=False):
    # dont need ctrl+c
    BINDINGS = [
        Binding(
            key,
            "quit",
            "Quit",
            tooltip="Quit the app and return to the command prompt.",
            show=False,
            priority=True,
        )
        for key in config["keybinds"]["quit_app"]
    ]
    # higher index = higher priority
    CSS_PATH = ["style.tcss", path.join(VAR_TO_DIR["CONFIG"], "style.tcss")]

    # command palette
    COMMAND_PALETTE_BINDING = config["keybinds"]["command_palette"]

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
    CLICK_CHAIN_TIME_THRESHOLD: int = config["settings"]["double_click_delay"]

    def __init__(
        self,
        startup_path: str = "",
        *,
        cwd_file: str | None = None,
        chooser_file: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.app_blurred: bool = False
        self.startup_path: str = startup_path
        self.has_pushed_screen: bool = False
        # Runtime output files from CLI
        self._cwd_file: str | None = cwd_file
        self._chooser_file: str | None = chooser_file

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
                    filelist = FileList(
                        id="file_list",
                        name="File List",
                        classes="file-list",
                    )
                    yield filelist
                yield PreviewContainer(
                    id="preview_sidebar",
                )
            with HorizontalGroup(id="footer"):
                yield ProcessContainer()
                yield MetadataContainer(id="metadata")
                yield Clipboard(id="clipboard")
            yield FileListRightClickOptionList(filelist, classes="hidden")

    def on_mount(self) -> None:
        # compact mode
        if config["interface"]["compact_mode"]:
            self.add_class("compact")
        else:
            self.remove_class("compact")

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
        # disable scrollbars
        self.show_horizontal_scrollbar = False
        self.show_vertical_scrollbar = False

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
        # if current screen isn't the app screen
        if len(self.screen_stack) != 1:
            return
        # Make sure that key binds don't break
        match event.key:
            # finder: fd/fzf
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
            # keybinds
            case key if key in config["keybinds"]["show_keybinds"]:
                self.push_screen(Keybinds())
            case key if (
                config["plugins"]["finder"]["enabled"]
                and key in config["plugins"]["finder"]["keybinds"]
            ):
                fd_exec: str = config["plugins"]["finder"]["executable"]
                if shutil.which(fd_exec) is not None:
                    try:

                        def on_response(selected_compressed: str | None) -> None:
                            if not selected_compressed:
                                return
                            selected = decompress(selected_compressed)
                            if path.isdir(selected):
                                self.cd(selected)
                            else:
                                self.cd(
                                    "." if selected == "" else path.dirname(selected),
                                    focus_on=path.basename(selected),
                                )

                        self.push_screen(FileSearch(), on_response)
                    except Exception as exc:
                        self.notify(str(exc), title="Finder", severity="error")
                else:
                    self.notify(
                        f"{config['plugins']['finder']['executable']} cannot be found in PATH.",
                        title="Plugins: finder",
                        severity="error",
                    )

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
        # 1) Write cwd to explicit --cwd-file if provided
        message = ""
        if self._cwd_file:
            try:
                with open(self._cwd_file, "w", encoding="utf-8") as f:
                    f.write(getcwd())
            except OSError:
                message += (
                    f"Failed to write cwd file `{path.basename(self._cwd_file)}`!\n"
                )
        # 2) Otherwise, honor legacy cd_on_quit behavior
        elif config["settings"]["cd_on_quit"]:
            try:
                with open(
                    path.join(VAR_TO_DIR["CONFIG"], "rovr_quit_cd_path"),
                    "w",
                    encoding="utf-8",
                ) as file:
                    file.write(getcwd())
            except OSError:
                message += "Failed to write `rovr_quit_cd_path`!\n"
        # 3) Write selected/active item(s) to --chooser-file, if provided
        if self._chooser_file:
            try:
                file_list = self.query_one("#file_list")
                selected = await file_list.get_selected_objects()
                if selected:
                    with open(self._chooser_file, "w", encoding="utf-8") as f:
                        f.write("\n".join(selected))
            except OSError:
                # Any failure writing chooser file should not block exit
                message += f"Failed to write chooser file `{path.basename(self._chooser_file)}`"
        self.exit(message.strip())

    def cd(
        self,
        directory: str,
        add_to_history: bool = True,
        focus_on: str | None = None,
        callback: Callable | None = None,
    ) -> None:
        # Makes sure `directory` is a directory, or chdir will fail with exception
        directory = ensure_existing_directory(directory)

        if normalise(getcwd()) == normalise(directory) or directory == "":
            add_to_history = False
        else:
            chdir(directory)

        self.query_one("#file_list", FileList).update_file_list(
            add_to_session=add_to_history, focus_on=focus_on
        )
        if hasattr(self, "tabWidget"):
            self.tabWidget.active_tab.session.search = ""
        if callback:
            self.call_later(callback)

    @work
    async def watch_for_changes_and_update(self) -> None:
        cwd = getcwd()
        items = get_filtered_dir_names(cwd, config["settings"]["show_hidden_files"])
        file_list = self.query_one(FileList)
        while True:
            await asyncio.sleep(1)
            new_cwd = getcwd()
            try:
                items = get_filtered_dir_names(
                    cwd, config["settings"]["show_hidden_files"]
                )
            except OSError:
                # PermissionError falls under this, but we catch everything else
                continue
            if cwd != new_cwd:
                cwd = new_cwd
            elif items != file_list.items_in_cwd:
                self.cd(cwd)

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

        # shortcuts panel
        yield SystemCommand(
            "Show keybinds available",
            "Show an interactive list of keybinds that have been set in the config",
            lambda: self.push_screen(Keybinds()),
        )

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

        if (
            config["plugins"]["finder"]["enabled"]
            and config["plugins"]["finder"]["keybinds"]
        ):
            yield SystemCommand(
                "Open finder",
                "Start searching the current directory using `fd`",
                lambda: self.on_key(
                    events.Key(
                        key=config["plugins"]["finder"]["keybinds"][0],
                        # character doesn't matter
                        character=config["plugins"]["finder"]["keybinds"][0],
                    )
                ),
            )
        if (
            config["plugins"]["zoxide"]["enabled"]
            and config["plugins"]["zoxide"]["keybinds"]
        ):
            yield SystemCommand(
                "Open zoxide",
                "Start searching for a directory to `z` to",
                lambda: self.on_key(
                    events.Key(
                        key=config["plugins"]["zoxide"]["keybinds"][0],
                        # character doesn't matter
                        character=config["plugins"]["zoxide"]["keybinds"][0],
                    )
                ),
            )
        if config["keybinds"]["toggle_hidden_files"]:
            if config["settings"]["show_hidden_files"]:
                yield SystemCommand(
                    "Hide Hidden Files",
                    "Exclude listing of hidden files and folders",
                    self.query_one("#file_list").toggle_hidden_files,
                )
            else:
                yield SystemCommand(
                    "Show Hidden Files",
                    "Include listing of hidden files and folders",
                    self.query_one("#file_list").toggle_hidden_files,
                )
        yield SystemCommand(
            "Reload File List",
            "Send a forceful reload of the file list, in case something goes wrong",
            lambda: self.cd(getcwd())
        )

    @work
    async def _toggle_transparency(self) -> None:
        self.ansi_color = not self.ansi_color
        await self.push_screen_wait(DummyScreen())
        self.query_one("#file_list").update_border_subtitle()

    @on(events.Click)
    @work(thread=True)
    def when_got_click(self, event: events.Click) -> None:
        if (
            not isinstance(event.widget, FileListRightClickOptionList)
            or event.button != 3
        ):
            self.query_one(FileListRightClickOptionList).add_class("hidden")


app = Application(watch_css=True)
