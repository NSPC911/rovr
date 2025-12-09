import asyncio
import contextlib
from os import path
from typing import ClassVar

from rich.segment import Segment
from rich.style import Style
from textual import events, on, work
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalGroup
from textual.screen import ModalScreen
from textual.strip import Strip
from textual.widgets import Input, OptionList, SelectionList
from textual.widgets.option_list import Option, OptionDoesNotExist
from textual.widgets.selection_list import Selection
from textual.worker import Worker, WorkerCancelled, get_current_worker

from rovr.classes.textual_options import ModalSearcherOption
from rovr.functions import icons as icon_utils
from rovr.functions import path as path_utils
from rovr.functions.icons import get_icon_for_file, get_icon_for_folder
from rovr.functions.utils import check_key
from rovr.variables.constants import config, vindings
from rovr.variables.maps import FD_TYPE_TO_ALIAS

INITIAL_FILTER_TYPES: dict[str, bool] = {
    ft: (ft in config["plugins"]["fd"]["default_filter_types"]) for ft in FD_TYPE_TO_ALIAS
}


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
        if self.screen.focused is not self.screen.search_input:
            self.screen.search_input.focus()


class FileSearchToggles(SelectionList):
    BINDINGS: ClassVar[list[BindingType]] = list(vindings)

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
            Selection("Filter Type", "", False, disabled=True),
            Selection("Files", "file", INITIAL_FILTER_TYPES["file"]),
            Selection("Folders", "directory", INITIAL_FILTER_TYPES["directory"]),
            Selection("Symlinks", "symlink", INITIAL_FILTER_TYPES["symlink"]),
            Selection("Executables", "executable", INITIAL_FILTER_TYPES["executable"]),
            Selection("Empty", "empty", INITIAL_FILTER_TYPES["empty"]),
            Selection("Socket", "socket", INITIAL_FILTER_TYPES["socket"]),
            Selection("Pipe", "pipe", INITIAL_FILTER_TYPES["pipe"]),
            Selection(
                "Char-Device", "char-device", INITIAL_FILTER_TYPES["char-device"]
            ),
            Selection(
                "Block-Device", "block-device", INITIAL_FILTER_TYPES["block-device"]
            ),
            id="file_search_toggles",
        )

    def on_mount(self) -> None:
        self.border_title = "Finder Options"

    # Use better versions of the checkbox icons
    def _get_left_gutter_width(
        self,
    ) -> int:
        """Returns the size of any left gutter that should be taken into account.

        Returns:
            The width of the left gutter.
        """
        # Calculate the exact width of the checkbox components
        return len(
            icon_utils.get_toggle_button_icon("left")
            + icon_utils.get_toggle_button_icon("inner")
            + " "
        )

    def render_line(self, y: int) -> Strip:
        """Render a line in the display.

        Args:
            y: The line to render.

        Returns:
            A [`Strip`][textual.strip.Strip] that is the line to render.
        """
        # Insane monkey patching was done here, mainly:
        # - replacing render_line from OptionList with super_render_line()
        #   to theme selected options when not highlighted.
        #   - ignore checkbox rendering on disabled options.
        # - using custom icons for the checkbox.

        def super_render_line(y: int, selection_style: str = "") -> Strip:
            line_number = self.scroll_offset.y + y
            try:
                option_index, line_offset = self._lines[line_number]
                option = self.options[option_index]
            except IndexError:
                return Strip.blank(
                    self.scrollable_content_region.width,
                    self.get_visual_style("option-list--option").rich_style,
                )

            mouse_over: bool = self._mouse_hovering_over == option_index
            component_class = ""
            if selection_style == "selection-list--button-selected":
                component_class = selection_style
            elif option.disabled:
                component_class = "option-list--option-disabled"
            elif self.highlighted == option_index:
                component_class = "option-list--option-highlighted"
            elif mouse_over:
                component_class = "option-list--option-hover"

            if component_class:
                style = self.get_visual_style("option-list--option", component_class)
            else:
                style = self.get_visual_style("option-list--option")

            strips = self._get_option_render(option, style)
            try:
                strip = strips[line_offset]
            except IndexError:
                return Strip.blank(
                    self.scrollable_content_region.width,
                    self.get_visual_style("option-list--option").rich_style,
                )
            return strip

        # calculate with checkbox rendering
        _, scroll_y = self.scroll_offset
        selection_index = scroll_y + y
        try:
            selection = self.get_option_at_index(selection_index)
        except OptionDoesNotExist:
            return Strip([*super_render_line(y)])

        if selection.disabled:
            return Strip([*super_render_line(y)])

        component_style = "selection-list--button"
        if selection.value in self._selected:
            component_style += "-selected"
        if self.highlighted == selection_index:
            component_style += "-highlighted"

        line = super_render_line(y, component_style)
        underlying_style = next(iter(line)).style or self.rich_style
        assert underlying_style is not None

        button_style = self.get_component_rich_style(component_style)

        side_style = Style.from_color(button_style.bgcolor, underlying_style.bgcolor)

        side_style += Style(meta={"option": selection_index})
        button_style += Style(meta={"option": selection_index})

        return Strip([
            Segment(icon_utils.get_toggle_button_icon("left"), style=side_style),
            Segment(
                icon_utils.get_toggle_button_icon("inner_filled")
                if selection.value in self._selected
                else icon_utils.get_toggle_button_icon("inner"),
                style=button_style,
            ),
            Segment(" ", style=underlying_style),
            *line,
        ])


