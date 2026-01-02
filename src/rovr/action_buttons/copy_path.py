from textual.widgets import Button

from rovr.classes.textual_options import FileListSelectionWidget
from rovr.functions.icons import get_icon
from rovr.functions.path import normalise
from rovr.variables.constants import config


class PathCopyButton(Button):
    ALLOW_MAXIMIZE = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            get_icon("general", "link")[0],
            classes="option",
            id="copy_path",
            *args,
            **kwargs,
        )

    def on_mount(self) -> None:
        if config["interface"]["tooltips"]:
            self.tooltip = "Copy path of item to the clipboard"

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Copy selected files to the clipboard"""
        if self.disabled:
            return
        highlighted: FileListSelectionWidget | None = (
            self.app.file_list.highlighted_option
        )
        if highlighted is None or not hasattr(highlighted, "dir_entry"):
            self.notify(
                "No items were selected.", title="Copy Path", severity="information"
            )
        else:
            self.app.copy_to_clipboard(normalise(highlighted.dir_entry.path))
            self.notify("Copied!", title="Copy Path", severity="information")
