from textual import events
from textual.app import ComposeResult
from textual.containers import Grid, HorizontalGroup, VerticalGroup
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class FileInUse(ModalScreen):
    """Screen to show when a file is in use by another process on Windows."""

    def __init__(self, message: str, border_title: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.message = message
        self.border_title = border_title

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            with VerticalGroup(id="question_container"):
                for message in self.message.splitlines():
                    yield Label(message, classes="question")
            with HorizontalGroup():
                yield Button("\\[O]K", id="ok", variant="primary")
                yield Button("\\[C]ancel", id="cancel", variant="warning")

    def on_mount(self) -> None:
        self.query_one("#dialog").border_title = self.border_title
        # focus the OK button like other modals
        try:
            self.query_one("#ok").focus()
        except Exception as _exc:  # noqa: PT001 - safe to ignore focus failures
            del _exc

    def on_key(self, event: events.Key) -> None:
        match event.key.lower():
            case "o" | "enter":
                event.stop()
                self.dismiss({"value": "ok"})
            case "c" | "escape":
                event.stop()
                self.dismiss({"value": "cancel"})

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss({"value": event.button.id == "ok"})
