from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.screen import ModalScreen

from rovr.components import PaddedOption, SpecialOptionList
from rovr.functions.utils import check_key, get_shortest_bind
from rovr.variables.constants import config
from rovr.widgets import Button, Label

delete_bind = get_shortest_bind(config["keybinds"]["delete_files"]["delete"])
trash_bind = get_shortest_bind(config["keybinds"]["delete_files"]["trash"])
cancel_bind = get_shortest_bind(config["keybinds"]["delete_files"]["cancel"])


class DeleteFiles(ModalScreen):
    """Screen with a dialog to confirm whether to delete files."""

    def __init__(self, message: str, paths: list[str]) -> None:
        super().__init__()
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
        match event.button.id:
            case "delete":
                self.action_delete()
            case "cancel":
                self.action_cancel()
            case "trash" if config["settings"]["use_recycle_bin"]:
                self.action_trash()
            case _:
                return

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.action_cancel()

    def on_key(self, event: events.Key) -> None:
        """Handle key presses."""
        if check_key(event, config["keybinds"]["delete_files"]["delete"]):
            event.stop()
            self.action_delete()
        elif check_key(event, config["keybinds"]["delete_files"]["cancel"]):
            event.stop()
            self.action_cancel()
        elif config["settings"]["use_recycle_bin"] and check_key(
            event, config["keybinds"]["delete_files"]["trash"]
        ):
            event.stop()
            self.action_trash()

    def action_delete(self) -> None:
        self.dismiss("delete")

    def action_cancel(self) -> None:
        self.dismiss("cancel")

    def action_trash(self) -> None:
        if config["settings"]["use_recycle_bin"]:
            self.dismiss("trash")
