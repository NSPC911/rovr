import shutil
from contextlib import suppress
from os import chdir, getcwd, path
from time import perf_counter, sleep
from types import SimpleNamespace
from typing import Callable, Iterable

from rich.console import Console
from textual import events, on, work
from textual.app import WINDOWS, App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.color import ColorParseError
from textual.containers import (
    HorizontalGroup,
    HorizontalScroll,
    Vertical,
    VerticalGroup,
)
from textual.content import Content
from textual.css.errors import StylesheetError
from textual.css.query import NoMatches
from textual.css.stylesheet import StylesheetParseError
from textual.dom import DOMNode
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
from rovr.action_buttons.sort_order import SortOrderButton, SortOrderPopup
from rovr.core import FileList, FileListContainer, PinnedSidebar, PreviewContainer
from rovr.core.file_list import FileListRightClickOptionList
from rovr.footer import Clipboard, MetadataContainer, ProcessContainer
from rovr.functions import icons
from rovr.functions.path import (
    ensure_existing_directory,
    get_filtered_dir_names,
    get_mounted_drives,
    normalise,
)
from rovr.functions.themes import get_custom_themes
from rovr.header import HeaderArea
from rovr.header.tabs import Tabline
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
from rovr.state_manager import StateManager
from rovr.variables.constants import MaxPossible, config
from rovr.variables.maps import VAR_TO_DIR

console = Console()


