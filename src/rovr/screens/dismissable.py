from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class Dismissable(ModalScreen):
    """Super simple screen that can be dismissed."""

    def __init__(self, message: str, border_subtitle: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.message = message
        self.border_subtitle = border_subtitle

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
        match event.key:
            case "escape" | "enter":
                event.stop()
                self.dismiss()
            case "tab":
                event.stop()
                self.focus_next()
            case "shift+tab":
                event.stop()
                self.focus_previous()

    @on(Button.Pressed, "#ok")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        self.dismiss()

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.dismiss()
