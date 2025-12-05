from textual.widgets import Button

from rovr.functions.icons import get_icon
from rovr.variables.constants import config


class CutButton(Button):
    ALLOW_MAXIMIZE = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            get_icon("general", "cut")[0], classes="option", id="cut", *args, **kwargs
        )

    def on_mount(self) -> None:
        if config["interface"]["tooltips"]:
            self.tooltip = "Cut selected files"

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Cut selected files to the clipboard"""
        if self.disabled:
            return
        selected_files = await self.app.query_one("#file_list").get_selected_objects()
        if selected_files:
            self.app.query_one("#clipboard").cut_to_clipboard(selected_files)
        else:
            self.notify(
                "No files selected to cut.", title="Cut Files", severity="warning"
            )
