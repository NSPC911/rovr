from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Label

from rovr.components import PaddedOption, SpecialOptionList
from rovr.functions.utils import check_key, get_shortest_bind
from rovr.variables.constants import config

delete_bind = get_shortest_bind(config["keybinds"]["delete_files"]["delete"])
trash_bind = get_shortest_bind(config["keybinds"]["delete_files"]["trash"])
cancel_bind = get_shortest_bind(config["keybinds"]["delete_files"]["cancel"])


class DeleteFiles(ModalScreen):
    """Screen with a dialog to confirm whether to delete files."""

    def __init__(self, message: str, paths: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self.message = message
        self.paths = paths

    def compose(self) -> ComposeResult:
        with Grid(
            id="dialog",
            classes=("with_trash" if config["settings"]["use_recycle_bin"] else "")
            + " delete",
        ):
            yield Label(self.message, id="question")
            yield SpecialOptionList(
                *[PaddedOption(loc) for loc in self.paths],
            )
            if config["settings"]["use_recycle_bin"]:
                yield Button(f"\\[{trash_bind}] Trash", variant="warning", id="trash")
                yield Button(f"\\[{delete_bind}] Delete", variant="error", id="delete")
                with Container():
                    yield Button(
                        f"\\[{cancel_bind}] Cancel", variant="success", id="cancel"
                    )
            else:
                yield Button(f"\\[{delete_bind}] Delete", variant="error", id="delete")
                yield Button(
                    f"\\[{cancel_bind}] Cancel", variant="success", id="cancel"
                )

    def on_mount(self) -> None:
        self.query_one("#cancel").focus()

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
