from os import getcwd, path

from textual import work
from textual.widgets import Button

from rovr.classes import IsValidFilePath
from rovr.functions.icons import get_icon
from rovr.functions.path import normalise
from rovr.screens import ModalInput
from rovr.variables.constants import config


class UnzipButton(Button):
    ALLOW_MAXIMIZE = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            get_icon("general", "open")[0],
            classes="option",
            id="unzip",
            *args,
            **kwargs,
        )

    def on_mount(self) -> None:
        if config["interface"]["tooltips"]:
            self.tooltip = "Extract selected archive"

    @work
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.disabled:
            return
        selected_files = await self.app.file_list.get_selected_objects()
        if not selected_files or len(selected_files) != 1:
            self.notify(
                "Please select exactly one archive to extract.",
                title="Unzip File",
                severity="warning",
            )
            return

        archive_path = selected_files[0]
        archive_name = path.basename(archive_path)

        default_folder_name = archive_name.rsplit(".", 1)[0]

        response: str = await self.app.push_screen(
            ModalInput(
                border_title="Extract Archive",
                border_subtitle=f"Extract '{archive_name}' to a new folder:",
                initial_value=default_folder_name,
                validators=[IsValidFilePath()],
                is_path=True,
                is_folder=True,
            ),
            wait_for_dismiss=True,
        )

        if not response:
            return

        destination_path = normalise(path.join(getcwd(), response))

        self.app.query_one("ProcessContainer").extract_archive(
            archive_path, destination_path
        )
        self.app.file_list.focus()
