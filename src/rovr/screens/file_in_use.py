from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Grid, HorizontalGroup, VerticalGroup
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Switch


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
            yield Button("\\[R]etry", variant="primary", id="try_again")
            yield Button("\\[S]kip", variant="warning", id="skip")
            with Container():
                yield Button("\\[C]ancel", variant="error", id="cancel")
            with HorizontalGroup(id="dontAskAgain"):
                yield Switch()
                yield Label("Apply to \\[a]ll")

    def on_mount(self) -> None:
        self.query_one("#dialog").border_title = "File in Use"
        # focus the Try Again button like other modals
        self.query_one("#try_again").focus()
        # Optionally add padding or styling here if needed for consistency

    def on_key(self, event: events.Key) -> None:
        """Handle key presses: R -> Try Again, Escape/C -> Cancel, S -> Skip, A -> Toggle."""
        match event.key.lower():
            case "r":
                event.stop()
                self.dismiss({
                    "value": "try_again",
                    "toggle": self.query_one(Switch).value,
                })
            case "escape" | "c":
                event.stop()
                # treat escape/c as cancel
                self.dismiss({
                    "value": "cancel",
                    "toggle": self.query_one(Switch).value,
                })
            case "s":
                event.stop()
                self.dismiss({"value": "skip", "toggle": self.query_one(Switch).value})
            case "a":
                event.stop()
                self.query_one(Switch).action_toggle_switch()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismisss({
            "value": event.button.id,
            "toggle": self.query_one(Switch).value,
        })

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.dismiss({"value": "cancel", "toggle": self.query_one(Switch).value})
