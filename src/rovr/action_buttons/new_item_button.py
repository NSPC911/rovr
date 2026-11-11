from __future__ import annotations

import contextlib
import os
from os import makedirs, path
from sys import platform
from tempfile import NamedTemporaryFile
from typing import cast

from textual import events, work
from textual.content import Content
from textual.widgets import Button
from textual.worker import Worker, WorkerError

import rovr.screens as screens
from rovr.classes.textual_validators import IsValidFilePath, PathNoLongerExists
from rovr.functions.cwd import getcwd
from rovr.functions.icons import get_icon
from rovr.functions.path import dump_exc, normalise
from rovr.functions.utils import command, dump_on_exc, run_command
from rovr.variables.constants import config

sep_check = "/" if platform != "win32" else ("\\", "/")


class NewItemButton(Button):
    ALLOW_MAXIMIZE = False

    def __init__(self) -> None:
        super().__init__(get_icon("general", "new")[0], classes="option", id="new")
        if config["interface"]["tooltips"]:
            self.tooltip = "Create a new file or directory"

    async def _on_click(self, event: events.Click) -> None:
        event.stop().prevent_default()
        if not self.has_class("-active"):
            if event.button == 1:
                self.press()
            else:
                await self.action_bulk_create()

    @work
    async def on_button_pressed(self) -> None:
        if self.disabled:
            return
        response = await self.app.push_screen(
            screens.ModalInput(
                border_title="Create New Item",
                border_subtitle=f"End with a slash ({os.path.sep}) to create a directory",
                is_path=True,
                validators=[PathNoLongerExists(), IsValidFilePath()],
            ),
            wait_for_dismiss=True,
        )
        if not response:
            return
        response = str(response)
        is_dir = response.endswith(sep_check)
        location = normalise(path.join(getcwd(), response))
        if is_dir:
            # recursive directory creation
            try:
                makedirs(location)
            except Exception as exc:
                self.notify(
                    # i had to force a cast, i didn't have any other choice
                    # notify supports non-string objects, but ty wasn't taking
                    # any of it, so i had to cast it
                    message=cast(
                        str,
                        Content(
                            f"Error creating directory '{response}'\n{type(exc).__name__}: {exc}"
                        ),
                    ),
                    title="New Item",
                    severity="error",
                    markup=False,
                )
        elif path.dirname(location):
            # recursive directory until file creation
            dir_path = path.dirname(location)
            try:
                makedirs(dir_path)
                # performance wise shouldn't be that bad, unless
                # the file is being created in a directory with a very long path
                # or some weird voodoo stuff happens, idk
                with open(location, "w") as f:
                    f.write("")  # Create an empty file
            except FileExistsError:
                with open(location, "w") as f:
                    f.write("")
            except Exception as exc:
                # i had to force a cast, i didn't have any other choice
                # notify supports non-string objects, but ty wasn't taking
                # any of it, so i had to cast it
                self.notify(
                    message=cast(
                        str,
                        Content(
                            f"Error creating file '{response}'\n{type(exc).__name__}: {exc}"
                        ),
                    ),
                    title="New Item",
                    severity="error",
                    markup=False,
                )
        else:
            # normal file creation I hope
            try:
                with open(location, "w") as f:
                    f.write("")  # Create an empty file
            except Exception as exc:
                self.notify(
                    message=f"Error creating file '{response}'\n{type(exc).__name__}: {exc}",
                    title="New Item",
                    severity="error",
                    markup=False,
                )
        with self.app.file_list.pause_checks(), dump_on_exc(self):
            self.app.file_list.focus()
            worker: Worker = self.app.file_list.update_file_list(
                add_to_session=False, focus_on=path.basename(location)
            )
            with contextlib.suppress(WorkerError):
                await worker.wait()

    @work
    async def action_bulk_create(self) -> None:
        temp = NamedTemporaryFile("w", encoding="utf-8", delete=False)  # noqa: SIM115
        temp_path = temp.name
        temp.write("")
        temp.flush()
        temp.close()

        bulk_editor = config["settings"]["editor"]["bulk_editor"]

        def on_error(message: str, title: str) -> None:
            self.notify(message, title=title, severity="error", markup=False)

        try:
            run_command(
                self.app,
                command(bulk_editor["run"], temp_path),
                run_type="suspend",
                shell=bulk_editor["shell"],
                on_error=on_error,
            )
        except FileNotFoundError:
            self.notify(
                f"Editor '{bulk_editor['run']}' not found. Check your config.",
                title="Editor not found",
                severity="error",
                markup=False,
            )
            return
        except Exception as exc:
            dump_exc(self, exc)
            self.notify(
                f"{type(exc).__name__}: {exc}",
                title="Error launching editor",
                severity="error",
                markup=False,
            )
            return

        with open(temp_path, encoding="utf-8") as file_handle:
            entries = [stripped for line in file_handle if (stripped := line.strip())]

        if not entries:
            self.notify(
                "No entries provided.",
                title="Bulk Create",
                severity="warning",
                markup=False,
            )
            return

        worker = self._bulk_creator(entries)
        created, already_exists, errors = await worker.wait()

        if created:
            with self.app.file_list.pause_checks(), dump_on_exc(self):
                self.app.file_list.focus()
                focus_on = path.basename(created[0].rstrip(os.path.sep))
                worker = self.app.file_list.update_file_list(
                    add_to_session=False, focus_on=focus_on
                )
                with contextlib.suppress(WorkerError):
                    await worker.wait()

        if already_exists:
            self.notify(
                "Some items already exist:\n" + "\n".join(already_exists),
                title="Bulk Create",
                severity="warning",
                markup=False,
            )
        if errors:
            self.notify(
                "Errors while creating:\n" + "\n".join(errors),
                title="Bulk Create",
                severity="error",
                markup=False,
            )
        if created:
            self.notify(
                f"Created {len(created)} item(s).",
                title="Bulk Create",
                severity="information",
                markup=False,
            )
        with contextlib.suppress(OSError):
            os.unlink(temp_path)

    @work(thread=True)
    def _bulk_creator(self, entries: list[str]) -> tuple[list[str], list[str], list[str]]:
        created: list[str] = []
        already_exists: list[str] = []
        errors: list[str] = []
        for entry in entries:
            is_dir = entry.endswith(sep_check)
            location = normalise(path.join(getcwd(), entry))
            if is_dir:
                location = location + os.path.sep
            try:
                if is_dir:
                    makedirs(location, exist_ok=False)
                else:
                    dir_path = path.dirname(location)
                    if dir_path:
                        makedirs(dir_path, exist_ok=True)
                    with open(location, "x") as created_file:
                        created_file.write("")
                created.append(location)
            except FileExistsError:
                already_exists.append(entry)
            except Exception as exc:
                errors.append(f"{entry}: {type(exc).__name__}: {exc}")
        return created, already_exists, errors
