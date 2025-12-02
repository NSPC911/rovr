from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Label

from rovr.functions.utils import check_key
from rovr.variables.constants import config


class DeleteFiles(ModalScreen):
    """Screen with a dialog to confirm whether to delete files."""

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            yield Label(self.message, id="question")
            if config["settings"]["use_recycle_bin"]:
                yield Button("\\[D] Trash", variant="warning", id="trash")
                yield Button("\\[X] Delete", variant="error", id="delete")
                with Container():
                    yield Button("\\[C]ancel", variant="primary", id="cancel")
            else:
                yield Button("\\[X] Delete", variant="error", id="delete")
                yield Button("\\[C]ancel", variant="primary", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        self.dismiss(event.button.id)

    def on_key(self, event: events.Key) -> None:
        """Handle key presses."""
        if check_key(event, config["keybinds"]["delete_files"]["delete"]):
            event.stop()
            self.dismiss("delete")
        elif check_key(event, config["keybinds"]["delete_files"]["cancel"]):
            event.stop()
            self.dismiss("cancel")
        elif (
            check_key(event, config["keybinds"]["delete_files"]["trash"])
            and config["settings"]["use_recycle_bin"]
        ):
            event.stop()
            self.dismiss("trash")

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.dismiss("cancel")
