from textual import events
from textual.app import ComposeResult
from textual.containers import Grid, HorizontalGroup, VerticalGroup
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Switch

from rovr.classes.mixins import Action, Actionable
from rovr.functions.utils import dismiss, get_shortest_bind
from rovr.variables.constants import config

yes_bind = get_shortest_bind(config["keybinds"]["yes_or_no"]["yes"])
no_bind = get_shortest_bind(config["keybinds"]["yes_or_no"]["no"])
dont_ask_bind = get_shortest_bind(config["keybinds"]["yes_or_no"]["dont_ask_again"])


class YesOrNo(Actionable, ModalScreen):
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
        self.ACTIONS: list[Action] = [
            Action(part, config["keybinds"]["yes_or_no"][part])
            for part in ("yes", "no")
        ]
        self.ACTIONS.append(
            Action(
                "dont_ask_again",
                config["keybinds"]["yes_or_no"]["dont_ask_again"],
                self.with_toggle,
            )
        )

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
            self.action_yes(event)
        else:
            self.action_no(event)

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            self.action_no(event)

    def action_yes(self, event: Message | None = None) -> None:
        dismiss(
            self,
            {"value": True, "toggle": self.query_one(Switch).value}
            if self.with_toggle
            else True,
            event,
        )

    def action_no(self, event: Message | None = None) -> None:
        dismiss(
            self,
            {"value": False, "toggle": self.query_one(Switch).value}
            if self.with_toggle
            else False,
            event,
        )

    def action_dont_ask_again(self) -> None:
        if self.with_toggle:
            self.query_one(Switch).action_toggle_switch()
