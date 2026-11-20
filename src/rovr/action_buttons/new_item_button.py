from __future__ import annotations

import contextlib
import os
from os import makedirs, path
from tempfile import NamedTemporaryFile
from typing import cast

from textual import events, work
from textual.content import Content
from textual.widgets import Button
from textual.worker import Worker, WorkerCancelled, WorkerError

import rovr.screens as screens
from rovr.classes.textual_validators import IsValidFilePath, PathNoLongerExists
from rovr.footer.process_container import ProcessContainer, ProgressBarContainer
from rovr.functions.cwd import getcwd
from rovr.functions.icons import get_icon
from rovr.functions.path import PATH_SEPARATORS, dump_exc, normalise
from rovr.functions.utils import command, dump_on_exc, run_command, s
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
            screens.ModalInput(
                border_title="Create New Item",
                border_subtitle=f"End with {path.sep} to create a directory",
                is_path=True,
                validators=[PathNoLongerExists(), IsValidFilePath()],
            ),
            wait_for_dismiss=True,
        )
        if not response:
            return
        response = str(response)
        location = normalise(getcwd(), response)
        if response.endswith(PATH_SEPARATORS):
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
        else:
            try:
                if dir_path := path.dirname(location):
                    makedirs(dir_path, exist_ok=True)
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
        cwd = getcwd()
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

        bar = ProgressBarContainer(
            total=len(entries) + 1,
            label="Creating items...",
            classes="active",
            advance_interval=0.25,
        )
        bar.set_icon(get_icon("general", "new")[0])
        self.app.query_one(ProcessContainer).mount(bar, before=0)
        worker = self._bulk_creator(entries, cwd, bar)
        try:
            first_created, errors, exists = await worker.wait()
        except WorkerCancelled:
            bar.panic(notify={"title": "Bulk Create", "message": "Operation cancelled"})
            return

        total = len(entries)
        if errors:
            bar.panic(
                bar_text=f"Created {total - len(errors) - exists} + {exists}/{total} items"
            )
        else:
            bar.ok()

        if first_created:
            with self.app.file_list.pause_checks(), dump_on_exc(self):
                self.app.file_list.focus()
                focus_on = path.basename(first_created)
                worker: Worker = self.app.file_list.update_file_list(
                    add_to_session=False, focus_on=focus_on
                )
                with contextlib.suppress(WorkerError):
                    await worker.wait()

        if errors:
            self.notify(
                "Errors while creating:\n" + "\n".join(errors),
                title="Bulk Create",
                severity="error",
                markup=False,
            )
        if first_created:
            self.notify(
                f"Created {(it := (total - len(errors) - exists))} item{s(it)}"
                + (f"\n{exists} already existed" if exists else ""),
                title="Bulk Create",
                severity="information",
                markup=False,
            )
        with contextlib.suppress(OSError):
            os.unlink(temp_path)

    @work(thread=True)
    def _bulk_creator(
        self, entries: list[str], cwd: str, bar: ProgressBarContainer
    ) -> tuple[str | None, list[str], int]:
        first_created: str | None = None
        exists: int = 0
        errors: list[str] = []
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        for entry in entries:
            bar.set_text(entry)
            is_dir = entry.endswith(PATH_SEPARATORS)
            location = normalise(cwd, entry)
            try:
                if is_dir:
                    makedirs(location, exist_ok=False)
                else:
                    dir_path = path.dirname(location)
                    if dir_path:
                        makedirs(dir_path, exist_ok=True)
                    os.close(os.open(location, flags, 0o666))
                # because you cant touch a file with nothing as a name
                if not first_created:
                    first_created = location
                bar.advance()
            except FileExistsError:
                # check if it is a conflict of type (file vs directory)
                if is_dir and not path.isdir(location):
                    errors.append(f"{entry}: Path exists but not a directory")
                elif not is_dir and not path.isfile(location):
                    errors.append(f"{entry}: Path exists but not a file")
                else:
                    exists += 1
                    bar.advance()
            except Exception as exc:
                errors.append(f"{entry}: {type(exc).__name__}: {exc}")
        return first_created, errors, exists
