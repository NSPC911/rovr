from textual import events, on
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
            yield Button("\\[R]Try Again", variant="primary", id="try_again")
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
        """Handle key presses: Enter -> Try Again, Escape/C -> Cancel, S -> Skip, A -> Toggle."""
        match event.key.lower():
            case "t":
                event.stop()
                # treat enter as Try Again
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

    @on(Button.Pressed, "#try_again")
    def on_try_again(self, event: Button.Pressed) -> None:
        """Handle Try Again button: return 'try_again' to callers."""
        self.dismiss({"value": "try_again", "toggle": self.query_one(Switch).value})

    @on(Button.Pressed, "#skip")
    def on_skip(self, event: Button.Pressed) -> None:
        """Handle Skip button: return 'skip' to callers."""
        self.dismiss({"value": "skip", "toggle": self.query_one(Switch).value})

    @on(Button.Pressed, "#cancel")
    def on_cancel(self, event: Button.Pressed) -> None:
        """Handle Cancel button: return 'cancel' to callers."""
        self.dismiss({"value": "cancel", "toggle": self.query_one(Switch).value})
