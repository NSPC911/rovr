import asyncio
import contextlib

from textual import events, work
from textual.app import ComposeResult
from textual.containers import VerticalGroup
from textual.content import Content
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from rovr.functions import path as path_utils
from rovr.variables.constants import config


class ZoxideOptionList(OptionList):
    async def _on_click(self, event: events.Click) -> None:
        """React to the mouse being clicked on an item.

        Args:
            event: The click event.
        """
        event.prevent_default()
        clicked_option: int | None = event.style.meta.get("option")
        if clicked_option is not None and not self._options[clicked_option].disabled:
            if event.chain == 2:
                if self.highlighted != clicked_option:
                    self.highlighted = clicked_option
                self.action_select()
            else:
                self.highlighted = clicked_option


class ZDToDirectory(ModalScreen):
    """Screen with a dialog to z to a directory, using zoxide"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._queued_task = None
        self._queued_task_args: Input.Changed | None = None

    def compose(self) -> ComposeResult:
        with VerticalGroup(id="zoxide_group", classes="zoxide_group"):
            yield Input(
                id="zoxide_input",
                placeholder="Enter directory name or pattern",
            )
            yield ZoxideOptionList(
                Option("  No input provided", disabled=True),
                id="zoxide_options",
                classes="empty",
            )

    def on_mount(self) -> None:
        self.zoxide_input: Input = self.query_one("#zoxide_input")
        self.zoxide_input.border_title = "zoxide"
        self.zoxide_input.focus()
        self.zoxide_options: ZoxideOptionList = self.query_one("#zoxide_options")
        self.zoxide_options.border_title = "Folders"
        self.zoxide_options.can_focus = False
        self.zoxide_updater(Input.Changed(self.zoxide_input, value=""))

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
            print(f"Problems while parsing zoxide line - '{line}'")
            return line, None

    @work(exclusive=True)
    async def zoxide_updater(self, event: Input.Changed) -> None:
        """Update the list"""
        search_term = event.value.strip()
        # check 1 for queue, to ignore subprocess as a whole

        zoxide_cmd = ["zoxide", "query", "--list"]
        show_scores = config["plugins"]["zoxide"].get("show_scores", False)
        if show_scores:
            zoxide_cmd.append("--score")
        zoxide_cmd.append("--")

        zoxide_cmd += search_term.split()

        try:
            zoxide_process = await asyncio.create_subprocess_exec(
                *zoxide_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(zoxide_process.communicate(), timeout=3)
        except (OSError, asyncio.exceptions.TimeoutError) as exc:
            if isinstance(exc, asyncio.exceptions.TimeoutError):
                zoxide_process.terminate()
            # zoxide not installed
            self.zoxide_options.clear_options()
            self.zoxide_options.add_option(
                Option(
                    "  zoxide is missing on $PATH or cannot be executed"
                    if isinstance(exc, OSError)
                    else "  zoxide took too long to respond",
                    disabled=True,
                )
            )
            return
        # check 2 for queue, to ignore mounting as a whole
        zoxide_options: ZoxideOptionList = self.query_one(
            "#zoxide_options", ZoxideOptionList
        )
        options = []
        if stdout:
            stdout = stdout.decode()
            first_score_width = 0
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
                options.append(
                    Option(Content(display_text), id=path_utils.compress(path))
                )
            if len(options) == len(zoxide_options.options) and all(
                options[i].id == zoxide_options.options[i].id
                for i in range(len(options))
            ):  # ie same~ish query, resulting in same result
                pass
            else:
                # unline normally, I'm using an add_option**s** function
                # using it without has a likelihood of DuplicateID being
                # raised, or just nothing showing up. By having the clear
                # options and add options functions nearby, it hopefully
                # reduces the likelihood of an empty option list
                zoxide_options.clear_options()
                zoxide_options.add_options(options)
                zoxide_options.remove_class("empty")
                zoxide_options.highlighted = 0
        else:
            # No Matches to the query text
            zoxide_options.clear_options()
            zoxide_options.add_option(
                Option("  --No matches found--", disabled=True),
            )
            zoxide_options.add_class("empty")
            zoxide_options.border_subtitle = "0/0"

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if any(
            worker.is_running and worker.node is self for worker in self.app.workers
        ):
            return
        if self.zoxide_options.highlighted is None:
            self.zoxide_options.highlighted = 0
        if (
            self.zoxide_options.highlighted_option
            and self.zoxide_options.highlighted_option.disabled
        ):
            return
        self.zoxide_options.action_select()

    # You can't manually tab into the option list, but you can click, so I guess
    @work(exclusive=True)
    async def on_option_list_option_selected(
        self, event: ZoxideOptionList.OptionSelected
    ) -> None:
        """Handle option selection."""
        selected_value = event.option.id
        assert selected_value is not None
        # ignore if zoxide got uninstalled, why are you doing this
        with contextlib.suppress(asyncio.exceptions.TimeoutError, OSError):
            zoxide_process = await asyncio.create_subprocess_exec(
                "zoxide",
                "add",
                path_utils.decompress(selected_value),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, _ = await asyncio.wait_for(zoxide_process.communicate(), timeout=3)
        if selected_value and not event.option.disabled:
            self.dismiss(selected_value)
        else:
            self.dismiss(None)

    def on_key(self, event: events.Key) -> None:
        """Handle key presses."""
        match event.key:
            case "escape":
                event.stop()
                self.dismiss(None)
            case "down":
                event.stop()
                zoxide_options = self.query_one("#zoxide_options")
                if zoxide_options.options:
                    zoxide_options.action_cursor_down()
            case "up":
                event.stop()
                zoxide_options = self.query_one("#zoxide_options")
                if zoxide_options.options:
                    zoxide_options.action_cursor_up()
            case "tab":
                event.stop()
                self.focus_next()
            case "shift+tab":
                event.stop()
                self.focus_previous()

    def on_option_list_option_highlighted(
        self, event: ZoxideOptionList.OptionHighlighted
    ) -> None:
        if (
            self.zoxide_options.option_count == 0
            or self.zoxide_options.get_option_at_index(0).disabled
        ):
            self.zoxide_options.border_subtitle = "0/0"
        elif self.zoxide_options.highlighted is not None:
            self.zoxide_options.border_subtitle = f"{self.zoxide_options.highlighted + 1}/{self.zoxide_options.option_count}"
