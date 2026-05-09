from textual import events, on
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList
from textual.worker import Worker

from rovr.classes.textual_options import ModalSearcherOption
from rovr.components.special_option_lists import DoubleClickableOptionList
from rovr.functions.utils import check_key
from rovr.variables.constants import config


class ModalSearchScreen(ModalScreen):
    """Base class for search-as-you-type modal screens."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._active_worker: Worker | None = None

    def on_mount(self) -> None:
        self.search_input: Input = self.query_one(Input)
        self.search_options: DoubleClickableOptionList = self.query_one(
            DoubleClickableOptionList
        )
        self.search_input.focus()
        self.search_options.can_focus = False

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

    @on(OptionList.OptionHighlighted)
    def handle_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if (
            self.search_options.option_count == 0
            or self.search_options.get_option_at_index(0).disabled
            or self.search_options.highlighted is None
        ):
            self.search_options.border_subtitle = "0/0"
        else:
            self.search_options.border_subtitle = f"{self.search_options.highlighted + 1}/{self.search_options.option_count}"

    @on(OptionList.OptionSelected)
    async def handle_option_selected(self, event: OptionList.OptionSelected) -> None:
        if not isinstance(event.option, ModalSearcherOption):
            self.dismiss(None)
            return
        selected_value = event.option.file_path
        if selected_value and not event.option.disabled:
            self.dismiss(selected_value)
        else:
            self.dismiss(None)

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
            self.dismiss(None)
