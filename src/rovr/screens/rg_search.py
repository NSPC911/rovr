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

from rovr.classes.mixins import CheckboxRenderingMixin, ScrollOffMixin
from rovr.classes.textual_options import ModalSearcherOption
from rovr.components import DoubleClickableOptionList, ModalSearchScreen
from rovr.functions import icons as icon_utils
from rovr.functions import path as path_utils
from rovr.functions.icons import get_icon_for_file, get_icon_for_folder
from rovr.variables.constants import bindings, config
from rovr.widgets import Input, SelectionList


class ContentSearchToggles(ScrollOffMixin, CheckboxRenderingMixin, SelectionList):
    BINDINGS: ClassVar[list[BindingType]] = list(bindings)

    def __init__(self) -> None:
        super().__init__(
            Selection(
                "Case Sensitive",
                "case_sensitive",
                config["plugins"]["rg"]["case_sensitive"],
            ),
            Selection(
                "Follow Symlinks",
                "follow_symlinks",
                config["plugins"]["rg"]["follow_symlinks"],
            ),
            Selection(
                "Search Hidden Files",
                "search_hidden",
                config["plugins"]["rg"]["search_hidden"],
            ),
            Selection(
                "No Ignore Parents",
                "no_ignore_parent",
                config["plugins"]["rg"]["no_ignore_parent"],
            ),
            id="content_search_toggles",
        )

    def on_mount(self) -> None:
        self.border_title = "rg options"

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


class ContentSearch(ModalSearchScreen):
    """Search file contents recursively using rg."""

    STREAM_BATCH_TIME: float = 0.25

    def compose(self) -> ComposeResult:
        with VerticalGroup(id="content_search_group"):
            yield Input(
                id="content_search_input",
                placeholder="Type to search files (rg)",
            )
            yield DoubleClickableOptionList(
                Option("  No input provided", disabled=True),
                id="content_search_options",
                classes="empty",
            )
        yield ContentSearchToggles()

    def on_mount(self) -> None:
        super().on_mount()
        self.search_input.border_title = "Find in files"
        self.search_options.border_title = "Results"
        self.rg_updater(Input.Changed(self.search_input, value=""))

    def on_input_changed(self, event: Input.Changed) -> None:
        self.rg_updater(event=event)

    @work
    async def rg_updater(self, event: Input.Changed) -> None:
        self._active_worker = get_current_worker()
        self.search_options.border_subtitle = ""
        search_term = event.value.strip()
        rg_exec = config["plugins"]["rg"]["executable"]

        rg_cmd = [rg_exec, "--count", "--color=never"]
        if config["plugins"]["rg"]["search_hidden"]:
            rg_cmd.append("--hidden")
        if config["plugins"]["rg"]["follow_symlinks"]:
            rg_cmd.append("--follow")
        if config["plugins"]["rg"]["no_ignore_parent"]:
            rg_cmd.append("--no-ignore-parent")
        if not config["plugins"]["rg"]["case_sensitive"]:
            rg_cmd.append("--ignore-case")
        if search_term:
            rg_cmd.append("--")
            rg_cmd.append(search_term)
        else:
            self.search_options.add_class("empty")
            self.search_options.clear_options()
            self.search_options.border_subtitle = ""
            return
        self.search_options.set_options([Option("  Searching...", disabled=True)])
        rg_process = None
        stderr_task: asyncio.Task[bytes] | None = None
        try:
            rg_process = await self.create_proc(*rg_cmd)
            timeout = float(config["plugins"]["rg"]["timeout"])
            loop = asyncio.get_running_loop()
            deadline = loop.time() + timeout

            if rg_process.stderr is not None:
                stderr_task = asyncio.create_task(rg_process.stderr.read())

            options: list[ModalSearcherOption] = []
            pending_options: list[ModalSearcherOption] = []
            did_render_results = False
            last_flush = time()

            while True:
                if self._active_worker is not get_current_worker():
                    rg_process.kill()
                    with contextlib.suppress(ProcessLookupError):
                        await rg_process.wait()
                    return

                if rg_process.stdout is None:
                    break

                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise asyncio.exceptions.TimeoutError

                line = await asyncio.wait_for(
                    rg_process.stdout.readline(), timeout=remaining
                )
                if not line:
                    break

                option = self.create_option_from_count_line(
                    line.decode(errors="replace")
                )
                if option is None:
                    continue

                pending_options.append(option)

                if time() - last_flush < self.STREAM_BATCH_TIME:
                    continue

                last_flush = time()

                if not did_render_results:
                    self.search_options.clear_options()
                    self.search_options.remove_class("empty")
                    did_render_results = True

                self.search_options.add_options(pending_options)
                options.extend(pending_options)
                pending_options.clear()

            if pending_options:
                if not did_render_results:
                    self.search_options.clear_options()
                    self.search_options.remove_class("empty")
                    did_render_results = True
                self.search_options.add_options(pending_options)

            remaining = deadline - loop.time()
            if remaining <= 0:
                raise asyncio.exceptions.TimeoutError
            await asyncio.wait_for(rg_process.wait(), timeout=remaining)

            if stderr_task is not None:
                with contextlib.suppress(asyncio.CancelledError):
                    await stderr_task

            if self._active_worker is not get_current_worker():
                return

            if options:
                if self.search_options.highlighted is None:
                    self.search_options.highlighted = 0
                return

            self.search_options.clear_options()
            self.search_options.add_option(
                Option("  --No matches found--", disabled=True),
            )
            self.search_options.add_class("empty")
            self.search_options.border_subtitle = ""
            return
        except (OSError, asyncio.exceptions.TimeoutError) as exc:
            if isinstance(exc, asyncio.exceptions.TimeoutError) and rg_process:
                rg_process.kill()

                with contextlib.suppress(
                    asyncio.exceptions.TimeoutError, ProcessLookupError
                ):
                    await asyncio.wait_for(rg_process.wait(), timeout=1)
            msg = (
                "  rg took too long to respond"
                if isinstance(exc, asyncio.exceptions.TimeoutError)
                else "  rg is missing on $PATH or cannot be executed"
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
        if event.selection.value in config["plugins"]["rg"]:
            config["plugins"]["rg"][event.selection.value] = (
                event.selection.value in event.selection_list.selected
            )
        self.post_message(
            Input.Changed(self.search_input, value=self.search_input.value)
        )

    def create_option_from_count_line(
        self, raw_line: str
    ) -> ModalSearcherOption | None:
        if ":" not in raw_line:
            return None
        raw_path, raw_count = raw_line.rsplit(":", 1)
        try:
            count = int(raw_count.strip())
        except ValueError:
            return None

        file_path = str(path_utils.normalise(raw_path.strip()))
        if not file_path:
            return None

        display_text = f" {file_path}:[dim]{count}[/]"
        if path.isdir(file_path):
            icon_factory = partial(get_icon_for_folder, file_path)
        else:
            icon_factory = partial(get_icon_for_file, file_path)
        return ModalSearcherOption(
            icon_factory,
            display_text,
            file_path,
        )
