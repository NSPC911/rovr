from typing import Literal

from textual.app import ComposeResult
from textual.containers import Grid, HorizontalGroup, VerticalGroup

from rovr.classes.textual_options import PasteScreenOption
from rovr.components import SpecialOptionList
from rovr.widgets import Button, Label, Switch

from .yes_or_no import YesOrNo, dont_ask_bind, no_bind, yes_bind


class PasteScreen(YesOrNo):
    def __init__(
        self,
        message: str,
        paths: dict[Literal["copy", "cut"], list[str]],
        destructive: bool = False,
        with_toggle: bool = False,
        border_title: str = "",
        border_subtitle: str = "",
    ) -> None:
        super().__init__(
            message, destructive, with_toggle, border_title, border_subtitle
        )
        self.paths = paths
        self.options = [
            PasteScreenOption(path, "copy") for path in self.paths["copy"]
        ] + [PasteScreenOption(path, "cut") for path in self.paths["cut"]]

    def compose(self) -> ComposeResult:
        with Grid(id="dialog", classes="paste"):
            with VerticalGroup(id="question_container"):
                for message in self.message.splitlines():
                    yield Label(message, classes="question")
            yield SpecialOptionList(*self.options)
            yield Button(
                f"\\[{yes_bind}] Yes",
                variant="error" if self.destructive else "success",
                id="yes",
            )
            yield Button(
                f"\\[{no_bind}] No",
                variant="success" if self.destructive else "error",
                id="no",
            )
            if self.with_toggle:
                with HorizontalGroup(id="dontAskAgain"):
                    yield Switch()
                    yield Label(f"\\[{dont_ask_bind}] Don't ask again")
