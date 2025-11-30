from textual import events
from textual.app import ComposeResult
from textual.containers import Grid, HorizontalGroup, VerticalGroup
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Switch


class YesOrNo(ModalScreen):
    """Screen with a dialog that asks whether you accept or deny"""

    def __init__(
        self,
        message: str,
        reverse_color: bool = False,
        with_toggle: bool = False,
        border_title: str = "",
        border_subtitle: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.message = message
        self.reverse_color = reverse_color
        self.with_toggle = with_toggle
        self.border_title = border_title
        self.border_subtitle = border_subtitle

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            with VerticalGroup(id="question_container"):
                for message in self.message.splitlines():
                    yield Label(message, classes="question")
            yield Button(
                "\\[Y]es",
                variant="error" if self.reverse_color else "primary",
                id="yes",
            )
            yield Button(
                "\\[N]o", variant="primary" if self.reverse_color else "error", id="no"
            )
            if self.with_toggle:
                with HorizontalGroup(id="dontAskAgain"):
                    yield Switch()
                    yield Label("Don't \\[a]sk again")

    def on_mount(self) -> None:
        self.query_one("#dialog").classes = "with_toggle" if self.with_toggle else ""
        self.query_one("#dialog").border_title = self.border_title
        self.query_one("#dialog").border_subtitle = self.border_subtitle

    def on_key(self, event: events.Key) -> None:
        """Handle key presses."""
        match event.key.lower():
            case "y":
                event.stop()
                self.dismiss(
                    {"value": True, "toggle": self.query_one(Switch).value}
                    if self.with_toggle
                    else True
                )
            case "n" | "escape":
                event.stop()
                self.dismiss(
                    {"value": False, "toggle": self.query_one(Switch).value}
                    if self.with_toggle
                    else False
                )
            case "a":
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
            self.dismiss("")
