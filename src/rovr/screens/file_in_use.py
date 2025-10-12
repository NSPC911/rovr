from textual import events, on
from textual.app import ComposeResult
from textual.containers import Grid, HorizontalGroup, VerticalGroup
from textual.screen import ModalScreen
from textual.widgets import Button, Label


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
            with HorizontalGroup():
                # TODO: three buttons + toggle like delete screen
                # one to eetry, another to skip, another to cancel
                yield Button("Ok", variant="primary", id="ok")

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
                self.dismiss({"value": False})

    @on(Button.Pressed, "#ok")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle OK button: return True to callers."""
        self.dismiss({"value": True})
