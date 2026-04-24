from rich.markup import escape
from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container, Grid, HorizontalGroup, VerticalGroup
from textual.screen import ModalScreen

from rovr.functions.utils import check_key, dismiss, get_shortest_bind
from rovr.variables.constants import config
from rovr.widgets import Button, Label, Switch

retry_bind = get_shortest_bind(config["keybinds"]["file_in_use"]["retry"])
cancel_bind = get_shortest_bind(config["keybinds"]["file_in_use"]["cancel"])
skip_bind = get_shortest_bind(config["keybinds"]["file_in_use"]["skip"])
dont_ask_bind = get_shortest_bind(config["keybinds"]["file_in_use"]["dont_ask_again"])


class FileInUse(ModalScreen):
    """Screen to show when a file is in use by another process on Windows."""

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Grid(id="dialog", classes="file_in_use"):
            with VerticalGroup(id="question_container"):
                for message in self.message.splitlines():
                    yield Label(escape(message), classes="question")
            yield Button(f"\\[{retry_bind}] Retry", variant="primary", id="try_again")
            yield Button(f"\\[{skip_bind}] Skip", variant="warning", id="skip")
            with Container():
                yield Button(f"\\[{cancel_bind}] Cancel", variant="error", id="cancel")
            with HorizontalGroup(id="dontAskAgain"):
                yield Switch()
                yield Label(f"\\[{dont_ask_bind}] Don't ask again")

    def on_mount(self) -> None:
        self.query_one("#dialog").border_title = "File in Use"
        # focus the Try Again button like other modals
        self.query_one("#try_again").focus()
        # Optionally add padding or styling here if needed for consistency

    def on_key(self, event: events.Key) -> None:
        if check_key(event, config["keybinds"]["file_in_use"]["retry"]):
            event.stop()
            self.action_retry()
        elif check_key(event, config["keybinds"]["file_in_use"]["cancel"]):
            event.stop()
            self.action_cancel()
        elif check_key(event, config["keybinds"]["file_in_use"]["skip"]):
            event.stop()
            self.action_skip()
        elif check_key(event, config["keybinds"]["file_in_use"]["dont_ask_again"]):
            event.stop()
            self.action_toggle_dont_ask_again()

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.action_cancel()

    @on(Button.Pressed, "#try_again")
    def action_retry(self) -> None:
        dismiss(
            self,
            {
                "value": "try_again",
                "toggle": self.query_one(Switch).value,
            },
        )

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        dismiss(
            self,
            {
                "value": "cancel",
                "toggle": self.query_one(Switch).value,
            },
        )

    @on(Button.Pressed, "#skip")
    def action_skip(self) -> None:
        dismiss(self, {"value": "skip", "toggle": self.query_one(Switch).value})

    def action_toggle_dont_ask_again(self) -> None:
        self.query_one(Switch).action_toggle_switch()
