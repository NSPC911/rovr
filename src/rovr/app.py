from __future__ import annotations

import asyncio
import multiprocessing
import os
import sys
import threading
from contextlib import suppress
from io import TextIOWrapper
from os import path
from subprocess import Popen, TimeoutExpired
from typing import Callable, Iterable

from rich.console import RenderableType
from rich.protocol import is_renderable
from textual import constants, events, on, work
from textual.app import WINDOWS, ComposeResult, ScreenStackError, SystemCommand
from textual.binding import Binding
from textual.containers import (
    HorizontalGroup,
    HorizontalScroll,
    Vertical,
    VerticalGroup,
)
from textual.css.query import NoMatches
from textual.dom import DOMNode
from textual.messages import ExitApp
from textual.screen import Screen
from textual.timer import Timer
from textual.types import NoActiveAppError
from textual.widget import Widget
from textual.widgets import Input, Label
from textual.widgets.selection_list import Selection
from textual.worker import Worker, WorkerFailed
from textual_drivers.dnd import (
    DNDApp,
    DNDDragIn,
    Drop,
)

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
from rovr.action_buttons.sort_order import SortOrderButton
from rovr.classes.app_mixins import DragAndDrop, KeyHandler, ThemeHandler
from rovr.classes.mixins import Action, Actionable
from rovr.classes.theme import RovrStylesheet
from rovr.classes.type_aliases import KeysConfig, ShellRunTypes
from rovr.components.popup_option_list import PopupOptionList
from rovr.core import (
    FileList,
    FileListContainer,
    PinnedSidebar,
    PinnedSidebarContainer,
    PreviewContainer,
)
from rovr.footer import Clipboard, MetadataContainer, ProcessContainer
from rovr.functions import drive_workers, multiprocessing_utils
from rovr.functions.cwd import chdir, getcwd
from rovr.functions.path import (
    dump_exc,
    ensure_existing_directory,
    get_direntry_for,
    get_filtered_dir_names,
    normalise,
)
from rovr.functions.themes import (
    register_all_themes,
    resolve_theme_ansi,
    theme_file_mtimes,
)
from rovr.functions.utils import (
    multiprocessing_process_error_checker,
    run_command,
    should_cancel,
)
from rovr.header import HeaderArea
from rovr.header.tabs import TablineTab
from rovr.navigation_widgets import (
    BackButton,
    ForwardButton,
    PathAutoCompleteInput,
    PathInput,
    UpButton,
)
from rovr.screens import ShellExec
from rovr.screens.way_too_small import TerminalTooSmall
from rovr.state_manager import StateManager
from rovr.variables.constants import MaxPossible, config, keys, log_name
from rovr.variables.maps import RovrVars

if constants.SCREENSHOT_LOCATION:
    constants.SCREENSHOT_LOCATION = normalise(getcwd(), constants.SCREENSHOT_LOCATION)


