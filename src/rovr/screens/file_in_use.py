from textual import events, on
from textual.app import ComposeResult
from textual.containers import Grid, VerticalGroup, HorizontalGroup
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class FileInUse(ModalScreen):
    """Screen to show when a file is in use by another process on Windows."""

    def __init__(self, message: str, **kwargs) -> None:
        # Some call sites still pass border_title/border_subtitle; remove them so
        # ModalScreen.__init__ doesn't receive unexpected keyword arguments.
        kwargs.pop("border_title", None)
        kwargs.pop("border_subtitle", None)
        super().__init__(**kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            # Follow the common modal convention: per-line Labels inside a question_container
            with VerticalGroup(id="question_container"):
                for message in self.message.splitlines():
                    yield Label(message, classes="question")
            with HorizontalGroup():
                yield Button("\\[Y]es", variant="primary", id="ok")

    def on_mount(self) -> None:
        self.query_one("#dialog").border_title = "File in Use"
        # focus the OK button like other modals
        self.query_one("#ok").focus()

    def on_key(self, event: events.Key) -> None:
        """Handle key presses: Enter -> OK, Escape -> Cancel."""
        match event.key.lower():
            case "enter" | "y":
                event.stop()
                # treat enter as OK
                self.dismiss({"value": True})
            case "escape":
                event.stop()
                # treat escape as cancel
                self.dismiss({"value": "cancel"})

    @on(Button.Pressed, "#ok")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle OK button: return True to callers."""
        self.dismiss({"value": True})
