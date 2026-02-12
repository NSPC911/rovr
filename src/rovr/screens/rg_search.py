import asyncio
import contextlib
from os import path
from typing import ClassVar

from textual import on, work
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalGroup
from textual.widgets import Input, SelectionList
from textual.widgets.option_list import Option
from textual.widgets.selection_list import Selection
from textual.worker import WorkerCancelled, get_current_worker

from rovr.classes.mixins import CheckboxRenderingMixin
from rovr.classes.textual_options import ModalSearcherOption
from rovr.components import DoubleClickableOptionList, ModalSearchScreen
from rovr.functions import icons as icon_utils
from rovr.functions import path as path_utils
from rovr.functions.icons import get_icon_for_file, get_icon_for_folder
from rovr.variables.constants import config, vindings


class ContentSearchToggles(CheckboxRenderingMixin, SelectionList):
    BINDINGS: ClassVar[list[BindingType]] = list(vindings)

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
        """Update the list using rg based on the search term."""
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
        try:
            rg_process = await asyncio.create_subprocess_exec(
                *rg_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            # 30 seconds is quite generous for rg to respond
            stdout, _ = await asyncio.wait_for(rg_process.communicate(), timeout=30)
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

        options: list[ModalSearcherOption] = []
        if stdout:
            stdout = stdout.decode()
            # fix output from --count
            # arranged as <path>:<count>
            # convert to (path, count) list
            stdout_lines: list[tuple[str, int]] = []
            for line in stdout.splitlines():
                if ":" in line:
                    path, count = line.rsplit(":", 1)
                    try:
                        stdout_lines.append((path, int(count)))
                    except ValueError:
                        continue  # skip lines with invalid count

            stdout_lines.sort(key=lambda x: x[1], reverse=True)
            worker = self.create_options(stdout_lines)
            try:
                options_result = await worker.wait()
                if options_result is not None:
                    options = options_result
            except WorkerCancelled:
                return  # anyways
            if self._active_worker is not get_current_worker():
                return  # another worker has taken over
            if options is None:
                return
            self.search_options.clear_options()
            if options:
                self.search_options.add_options(options)
                self.search_options.remove_class("empty")
                self.search_options.highlighted = 0
                return
        else:
            self.search_options.clear_options()
            self.search_options.add_option(
                Option("  --No matches found--", disabled=True),
            )
            self.search_options.add_class("empty")
            self.search_options.border_subtitle = ""

    @on(SelectionList.SelectionToggled)
    def toggles_toggled(self, event: SelectionList.SelectionToggled) -> None:
        if event.selection.value in config["plugins"]["rg"]:
            config["plugins"]["rg"][event.selection.value] = (
                event.selection.value in event.selection_list.selected
            )
        self.post_message(
            Input.Changed(self.search_input, value=self.search_input.value)
        )

    @work(thread=True, exit_on_error=False)
    def create_options(
        self, stdout: list[tuple[str, int]]
    ) -> list[ModalSearcherOption] | None:
        options: list[ModalSearcherOption] = []
        for line in stdout:
            file_path = path_utils.normalise(line[0].strip())
            if not file_path:
                continue
            display_text = f" {file_path}:[dim]{line[1]}[/]"
            icon: list[str] = (
                get_icon_for_folder(file_path)
                if path.isdir(file_path)
                else get_icon_for_file(file_path)
            )
            options.append(
                ModalSearcherOption(
                    icon,
                    display_text,
                    file_path,
                )
            )
        return options
