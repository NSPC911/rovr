import contextlib
from os import getcwd, makedirs, path
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


class NewItemButton(Button):
    ALLOW_MAXIMIZE = False

    def __init__(self) -> None:
        super().__init__(get_icon("general", "new")[0], classes="option", id="new")

    def on_mount(self) -> None:
        if config["interface"]["tooltips"]:
            self.tooltip = "Create a new file or directory"

    @work
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.disabled:
            return
        response: str = await self.app.push_screen(
            ModalInput(
                border_title="Create New Item",
                border_subtitle="End with a slash (/) to create a directory",
                is_path=True,
                validators=[PathDoesntExist(), IsValidFilePath()],
            ),
            wait_for_dismiss=True,
        )
        if response == "":
            return
        location = normalise(path.join(getcwd(), response)) + (
            "/" if response.endswith("/") or response.endswith("\\") else ""
        )
        if location.endswith("/"):
            # recursive directory creation
            try:
                makedirs(location)
            except Exception as e:
                self.notify(
                    # i had to force a cast, i didn't have any other choice
                    # notify supports non-string objects, but ty wasn't taking
                    # any of it, so i had to cast it
                    message=cast(
                        str,
                        Content(
                            f"Error creating directory '{response}'\n{type(e).__name__}: {e}"
                        ),
                    ),
                    title="New Item",
                    severity="error",
                )
        elif len(location.split("/")) > 1:
            # recursive directory until file creation
            location_parts = location.split("/")
            dir_path = "/".join(location_parts[:-1])
            try:
                makedirs(dir_path)
                with open(location, "w") as f:
                    f.write("")  # Create an empty file
            except FileExistsError:
                with open(location, "w") as f:
                    f.write("")
            except Exception as e:
                # i had to force a cast, i didn't have any other choice
                # notify supports non-string objects, but ty wasn't taking
                # any of it, so i had to cast it
                self.notify(
                    message=cast(
                        str,
                        Content(
                            f"Error creating file '{response}'\n{type(e).__name__}: {e}"
                        ),
                    ),
                    title="New Item",
                    severity="error",
                )
        else:
            # normal file creation I hope
            try:
                with open(location, "w") as f:
                    f.write("")  # Create an empty file
            except Exception as e:
                self.notify(
                    message=cast(
                        str,
                        Content(
                            f"Error creating file '{response}'\n{type(e).__name__}: {e}"
                        ),
                    ),
                    title="New Item",
                    severity="error",
                )
        self.app.file_list_pause_check = True
        file_list = self.app.query_one("#file_list")
        file_list.focus()
        worker: Worker = file_list.update_file_list(
            add_to_session=False, focus_on=path.basename(location)
        )
        with contextlib.suppress(WorkerError):
            await worker.wait()
        self.app.file_list_pause_check = False
