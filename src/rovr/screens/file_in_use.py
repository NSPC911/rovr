from typing import Literal, TypedDict

from rich.markup import escape
from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container, Grid, HorizontalGroup
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Switch

from rovr.functions.utils import check_key, dismiss, get_shortcut
from rovr.variables.constants import config


class FileInUse(ModalScreen):
    """Screen to show when a file is in use by another process on Windows."""

    key_contexts = ("file_in_use",)

    class ReturnType(TypedDict):
        value: Literal["try_again", "cancel", "skip"]
        toggle: bool

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        retry_bind = get_shortcut("file_in_use", "retry")
        cancel_bind = get_shortcut("file_in_use", "cancel")
        skip_bind = get_shortcut("file_in_use", "skip")
        dont_ask_bind = get_shortcut(
            "file_in_use", "toggle_dont_ask_again", legacy_action="dont_ask_again"
        )
        with Grid(id="dialog"):
            yield Label(escape(self.message), classes="question")
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
        if getattr(self.app, "keys", ()):
            return
        if check_key(event, config["keybinds"]["file_in_use"]["retry"]):
            self.action_retry(event)
        elif check_key(event, config["keybinds"]["file_in_use"]["cancel"]):
            self.action_cancel(event)
        elif check_key(event, config["keybinds"]["file_in_use"]["skip"]):
            self.action_skip(event)
        elif check_key(event, config["keybinds"]["file_in_use"]["dont_ask_again"]):
            self.action_toggle_dont_ask_again()

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.action_cancel()

    @on(Button.Pressed, "#try_again")
    def action_retry(self, event: Message | None = None) -> None:
        dismiss(
            self,
            FileInUse.ReturnType(
                value="try_again",
                toggle=self.query_one(Switch).value,
            ),
            event,
        )

    @on(Button.Pressed, "#cancel")
    def action_cancel(self, event: Message | None = None) -> None:
        dismiss(
            self,
            FileInUse.ReturnType(
                value="cancel",
                toggle=self.query_one(Switch).value,
            ),
            event,
        )

    @on(Button.Pressed, "#skip")
    def action_skip(self, event: Message | None = None) -> None:
        dismiss(
            self,
            FileInUse.ReturnType(value="skip", toggle=self.query_one(Switch).value),
            event,
        )

    def action_toggle_dont_ask_again(self) -> None:
        self.query_one(Switch).action_toggle_switch()
