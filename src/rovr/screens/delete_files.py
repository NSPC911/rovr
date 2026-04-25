from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.message import Message
from textual.screen import ModalScreen

from rovr.components import PaddedOption, SpecialOptionList
from rovr.functions.utils import check_key, dismiss, get_shortest_bind
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

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            self.action_cancel(event)

    def on_key(self, event: events.Key) -> None:
        """Handle key presses."""
        if check_key(event, config["keybinds"]["delete_files"]["delete"]):
            self.action_delete(event)
        elif check_key(event, config["keybinds"]["delete_files"]["cancel"]):
            event.stop()
            self.action_cancel(event)
        elif config["settings"]["use_recycle_bin"] and check_key(
            event, config["keybinds"]["delete_files"]["trash"]
        ):
            self.action_trash(event)

    @on(Button.Pressed, "#delete")
    def action_delete(self, event: Message) -> None:
        dismiss(self, "delete", event)

    @on(Button.Pressed, "#cancel")
    def action_cancel(self, event: Message) -> None:
        dismiss(self, "cancel", event)

    @on(Button.Pressed, "#trash")
    def action_trash(self, event: Message) -> None:
        dismiss(self, "trash", event)