class Application(App, inherit_bindings=False):
    # don't need ctrl+c
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
        self.log("Starting Rovr...")
        with Vertical(id="root"):
            yield HeaderArea(id="headerArea")
            with VerticalGroup(id="menuwrapper"):
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
                    yield SortOrderButton()
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
                        placeholder=f"{icons.get_icon('general', 'search')[0]} Search"
                    )
                    yield PinnedSidebar(id="pinned_sidebar")
                filelistcontainer = FileListContainer()
                yield filelistcontainer
                yield PreviewContainer(
                    id="preview_sidebar",
                )
            yield FileListRightClickOptionList(
                filelistcontainer.filelist, classes="hidden"
            )
            with HorizontalGroup(id="footer"):
                yield ProcessContainer()
                yield MetadataContainer(id="metadata")
                yield Clipboard(id="clipboard")
            yield StateManager(id="state_manager")

    def on_mount(self) -> None:
        # compact mode
        if config["interface"]["compact_mode"]["buttons"]:
            self.add_class("compact-buttons")
        else:
            self.add_class("comfy-buttons")
        if config["interface"]["compact_mode"]["panels"]:
            self.add_class("compact-panels")
        else:
            self.add_class("comfy-panels")

        # border titles
        self.query_one("#menuwrapper").border_title = "Options"
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
        self.tabWidget: Tabline = self.query_one(Tabline)

        # Change to startup directory. This also calls update_file_list()
        self.cd(
            directory=path.abspath(self.startup_path),
            focus_on=path.basename(self.startup_path),
        )
        self.query_one("#file_list").focus()
        # restore UI state from saved state file
        self.query_one(StateManager).restore_state()
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
        if self.focused is None or not isinstance(self.focused.parent, DOMNode):
            return
        # if current screen isn't the app screen
        if len(self.screen_stack) != 1:
            return
        # Make sure that key binds don't break
        match event.key:
            # placeholder, not yet existing
            case "escape" if self.focused.id and "search" in self.focused.id:
                match self.focused.id:
                    case "search_file_list":
                        self.query_one("#file_list").focus()
                    case "search_pinned_sidebar":
                        self.query_one("#pinned_sidebar").focus()
                return
            # backspace is used by default bindings to head up in history
            # so just avoid it
            case "backspace" if isinstance(self.focused, Input) or (
                self.focused.id and "search" in self.focused.id
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
                self.query_one(StateManager).toggle_pinned_sidebar()
            case key if key in config["keybinds"]["toggle_preview_sidebar"]:
                self.query_one("#file_list").focus()
                self.query_one(StateManager).toggle_preview_sidebar()
            case key if key in config["keybinds"]["toggle_footer"]:
                self.query_one("#file_list").focus()
                self.query_one(StateManager).toggle_footer()
            case key if key in config["keybinds"]["toggle_menuwrapper"]:
                self.query_one("#file_list").focus()
                self.query_one(StateManager).toggle_menuwrapper()
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
                        pathinput: PathInput = self.query_one(PathInput)
                        pathinput.value = response
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

                        def on_response(selected: str | None) -> None:
                            if selected is None:
                                return
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
            case key if key in config["keybinds"]["suspend_app"]:
                if WINDOWS:
                    self.notify(
                        "rovr cannot be suspended on Windows!",
                        title="Suspend App",
                        severity="warning",
                    )
                else:
                    self.action_suspend_process()
            case key if key in config["keybinds"]["change_sort_order"]:
                await self.query_one(SortOrderButton).open_popup(event)

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
        # Write cwd to explicit --cwd-file if provided
        message = ""
        if self._cwd_file:
            try:
                with open(self._cwd_file, "w", encoding="utf-8") as f:
                    f.write(getcwd())
            except OSError:
                message += (
                    f"Failed to write cwd file `{path.basename(self._cwd_file)}`!\n"
                )
        # Write selected/active item(s) to --chooser-file, if provided
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
            try:
                chdir(directory)
            except PermissionError as exc:
                self.notify(
                    f"You cannot enter into {directory}!\n{exc.strerror}",
                    title="App: cd",
                    severity="error",
                )
                return
            except FileNotFoundError:
                self.notify(
                    f"{directory}\nno longer exists!", title="App: cd", severity="error"
                )
                return

        self.query_one("#file_list", FileList).update_file_list(
            add_to_session=add_to_history, focus_on=focus_on
        )
        if hasattr(self, "tabWidget"):
            self.tabWidget.active_tab.session.search = ""
        if callback:
            self.call_later(callback)

    @work(thread=True)
    def watch_for_changes_and_update(self) -> None:
        cwd = getcwd()
        file_list = self.query_one(FileList)
        pins_path = path.join(VAR_TO_DIR["CONFIG"], "pins.json")
        pins_mtime = None
        with suppress(OSError):
            pins_mtime = path.getmtime(pins_path)
        state_path = path.join(VAR_TO_DIR["CONFIG"], "state.toml")
        state_mtime = None
        with suppress(OSError):
            state_mtime = path.getmtime(state_path)
        drives = get_mounted_drives()
        drive_update_every = int(config["settings"]["drive_watcher_frequency"])
        count: int = -1
        while True:
            sleep(1)
            count += 1
            if count >= drive_update_every:
                count = 0
            new_cwd = getcwd()
            if not path.exists(new_cwd):
                file_list.update_file_list(add_to_session=False)
            elif cwd != new_cwd:
                cwd = new_cwd
                continue
            else:
                with suppress(OSError):
                    # this is weird, so `get_filtered_dir_names` is a sync
                    # function, so `call_from_thread` shouldn't be required
                    # but without it, this thread goes in a limbo state where
                    # after quiting, it still runs this, so the app never quits
                    items = self.call_from_thread(
                        get_filtered_dir_names,
                        cwd,
                        config["settings"]["show_hidden_files"],
                    )
                if items != file_list.items_in_cwd:
                    self.cd(cwd)
            # check pins.json
            new_mtime = None
            reload_called: bool = False
            with suppress(OSError):
                new_mtime = path.getmtime(pins_path)
            if new_mtime != pins_mtime:
                pins_mtime = new_mtime
                if new_mtime is not None:
                    self.app.call_from_thread(
                        self.query_one("#pinned_sidebar").reload_pins
                    )
                    reload_called = True
            # check state.toml
            new_state_mtime = None
            with suppress(OSError):
                new_state_mtime = path.getmtime(state_path)
            if new_state_mtime != state_mtime:
                state_mtime = new_state_mtime
                if new_state_mtime is not None:
                    state_manager: StateManager = self.query_one(StateManager)
                    self.app.call_from_thread(state_manager._load_state)
                    self.app.call_from_thread(state_manager.restore_state)
            # check drives
            if count == 0 and not reload_called:
                try:
                    new_drives = get_mounted_drives()
                    if new_drives != drives:
                        drives = new_drives
                        self.app.call_from_thread(
                            self.query_one("#pinned_sidebar").reload_pins
                        )
                except Exception as exc:
                    self.notify(
                        f"{type(exc).__name__}: {exc}",
                        title="Change Watcher",
                        severity="warning",
                    )

    @work(exclusive=True)
    async def on_resize(self, event: events.Resize) -> None:
        if (
            event.size.height < MaxPossible.height
            or event.size.width < MaxPossible.width
        ) and not self.has_pushed_screen:
            self.has_pushed_screen = True
            await self.push_screen_wait(TerminalTooSmall())
            self.has_pushed_screen = False
        self.hide_popups()

    async def _on_css_change(self) -> None:
        if self.css_monitor is not None:
            css_paths = self.css_monitor._paths
        else:
            css_paths = self.css_path
        if css_paths:
            try:
                time = perf_counter()
                stylesheet = self.stylesheet.copy()
                try:
                    # textual issue, i don't want to fix the typing
                    stylesheet.read_all(css_paths)  # ty: ignore[invalid-argument-type]
                except StylesheetError as error:
                    # If one of the CSS paths is no longer available (or perhaps temporarily unavailable),
                    #  we'll end up with partial CSS, which is probably confusing more than anything. We opt to do
                    #  nothing here, knowing that we'll retry again very soon, on the next file monitor invocation.
                    #  Related issue: https://github.com/Textualize/textual/issues/3996
                    self._css_has_errors = True
                    self.notify(
                        str(error),
                        title=f"CSS: {type(error).__name__}",
                        severity="error",
                    )
                    return
                stylesheet.parse()
                elapsed = (perf_counter() - time) * 1000
                self.notify(
                    f"Reloaded {len(css_paths)} CSS files in {elapsed:.0f} ms",
                    title="CSS",
                )
            except StylesheetParseError as exc:
                self._css_has_errors = True
                with self.suspend():
                    console.print(exc.errors)
                    try:
                        console.input(" [bright_blue]Continue? [/]")
                    except EOFError:
                        self.exit(return_code=1)
            except Exception as error:
                # TODO: Catch specific exceptions
                self._css_has_errors = True
                self.bell()
                self.notify(
                    str(error), title=f"CSS: {type(error).__name__}", severity="error"
                )
            else:
                self._css_has_errors = False
                self.stylesheet = stylesheet
                self.stylesheet.update(self)
                for screen in self.screen_stack:
                    self.stylesheet.update(screen)

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
            lambda: self.cd(getcwd()),
        )

    @work
    async def _toggle_transparency(self) -> None:
        self.ansi_color = not self.ansi_color
        await self.push_screen_wait(DummyScreen())
        self.query_one("#file_list").update_border_subtitle()

    @on(events.Click)
    def when_got_click(self, event: events.Click) -> None:
        if (
            not isinstance(event.widget, (FileListRightClickOptionList, SortOrderPopup))
            or event.button == 1
        ):
            self.hide_popups()

    async def hide_popups(self) -> None:
        with suppress(NoMatches):
            self.query_one(FileListRightClickOptionList).add_class("hidden")
        with suppress(NoMatches):
            self.query_one(SortOrderPopup).add_class("hidden")


app = Application(watch_css=True)
