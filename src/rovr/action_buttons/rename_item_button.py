import contextlib
from os import getcwd, path
from shutil import move
from typing import cast

from textual import work
from textual.content import Content
from textual.widgets import Button
from textual.worker import Worker, WorkerError

from rovr.classes import IsValidFilePath, PathDoesntExist
from rovr.functions.icons import get_icon
from rovr.functions.path import normalise
from rovr.screens import ModalInput
from rovr.variables.constants import config


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
        if self.disabled:
            return
        selected_files = await self.app.query_one("#file_list").get_selected_objects()
        if selected_files is None or len(selected_files) != 1:
            self.notify(
                "Please select exactly one file to rename.",
                title="Rename File",
                severity="warning",
            )
            return
        else:
            selected_file = selected_files[0]
            type_of_file = "Folder" if path.isdir(selected_file) else "File"
            response: str = await self.app.push_screen(
                ModalInput(
                    border_title=f"Rename {type_of_file}",
                    border_subtitle=f"Current name: {path.basename(selected_file)}",
                    initial_value=path.basename(selected_file),
                    validators=[
                        IsValidFilePath(),
                        PathDoesntExist(accept=[path.basename(selected_file)]),
                    ],
                    is_path=True,
                    is_folder=type_of_file == "Folder",
                ),
                wait_for_dismiss=True,
            )
            if response in ["", path.basename(selected_file)]:
                return
            old_name = normalise(path.abspath(path.join(getcwd(), selected_file)))
            new_name = normalise(path.abspath(path.join(getcwd(), response)))
            if not path.exists(old_name):
                self.notify(
                    message=f"'{selected_file}' no longer exists.",
                    title="Rename",
                    severity="error",
                )
                return
            elif old_name == new_name:
                return
            try:
                move(old_name, new_name)
            except Exception as e:
                # i had to force a cast, i didn't have any other choice
                # notify supports non-string objects, but ty wasn't taking
                # any of it, so i had to cast it
                self.notify(
                    message=cast(
                        str,
                        Content(
                            f"Error renaming '{selected_file}' to '{response}': {e}"
                        ),
                    ),
                    title="Rename",
                    severity="error",
                )
        self.app.file_list_pause_check = True  # ty: ignore[invalid-assignment]
        file_list = self.app.query_one("#file_list")
        file_list.focus()
        worker: Worker = file_list.update_file_list(
            add_to_session=False, focus_on=path.basename(new_name)
        )
        with contextlib.suppress(WorkerError):
            await worker.wait()
        self.app.file_list_pause_check = False  # ty: ignore[invalid-assignment]
