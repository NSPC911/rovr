import shlex
from contextlib import suppress
from os import path
from sys import platform

from textual import events, on
from textual.app import ComposeResult
from textual.containers import Grid, HorizontalGroup
from textual.screen import ModalScreen
from textual.widgets import Button, OptionList

from rovr.classes.mixins import Action, Actionable
from rovr.classes.textual_options import OptionWithValue
from rovr.functions.icons import get_icon_smart
from rovr.functions.utils import dismiss, get_shortest_bind
from rovr.variables.constants import config

from .typed import PasteDropReturnType

copy_bind = get_shortest_bind(config["keybinds"]["drag_and_drop"]["copy"])
move_bind = get_shortest_bind(config["keybinds"]["drag_and_drop"]["move"])
cancel_bind = get_shortest_bind(config["keybinds"]["drag_and_drop"]["cancel"])


class PasteDropScreen(Actionable, ModalScreen[PasteDropReturnType]):
    def __init__(
        self,
        initial_paste_event: events.Paste,
    ) -> None:
        super().__init__()
        self.file_paths: set[str] = set()
        self.call_after_refresh(self.post_message, initial_paste_event)
        self.ACTIONS = [
            Action(
                lambda: self.query_one("#copy", Button).press,
                config["keybinds"]["drag_and_drop"]["copy"],
            ),
            Action(
                lambda: self.query_one("#move", Button).press,
                config["keybinds"]["drag_and_drop"]["move"],
            ),
            Action(
                lambda: self.query_one("#cancel", Button).press,
                config["keybinds"]["drag_and_drop"]["cancel"],
            ),
        ]

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            yield OptionList(id="drag_and_drop_list")
            yield Button("Copy", id="copy", variant="success")
            yield Button("Move", id="move", variant="warning")
            with HorizontalGroup():
                yield Button("Cancel", id="cancel", variant="error")

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

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            dismiss(self, None, event)

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "copy" | "move":
                dismiss(
                    self,
                    PasteDropReturnType(sorted(list(self.file_paths)), event.button.id),
                    event,
                )
            case "cancel":
                dismiss(self, None, event)
