from rovr.functions.icons import get_icon
from rovr.variables.constants import config
from rovr.widgets import Button


class CutButton(Button):
    ALLOW_MAXIMIZE = False

    def __init__(self) -> None:
        super().__init__(get_icon("general", "cut")[0], classes="option", id="cut")
        if config["interface"]["tooltips"]:
            self.tooltip = "Cut selected files"

    async def on_button_pressed(self) -> None:
        """Cut selected files to the clipboard"""
        if self.disabled:
            return
        selected_files = await self.app.file_list.get_selected_objects()
        if selected_files:
            self.app.Clipboard.cut_to_clipboard(selected_files)
        else:
            self.notify(
                "No files selected to cut.", title="Cut Files", severity="warning"
            )
