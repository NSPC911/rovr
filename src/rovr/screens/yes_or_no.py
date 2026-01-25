from textual import events
from textual.app import ComposeResult
from textual.containers import Grid, HorizontalGroup, VerticalGroup
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Switch

from rovr.functions.utils import check_key, get_shortest_bind
from rovr.variables.constants import config

yes_bind = get_shortest_bind(config["keybinds"]["yes_or_no"]["yes"])
no_bind = get_shortest_bind(config["keybinds"]["yes_or_no"]["no"])
dont_ask_bind = get_shortest_bind(config["keybinds"]["yes_or_no"]["dont_ask_again"])


class YesOrNo(ModalScreen):
    """Screen with a dialog that asks whether you accept or deny"""

    def __init__(
        self,
        message: str,
        destructive: bool = False,
        with_toggle: bool = False,
        border_title: str = "",
        border_subtitle: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.message = message
        self.destructive = destructive
        self.with_toggle = with_toggle
        self.border_title = border_title
        self.border_subtitle = border_subtitle

    def compose(self) -> ComposeResult:
        with Grid(id="dialog", classes="yes_or_no"):
            with VerticalGroup(id="question_container"):
                for message in self.message.splitlines():
                    yield Label(message, classes="question")
            yield Button(
                f"\\[{yes_bind}] Yes",
                variant="error" if self.destructive else "success",
                id="yes",
            )
            yield Button(
                f"\\[{no_bind}] No",
                variant="success" if self.destructive else "error",
                id="no",
            )
            if self.with_toggle:
                with HorizontalGroup(id="dontAskAgain"):
                    yield Switch()
                    yield Label(f"\\[{dont_ask_bind}] Don't ask again")

    def on_mount(self) -> None:
        self.query_one("#dialog").classes = "with_toggle" if self.with_toggle else ""
        self.query_one("#dialog").border_title = self.border_title
        self.query_one("#dialog").border_subtitle = self.border_subtitle

    def on_key(self, event: events.Key) -> None:
        """Handle key presses."""
        if check_key(event, config["keybinds"]["yes_or_no"]["yes"]):
            event.stop()
            self.dismiss(
                {"value": True, "toggle": self.query_one(Switch).value}
                if self.with_toggle
                else True
            )
        elif check_key(event, config["keybinds"]["yes_or_no"]["no"]):
            event.stop()
            self.dismiss(
                {"value": False, "toggle": self.query_one(Switch).value}
                if self.with_toggle
                else False
            )
        elif (
            check_key(event, config["keybinds"]["yes_or_no"]["dont_ask_again"])
            and self.with_toggle
        ):
            event.stop()
            self.query_one(Switch).action_toggle_switch()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(
            {"value": event.button.id == "yes", "toggle": self.query_one(Switch).value}
            if self.with_toggle
            else event.button.id == "yes"
        )

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.dismiss(
                {"value": False, "toggle": self.query_one(Switch).value}
                if self.with_toggle
                else False
            )
