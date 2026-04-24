import asyncio
import contextlib
from functools import partial
from os import path
from time import time
from typing import ClassVar

from textual import on, work
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalGroup
from textual.widgets.option_list import Option
from textual.widgets.selection_list import Selection
from textual.worker import get_current_worker

from rovr.classes.mixins import CheckboxRenderingMixin
from rovr.classes.textual_options import ModalSearcherOption
from rovr.components import ModalSearchScreen
from rovr.components.special_option_lists import DoubleClickableScrollOffOptionList
from rovr.functions import icons as icon_utils
from rovr.functions import path as path_utils
from rovr.functions.icons import get_icon_for_file, get_icon_for_folder
from rovr.variables.constants import bindings, config
from rovr.variables.maps import FD_TYPE_TO_ALIAS
from rovr.widgets import Input, SelectionList

FILTER_TYPES: dict[str, bool] = {
    ft: (ft in config["plugins"]["fd"]["default_filter_types"])
    for ft in FD_TYPE_TO_ALIAS
}


class FileSearchToggles(CheckboxRenderingMixin, SelectionList, inherit_bindings=False):
    BINDINGS: ClassVar[list[BindingType]] = list(bindings)

    def __init__(self) -> None:
        super().__init__(
            Selection(
                "Relative Paths",
                "relative_paths",
                config["plugins"]["fd"]["relative_paths"],
            ),
            Selection(
                "Follow Symlinks",
                "follow_symlinks",
                config["plugins"]["fd"]["follow_symlinks"],
            ),
            Selection(
                "No Ignore Parents",
                "no_ignore_parent",
                config["plugins"]["fd"]["no_ignore_parent"],
            ),
            Selection(
                "Search Hidden",
                "search_hidden",
                config["plugins"]["fd"]["search_hidden"],
            ),
            Selection("Filter Type", "", False, disabled=True),
            Selection("Files", "file", FILTER_TYPES["file"]),
            Selection("Folders", "directory", FILTER_TYPES["directory"]),
            Selection("Symlinks", "symlink", FILTER_TYPES["symlink"]),
            Selection("Executables", "executable", FILTER_TYPES["executable"]),
            Selection("Empty", "empty", FILTER_TYPES["empty"]),
            Selection("Socket", "socket", FILTER_TYPES["socket"]),
            Selection("Pipe", "pipe", FILTER_TYPES["pipe"]),
            Selection("Char-Device", "char-device", FILTER_TYPES["char-device"]),
            Selection("Block-Device", "block-device", FILTER_TYPES["block-device"]),
            id="file_search_toggles",
        )

    def on_mount(self) -> None:
        self.border_title = "fd options"

    def _get_checkbox_icon_set(self) -> list[str]:
        """
        Get the set of icons to use for checkbox rendering.

        ContentSearchToggles uses a different icon set (missing right icon).

        Returns:
            List of icon strings for left, inner, right, and spacing.
        """
        return [
            icon_utils.get_toggle_button_icon("left"),
            icon_utils.get_toggle_button_icon("inner"),
            "",  # No right icon for ContentSearchToggles
            " ",
        ]


