import contextlib
from os import getcwd, makedirs, path
from tempfile import NamedTemporaryFile
from typing import cast

from textual import events, work
from textual.content import Content
from textual.widgets import Button
from textual.worker import Worker, WorkerError

from rovr.classes.textual_validators import IsValidFilePath, PathNoLongerExists
from rovr.functions.icons import get_icon
from rovr.functions.path import dump_exc, normalise
from rovr.functions.utils import command, run_command
from rovr.screens import ModalInput
from rovr.variables.constants import config


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
            ModalInput(
                border_title="Create New Item",
                border_subtitle="End with a slash (/) to create a directory",
                is_path=True,
                validators=[PathNoLongerExists(), IsValidFilePath()],
            ),
            wait_for_dismiss=True,
        )
        if not response:
            return
        response = str(response)
        location = normalise(path.join(getcwd(), response)) + (
            "/" if response.endswith("/") or response.endswith("\\") else ""
        )
        if location.endswith("/"):
            # recursive directory creation
            try:
                worker = self.app.run_in_thread(makedirs, location)
                await worker.wait()
                if isinstance(worker.result, Exception):
                    raise worker.result
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
        elif len(location.split("/")) > 1:
            # recursive directory until file creation
            location_parts = location.split("/")
            dir_path = "/".join(location_parts[:-1])
            try:
                worker = self.app.run_in_thread(makedirs, dir_path)
                await worker.wait()
                if isinstance(worker.result, Exception):
                    raise worker.result
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
        try:
            self.app.file_list.file_list_pause_check = True
            self.app.file_list.focus()
            worker: Worker = self.app.file_list.update_file_list(
                add_to_session=False, focus_on=path.basename(location.rstrip("/"))
            )
            with contextlib.suppress(WorkerError):
                await worker.wait()
        except Exception as exc:
            dump_exc(self, exc)
        finally:
            self.app.file_list.file_list_pause_check = False

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
                command(
                    bulk_editor["run"],
                    temp_path,
                    bulk_editor["shell"],
                ),
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
            lines = [line.strip() for line in file_handle.read().splitlines()]

        entries = [line for line in lines if line]
        if not entries:
            self.notify(
                "No entries provided.",
                title="Bulk Create",
                severity="warning",
                markup=False,
            )
            return

        created: list[str] = []
        already_exists: list[str] = []
        errors: list[str] = []

        for entry in entries:
            is_dir = entry.endswith(("/", "\\"))
            location = normalise(path.join(getcwd(), entry))
            if is_dir:
                location = location + "/"
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

        if created:
            try:
                self.app.file_list.file_list_pause_check = True
                self.app.file_list.focus()
                focus_on = path.basename(created[0].rstrip("/"))
                worker = self.app.file_list.update_file_list(
                    add_to_session=False, focus_on=focus_on
                )
                with contextlib.suppress(WorkerError):
                    await worker.wait()
            except Exception as exc:
                dump_exc(self, exc)
            finally:
                self.app.file_list.file_list_pause_check = False

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
            path.unlink(temp_path)
