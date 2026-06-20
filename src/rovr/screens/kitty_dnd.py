from asyncio import sleep

from textual import work
from textual.app import ComposeResult
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.validation import Function
from textual.widgets import Button, Input, OptionList
from textual.widgets.option_list import Option

from rovr.classes.mixins import Action, Actionable
from rovr.classes.textual_validators import IsValidFilePath, PathNoLongerExists
from rovr.functions.utils import dismiss, get_shortest_bind
from rovr.screens.typed import KittyDNDReturnType
from rovr.variables.constants import config

copy_bind = get_shortest_bind(config["keybinds"]["drag_and_drop"]["copy"])
cancel_bind = get_shortest_bind(config["keybinds"]["drag_and_drop"]["cancel"])


class KittyDND(Actionable, ModalScreen[KittyDNDReturnType | None]):
    def __init__(self, mimes: list[str]) -> None:
        super().__init__()
        self.mimes = mimes
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
            yield OptionList(
                *[Option(f" {mime}") for i, mime in enumerate(self.mimes)],
                id="kitty_dnd_list",
                markup=False,
            )
            yield Input(
                placeholder="Enter filename",
                valid_empty=False,
                id="save_name",
                validators=[
                    IsValidFilePath(),
                    PathNoLongerExists(),
                    Function(lambda v: not v.endswith("/"), "Cannot be a folder."),
                ],
                validate_on=["changed"],
            )
            yield Button("Copy", id="copy", variant="success")
            yield Button("Cancel", id="cancel", variant="error")

    def on_mount(self) -> None:
        self.option_list = self.query_one(OptionList)
        self.option_list.border_title = "Select MIME type"
        self.input = self.query_one(Input)
        self.post_message(Input.Changed(self.input, self.input.value))

    def on_input_changed(self, event: Input.Changed) -> None:
        if self.input.is_valid and event.value != "":
            self.input.classes = "valid"
            self.input.border_subtitle = ""
        else:
            self.input.classes = "invalid"
            if event.validation_result:
                try:
                    self.input.border_subtitle = str(
                        event.validation_result.failure_descriptions[0]
                    )
                except IndexError:
                    # fuck it, just post a new message
                    self.post_message(
                        Input.Changed(
                            self.input,
                            self.input.value,
                            self.input.validate(self.input.value),
                        )
                    )
            else:
                # valid_empty = False
                self.input.border_subtitle = "The value must not be empty!"

    @work
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.input.is_valid and event.value != "":
            self.query_one("#copy").press()
        else:
            for _ in range(2):
                self.query_one("#dialog").styles.offset = (1, 0)
                await sleep(0.1)
                self.query_one("#dialog").styles.offset = (0, 0)
                await sleep(0.1)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "copy":
                dismiss(
                    self,
                    KittyDNDReturnType(
                        self.query_one(OptionList).highlighted,
                        self.query_one(Input).value,
                    ),
                )
            case "cancel":
                dismiss(self, None, event)
