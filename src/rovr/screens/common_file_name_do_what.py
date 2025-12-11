from textual import events
from textual.app import ComposeResult
from textual.containers import Grid, HorizontalGroup, VerticalGroup
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Switch

from rovr.functions.utils import check_key, get_shortest_bind
from rovr.variables.constants import config

overwrite_bind = get_shortest_bind(config["keybinds"]["filename_conflict"]["overwrite"])
rename_bind = get_shortest_bind(config["keybinds"]["filename_conflict"]["rename"])
skip_bind = get_shortest_bind(config["keybinds"]["filename_conflict"]["skip"])
cancel_bind = get_shortest_bind(config["keybinds"]["filename_conflict"]["cancel"])
dont_ask_bind = get_shortest_bind(config["keybinds"]["filename_conflict"]["dont_ask_again"])


class CommonFileNameDoWhat(ModalScreen):
    """Screen with a dialog to confirm whether to overwrite, rename, skip or cancel."""

    def __init__(
        self, message: str, border_title: str = "", border_subtitle: str = "", **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.message = message
        self.border_title = border_title
        self.border_subtitle = border_subtitle

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            with VerticalGroup(id="question_container"):
                for message in self.message.splitlines():
                    yield Label(message, classes="question")
            yield Button(
                f"\\[{overwrite_bind}] overwrite", variant="error", id="overwrite"
            )
            yield Button(f"\\[{rename_bind}] rename", variant="warning", id="rename")
            yield Button(f"\\[{skip_bind}] skip", variant="default", id="skip")
            yield Button(f"\\[{cancel_bind}] cancel", variant="primary", id="cancel")
            with HorizontalGroup(id="dontAskAgain"):
                yield Switch()
                yield Label(f"\\[{dont_ask_bind}] Don't ask again")

    def on_mount(self) -> None:
        self.query_one("#dialog").border_title = self.border_title
        self.query_one("#dialog").border_subtitle = self.border_subtitle

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss({
            "value": event.button.id,
            "same_for_next": self.query_one(Switch).value,
        })

    def on_key(self, event: events.Key) -> None:
        """Handle key presses."""
        if check_key(event, config["keybinds"]["filename_conflict"]["overwrite"]):
            event.stop()
            self.dismiss({
                "value": "overwrite",
                "same_for_next": self.query_one(Switch).value,
            })
        elif check_key(event, config["keybinds"]["filename_conflict"]["rename"]):
            event.stop()
            self.dismiss({
                "value": "rename",
                "same_for_next": self.query_one(Switch).value,
            })
        elif check_key(event, config["keybinds"]["filename_conflict"]["skip"]):
            event.stop()
            self.dismiss({
                "value": "skip",
                "same_for_next": self.query_one(Switch).value,
            })
        elif check_key(event, config["keybinds"]["filename_conflict"]["cancel"]):
            event.stop()
            self.dismiss({
                "value": "cancel",
                "same_for_next": self.query_one(Switch).value,
            })
        elif check_key(
            event, config["keybinds"]["filename_conflict"]["dont_ask_again"]
        ):
            event.stop()
            self.query_one(Switch).action_toggle_switch()

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.dismiss({
                "value": "cancel",
                "same_for_next": self.query_one(Switch).value,
            })
