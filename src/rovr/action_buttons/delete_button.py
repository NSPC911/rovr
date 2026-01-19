from textual.widgets import Button

from rovr.functions.icons import get_icon
from rovr.screens import DeleteFiles
from rovr.variables.constants import config


class DeleteButton(Button):
    ALLOW_MAXIMIZE = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            get_icon("general", "delete")[0],
            classes="option",
            id="delete",
            *args,
            **kwargs,
        )

    def on_mount(self) -> None:
        if config["interface"]["tooltips"]:
            self.tooltip = "Delete selected files"

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Delete selected files or directories"""
        if self.disabled:
            return
        selected_files = await self.app.file_list.get_selected_objects()
        if selected_files:

            async def callback(response: str) -> None:
                """Callback to remove files after confirmation"""
                if response == "delete":
                    self.app.query_one("ProcessContainer").delete_files(
                        selected_files, compressed=False, ignore_trash=True
                    )
                elif response == "trash":
                    self.app.query_one("ProcessContainer").delete_files(
                        selected_files,
                        compressed=False,
                        ignore_trash=False,
                    )

            self.app.push_screen(
                DeleteFiles(
                    message=f"Are you sure you want to delete {len(selected_files)} file{'s' if len(selected_files) != 1 else ''}?",
                    paths=selected_files,
                ),
                callback=callback,
            )
        else:
            self.notify(
                "No files selected to delete.",
                title="Delete Files",
                severity="warning",
            )
