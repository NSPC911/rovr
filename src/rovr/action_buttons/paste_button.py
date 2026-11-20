from __future__ import annotations

from typing import Literal, cast

from textual import work
from textual.widgets import Button

import rovr.screens as screens
from rovr.functions.cwd import getcwd
from rovr.functions.icons import get_icon
from rovr.functions.utils import s
from rovr.variables.constants import config


class PasteButton(Button):
    ALLOW_MAXIMIZE = False

    def __init__(self) -> None:
        super().__init__(get_icon("general", "paste")[0], classes="option", id="paste")
        if config["interface"]["tooltips"]:
            self.tooltip = "Paste files from clipboard"

    @work
    async def on_button_pressed(self) -> None:
        """Paste files from clipboard"""
        if self.disabled:
            return
        type_of_selection, paths = cast(
            tuple[Literal["copy", "cut"] | None, list[str]],
            self.app.query_one("Clipboard").selected,
        )
        if type_of_selection and paths:
            label = "move" if type_of_selection == "cut" else "copy"
            result = await self.app.push_screen_wait(
                screens.PasteScreen(
                    message="Are you sure you want to "
                    f"{label} {len(paths)} item{s(len(paths))}?",
                    paths=paths,
                    type_of_selection=type_of_selection,
                )
            )

            if result:
                self.app.query_one("ProcessContainer").paste_items(
                    type_of_selection, paths, getcwd()
                )