class FileSearch(ModalScreen):
    """Search for files recursively using fd."""

    FILTER_TYPES: dict[str, bool] = INITIAL_FILTER_TYPES.copy()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._active_worker: Worker | None = None

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
        yield FileSearchToggles()

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
        self.fd_updater(event=event)

    @work
    async def fd_updater(self, event: Input.Changed) -> None:
        """Update the list using fd based on the search term."""
        self._active_worker = get_current_worker()
        search_term = event.value.strip()
        fd_exec = config["plugins"]["fd"]["executable"]

        fd_cmd = [fd_exec]
        if config["settings"]["show_hidden_files"]:
            fd_cmd.append("--hidden")
        if not config["plugins"]["fd"]["relative_paths"]:
            fd_cmd.append("--absolute-path")
        if config["plugins"]["fd"]["follow_symlinks"]:
            fd_cmd.append("--follow")
        if config["plugins"]["fd"]["no_ignore_parent"]:
            fd_cmd.append("--no-ignore-parent")
        for filter_type, should_use in self.FILTER_TYPES.items():
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
        try:
            fd_process = await asyncio.create_subprocess_exec(
                *fd_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(fd_process.communicate(), timeout=3)
        except (OSError, asyncio.exceptions.TimeoutError) as exc:
            if isinstance(exc, asyncio.exceptions.TimeoutError):
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

        options: list[ModalSearcherOption] = []
        if stdout:
            stdout = stdout.decode()
            worker = self.create_options(stdout)
            try:
                options: list[ModalSearcherOption] = await worker.wait()
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
            else:
                self.search_options.add_option(
                    Option("  --No matches found--", disabled=True),
                )
                self.search_options.add_class("empty")
                self.search_options.border_subtitle = ""
        else:
            self.search_options.clear_options()
            self.search_options.add_option(
                Option("  --No matches found--", disabled=True),
            )
            self.search_options.add_class("empty")
            self.search_options.border_subtitle = ""

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
    @on(OptionList.OptionSelected, "FileSearchOptionList")
    async def file_search_option_selected(
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

    @on(OptionList.OptionHighlighted, "FileSearchOptionList")
    def file_search_change_highlighted(
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

    @on(SelectionList.SelectionToggled)
    def toggles_toggled(self, event: SelectionList.SelectionToggled) -> None:
        if event.selection.value in self.FILTER_TYPES:
            self.FILTER_TYPES[event.selection.value] = (
                event.selection.value in event.selection_list.selected
            )
        elif event.selection.value in (config["plugins"]["fd"]):
            config["plugins"]["fd"][event.selection.value] = (
                event.selection.value in event.selection_list._selected
            )
        self.post_message(
            Input.Changed(self.search_input, value=self.search_input.value)
        )

    @work(thread=True, exit_on_error=False)
    def create_options(self, stdout: str) -> list[ModalSearcherOption] | None:
        options: list[ModalSearcherOption] = []
        for line in stdout.splitlines():
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
        return options

    def on_key(self, event: events.Key) -> None:
        if check_key(event, config["keybinds"]["filter_modal"]["exit"]):
            event.stop()
            self.dismiss(None)
        elif check_key(
            event, config["keybinds"]["filter_modal"]["down"]
        ) and isinstance(self.focused, Input):
            event.stop()
            if self.search_options.options:
                self.search_options.action_cursor_down()
        elif check_key(event, config["keybinds"]["filter_modal"]["up"]) and isinstance(
            self.focused, Input
        ):
            event.stop()
            if self.search_options.options:
                self.search_options.action_cursor_up()
        elif event.key == "tab":
            event.stop()
            self.focus_next()
        elif event.key == "shift+tab":
            event.stop()
            self.focus_previous()

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.dismiss("")
