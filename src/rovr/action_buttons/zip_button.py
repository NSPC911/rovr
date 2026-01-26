from os import getcwd, path
from typing import cast

from textual import work
from textual.widgets import Button

from rovr.classes import (
    EndsWithAnArchiveExtension,
    EndsWithRar,
    IsValidFilePath,
    PathDoesntExist,
)
from rovr.functions.icons import get_icon
from rovr.functions.path import normalise
from rovr.screens import ZipUpScreen
from rovr.screens.typed import ZipScreenReturnType
from rovr.variables.constants import config


class ZipButton(Button):
    ALLOW_MAXIMIZE = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            get_icon("general", "zip")[0], classes="option", id="zip", *args, **kwargs
        )

    def on_mount(self) -> None:
        if config["interface"]["tooltips"]:
            self.tooltip = "Compress selected files"

    @work
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.disabled:
            return
        selected_files = await self.app.file_list.get_selected_objects()
        if not selected_files:
            self.notify(
                "No files selected to zip.",
                title="Zip Files",
                severity="warning",
            )
            return

        parent_folder_name = path.basename(getcwd())
        default_zip_name = f"{parent_folder_name}.zip"

        response = cast(
            ZipScreenReturnType,
            await self.app.push_screen(
                ZipUpScreen(
                    border_subtitle="Enter the name for the zip file",
                    initial_value=default_zip_name,
                    validators=[
                        PathDoesntExist(strict=False),
                        IsValidFilePath(),
                        EndsWithRar(),
                        EndsWithAnArchiveExtension(),
                    ],
                    is_path=True,
                ),
                wait_for_dismiss=True,
            ),
        )

        if not response:
            return

        archive_name = normalise(path.join(getcwd(), response.path))

        self.app.query_one("ProcessContainer").create_archive(
            selected_files, archive_name, response.algo, response.level
        )
        self.app.file_list.focus()
