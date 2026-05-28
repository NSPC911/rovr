import shlex
from contextlib import suppress
from os import path
from sys import platform

from textual import events, on
from textual.app import ComposeResult
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.widgets import Button, OptionList

from rovr.classes.textual_options import OptionWithValue
from rovr.functions.icons import get_icon_smart
from rovr.functions.utils import dismiss

from .typed import DragAndDropReturnType


class DragAndDropScreen(ModalScreen[DragAndDropReturnType]):
    def __init__(
        self,
        initial_paste_event: events.Paste,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.file_paths: set[str] = set()
        self.call_after_refresh(self.post_message, initial_paste_event)

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            yield OptionList(id="drag_and_drop_list")
            yield Button("Copy", id="copy", variant="success")
            yield Button("Move", id="move", variant="warning")

    def on_mount(self) -> None:
        self.query_one(Grid).border_title = "Drag and Drop"

    @on(events.Paste)
    def on_paste(self, event: events.Paste) -> None:
        # attempt to parse it
        # first check if it is a full filepath
        event.text = event.text.strip()
        if path.lexists(event.text):
            self.file_paths.add(event.text.strip().strip('"').strip("'"))
        # otherwise, try to parse it as a list of arguments
        else:
            file_paths: list[str] = []
            with suppress(ValueError):
                file_paths = [
                    fp.strip().strip('"').strip("'")
                    for fp in shlex.split(event.text, posix=platform != "win32")
                ]
            for file_path in file_paths:
                if path.lexists(file_path):
                    self.file_paths.add(file_path)

        options: list[OptionWithValue] = []
        for file_path in sorted(list(self.file_paths)):
            options.append(
                OptionWithValue(
                    lambda file_path=file_path: get_icon_smart(file_path),
                    path.basename(file_path),
                    file_path,
                )
            )
        self.query_one(OptionList).set_options(options)

    def on_key(self, event: events.Key) -> None:
        """Handle escape key to dismiss the dialog."""
        if event.key == "escape":
            event.stop()
            dismiss(self, None, event)

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            dismiss(self, None, event)

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id not in ("copy", "move"):
            return
        dismiss(
            self,
            DragAndDropReturnType(sorted(list(self.file_paths)), event.button.id),
            event,
        )
