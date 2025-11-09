from os import path
from subprocess import TimeoutExpired, run

from textual import events, work
from textual.app import ComposeResult
from textual.containers import VerticalGroup
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from rovr.classes.textual_options import ModalSearcherOption
from rovr.functions import path as path_utils
from rovr.functions.icons import get_icon_for_file, get_icon_for_folder
from rovr.variables.constants import config


class FileSearchOptionList(OptionList):
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


class FileSearch(ModalScreen):
    """Search for files recursively using fd (and optionally fzf separately)."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._queued_task = None
        self._queued_task_args: Input.Changed | None = None

    def compose(self) -> ComposeResult:
        with VerticalGroup(id="file_search_group", classes="file_search_group"):
            yield Input(
                id="file_search_input",
                placeholder="Type to search files (fd)",
            )
            yield FileSearchOptionList(
                Option("  No input provided", disabled=True),
                id="file_search_options",
                classes="empty",
            )

    def on_mount(self) -> None:
        self.search_input: Input = self.query_one("#file_search_input")
        self.search_input.border_title = "Find Files"
        self.search_input.focus()
        self.search_options: FileSearchOptionList = self.query_one(
            "#file_search_options"
        )
        self.search_options.border_title = "Files"
        self.search_options.can_focus = False
        self.fd_updater(Input.Changed(self.search_input, value=""))

    def on_input_changed(self, event: Input.Changed) -> None:
        if any(
            worker.is_running and worker.node is self for worker in self.app.workers
        ):
            self._queued_task = self.fd_updater
            self._queued_task_args = event
        else:
            self.fd_updater(event=event)

    def any_in_queue(self) -> bool:
        if self._queued_task is not None:
            self._queued_task(self._queued_task_args)
            self._queued_task, self._queued_task_args = None, None
            return True
        return False

    @work(thread=True)
    def fd_updater(self, event: Input.Changed) -> None:
        """Update the list using fd based on the search term."""
        search_term = event.value.strip()
        if self.any_in_queue():
            return

        fd_exec = config["plugins"]["finder"]["executable"]

        fd_cmd = [
            fd_exec,
            "--type",
            "f",
            "--type",
            "d",
        ]
        if config["settings"]["show_hidden_files"]:
            fd_cmd.append("--hidden")
        if not config["plugins"]["finder"]["relative_paths"]:
            fd_cmd.append("--absolute-path")
        if config["plugins"]["finder"]["follow_symlinks"]:
            fd_cmd.append("--follow")
        if search_term:
            fd_cmd.append("--")
            fd_cmd.append(search_term)
        else:
            self.app.call_from_thread(self.search_options.add_class, "empty")
            self.app.call_from_thread(self.search_options.clear_options)
            return
        try:
            fd_output = run(fd_cmd, capture_output=True, text=True, timeout=3)
        except (OSError, TimeoutExpired) as exc:
            if self.any_in_queue():
                return
            self.app.call_from_thread(self.search_options.clear_options)
            msg = (
                "  fd is missing on $PATH or cannot be executed"
                if isinstance(exc, OSError)
                else "  fd took too long to respond"
            )
            self.app.call_from_thread(
                self.search_options.add_option, Option(msg, disabled=True)
            )
            self.any_in_queue()
            return

        if self.any_in_queue():
            return

        options: list[ModalSearcherOption] = []
        if fd_output.stdout:
            for line in fd_output.stdout.splitlines():
                file_path = path_utils.normalise(line.strip())
                file_path_str = str(file_path)
                if not file_path_str:
                    continue
                display_text = f" {file_path_str}"
                icon: list[str] = (
                    get_icon_for_folder(file_path_str)
                    if path.isdir(file_path_str)
                    else get_icon_for_file(file_path_str)
                )
                options.append(
                    ModalSearcherOption(
                        icon,
                        display_text,
                        file_path_str,
                    )
                )

            self.app.call_from_thread(self.search_options.clear_options)
            if options:
                self.app.call_from_thread(self.search_options.add_options, options)
                self.app.call_from_thread(self.search_options.remove_class, "empty")
                self.app.call_from_thread(
                    lambda: setattr(self.search_options, "highlighted", 0)
                )
            else:
                self.app.call_from_thread(
                    self.search_options.add_option,
                    Option("  --No matches found--", disabled=True),
                )
                self.app.call_from_thread(self.search_options.add_class, "empty")
        else:
            self.app.call_from_thread(self.search_options.clear_options)
            self.app.call_from_thread(
                self.search_options.add_option,
                Option("  --No matches found--", disabled=True),
            )
            self.app.call_from_thread(self.search_options.add_class, "empty")

        if self.any_in_queue():
            return

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if any(
            worker.is_running and worker.node is self for worker in self.app.workers
        ):
            return
        if self.search_options.highlighted is None:
            self.search_options.highlighted = 0
        if self.search_options.option_count == 0 or (
            self.search_options.highlighted_option
            and self.search_options.highlighted_option.disabled
        ):
            return
        self.search_options.action_select()

    @work(exclusive=True)
    async def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        if not isinstance(event.option, ModalSearcherOption):
            self.dismiss(None)
            return
        selected_value = event.option.file_path
        if selected_value and not event.option.disabled:
            self.dismiss(selected_value)
        else:
            self.dismiss(None)

    def on_key(self, event: events.Key) -> None:
        match event.key:
            case "escape":
                event.stop()
                self.dismiss(None)
            case "down":
                event.stop()
                if self.search_options.options:
                    self.search_options.action_cursor_down()
            case "up":
                event.stop()
                if self.search_options.options:
                    self.search_options.action_cursor_up()
            case "tab":
                event.stop()
                self.focus_next()
            case "shift+tab":
                event.stop()
                self.focus_previous()

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        if (
            self.search_options.option_count == 0
            or self.search_options.get_option_at_index(0).disabled
            or self.search_options.highlighted is None
        ):
            self.search_options.border_subtitle = "0/0"
        else:
            self.search_options.border_subtitle = f"{str(self.search_options.highlighted + 1)}/{self.search_options.option_count}"
