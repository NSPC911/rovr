from textual import work
from textual.widgets import Button

from rovr.functions.icons import get_icon
from rovr.functions.path import dump_exc
from rovr.functions.system_clipboard import (
    ClipboardError,
    ClipboardToolNotFoundError,
    copy_files_to_system_clipboard,
)
from rovr.variables.constants import config


class SystemCopyButton(Button):
    ALLOW_MAXIMIZE = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            get_icon("general", "copy")[0],
            classes="option",
            id="system_copy",
            *args,
            **kwargs,
        )

    def on_mount(self) -> None:
        if config["interface"]["tooltips"]:
            self.tooltip = "Copy selected files to system clipboard"

    @work
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Copy selected files to the system clipboard."""
        if self.disabled:
            return
        selected_files = await self.app.file_list.get_selected_objects()
        if not selected_files:
            self.notify(
                "No files selected to copy.", title="System Copy", severity="warning"
            )
            return

        output = await copy_files_to_system_clipboard(selected_files)
        if output is True:
            self.notify(
                "Files copied to system clipboard.",
                title="System Copy",
                severity="information",
            )
        elif isinstance(output, ClipboardToolNotFoundError):
            self.notify(
                str(output),
                title="Missing Clipboard Tool",
                severity="error",
            )
            dump_exc(self, output)
        elif isinstance(output, ClipboardError):
            self.notify(
                str(output),
                title="Clipboard Error",
                severity="error",
            )
            dump_exc(self, output)
