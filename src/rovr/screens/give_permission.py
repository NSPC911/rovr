from textual import events
from textual.app import ComposeResult
from textual.containers import Grid, HorizontalGroup, VerticalGroup
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Switch


class GiveMePermission(ModalScreen):
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
            yield Button("\\[Y]es", id="force", variant="error")
            yield Button("\\[N]o/\\[S]kip", id="skip", variant="warning")
            with HorizontalGroup():
                yield Button("\\[C]ancel", id="cancel", variant="default")
            with HorizontalGroup(id="dontAskAgain"):
                yield Switch()
                yield Label("Don't \\[a]sk again")

    def on_mount(self) -> None:
        self.query_one("#dialog").border_title = self.border_title
        self.query_one("#dialog").border_subtitle = self.border_subtitle

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss({"value": event.button.id, "toggle": self.query_one(Switch).value})

    def on_key(self, event: events.Key) -> None:
        match event.key.lower():
            case "y":
                event.stop()
                self.dismiss({"value": "force", "toggle": self.query_one(Switch).value})
            case "n" | "s":
                event.stop()
                self.dismiss({"value": "skip", "toggle": self.query_one(Switch).value})
            case "escape" | "c":
                event.stop()
                self.dismiss({
                    "value": "cancel",
                    "toggle": self.query_one(Switch).value,
                })
            case "a":
                event.stop()
                self.query_one(Switch).action_toggle_switch()

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.dismiss("")
