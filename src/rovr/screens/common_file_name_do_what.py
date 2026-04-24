from textual import events
from textual.app import ComposeResult
from textual.containers import Grid, HorizontalGroup, VerticalGroup
from textual.screen import ModalScreen

from rovr.functions.utils import check_key, dismiss, get_shortest_bind
from rovr.variables.constants import config
from rovr.widgets import Button, Label, Switch

overwrite_bind = get_shortest_bind(config["keybinds"]["filename_conflict"]["overwrite"])
rename_bind = get_shortest_bind(config["keybinds"]["filename_conflict"]["rename"])
skip_bind = get_shortest_bind(config["keybinds"]["filename_conflict"]["skip"])
cancel_bind = get_shortest_bind(config["keybinds"]["filename_conflict"]["cancel"])
dont_ask_bind = get_shortest_bind(
    config["keybinds"]["filename_conflict"]["dont_ask_again"]
)


class FileNameConflict(ModalScreen):
    """Screen with a dialog to confirm whether to overwrite, rename, skip or cancel."""

    def __init__(
        self, message: str, border_title: str = "", border_subtitle: str = ""
    ) -> None:
        super().__init__()
        self.message = message
        self.border_title = border_title
        self.border_subtitle = border_subtitle

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            with VerticalGroup(id="question_container"):
                for message in self.message.splitlines():
                    yield Label(message, classes="question")
            yield Button(
                f"\\[{overwrite_bind}] Overwrite", variant="error", id="overwrite"
            )
            yield Button(f"\\[{rename_bind}] Rename", variant="warning", id="rename")
            yield Button(f"\\[{skip_bind}] Skip", variant="default", id="skip")
            yield Button(f"\\[{cancel_bind}] Cancel", variant="primary", id="cancel")
            with HorizontalGroup(id="dontAskAgain"):
                yield Switch()
                yield Label(f"\\[{dont_ask_bind}] Don't ask again")

    def on_mount(self) -> None:
        self.query_one("#dialog").border_title = self.border_title
        self.query_one("#dialog").border_subtitle = self.border_subtitle

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "overwrite":
                self.action_overwrite()
            case "rename":
                self.action_rename()
            case "skip":
                self.action_skip()
            case "cancel":
                self.action_cancel()

    def on_key(self, event: events.Key) -> None:
        """Handle key presses."""
        if check_key(event, config["keybinds"]["filename_conflict"]["overwrite"]):
            self.action_overwrite()
        elif check_key(event, config["keybinds"]["filename_conflict"]["rename"]):
            self.action_rename()
        elif check_key(event, config["keybinds"]["filename_conflict"]["skip"]):
            self.action_skip()
        elif check_key(event, config["keybinds"]["filename_conflict"]["cancel"]):
            self.action_cancel()
        elif check_key(
            event, config["keybinds"]["filename_conflict"]["dont_ask_again"]
        ):
            self.action_dont_ask_again()
        else:
            return
        event.stop()

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.action_cancel()

    def action_overwrite(self) -> None:
        dismiss(
            self,
            {
                "value": "overwrite",
                "same_for_next": self.query_one(Switch).value,
            },
        )

    def action_rename(self) -> None:
        dismiss(
            self,
            {
                "value": "rename",
                "same_for_next": self.query_one(Switch).value,
            },
        )

    def action_skip(self) -> None:
        dismiss(
            self,
            {
                "value": "skip",
                "same_for_next": self.query_one(Switch).value,
            },
        )

    def action_cancel(self) -> None:
        dismiss(
            self,
            {
                "value": "cancel",
                "same_for_next": self.query_one(Switch).value,
            },
        )

    def action_dont_ask_again(self) -> None:
        self.query_one(Switch).action_toggle_switch()
