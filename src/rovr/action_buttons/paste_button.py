from textual import work
from textual.widgets import Button

from rovr.classes.textual_options import ClipboardSelectionValue
from rovr.functions.cwd import getcwd
from rovr.functions.icons import get_icon
from rovr.functions.utils import s
from rovr.screens.paste_screen import PasteScreen
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
        selected_items: list[ClipboardSelectionValue] = self.app.query_one(
            "Clipboard"
        ).selected  # dont include highlighted
        if selected_items:
            # split into copy/cut based on attrs
            to_copy, to_cut = (
                [
                    item.path
                    for item in selected_items
                    if item.type_of_selection == "copy"
                ],
                [
                    item.path
                    for item in selected_items
                    if item.type_of_selection == "cut"
                ],
            )

            result = await self.app.push_screen_wait(
                PasteScreen(
                    message="Are you sure you want to "
                    + (
                        f"copy {len(to_copy)} item{s(to_copy)}{s(to_cut, ' and ')}"
                        if len(to_copy) > 0
                        else ""
                    )
                    + (f"cut {len(to_cut)} item{s(to_cut)}" if len(to_cut) > 0 else "")
                    + "?",
                    paths={"copy": to_copy, "cut": to_cut},
                    destructive=True,
                )
            )

            if result:
                self.app.query_one("ProcessContainer").paste_items(
                    to_copy, to_cut, getcwd()
                )
