from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.screen import ModalScreen

from rovr.widgets import Button, Label


class Dismissible(ModalScreen):
    """Super simple screen that can be dismissed."""

    def __init__(
        self, message: str, border_subtitle: str = "", additional_classes: str = ""
    ) -> None:
        super().__init__()
        self.message = message
        self.border_subtitle = border_subtitle
        self.add_class(additional_classes)

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            yield Label(self.message, id="message")
            with Container():
                yield Button("Ok", variant="primary", id="ok")

    def on_mount(self) -> None:
        self.query_one("#ok").focus()
        self.query_one("#dialog").border_subtitle = self.border_subtitle

    def on_key(self, event: events.Key) -> None:
        """Handle key presses."""
        if event.key in ("escape", "enter"):
            event.stop()
            self.dismiss()

    @on(Button.Pressed, "#ok")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        self.dismiss()

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.dismiss()