class Application(
    Actionable,
    ThemeHandler,
    DragAndDrop,
    KeyHandler,
    DNDApp,
    inherit_bindings=False,
):
    # our own form of BINDINGS that utilises check_key
    # key: str the action to use
    # value: bool or callable that returns bool,
    #        whether the keybind can be used or not
    ACTIONS: list[Action] = [
        Action(action, config["keybinds"][action])
        for action in (
            "focus_toggle_pinned_sidebar",
            "focus_file_list",
            "focus_toggle_preview_sidebar",
            "focus_toggle_path_switcher",
            "focus_toggle_processes",
            "focus_toggle_metadata",
            "focus_toggle_clipboard",
            "toggle_pinned_sidebar",
            "toggle_preview_sidebar",
            "toggle_footer",
            "toggle_menu_wrapper",
            "tab_next",
            "tab_previous",
            "tab_new",
            "tab_close",
            "show_keybinds",
            "show_shell_screen",
            "suspend_process",
        )
    ] + [
        Action(action, config["plugins"][plugin]["keybinds"])
        for action, plugin in (
            ("cd_zoxide", "zoxide"),
            ("search_fd", "fd"),
            ("search_rg", "rg"),
        )
    ]

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

    MULTIPROCESSING_PROCESS_ALLOWED: bool = getattr(
        sys, "_is_gil_enabled", lambda: True
    )()

    keys: KeysConfig = keys

    def __init__(
        self,
        startup_path: str | Iterable[str] | None = None,
        *,
        cwd_file: str | TextIOWrapper | None = None,
        chooser_file: str | TextIOWrapper | None = None,
        show_keys: bool = False,
        force_crash_in: float = 0,
        force_exit_on_shutdown: bool = False,
    ) -> None:
        super().__init__(watch_css=True)
        # replace the plain Stylesheet created by App.__init__ before any CSS
        # is read, so `$variable:` declarations are stripped from the files
        # (their values are injected through get_css_variables instead)
        self.stylesheet = RovrStylesheet(variables=self.get_css_variables())
        self.app_blurred: bool = False
        self.has_pushed_screen: bool = False
        # Runtime output files from CLI
        self._cwd_file: str | TextIOWrapper | None = cwd_file
        self._chooser_file: str | TextIOWrapper | None = chooser_file
        self._chooser_paths: list[str] | None = None
        self._show_keys: bool = show_keys
        self._force_crash_in: float = force_crash_in
        self._force_exit_on_shutdown = force_exit_on_shutdown
        self._force_exit_timer: threading.Timer | None = None
        self._pins_mtime: float | None = None
        self._highlighted_file_mtime: float | None = None

        self._file_list_container = FileListContainer()
        self._pinned_sidebar_container = PinnedSidebarContainer()
        # shutdown event for bg thread
        self._shutdown_event = threading.Event()
        self._background_processes: set[Popen] = set()
        # cannot use self.clipboard, reserved for Textual's clipboard
        self.Clipboard = Clipboard()
        if startup_path is None:
            startup_paths = []
        elif isinstance(startup_path, str):
            startup_paths = [startup_path]
        else:
            startup_paths = list(startup_path)
        self._startup_locations: list[tuple[str, str | None]] = []
        for startup_item in startup_paths:
            expanded_path = path.expanduser(startup_item)
            resolved_path = path.normpath(
                expanded_path
                if path.isabs(expanded_path)
                else path.join(getcwd(), expanded_path)
            )
            directory = normalise(ensure_existing_directory(resolved_path))
            focus_on = (
                path.basename(resolved_path) if path.isfile(resolved_path) else None
            )
            self._startup_locations.append((directory, focus_on))
        if not self._startup_locations:
            self._startup_locations.append((normalise(getcwd()), None))
        chdir(self._startup_locations[0][0])

        self._p_timer: Timer | None = None
        self._dnd_timer: tuple[Timer, TablineTab | UpButton | str, DNDDragIn] | None = (
            None
        )
        self._dnd_dragged_paths: list[str] = []
        self._dnd_drop_metadata: dict[Drop, tuple[str, bool]] = {}

        self._on_mount_done: bool = False
        self.last_available_cd = getcwd()

        self._theme_errors: list[str] = register_all_themes(self)
        self._theme_file_mtimes: dict[str, float] = theme_file_mtimes()
        self.ansi_color = config["theme"]["transparent"]
        self.theme = config["theme"]["default"]
        # ensure the theme css source exists (possibly empty) before Textual
        # reads the style.tcss files, so its position in the source order is
        # the same no matter which theme the app started with
        self._load_theme_css()

    @property
    def file_list(self) -> FileList:
        if not self._file_list_container.filelist.is_mounted:
            self._file_list_container.remount_filelist()
        return self._file_list_container.filelist

    def compose(self) -> ComposeResult:
        self.log("Starting Rovr...")
        root_classes = (
            "compact-buttons"
            if config["interface"]["compact_mode"]["buttons"]
            else "comfy-buttons"
        ) + (
            " compact-panels"
            if config["interface"]["compact_mode"]["panels"]
            else " comfy-panels"
        )
        with Vertical(id="root", classes=root_classes.strip()):
            header = HeaderArea(self._startup_locations)
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
                yield self._pinned_sidebar_container
                yield self._file_list_container
                yield PreviewContainer()
            with HorizontalGroup(id="footer"):
                yield ProcessContainer().data_bind(Application.theme)
                yield MetadataContainer()
                yield self.Clipboard
            yield StateManager()

    def on_mount(self) -> None:
        for error in self._theme_errors:
            self.notify(error, title="Theme Error", severity="warning", markup=False)
        self.set_interval(1, self._poll_theme_files)
        # title for screenshots

        if self._force_crash_in > 0:
            self.call_later(self._force_crash)

        self.call_later(self.call_later, self.post_mount)
        self._on_mount_done = True
        if self.is_headless:
            if sys.platform == "win32":
                self._original_stderr = open(  # noqa: SIM115
                    "CONOUT$", "w", encoding="utf-8", errors="ignore"
                )
            else:
                self._original_stderr = open(  # noqa: SIM115
                    "/dev/stderr", "w", encoding="utf-8", errors="ignore"
                )

    def post_mount(self) -> None:
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
        self.file_list.update_border_subtitle()
        # self.call_after_refresh(sleep, 1)
        self.add_dnd_class_target(self._file_list_container)
        self.add_dnd_class_target(self._pinned_sidebar_container)

    @work
    async def _force_crash(self) -> None:
        await asyncio.sleep(self._force_crash_in)
        1 / 0

    def on_unmount(self) -> None:
        self._shutdown_event.set()
        for proc in tuple(self._background_processes):
            self._stop_background_process(proc)

    @staticmethod
    def _stop_background_process(proc: Popen) -> None:
        if proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=0.5)
        except TimeoutExpired:
            proc.kill()

    def action_focus_next(self) -> None:
        if config["interface"]["allow_tab_nav"]:
            super().action_focus_next()

    def action_focus_previous(self) -> None:
        if config["interface"]["allow_tab_nav"]:
            super().action_focus_previous()

    def show_key(self, event: events.Key) -> None:
        if self._show_keys:
            with suppress(NoMatches):
                using = KeyHandler.shorten_key(event.key)
                wid = self.query_one("#showKeys", Label)
                if wid.content != using:
                    wid.update(using)

    async def on_key(self, event: events.Key) -> None:
        # show key
        if self._show_keys:
            self.show_key(event)

        # if current screen isn't the app screen
        if len(self.screen_stack) != 1:
            event.prevent_default()
            await self._on_key(event)
            return
        # Not really sure why this can happen, but I will still handle this
        if self.focused is None or not isinstance(self.focused.parent, DOMNode):
            event.prevent_default()
            return
        # Make sure that key binds don't break
        # placeholder, not yet existing
        if (
            not self.keys
            and event.key == "escape"
            and self.focused.id
            and "search" in self.focused.id
        ):
            if self._focused_id == "search_file_list":
                self.file_list.focus()
            elif self._focused_id == "search_pinned_sidebar":
                self.query_one("#pinned_sidebar").focus()
            event.prevent_default()
        # backspace is used by default bindings to head up in history
        # so just avoid it
        elif event.key == "backspace" and (
            isinstance(self.focused, Input)
            or (self.focused.id and "search" in self.focused.id)
        ):
            event.prevent_default()
            await self._on_key(event)

    def on_shell_exec_response(
        self, response: ShellExec.ReturnType | None, shell: bool = True
    ) -> None:
        if response is None or response.command == "":
            return

        proc = run_command(
            self, response.command, run_type=response.run_type, shell=shell
        )
        if response.run_type == "background":
            self.shell_thread(proc, "Shell Exec")

    @work(thread=True)
    def shell_thread(self, proc: Popen, title: str = "") -> None:
        self._background_processes.add(proc)
        try:
            while True:
                try:
                    stdout_bytes, stderr_bytes = proc.communicate(timeout=0.2)
                    break
                except TimeoutExpired:
                    if should_cancel() or self._shutdown_event.is_set():
                        self._stop_background_process(proc)
                        return
        finally:
            self._background_processes.discard(proc)
        if should_cancel() or self._shutdown_event.is_set():
            return
        stdout = stdout_bytes.decode().strip()
        stderr = stderr_bytes.decode().strip()
        if stdout and stderr:
            msg = f"stdout = {stdout}\nstderr = {stderr}\n"
        elif stdout and not stderr:
            msg = str(stdout)
        elif not stdout and stderr:
            msg = str(stderr)
        else:
            msg = f"Process completed with code {proc.returncode}"
        self.call_from_thread(
            self.notify,
            msg.strip(),
            title=title,
            severity="information" if proc.returncode == 0 else "error",
        )

    def on_app_blur(self, event: events.AppBlur) -> None:
        self.app_blurred = True

    def on_app_focus(self, event: events.AppFocus) -> None:
        self.app_blurred = False

    def _set_mouse_over(
        self, widget: Widget | None, hover_widget: Widget | None
    ) -> None:
        # Textual re-applies hover styles twice per MouseMove even when the
        # hovered widget hasn't changed, which floods the message queue when a
        # custom stylesheet marks large containers as hover-styled
        if widget is self.mouse_over and hover_widget is self.hover_over:
            return
        super()._set_mouse_over(widget, hover_widget)

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
        # Only an explicit open action confirms a chooser selection.
        if self._chooser_file and self._chooser_paths:
            selected = self._chooser_paths
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

    @on(ExitApp)
    def _arm_force_exit_timer(self) -> None:
        if not self._force_exit_on_shutdown or self._force_exit_timer is not None:
            return
        self._force_exit_timer = threading.Timer(
            0.5,
            os._exit,
            args=(0,),
        )
        self._force_exit_timer.daemon = True
        self._force_exit_timer.start()

    def cancel_force_exit_timer(self) -> None:
        if self._force_exit_timer is not None:
            self._force_exit_timer.cancel()
            self._force_exit_timer = None

    def open_recycle_bin(self) -> None:
        """Open the recycle bin browser, refreshing the file list on restore."""
        from rovr.screens import TrashScreen

        async def callback(changed: bool) -> None:
            if changed:
                self.file_list.update_file_list(add_to_session=False)

        self.push_screen(TrashScreen(), callback=callback)

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
        self.title = f"rovr @ {path.basename(directory)}"
        if self.return_code is not None:
            return
        directory = ensure_existing_directory(directory)

        try:
            if normalise(getcwd()) == normalise(directory) or directory == "":
                add_to_history = False
            else:
                chdir(directory)
                self.last_available_cd = directory
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

        try:
            worker = self.file_list.update_file_list(
                add_to_session=add_to_history,
                focus_on=focus_on,
                has_selected=has_selected,
                callback=callback,
                clear_search=clear_search,
            )
            return worker
        except (NoActiveAppError, WorkerFailed) as exc:
            exc = exc.error if isinstance(exc, WorkerFailed) else exc
            if isinstance(exc, NoActiveAppError):
                # This can only happen if the app is in the process of shutting
                # down, so we can just ignore this error
                return

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
        drive_update_every = int(config["interface"]["drive_watcher_frequency"])
        count: int = -2
        style_available: bool = self.CUSTOM_STYLE_AVAILABLE
        custom_style_path = path.join(RovrVars.ROVRCONFIG, "style.tcss")
        new_drives: list[str] | None = None
        cwd_mtime: float | None = None
        pin_sidebar = self.query_one(PinnedSidebar)

        i_should_shut_down = lambda: (
            self._shutdown_event.is_set() or self.return_code is not None
        )

        while True:
            if self._shutdown_event.wait(timeout=1):
                return
            if i_should_shut_down():
                return
            count += 1
            if count >= drive_update_every:
                count = 0
            try:
                new_cwd = getcwd()
                if not self.file_list.file_list_pause_check:
                    if not path.exists(new_cwd):
                        file_list.update_file_list(add_to_session=False)
                    elif cwd != new_cwd:
                        cwd = new_cwd
                        cwd_mtime = None
                        continue
                    else:
                        # only rescan when the directory mtime changed;
                        # renames/creates/deletes always bump it
                        new_cwd_mtime = None
                        with suppress(OSError):
                            new_cwd_mtime = path.getmtime(cwd)
                        if new_cwd_mtime != cwd_mtime:
                            cwd_mtime = new_cwd_mtime
                            items = None
                            with suppress(OSError):
                                items = get_filtered_dir_names(
                                    cwd,
                                    config["interface"]["show_hidden_files"],
                                )
                            if items is not None and items != file_list.items_in_cwd:
                                self.cd(cwd)
            except FileNotFoundError:
                self.file_list.set_options([
                    Selection(
                        " FileNotFoundError: Directory was removed while inside it.",
                        value="",
                        id="perm",
                        disabled=True,
                    )
                ])

            if i_should_shut_down():
                return

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
                    pin_sidebar.reload_pins()
                    reload_called = True
            if i_should_shut_down():
                return

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
            if i_should_shut_down():
                return

            # check drives
            if count == 0 and not reload_called:
                try:
                    if self.MULTIPROCESSING_PROCESS_ALLOWED:
                        # Run drive check in a separate process using multiprocessing.Process
                        # Using Queue to get the result back from the process
                        result_queue: multiprocessing.Queue[list[str]] = (
                            multiprocessing.Queue()
                        )

                        process = multiprocessing.Process(
                            target=drive_workers.get_mounted_drives_worker,
                            args=(result_queue, sys.platform, config),
                        )
                        multiprocessing_utils.start_process(process)
                        process.join(timeout=2.0)

                        if process.is_alive():
                            # Timeout - terminate the process
                            process.terminate()
                            process.join(timeout=0.5)
                            if process.is_alive():
                                process.kill()
                        elif not result_queue.empty():
                            # Process completed successfully
                            new_drives = result_queue.get_nowait()
                    else:
                        new_drives = drive_workers.get_mounted_drives(
                            sys.platform, config
                        )
                    if new_drives is not None and new_drives != pin_sidebar.DRIVES:
                        pin_sidebar.reload_pins()
                except Exception as exc:
                    if multiprocessing_process_error_checker(self, exc):
                        count = -1  # try again immediately on next loop
                    else:
                        self.notify(
                            f"{type(exc).__name__}: {exc}",
                            title="Drives Watcher",
                            severity="warning",
                            markup=False,
                        )
                        dump_exc(self, exc)
            if i_should_shut_down():
                return

            # check highlighted file mtime
            if not self.file_list.file_list_pause_check:
                highlighted_option = file_list.highlighted_option
                # TODO: The `file_list.highlighted_option` is modified at runtime
                # and does not match the type checking.
                # In `test_new_button` case, it becomes a `textual.widgets._selection_list.Selection` object
                # instead of `FileListSelectionWidget`.
                # It should be fixed to avoid surpising bug.
                if highlighted_option is not None and isinstance(
                    getattr(highlighted_option, "dir_entry", None), os.DirEntry
                ):
                    highlighted_path = highlighted_option.dir_entry.path
                    if not highlighted_option.dir_entry.is_dir():
                        new_highlighted_mtime = None
                        with suppress(OSError):
                            new_highlighted_mtime = path.getmtime(highlighted_path)
                        if (
                            new_highlighted_mtime is not None
                            and new_highlighted_mtime != self._highlighted_file_mtime
                        ):
                            self._highlighted_file_mtime = new_highlighted_mtime
                            self.query_one(PreviewContainer).show_preview(
                                highlighted_path,
                                new_highlighted_mtime,
                            )
                            dir_entry = get_direntry_for(highlighted_path)
                            if dir_entry is not None:
                                highlighted_option.dir_entry = dir_entry
                                highlighted_option._invalidate_prompt_cache()
                                file_list.call_next(file_list.refresh)
                                self.query_one(MetadataContainer).update_metadata(
                                    dir_entry
                                )
            if i_should_shut_down():
                return

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

    def watch_title(self, title: str) -> None:
        try:
            self._driver.write(f"\x1b]0;{title}\x07")
            self._driver.flush()
        except AttributeError:
            # driver not yet initialised
            pass

    def export_screenshot(
        self,
        *,
        title: str | None = None,
        simplify: bool = False,
    ) -> str:
        """super version but without title because i hate the title"""  # noqa: DOC201
        import io

        from rich.console import Console

        assert self._driver is not None, "App must be running"
        width, height = self.size

        console = Console(
            width=width,
            height=height,
            file=io.StringIO(),
            force_terminal=True,
            color_system="truecolor",
            record=True,
            legacy_windows=False,
            safe_box=False,
        )
        screen_render = self.screen._compositor.render_update(
            full=True, screen_stack=self.app._background_screens, simplify=simplify
        )
        console.print(screen_render)
        return console.export_svg(title="")

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        # TODO: remove command palette for a custom version some day
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

        _, ansi_is_fixed = resolve_theme_ansi(
            self.current_theme, config["theme"]["transparent"]
        )
        if not ansi_is_fixed:
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
                self.action_search_fd,
            )
        if (
            config["plugins"]["zoxide"]["enabled"]
            and config["plugins"]["zoxide"]["keybinds"]
        ):
            yield SystemCommand(
                "Open zoxide",
                "Start searching for a directory to `z` to",
                self.action_cd_zoxide,
            )
        if config["plugins"]["rg"]["enabled"] and config["plugins"]["rg"]["keybinds"]:
            yield SystemCommand(
                "Open ripgrep",
                "Start searching the current directory for a string using `rg`",
                self.action_search_rg,
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

    @on(events.Click)
    def when_got_click(self, event: events.Click) -> None:
        if not isinstance(event.widget, (PopupOptionList)) or event.button == 1:
            self.hide_popups()

    @on(events.AppBlur)
    def hide_popups(self) -> None:
        # just in case
        with suppress(NoMatches):
            for popup in self.query(PopupOptionList):
                popup.display = False

    @on(ExitApp)
    def on_exit_app(self) -> None:
        import rovr.monkey_patches._spam  # noqa: F401

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
        self.post_message(ExitApp())
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

    def action_focus_toggle_path_switcher(self) -> None:
        if (path_switcher := self.query_one("#path_switcher")).has_focus:
            self.file_list.focus()
        else:
            path_switcher.focus()

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
        self.action_cycle_tab(1)

    def action_tab_previous(self) -> None:
        self.action_cycle_tab(-1)

    def action_cycle_tab(self, offset: int) -> None:
        self.tabWidget.action_cycle_tab(offset)

    def action_activate_tab(self, index: int) -> None:
        self.tabWidget.action_activate_tab(index)

    async def action_tab_new(self) -> None:
        await self.query_one("NewTabButton").on_button_pressed()

    async def action_tab_close(self) -> None:
        if self.tabWidget.tab_count > 1:
            await self.tabWidget.remove_tab(self.tabWidget.active_tab)

    def action_cd_zoxide(self) -> None:
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
        from rovr.screens import Keybinds, ScopedKeybinds

        self.push_screen(ScopedKeybinds() if self.keys else Keybinds())

    def action_search_fd(self) -> None:
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

    def action_search_rg(self) -> None:
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
        self.push_screen(
            ShellExec(),
            callback=lambda response: self.on_shell_exec_response(response),
        )

    def action_print_dom(self) -> None:
        # basically --tree-dom but without instant exit
        from rovr import get_console

        with self.suspend():
            get_console().print(self.tree)

    def action_run_command(self, command: list[str], run_type: ShellRunTypes) -> None:
        if not isinstance(command, list) or not all(
            isinstance(c, str) for c in command
        ):
            self.notify(
                "Invalid command provided. Command must be a list of strings."
                + "\nUse `run_shell` if you want to run a string command instead",
                title="Run Command",
                severity="error",
            )
        self.on_shell_exec_response(
            ShellExec.ReturnType(command=command, run_type=run_type), shell=False
        )

    def action_run_shell(self, command: str, run_type: ShellRunTypes) -> None:
        if not isinstance(command, str):
            self.notify(
                "Invalid command provided. Command must be a string."
                + "\nUse `run_command` if you want to run a list of strings instead",
                title="Run Shell",
                severity="error",
            )
        self.on_shell_exec_response(
            ShellExec.ReturnType(command=command, run_type=run_type), shell=True
        )
