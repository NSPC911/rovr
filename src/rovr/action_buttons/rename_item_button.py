from os import getcwd, path
from shutil import move

from textual import work
from textual.content import Content
from textual.widgets import Button

from rovr.screens import ModalInput
from rovr.utils import config, get_icon, normalise
from rovr.validators import IsValidFilePath, PathDoesntExist


class RenameItemButton(Button):
    ALLOW_MAXIMIZE = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            get_icon("general", "rename")[0],
            classes="option",
            id="rename",
            *args,
            **kwargs,
        )

    def on_mount(self) -> None:
        if config["interface"]["tooltips"]:
            self.tooltip = "Rename selected files"

    @work
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        selected_files = await self.app.query_one("#file_list").get_selected_objects()
        if selected_files is None or len(selected_files) != 1:
            self.notify(
                "Please select exactly one file to rename.",
                title="Rename File",
                severity="warning",
            )
        else:
            selected_file = selected_files[0]
            type_of_file = "Folder" if path.isdir(selected_file) else "File"
            response: str = await self.app.push_screen(
                ModalInput(
                    border_title=f"Rename {type_of_file}",
                    border_subtitle=f"Current name: {path.basename(selected_file)}",
                    initial_value=path.basename(selected_file),
                    validators=[IsValidFilePath(), PathDoesntExist()],
                    is_path=True,
                    is_folder=type_of_file == "Folder",
                ),
                wait_for_dismiss=True,
            )
            if response in ["", path.basename(selected_file)]:
                return
            old_name = normalise(path.realpath(path.join(getcwd(), selected_file)))
            new_name = normalise(path.realpath(path.join(getcwd(), response)))
            if not path.exists(old_name):
                self.notify(
                    message=f"'{selected_file}' no longer exists.",
                    title="Rename",
                    severity="error",
                )
                return
            try:
                move(old_name, new_name)
            except Exception as e:
                self.notify(
                    message=Content(
                        f"Error renaming '{selected_file}' to '{response}': {e}"
                    ),
                    title="Rename",
                    severity="error",
                )
        self.app.query_one("#file_list").focus()
