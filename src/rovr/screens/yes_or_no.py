from textual import events
from textual.app import ComposeResult
from textual.containers import Grid, HorizontalGroup, VerticalGroup
from textual.screen import ModalScreen

from rovr.functions.utils import check_key, get_shortest_bind
from rovr.variables.constants import config
from rovr.widgets import Button, Label, Switch

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
    ) -> None:
        super().__init__()
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.action_yes()
        else:
            self.action_no()

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.action_no()

    def on_key(self, event: events.Key) -> None:
        """Handle key presses."""
        if check_key(event, config["keybinds"]["yes_or_no"]["yes"]):
            self.action_yes()
        elif check_key(event, config["keybinds"]["yes_or_no"]["no"]):
            self.action_no()
        elif self.with_toggle and check_key(
            event, config["keybinds"]["yes_or_no"]["dont_ask_again"]
        ):
            self.action_toggle_dont_ask_again()
        else:
            return
        event.stop()

    def action_yes(self) -> None:
        self.dismiss(
            {"value": True, "toggle": self.query_one(Switch).value}
            if self.with_toggle
            else True
        )

    def action_no(self) -> None:
        self.dismiss(
            {"value": False, "toggle": self.query_one(Switch).value}
            if self.with_toggle
            else False
        )

    def action_toggle_dont_ask_again(self) -> None:
        if self.with_toggle:
            self.query_one(Switch).action_toggle_switch()