class FileSearch(ModalSearchScreen):
    """Search for files recursively using fd."""

    STREAM_BATCH_TIME: float = 0.25

    def compose(self) -> ComposeResult:
        with VerticalGroup(id="file_search_group", classes="file_search_group"):
            yield Input(
                id="file_search_input",
                placeholder="Type to search files (fd)",
            )
            yield DoubleClickableScrollOffOptionList(
                Option("  No input provided", disabled=True),
                id="file_search_options",
                classes="empty",
            )
        yield FileSearchToggles()

    def on_mount(self) -> None:
        super().on_mount()
        self.search_input.border_title = "Find Files"
        self.search_options.border_title = "Files"
        self.fd_updater(Input.Changed(self.search_input, value=""))

    def on_input_changed(self, event: Input.Changed) -> None:
        self.fd_updater(event=event)

    @work
    async def fd_updater(self, event: Input.Changed) -> None:
        self._active_worker = get_current_worker()
        search_term = event.value.strip()
        fd_exec = config["plugins"]["fd"]["executable"]

        fd_cmd = [fd_exec]
        if config["interface"]["show_hidden_files"]:
            fd_cmd.append("--hidden")
        if not config["plugins"]["fd"]["relative_paths"]:
            fd_cmd.append("--absolute-path")
        if config["plugins"]["fd"]["follow_symlinks"]:
            fd_cmd.append("--follow")
        if config["plugins"]["fd"]["no_ignore_parent"]:
            fd_cmd.append("--no-ignore-parent")
        if config["plugins"]["fd"]["search_hidden"]:
            fd_cmd.append("--hidden")
        for filter_type, should_use in FILTER_TYPES.items():
            if should_use:
                fd_cmd.extend(["--type", FD_TYPE_TO_ALIAS[filter_type]])
        if search_term:
            fd_cmd.append("--")
            fd_cmd.append(search_term)
        else:
            self.search_options.add_class("empty")
            self.search_options.clear_options()
            self.search_options.border_subtitle = ""
            return
        self.search_options.set_options([Option("  Searching...", disabled=True)])
        fd_process = None
        stderr_task: asyncio.Task[bytes] | None = None
        try:
            fd_process = await self.create_proc(*fd_cmd)
            timeout = float(config["plugins"]["fd"]["timeout"])
            loop = asyncio.get_running_loop()
            deadline = loop.time() + timeout

            if fd_process.stderr is not None:
                stderr_task = asyncio.create_task(fd_process.stderr.read())

            pending_options: list[ModalSearcherOption] = []
            is_empty = True
            last_flush = time()

            while True:
                if self._active_worker is not get_current_worker():
                    fd_process.kill()
                    with contextlib.suppress(ProcessLookupError):
                        await fd_process.wait()
                    return

                if fd_process.stdout is None:
                    break

                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise asyncio.exceptions.TimeoutError

                line = await asyncio.wait_for(
                    fd_process.stdout.readline(), timeout=remaining
                )
                if not line:
                    break

                option = self.create_option(line.decode(errors="replace"))
                if option is None:
                    continue

                pending_options.append(option)

                if time() - last_flush < self.STREAM_BATCH_TIME:
                    continue
                else:
                    last_flush = time()

                if is_empty:
                    self.search_options.clear_options()
                    self.search_options.remove_class("empty")
                    is_empty = False

                self.search_options.add_options(pending_options)
                pending_options.clear()
                if self.search_options.highlighted is None:
                    self.search_options.highlighted = 0
                self.handle_highlighted()

            if pending_options:
                if is_empty:
                    self.search_options.clear_options()
                    self.search_options.remove_class("empty")
                self.search_options.add_options(pending_options)

            remaining = deadline - loop.time()
            if remaining <= 0:
                raise asyncio.exceptions.TimeoutError
            await asyncio.wait_for(fd_process.wait(), timeout=remaining)

            if stderr_task is not None:
                with contextlib.suppress(asyncio.CancelledError):
                    await stderr_task

            if self._active_worker is not get_current_worker():
                return

            if not self.search_options.get_option_at_index(0).disabled:
                if self.search_options.highlighted is None:
                    self.search_options.highlighted = 0
                return

            self.search_options.set_options((
                Option("  --No matches found--", disabled=True),
            ))
            self.search_options.add_class("empty")
            self.search_options.border_subtitle = ""
            if not stderr_task:
                return
        except (OSError, asyncio.exceptions.TimeoutError) as exc:
            if isinstance(exc, asyncio.exceptions.TimeoutError) and fd_process:
                fd_process.kill()

                with contextlib.suppress(
                    asyncio.exceptions.TimeoutError, ProcessLookupError
                ):
                    await asyncio.wait_for(fd_process.wait(), timeout=1)
            msg = (
                "  fd is missing on $PATH or cannot be executed"
                if isinstance(exc, OSError)
                else "  fd took too long to respond"
            )
            self.search_options.set_options([
                Option(msg, disabled=True),
                Option(f"{type(exc).__name__}: {exc}", disabled=True),
            ])
            return
        finally:
            if stderr_task is not None and not stderr_task.done():
                stderr_task.cancel()

    @on(SelectionList.SelectionToggled)
    def toggles_toggled(self, event: SelectionList.SelectionToggled) -> None:
        if event.selection.value in FILTER_TYPES:
            FILTER_TYPES[event.selection.value] = (
                event.selection.value in event.selection_list.selected
            )
        elif event.selection.value in config["plugins"]["fd"]:
            config["plugins"]["fd"][event.selection.value] = (
                event.selection.value in event.selection_list.selected
            )
        self.post_message(
            Input.Changed(self.search_input, value=self.search_input.value)
        )

    def create_option(self, raw_line: str) -> ModalSearcherOption | None:
        file_path = path_utils.normalise(raw_line.strip())
        file_path_str = str(file_path)
        if not file_path_str:
            return None
        display_text = f" {file_path_str}"
        if path.isdir(file_path_str):
            icon_factory = partial(get_icon_for_folder, file_path_str)
        else:
            icon_factory = partial(get_icon_for_file, file_path_str)
        return ModalSearcherOption(
            icon_factory,
            display_text,
            file_path_str,
        )
