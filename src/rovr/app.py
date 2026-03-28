import asyncio
import threading
from contextlib import suppress
from io import TextIOWrapper
from os import chdir, getcwd, path
from time import perf_counter
from typing import Callable, Iterable, overload

from rich.console import Console, RenderableType
from rich.protocol import is_renderable
from textual import constants, events, on, work
from textual.app import WINDOWS, App, ComposeResult, ScreenStackError, SystemCommand
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
from textual.css.query import NoMatches, QueryType
from textual.css.stylesheet import StylesheetParseError
from textual.dom import DOMNode
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Input, Label
from textual.worker import Worker

from rovr.action_buttons import (
    CopyButton,
    CutButton,
    DeleteButton,
    NewItemButton,
    PasteButton,
    RenameItemButton,
    UnzipButton,
    ZipButton,
)
from rovr.action_buttons.sort_order import SortOrderButton, SortOrderPopup
from rovr.classes.type_aliases import DirEntryType
from rovr.components import SearchInput
from rovr.components.popup_option_list import PopupOptionList
from rovr.core import (
    FileList,
    FileListContainer,
    FileListRightClickOptionList,
    PinnedSidebar,
    PreviewContainer,
)
from rovr.footer import Clipboard, MetadataContainer, ProcessContainer
from rovr.functions import icons
from rovr.functions.path import (
    dump_exc,
    ensure_existing_directory,
    get_direntry_for,
    get_filtered_dir_names,
    get_mounted_drives,
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
from rovr.screens.typed import ShellExecReturnType
from rovr.state_manager import StateManager
from rovr.variables.constants import MaxPossible, config, log_name
from rovr.variables.maps import RovrVars

console = Console()

if constants.SCREENSHOT_LOCATION:
    constants.SCREENSHOT_LOCATION = normalise(getcwd(), constants.SCREENSHOT_LOCATION)


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
    CSS_PATH = ["style.tcss"] + (
        [path.join(RovrVars.ROVRCONFIG, "style.tcss")]
        if path.exists(path.join(RovrVars.ROVRCONFIG, "style.tcss"))
        else []
    )

    CUSTOM_STYLE_AVAILABLE: bool = path.exists(
        path.join(RovrVars.ROVRCONFIG, "style.tcss")
    )

    # command palette
    COMMAND_PALETTE_BINDING = config["keybinds"]["command_palette"]

    # reactivity
    HORIZONTAL_BREAKPOINTS = (
        [(0, "-filelist-only"), (35, "-no-preview"), (70, "-all-horizontal")]
        if config["interface"]["use_reactive_layout"]
        else []
    )
    VERTICAL_BREAKPOINTS = (
        [
            (0, "-middle-only"),
            (16, "-no-menu-at-all"),
            (19, "-no-path"),
            (24, "-all-vertical"),
        ]
        if config["interface"]["use_reactive_layout"]
        else []
    )
    CLICK_CHAIN_TIME_THRESHOLD = config["interface"]["double_click_delay"]

    def __init__(
        self,
        startup_path: str = "",
        *,
        cwd_file: str | TextIOWrapper | None = None,
        chooser_file: str | TextIOWrapper | None = None,
        show_keys: bool = False,
        tree_dom: bool = False,
        force_crash_in: float = 0,
    ) -> None:
        super().__init__(watch_css=True)
        self.app_blurred: bool = False
        self.has_pushed_screen: bool = False
        # Runtime output files from CLI
        self._cwd_file: str | TextIOWrapper | None = cwd_file
        self._chooser_file: str | TextIOWrapper | None = chooser_file
        self._show_keys: bool = show_keys
        self._exit_with_tree: bool = tree_dom
        self._force_crash_in: float = force_crash_in
        self._pins_mtime: float | None = None
        self._highlighted_file_mtime: float | None = None

        self._file_list_container = FileListContainer()
        self.file_list = self._file_list_container.filelist
        # shutdown event for bg thread
        self._shutdown_event = threading.Event()
        # cannot use self.clipboard, reserved for Textual's clipboard
        self.Clipboard = Clipboard()
        if startup_path:
            chdir(ensure_existing_directory(startup_path))

    def compose(self) -> ComposeResult:
        self.log("Starting Rovr...")
        root_classes = (
            "compact-buttons"
            if config["interface"]["compact_mode"]["buttons"]
            else "comfy-buttons" + " compact-panels"
            if config["interface"]["compact_mode"]["panels"]
            else " comfy-panels"
        )
        with Vertical(id="root", classes=root_classes):
            header = HeaderArea()
            self.tabWidget = header.tabline
            yield header
            with VerticalGroup(id="menu_wrapper"):
                with HorizontalScroll(id="menu"):
                    yield CopyButton()
                    yield CutButton()
                    yield PasteButton()
                    yield NewItemButton()
                    yield RenameItemButton()
                    yield DeleteButton()
                    yield ZipButton()
                    yield UnzipButton()
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
                yield self._file_list_container
                yield PreviewContainer()
            with HorizontalGroup(id="footer"):
                yield ProcessContainer()
                yield MetadataContainer()
                yield self.Clipboard
            yield StateManager()

    def on_mount(self) -> None:
        # exit for tree print
        if self._exit_with_tree:
            console = Console()
            with self.suspend():
                console.print(self.tree)
                self.exit()
            return

        # themes
        try:
            for theme in get_custom_themes():
                self.register_theme(theme)
            parse_failed = False
        except ColorParseError as exc:
            parse_failed = True
            exception = exc
        if parse_failed:
            self.exit(
                return_code=1,
                message=Content.from_markup(
                    f"[underline ansi_red]Config Error[/]\n[bold ansi_cyan]custom_themes.bar_gradient[/]: {exception}"
                ),
            )
            return
        self.theme = config["theme"]["default"]
        if self.theme == "dark-pink":
            from rovr.functions.config import get_version

            self.notify(
                f"The 'dark-pink' theme will be removed in v0.8.0 (Current version is {get_version()}). Switch to 'rose_pine' instead.",
                title="Deprecation",
                severity="warning",
            )
        self.ansi_color = config["theme"]["transparent"]

        # title for screenshots
        self.title = ""

        if self._force_crash_in > 0:
            self.call_later(self._force_crash)

        self.call_after_refresh(self._finish_post_mount_setup)

    def _finish_post_mount_setup(self) -> None:
        # border titles
        self.query_one("#menu_wrapper").border_title = "Options"
        self.query_one("#pinned_sidebar_container").border_title = "Sidebar"
        self.query_one("#file_list_container").border_title = "Files"
        self.query_one("#processes").border_title = "Processes"
        self.query_one("#metadata").border_title = "Metadata"
        self.Clipboard.border_title = "Clipboard"

        # tooltips
        if config["interface"]["tooltips"]:
            self.query_one("#back").tooltip = "Go back in history"
            self.query_one("#forward").tooltip = "Go forward in history"
            self.query_one("#up").tooltip = "Go up the directory tree"

        # restore UI state from saved state file
        state_manager = self.query_one(StateManager)
        state_manager.restore_state()
        # Apply folder-specific sort preferences for initial directory
        state_manager.apply_folder_sort_prefs(normalise(getcwd()))
        # start mini watcher
        self.watch_for_changes_and_update()
        # disable scrollbars
        self.show_horizontal_scrollbar = False
        self.show_vertical_scrollbar = False
        # for show keys
        if self._show_keys:
            label = Label("", id="showKeys")
            self.query_one("#below_menu > HorizontalGroup").mount(
                label, after="PathInput"
            )

    @work
    async def _force_crash(self) -> None:
        await asyncio.sleep(self._force_crash_in)
        1 / 0

    def on_unmount(self) -> None:
        self._shutdown_event.set()

    def action_focus_next(self) -> None:
        if config["interface"]["allow_tab_nav"]:
            super().action_focus_next()

    def action_focus_previous(self) -> None:
        if config["interface"]["allow_tab_nav"]:
            super().action_focus_previous()

    async def on_key(self, event: events.Key) -> None:
        from rovr.functions.utils import check_key

        # show key
        if self._show_keys:
            with suppress(NoMatches):
                self.query_one("#showKeys").update(event.key)
                self.query_one("#showKeys").tooltip = (
                    f"Key = '{event.key}'"
                    + (
                        f"\nCharacter = '{event.character}'"
                        if event.is_printable
                        else ""
                    )
                    + f"\nAliases = {event.aliases}"
                )

        # Not really sure why this can happen, but I will still handle this
        if self.focused is None or not isinstance(self.focused.parent, DOMNode):
            return
        # if current screen isn't the app screen
        if len(self.screen_stack) != 1:
            return
        # Make sure that key binds don't break
        # placeholder, not yet existing
        if event.key == "escape" and self.focused.id and "search" in self.focused.id:
            if self._focused_id == "search_file_list":
                self.file_list.focus()
            elif self._focused_id == "search_pinned_sidebar":
                self.query_one("#pinned_sidebar").focus()
            return
        # backspace is used by default bindings to head up in history
        # so just avoid it
        elif event.key == "backspace" and (
            isinstance(self.focused, Input)
            or (self.focused.id and "search" in self.focused.id)
        ):
            return
        # focus toggle pinned sidebar
        elif check_key(event, config["keybinds"]["focus_toggle_pinned_sidebar"]):
            self.action_focus_toggle_pinned_sidebar()
        # Focus file list from anywhere except input
        elif check_key(event, config["keybinds"]["focus_file_list"]):
            self.action_focus_file_list()
        # Focus toggle preview sidebar
        elif check_key(event, config["keybinds"]["focus_toggle_preview_sidebar"]):
            self.action_focus_toggle_preview_sidebar()
        # Focus path switcher
        elif check_key(event, config["keybinds"]["focus_toggle_path_switcher"]):
            self.action_focus_path_switcher()
        # Focus processes
        elif check_key(event, config["keybinds"]["focus_toggle_processes"]):
            self.action_focus_toggle_processes()
        # Focus metadata
        elif check_key(event, config["keybinds"]["focus_toggle_metadata"]):
            self.action_focus_toggle_metadata()
        # Focus clipboard
        elif check_key(event, config["keybinds"]["focus_toggle_clipboard"]):
            self.action_focus_toggle_clipboard()
        # Toggle hiding panels
        elif check_key(event, config["keybinds"]["toggle_pinned_sidebar"]):
            self.action_toggle_pinned_sidebar()
        elif check_key(event, config["keybinds"]["toggle_preview_sidebar"]):
            self.action_toggle_preview_sidebar()
        elif check_key(event, config["keybinds"]["toggle_footer"]):
            self.action_toggle_footer()
        elif check_key(event, config["keybinds"]["toggle_menu_wrapper"]):
            self.action_toggle_menu_wrapper()
        elif check_key(event, config["keybinds"]["tab_next"]):
            self.action_tab_next()
        elif check_key(event, config["keybinds"]["tab_previous"]):
            self.action_tab_previous()
        elif check_key(event, config["keybinds"]["tab_new"]):
            await self.action_tab_new()
        elif check_key(event, config["keybinds"]["tab_close"]):
            await self.action_tab_close()
        elif check_key(event, config["keybinds"]["show_keybinds"]):
            self.action_show_keybinds()
        elif check_key(event, config["keybinds"]["show_shell_screen"]):
            self.action_show_shell_screen()
        # zoxide
        elif check_key(event, config["plugins"]["zoxide"]["keybinds"]):
            self.action_plugin_zoxide()
        # keybinds
        elif check_key(event, config["plugins"]["fd"]["keybinds"]):
            self.action_plugin_fd()
        elif check_key(event, config["plugins"]["rg"]["keybinds"]):
            self.action_plugin_rg()
        elif check_key(event, config["keybinds"]["suspend_process"]):
            self.action_suspend_process()

    @work
    async def on_shell_exec_response(
        self, response: ShellExecReturnType | None
    ) -> None:
        if response is None or response.command == "":
            return
        match response.mode:
            case "background":
                proc = await asyncio.create_subprocess_shell(
                    response.command,
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                self.notify(
                    f"stdout: {stdout.decode(errors='ignore').strip()}\nstderr: {stderr.decode(errors='ignore').strip()}",
                    title=f"Shell: {response.command}",
                    severity="information" if proc.returncode == 0 else "error",
                    markup=False,
                )
            case "block":
                import subprocess

                output = subprocess.run(  # noqa: ASYNC221
                    response.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.notify(
                    f"stdout: {output.stdout.strip()}\nstderr: {output.stderr.strip()}",
                    title=f"Shell: {response.command}",
                    severity="information" if output.returncode == 0 else "error",
                    markup=False,
                )
            case "suspend":
                import subprocess

                with self.suspend():
                    # intended to block the app, await does nothing because the
                    # app itself is suspended
                    output = subprocess.run(  # noqa: ASYNC221
                        response.command,
                        shell=True,
                        check=False,
                    )
                self.notify(
                    f"Command '{response.command}' finished with return code {output.returncode}.",
                    title=f"Shell: {response.command}",
                    severity="information" if output.returncode == 0 else "error",
                    markup=False,
                )

    def on_app_blur(self, event: events.AppBlur) -> None:
        self.app_blurred = True

    def on_app_focus(self, event: events.AppFocus) -> None:
        self.app_blurred = False

    @work
    async def action_quit(self) -> None:
        from rovr.screens import YesOrNo

        process_container = self.query_one(ProcessContainer)
        if len(process_container.query("ProgressBarContainer")) != len(
            process_container.query(".done")
        ) + len(process_container.query(".error")) and not await self.push_screen_wait(
            YesOrNo(
                f"{len(process_container.query('ProgressBarContainer')) - len(process_container.query('.done')) - len(process_container.query('.error'))}"
                + " processes are still running!\nAre you sure you want to quit?",
                border_title="Quit [teal]rovr[/teal]",
                destructive=True,
            )
        ):
            return
        # Write cwd to explicit --cwd-file if provided
        message = ""
        if self._cwd_file:
            if isinstance(self._cwd_file, TextIOWrapper):
                try:
                    self._cwd_file.write(getcwd())
                    self._cwd_file.flush()
                except OSError:
                    message += "Failed to write cwd to stdout!\n"
            else:
                try:
                    with open(self._cwd_file, "w", encoding="utf-8") as f:
                        f.write(getcwd())
                except OSError:
                    message += (
                        f"Failed to write cwd file `{path.basename(self._cwd_file)}`!\n"
                    )
        # Write selected/active item(s) to --chooser-file, if provided
        if self._chooser_file:
            selected = await self.file_list.get_selected_objects()
            if selected:
                if isinstance(self._chooser_file, TextIOWrapper):
                    try:
                        self._chooser_file.write("\n".join(selected))
                        self._chooser_file.flush()
                    except OSError:
                        message += "Failed to write chooser to stdout!\n"
                else:
                    try:
                        with open(self._chooser_file, "w", encoding="utf-8") as f:
                            f.write("\n".join(selected))
                    except OSError:
                        # Any failure writing chooser file should not block exit
                        message += f"Failed to write chooser file `{path.basename(self._chooser_file)}`"
        self.exit(message.strip() if message else None)

    def cd(
        self,
        directory: str,
        add_to_history: bool = True,
        focus_on: str | None = None,
        has_selected: bool = False,
        callback: Callable | None = None,
        clear_search: bool = True,
    ) -> Worker | None:
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
                    markup=False,
                )
                return
            except FileNotFoundError:
                self.notify(
                    f"{directory}\nno longer exists!",
                    title="App: cd",
                    severity="error",
                    markup=False,
                )
                return

        # Apply folder-specific sort preferences if they exist
        with suppress(NoMatches):
            state_manager: StateManager = self.query_one(StateManager)
            state_manager.apply_folder_sort_prefs(normalise(getcwd()))

        return self.file_list.update_file_list(
            add_to_session=add_to_history,
            focus_on=focus_on,
            has_selected=has_selected,
            callback=callback,
            clear_search=clear_search,
        )

    @work(thread=True)
    def watch_for_changes_and_update(self) -> None:
        cwd = getcwd()
        file_list: FileList = self.query_one(FileList)
        pins_path = path.join(RovrVars.ROVRCONFIG, "pins.json")
        with suppress(OSError):
            self._pins_mtime = path.getmtime(pins_path)
        state_path = path.join(RovrVars.ROVRCONFIG, "state.toml")
        state_mtime = None
        with suppress(OSError):
            state_mtime = path.getmtime(state_path)
        drives = get_mounted_drives()
        drive_update_every = int(config["interface"]["drive_watcher_frequency"])
        count: int = -1
        style_available: bool = self.CUSTOM_STYLE_AVAILABLE
        custom_style_path = path.join(RovrVars.ROVRCONFIG, "style.tcss")
        while True:
            for _ in range(4):
                # essentially sleep 1 second, but with extra steps
                if self._shutdown_event.wait(timeout=0.25):
                    return
                if self.return_code is not None:
                    # fail safe if for any reason, the thread continues running after exit
                    return
            count += 1
            if count >= drive_update_every:
                count = 0
            new_cwd = getcwd()
            if not self.file_list.file_list_pause_check:
                if not path.exists(new_cwd):
                    file_list.update_file_list(add_to_session=False)
                elif cwd != new_cwd:
                    cwd = new_cwd
                    continue
                else:
                    items = None
                    with suppress(OSError):
                        items = get_filtered_dir_names(
                            cwd,
                            config["interface"]["show_hidden_files"],
                        )
                    if items is not None and items != file_list.items_in_cwd:
                        self.cd(cwd)
            # check pins.json
            new_mtime = None
            reload_called: bool = False
            with suppress(OSError):
                new_mtime = path.getmtime(pins_path)
            if new_mtime != self._pins_mtime:
                self._pins_mtime = new_mtime
                if new_mtime is not None:
                    # no, this doesn't need to be called from thread
                    # this is _not_ a sync function, it is a worker
                    # and workers run separate from a thread, so there
                    # really is no issue here, thanks to any AI
                    # models raising false issues on thread safety
                    self.query_one(PinnedSidebar).reload_pins()
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
                        self.query_one(PinnedSidebar).reload_pins()
                except Exception as exc:
                    self.notify(
                        f"{type(exc).__name__}: {exc}",
                        title="Change Watcher",
                        severity="warning",
                        markup=False,
                    )
            # check highlighted file mtime
            if not self.file_list.file_list_pause_check:
                highlighted_option = file_list.highlighted_option
                if highlighted_option is not None and isinstance(
                    getattr(highlighted_option, "dir_entry", None), DirEntryType
                ):
                    highlighted_path = highlighted_option.dir_entry.path
                    if not path.isdir(highlighted_path):
                        new_highlighted_mtime = None
                        with suppress(OSError):
                            new_highlighted_mtime = path.getmtime(highlighted_path)
                        if (
                            new_highlighted_mtime is not None
                            and new_highlighted_mtime != self._highlighted_file_mtime
                        ):
                            self._highlighted_file_mtime = new_highlighted_mtime
                            self.query_one(PreviewContainer).show_preview(
                                highlighted_path
                            )
                            dir_entry = get_direntry_for(highlighted_path)
                            if dir_entry is not None:
                                highlighted_option.dir_entry = dir_entry
                                self.query_one(MetadataContainer).update_metadata(
                                    dir_entry
                                )
            if not self.CUSTOM_STYLE_AVAILABLE:
                if not style_available and path.exists(custom_style_path):
                    style_available = True
                    self.notify(
                        "Custom [b]style.tcss[/] was detected.\nPlease relaunch rovr to apply the custom stylesheet.",
                        title="Styles",
                        severity="information",
                    )
                elif not path.exists(custom_style_path):
                    style_available = False

    @work(exclusive=True)
    async def on_resize(self, event: events.Resize) -> None:
        from rovr.screens.way_too_small import TerminalTooSmall

        if (
            event.size.height < MaxPossible.height
            or event.size.width < MaxPossible.width
        ) and not self.has_pushed_screen:
            self.has_pushed_screen = True
            await self.push_screen(TerminalTooSmall())
            self.has_pushed_screen = False
        else:
            with suppress(ScreenStackError):
                if len(self.screen_stack) > 1 and isinstance(
                    self.screen_stack[-1], TerminalTooSmall
                ):
                    self.pop_screen()
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
                    if all(path.exists(css_path) for css_path in css_paths):
                        self.notify(
                            str(error),
                            title=f"CSS: {type(error).__name__}",
                            severity="error",
                            markup=False,
                        )
                    else:
                        unable_path = [
                            css_path
                            for css_path in css_paths
                            if not path.exists(css_path)
                        ]
                        if len(unable_path) == 1:
                            self.notify(
                                f"CSS file {unable_path[0]} cannot be found.",
                                title="CSS: File Not Found",
                                severity="warning",
                                markup=False,
                            )
                        else:
                            self.notify(
                                f"CSS files {unable_path} cannot be found.",
                                title="CSS: Files Not Found",
                                severity="warning",
                                markup=False,
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
                    str(error),
                    title=f"CSS: {type(error).__name__}",
                    severity="error",
                    markup=False,
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
            self.action_show_keybinds,
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
                lambda: self.call_later(self._toggle_transparency),
            )
        else:
            yield SystemCommand(
                "Enable Transparent Theme",
                "Have a transparent background.",
                lambda: self.call_later(self._toggle_transparency),
            )

        if (
            config["plugins"]["fd"]["enabled"]
            and len(config["plugins"]["fd"]["keybinds"]) > 0
        ):
            yield SystemCommand(
                "Open fd",
                "Start searching the current directory using `fd`",
                self.action_plugin_fd,
            )
        if (
            config["plugins"]["zoxide"]["enabled"]
            and config["plugins"]["zoxide"]["keybinds"]
        ):
            yield SystemCommand(
                "Open zoxide",
                "Start searching for a directory to `z` to",
                self.action_plugin_zoxide,
            )
        if config["plugins"]["rg"]["enabled"] and config["plugins"]["rg"]["keybinds"]:
            yield SystemCommand(
                "Open ripgrep",
                "Start searching the current directory for a string using `rg`",
                self.action_plugin_rg,
            )
        if config["keybinds"]["toggle_hidden_files"]:
            if config["interface"]["show_hidden_files"]:
                yield SystemCommand(
                    "Hide Hidden Files",
                    "Exclude listing of hidden files and folders",
                    self.file_list.action_toggle_hidden_files,
                )
            else:
                yield SystemCommand(
                    "Show Hidden Files",
                    "Include listing of hidden files and folders",
                    self.file_list.action_toggle_hidden_files,
                )
        yield SystemCommand(
            "Reload File List",
            "Send a forceful reload of the file list, in case something goes wrong",
            lambda: self.cd(getcwd()),
        )

    @work
    async def _toggle_transparency(self) -> None:
        self.ansi_color = not self.ansi_color
        self.refresh()
        self.refresh_css()
        self.file_list.update_border_subtitle()

    @on(events.Click)
    def when_got_click(self, event: events.Click) -> None:
        if (
            not isinstance(event.widget, (FileListRightClickOptionList, SortOrderPopup))
            or event.button == 1
        ):
            self.hide_popups()

    def hide_popups(self) -> None:
        # just in case
        with suppress(NoMatches):
            for popup in self.query(PopupOptionList):
                popup.add_class("hidden")

    @work(thread=True)
    def run_in_thread(self, function: Callable, *args, **kwargs) -> Worker | Exception:
        """
        Run a function in a thread and return a worker for it.
        Args:
            function(callable): the function to run
            *args: positional arguments for the function
            **kwargs: keyword arguments for the function

        Returns:
            Worker: the worker for the function
            Exception: if something fails
        """
        try:
            return function(*args, **kwargs)
        except Exception as exc:
            return exc

    def panic(self, *renderables: RenderableType) -> None:
        if not all(is_renderable(renderable) for renderable in renderables):
            raise TypeError("Can only call panic with strings or Rich renderables")
        # hardcode to not pre-render please
        self._exit_renderables.extend(renderables)
        self._close_messages_no_wait()

    def _fatal_error(self) -> None:
        """Exits the app after an unhandled exception."""
        import rich
        from rich.traceback import Traceback

        self.bell()
        traceback = Traceback(
            show_locals=True, width=None, locals_max_length=5, suppress=[rich]
        )
        # hardcode to not pre-render please
        self._exit_renderables.append(traceback)
        self._close_messages_no_wait()

    def _print_error_renderables(self) -> None:
        """Print and clear exit renderables."""
        from rich.panel import Panel
        from rich.traceback import Traceback

        error_count = len(self._exit_renderables)
        traceback_involved = False
        for renderable in self._exit_renderables:
            self.error_console.print(renderable)
            if isinstance(renderable, Traceback):
                traceback_involved = True
                dump_exc(self, renderable)
        if traceback_involved:
            if error_count > 1:
                self.error_console.print(
                    f"\n[b]NOTE:[/b] {error_count} errors shown above.", markup=True
                )
            if error_count != 0:
                dump_path = path.join(
                    path.realpath(RovrVars.ROVRCONFIG), "logs", f"{log_name}.log"
                )
                self.error_console.print(
                    Panel(
                        f"The error has been dumped to {dump_path}",
                        expand=False,
                        border_style="red",
                        padding=(0, 2),
                    ),
                    style="bold red",
                )
        self._exit_renderables.clear()
        self.workers.cancel_all()

    @property
    def _focused_id(self) -> str | None:
        if self.focused is not None:
            return self.focused.id
        return None

    @overload
    def query_one(self, selector: str) -> Widget: ...

    @overload
    def query_one(self, selector: type[QueryType]) -> QueryType: ...

    @overload
    def query_one(self, selector: str, expect_type: type[QueryType]) -> QueryType: ...

    def query_one(
        self,
        selector: str | type[QueryType],
        expect_type: type[QueryType] | None = None,
    ) -> QueryType | Widget:
        try:
            return super().query_one(selector, expect_type)  # ty: ignore[invalid-argument-type]
        except NoMatches:
            # Try fixing the problem ourselves
            if selector in ("FileList", "#file_list") or FileList in (
                selector,
                expect_type,
            ):
                # weird bug where sometimes the filelist just disappears, so we just remake the widget
                self.file_list = FileList()
                self._file_list_container.mount(self.file_list, before="PathInput")
                self._file_list_container.filelist = self.file_list
                return self.file_list
            elif selector in ("#clipboard", "Clipboard") or Clipboard in (
                selector,
                expect_type,
            ):
                # same issue here, albeit less common
                self.Clipboard = Clipboard()
                self.query_one("#footer").mount(self.Clipboard)
                return self.Clipboard
            else:
                raise

    # actions
    def action_focus_toggle_pinned_sidebar(self) -> None:
        if (
            self._focused_id == "pinned_sidebar"
            or "hide" in self.query_one("#pinned_sidebar_container").classes
        ):
            self.file_list.focus()
        elif self.query_one("#pinned_sidebar_container").display:
            self.query_one("#pinned_sidebar").focus()

    def action_focus_file_list(self) -> None:
        self.file_list.focus()

    def action_focus_toggle_preview_sidebar(self) -> None:
        if (
            self._focused_id == "preview_sidebar"
            or self.focused.parent.id == "preview_sidebar"
            or "hide" in self.query_one("#preview_sidebar").classes
        ):
            self.file_list.focus()
        elif self.query_one(PreviewContainer).display:
            with suppress(NoMatches):
                self.query_one("PreviewContainer > *").focus()
        else:
            self.file_list.focus()

    def action_focus_path_switcher(self) -> None:
        self.query_one("#path_switcher").focus()

    def action_focus_toggle_processes(self) -> None:
        if (
            self._focused_id == "processes"
            or "hide" in self.query_one("#processes").classes
        ):
            self.file_list.focus()
        elif self.query_one("#footer").display:
            self.query_one("#processes").focus()

    def action_focus_toggle_metadata(self) -> None:
        if self._focused_id == "metadata":
            self.file_list.focus()
        elif self.query_one("#footer").display:
            self.query_one("#metadata").focus()

    def action_focus_toggle_clipboard(self) -> None:
        if self._focused_id == "clipboard":
            self.file_list.focus()
        elif self.query_one("#footer").display:
            self.Clipboard.focus()

    def action_toggle_pinned_sidebar(self) -> None:
        self.file_list.focus()
        self.query_one(StateManager).toggle_pinned_sidebar()

    def action_toggle_preview_sidebar(self) -> None:
        self.file_list.focus()
        self.query_one(StateManager).toggle_preview_sidebar()

    def action_toggle_footer(self) -> None:
        self.file_list.focus()
        self.query_one(StateManager).toggle_footer()

    def action_toggle_menu_wrapper(self) -> None:
        self.file_list.focus()
        self.query_one(StateManager).toggle_menu_wrapper()

    def action_tab_next(self) -> None:
        if self.tabWidget.active_tab is not None:
            self.tabWidget.action_next_tab()

    def action_tab_previous(self) -> None:
        if self.tabWidget.active_tab is not None:
            self.tabWidget.action_previous_tab()

    async def action_tab_new(self) -> None:
        await self.query_one("NewTabButton").on_button_pressed()

    async def action_tab_close(self) -> None:
        if self.tabWidget.tab_count > 1:
            await self.tabWidget.remove_tab(self.tabWidget.active_tab)

    def action_plugin_zoxide(self) -> None:
        import shutil

        if not config["plugins"]["zoxide"]["enabled"]:
            return
        if shutil.which("zoxide") is None:
            self.notify(
                "Zoxide is not installed or not in PATH.",
                title="Zoxide",
                severity="error",
            )
            return

        def on_response(response: str) -> None:
            """Handle the response from the ZDToDirectory dialog."""
            if response:
                pathInput: PathInput = self.query_one(PathInput)
                pathInput.value = response
                pathInput.on_input_submitted(
                    PathInput.Submitted(pathInput, pathInput.value)
                )

        from rovr.screens import ZDToDirectory

        self.push_screen(ZDToDirectory(), on_response)

    def action_show_keybinds(self) -> None:
        from rovr.screens import Keybinds

        self.push_screen(Keybinds())

    def action_plugin_fd(self) -> None:
        import shutil

        if not config["plugins"]["fd"]["enabled"]:
            return
        fd_exec = shutil.which(config["plugins"]["fd"]["executable"]) or shutil.which(
            "fd"
        )
        if fd_exec is not None:
            try:

                def on_response(selected: str | None) -> None:
                    if selected is None or selected == "":
                        return
                    if path.isdir(selected):
                        self.cd(selected)
                    else:
                        self.cd(
                            path.dirname(selected),
                            focus_on=path.basename(selected),
                        )

                from rovr.screens import FileSearch

                self.push_screen(FileSearch(), on_response)
            except Exception as exc:
                dump_exc(self, exc)
                self.notify(
                    str(exc), title="Plugins: fd", severity="error", markup=False
                )
        else:
            self.notify(
                f"{config['plugins']['fd']['executable']} cannot be found in PATH.",
                title="Plugins: fd",
                severity="error",
                markup=False,
            )

    def action_plugin_rg(self) -> None:
        import shutil

        if not config["plugins"]["rg"]["enabled"]:
            return
        rg_exec = shutil.which(config["plugins"]["rg"]["executable"]) or shutil.which(
            "rg"
        )
        if rg_exec is not None:
            try:

                def on_response(selected: str | None) -> None:
                    if selected is None or selected == "":
                        return
                    else:
                        self.cd(
                            path.dirname(selected),
                            focus_on=path.basename(selected),
                        )

                from rovr.screens import ContentSearch

                self.push_screen(ContentSearch(), on_response)
            except Exception as exc:
                dump_exc(self, exc)
                self.notify(
                    str(exc), title="Plugins: rg", severity="error", markup=False
                )
        else:
            self.notify(
                f"{config['plugins']['rg']['executable']} cannot be found in PATH.",
                title="Plugins: rg",
                severity="error",
                markup=False,
            )

    def action_suspend_process(self) -> None:
        if WINDOWS:
            self.notify(
                "rovr cannot be suspended on Windows!",
                title="Suspend App",
                severity="warning",
            )
        else:
            super().action_suspend_process()

    def action_show_shell_screen(self) -> None:
        from rovr.screens import ShellExec

        self.push_screen(
            ShellExec(),
            callback=lambda response: self.on_shell_exec_response(response),
        )
