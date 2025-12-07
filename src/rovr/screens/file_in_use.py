from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Grid, HorizontalGroup, VerticalGroup
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Switch

from rovr.functions.utils import check_key
from rovr.variables.constants import config

least_len: tuple[int | None, str] = (None, "")
for bind in config["keybinds"]["file_in_use"]["retry"]:
    if least_len[0] is None or least_len[0] > len(bind):
        least_len = (len(bind), bind)
retry_bind = least_len[1]
least_len: tuple[int | None, str] = (None, "")
for bind in config["keybinds"]["file_in_use"]["cancel"]:
    if least_len[0] is None or least_len[0] > len(bind):
        least_len = (len(bind), bind)
cancel_bind = least_len[1]
least_len: tuple[int | None, str] = (None, "")
for bind in config["keybinds"]["file_in_use"]["skip"]:
    if least_len[0] is None or least_len[0] > len(bind):
        least_len = (len(bind), bind)
skip_bind = least_len[1]
least_len: tuple[int | None, str] = (None, "")
for bind in config["keybinds"]["file_in_use"]["dont_ask_again"]:
    if least_len[0] is None or least_len[0] > len(bind):
        least_len = (len(bind), bind)
dont_ask_bind = least_len[1]


class FileInUse(ModalScreen):
    """Screen to show when a file is in use by another process on Windows."""

    def __init__(self, message: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            with VerticalGroup(id="question_container"):
                for message in self.message.splitlines():
                    yield Label(message, classes="question")
            yield Button(f"\\[{retry_bind}] Retry", variant="primary", id="try_again")
            yield Button(f"\\[{skip_bind}] Skip", variant="warning", id="skip")
            with Container():
                yield Button(f"\\[{cancel_bind}] Cancel", variant="error", id="cancel")
            with HorizontalGroup(id="dontAskAgain"):
                yield Switch()
                yield Label(f"[{dont_ask_bind}] Don't ask again")

    def on_mount(self) -> None:
        self.query_one("#dialog").border_title = "File in Use"
        # focus the Try Again button like other modals
        self.query_one("#try_again").focus()
        # Optionally add padding or styling here if needed for consistency

    def on_key(self, event: events.Key) -> None:
        if check_key(event, config["keybinds"]["file_in_use"]["retry"]):
            event.stop()
            self.dismiss({
                "value": "try_again",
                "toggle": self.query_one(Switch).value,
            })
        elif check_key(event, config["keybinds"]["file_in_use"]["cancel"]):
            event.stop()
            self.dismiss({
                "value": "cancel",
                "toggle": self.query_one(Switch).value,
            })
        elif check_key(event, config["keybinds"]["file_in_use"]["skip"]):
            event.stop()
            self.dismiss({"value": "skip", "toggle": self.query_one(Switch).value})
        elif check_key(event, config["keybinds"]["file_in_use"]["dont_ask_again"]):
            event.stop()
            self.query_one(Switch).action_toggle_switch()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss({
            "value": event.button.id,
            "toggle": self.query_one(Switch).value,
        })

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.dismiss({"value": "cancel", "toggle": self.query_one(Switch).value})
