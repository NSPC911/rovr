import asyncio
import contextlib
from typing import cast

from textual import on, work
from textual.app import ComposeResult
from textual.containers import VerticalGroup
from textual.widgets import Input, OptionList
from textual.worker import WorkerCancelled

from rovr.classes.textual_options import ModalSearcherOption
from rovr.components import DoubleClickableOptionList, ModalSearchScreen
from rovr.functions.utils import should_cancel
from rovr.variables.constants import config


class ZDToDirectory(ModalSearchScreen):
    """Screen with a dialog to z to a directory, using zoxide"""

    def compose(self) -> ComposeResult:
        with VerticalGroup(id="zoxide_group", classes="zoxide_group"):
            yield Input(
                id="zoxide_input",
                placeholder="Enter directory name or pattern",
            )
            yield DoubleClickableOptionList(
                ModalSearcherOption(None, "  No input provided", disabled=True),
                id="zoxide_options",
                classes="empty",
            )

    def on_mount(self) -> None:
        super().on_mount()
        self.search_input.border_title = "zoxide"
        self.search_options.border_title = "Folders"
        self.zoxide_updater(Input.Changed(self.search_input, value=""))

    def on_input_changed(self, event: Input.Changed) -> None:
        self.zoxide_updater(event=event)

    def _parse_zoxide_line(
        self, line: str, show_scores: bool
    ) -> tuple[str, str | None]:
        line = line.strip()
        if not show_scores:
            return line, None

        # Example "  <floating_score> <path_with_spaces>"
        # Split only on first space to make sure path with spaces work
        parts = line.split(None, 1)
        if len(parts) == 2:
            score_str, path = parts
            return path, score_str
        else:
            # This should ideally never happen
            self.notify(
                # Not printing the entire line as that could be too big for UI
                # message. We anyway have the lines in logs
                "Unexpected tokens count while parsing zoxide lines",
                title="Zoxide Plugin",
                severity="error",
            )
            self.log(f"Problems while parsing zoxide line - '{line}'")
            return line, None

    @work(exclusive=True)
    async def zoxide_updater(self, event: Input.Changed) -> None:
        """Update the list"""
        search_term = event.value.strip()
        # check 1 for queue, to ignore subprocess as a whole
        if should_cancel():
            return

        zoxide_cmd = ["zoxide", "query", "--list"]
        show_scores = config["plugins"]["zoxide"].get("show_scores", False)
        if show_scores:
            zoxide_cmd.append("--score")
        zoxide_cmd.append("--")

        zoxide_cmd += search_term.split()

        zoxide_process = None
        try:
            zoxide_process = await asyncio.create_subprocess_exec(
                *zoxide_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(zoxide_process.communicate(), timeout=3)
        except (OSError, asyncio.exceptions.TimeoutError) as exc:
            if isinstance(exc, asyncio.exceptions.TimeoutError) and zoxide_process:
                zoxide_process.kill()
            # zoxide not installed
            self.search_options.clear_options()
            self.search_options.add_option(
                ModalSearcherOption(
                    None,
                    "  zoxide is missing on $PATH or cannot be executed"
                    if isinstance(exc, OSError)
                    else "  zoxide took too long to respond",
                    disabled=True,
                )
            )
            return

        # check 2 for queue, to ignore mounting as a whole
        if should_cancel():
            return
        if stdout:
            stdout = stdout.decode()
            worker = self.create_options(show_scores, stdout)
            try:
                options_result = await worker.wait()
                if options_result is not None:
                    options = options_result
                else:
                    return
            except WorkerCancelled:
                return  # anyways
            if options is None:
                return
            if len(options) == len(self.search_options.options) and all(
                isinstance(options[i], ModalSearcherOption)
                and isinstance(self.search_options.options[i], ModalSearcherOption)
                and options[i].file_path
                == cast(ModalSearcherOption, self.search_options.options[i]).file_path
                for i in range(len(options))
            ):  # ie same~ish query, resulting in same result
                pass
            else:
                # unline normally, I'm using an add_option**s** function
                # using it without has a likelihood of DuplicateID being
                # raised, or just nothing showing up. By having the clear
                # options and add options functions nearby, it hopefully
                # reduces the likelihood of an empty option list
                self.search_options.set_options(options)
                self.search_options.remove_class("empty")
                self.search_options.highlighted = 0
                if should_cancel():
                    return
        else:
            # No Matches to the query text
            self.search_options.clear_options()
            self.search_options.add_option(
                ModalSearcherOption(None, "  --No matches found--", disabled=True),
            )
            self.search_options.add_class("empty")
            self.search_options.border_subtitle = "0/0"

    @work(exclusive=True)
    @on(OptionList.OptionSelected)
    async def handle_zd_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        if not isinstance(event.option, ModalSearcherOption):
            # theoretically this shouldnt happen, but precautions
            self.dismiss(None)
            return

        selected_value = event.option.file_path
        if selected_value is None:
            self.dismiss(None)
            return None
        # ignore if zoxide got uninstalled, why are you doing this
        with contextlib.suppress(asyncio.exceptions.TimeoutError, OSError):
            zoxide_process = await asyncio.create_subprocess_exec(
                "zoxide",
                "add",
                selected_value,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, _ = await asyncio.wait_for(zoxide_process.communicate(), timeout=3)
        if not event.option.disabled:
            self.dismiss(selected_value)
        else:
            self.dismiss(None)

    @work(thread=True)
    def create_options(
        self, show_scores: bool, stdout: str
    ) -> list[ModalSearcherOption] | None:
        first_score_width = 0
        options: list[ModalSearcherOption] = []
        for line in stdout.splitlines():
            path, score = self._parse_zoxide_line(line, show_scores)
            if show_scores and score:
                # This ensures that we only add necessary padding
                # first score is going to be the largest, so we take its width
                if first_score_width == 0:
                    first_score_width = len(score)
                # Fixed size to make it look good.
                display_text = f" {score:>{first_score_width}} │ {path}"
            else:
                display_text = f" {path}"

            # Use original path for ID (not display text)
            options.append(ModalSearcherOption(None, display_text, path))
            if should_cancel():
                return
        return options
