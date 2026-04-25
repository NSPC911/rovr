from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container, Grid, HorizontalGroup, VerticalGroup
from textual.message import Message
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
        self,
        message: str,
        border_title: str = "",
        border_subtitle: str = "",
        allow_overwrite: bool = True,
    ) -> None:
        super().__init__()
        self.message = message
        self.border_title = border_title
        self.border_subtitle = border_subtitle
        self.allow_overwrite = allow_overwrite
        if not allow_overwrite:
            self.add_class("no_overwrite")

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            with VerticalGroup(id="question_container"):
                for message in self.message.splitlines():
                    yield Label(message, classes="question")
            if self.allow_overwrite:
                yield Button(
                    f"\\[{overwrite_bind}] Overwrite", variant="error", id="overwrite"
                )
            yield Button(f"\\[{rename_bind}] Rename", variant="warning", id="rename")
            yield Button(f"\\[{skip_bind}] Skip", variant="success", id="skip")
            if not self.allow_overwrite:
                with Container():
                    yield Button(
                        f"\\[{cancel_bind}] Cancel", variant="primary", id="cancel"
                    )
            else:
                yield Button(
                    f"\\[{cancel_bind}] Cancel", variant="primary", id="cancel"
                )
            with HorizontalGroup(id="dontAskAgain"):
                yield Switch()
                yield Label(f"\\[{dont_ask_bind}] Don't ask again")

    def on_mount(self) -> None:
        self.query_one("#dialog").border_title = self.border_title
        self.query_one("#dialog").border_subtitle = self.border_subtitle

    def on_key(self, event: events.Key) -> None:
        """Handle key presses."""
        if self.allow_overwrite and check_key(
            event, config["keybinds"]["filename_conflict"]["overwrite"]
        ):
            self.action_overwrite(event)
        elif check_key(event, config["keybinds"]["filename_conflict"]["rename"]):
            self.action_rename(event)
        elif check_key(event, config["keybinds"]["filename_conflict"]["skip"]):
            self.action_skip(event)
        elif check_key(event, config["keybinds"]["filename_conflict"]["cancel"]):
            self.action_cancel(event)
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
            self.action_cancel(event)

    @on(Button.Pressed, "#overwrite")
    def action_overwrite(self, event: Message | None = None) -> None:
        dismiss(
            self,
            {
                "value": "overwrite",
                "same_for_next": self.query_one(Switch).value,
            },
            event,
        )

    @on(Button.Pressed, "#rename")
    def action_rename(self, event: Message | None = None) -> None:
        dismiss(
            self,
            {
                "value": "rename",
                "same_for_next": self.query_one(Switch).value,
            },
            event,
        )

    @on(Button.Pressed, "#skip")
    def action_skip(self, event: Message | None = None) -> None:
        dismiss(
            self,
            {
                "value": "skip",
                "same_for_next": self.query_one(Switch).value,
            },
            event,
        )

    @on(Button.Pressed, "#cancel")
    def action_cancel(self, event: Message | None = None) -> None:
        dismiss(
            self,
            {
                "value": "cancel",
                "same_for_next": self.query_one(Switch).value,
            },
            event,
        )

    def action_dont_ask_again(self) -> None:
        self.query_one(Switch).action_toggle_switch()
