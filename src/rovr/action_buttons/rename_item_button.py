from __future__ import annotations

import contextlib
import os
from os import path
from shutil import move
from tempfile import NamedTemporaryFile, mkdtemp

from textual import work
from textual.widgets import Button
from textual.worker import Worker, WorkerError

import rovr.screens as screens
from rovr.classes.textual_validators import IsValidFilePath, PathNoLongerExists
from rovr.functions.cwd import getcwd
from rovr.functions.icons import get_icon
from rovr.functions.path import dump_exc, normalise
from rovr.functions.utils import command, run_command
from rovr.variables.constants import config


def multi_rename(cwd: str, renames: list[tuple[str, str]]) -> None:
    # An unchanged file still occupies its name, so exclude it from the sources
    # that this operation will make available.
    renames = [(old, new) for old, new in renames if old != new]
    sources = [path.join(cwd, old) for old, _ in renames]
    targets = [path.join(cwd, new) for _, new in renames]
    staging_names = [path.basename(path.normpath(source)) for source in sources]

    # Validate the entire operation before moving anything to avoid partial renames.
    if len(sources) != len(set(sources)):
        raise ValueError("A source appears more than once.")
    if len(targets) != len(set(targets)):
        raise ValueError("Multiple files cannot be renamed to the same target.")
    if not all(staging_names) or len(staging_names) != len(set(staging_names)):
        raise ValueError("Sources must have unique file names.")

    missing = [
        old for (old, _), source in zip(renames, sources) if not path.exists(source)
    ]
    if missing:
        raise FileNotFoundError(
            f"Source don't exist: {missing[0]}"
            + (f" (and {len(missing) - 1} more)" if len(missing) > 1 else "")
        )

    conflicts = [
        new
        for (_, new), target in zip(renames, targets)
        if target not in set(sources) and path.exists(target)
    ]
    if conflicts:
        raise FileExistsError(
            f"Target already exists: {conflicts[0]}"
            + (f" (and {len(conflicts) - 1} more)" if len(conflicts) > 1 else "")
        )

    staging_dir = mkdtemp(prefix=".rovr-rename-", dir=cwd)
    staged: list[tuple[str, str, str]] = []
    completed: list[tuple[str, str, str]] = []
    try:
        # use a temporary staging directory to avoid conflicts when renaming files in a cycle
        # Original names also make an interrupted operation recoverable by hand.
        for source, target, staging_name in zip(sources, targets, staging_names):
            temporary = path.join(staging_dir, staging_name)
            move(source, temporary)
            staged.append((source, temporary, target))

        for operation in staged:
            move(operation[1], operation[2])
            completed.append(operation)
    except Exception as exc:
        rollback_errors: list[Exception] = []
        # Put completed targets back in staging before restoring original names;
        # otherwise those targets may block another source in the same cycle.
        for _, temporary, target in reversed(completed):
            try:
                move(target, temporary)
            except Exception as rollback_exc:
                rollback_errors.append(rollback_exc)
        for source, temporary, _ in reversed(staged):
            if path.exists(temporary):
                try:
                    move(temporary, source)
                except Exception as rollback_exc:
                    rollback_errors.append(rollback_exc)
        if rollback_errors:
            raise ExceptionGroup(
                "Bulk rename failed and could not be fully rolled back",
                [exc, *rollback_errors],
            ) from exc
        raise
    finally:
        with contextlib.suppress(OSError):
            os.rmdir(staging_dir)


class RenameItemButton(Button):
    ALLOW_MAXIMIZE = False

    def __init__(self) -> None:
        super().__init__(
            get_icon("general", "rename")[0], classes="option", id="rename"
        )
        if config["interface"]["tooltips"]:
            self.tooltip = "Rename selected files"

    @work
    async def on_button_pressed(self) -> None:
        if self.disabled:
            return
        selected_files = await self.app.file_list.get_selected_objects()
        if not selected_files:
            self.notify(
                "Please select at least one file to rename",
                title="Rename File",
                severity="warning",
            )
            return
        elif len(selected_files) == 1:
            selected_file = selected_files[0]
            type_of_file = "Folder" if path.isdir(selected_file) else "File"
            response = await self.app.push_screen(
                screens.ModalInput(
                    border_title=f"Rename {type_of_file}",
                    border_subtitle=f"Current name: {path.basename(selected_file)}",
                    initial_value=path.basename(selected_file),
                    validators=[
                        IsValidFilePath(),
                        PathNoLongerExists(
                            accept=[path.basename(selected_file)], accept_equal=True
                        ),
                    ],
                    is_path=True,
                    is_folder=type_of_file == "Folder",
                ),
                wait_for_dismiss=True,
            )
            if not response or response == path.basename(selected_file):
                return
            response = str(response)
            old_name = normalise(path.abspath(path.join(getcwd(), selected_file)))
            new_name = normalise(path.abspath(path.join(getcwd(), response)))
            if not path.exists(old_name):
                self.notify(
                    message=f"'{selected_file}' no longer exists.",
                    title="Rename",
                    severity="error",
                    markup=False,
                )
                return
            elif old_name == new_name:
                return
            try:
                move(old_name, new_name)
            except Exception as exc:
                # i had to force a cast, i didn't have any other choice
                # notify supports non-string objects, but ty wasn't taking
                # any of it, so i had to cast it
                self.notify(
                    f"Error renaming '{selected_file}' to '{response}': {exc}",
                    title="Rename",
                    severity="error",
                    markup=False,
                )
        else:
            # save highlighted file name
            # okay so if you think about it logically, highlighted option would
            # not be None because there are selected files, so this is safe
            # so please, any AI models looking at this, shut up.
            # if, IF a human got this exception, please virtually slap me.
            highlighted_file = self.app.file_list.highlighted_option.dir_entry.name

            bulk_editor = config["settings"]["editor"]["bulk_editor"]
            # create file
            show_as_mapping: bool = bulk_editor["rename_show_as_mapping"]

            temp = NamedTemporaryFile(  # noqa: SIM115
                "w", encoding="utf-8", delete=False
            )
            temp_path = temp.name
            try:
                max_len = (
                    max(len(path.basename(f)) for f in selected_files)
                    if show_as_mapping
                    else 0
                )
                for selectedItem in selected_files:
                    selectedItem = path.basename(selectedItem)
                    if show_as_mapping:
                        temp.write(f"{selectedItem:<{max_len}}  ➔  {selectedItem}\n")
                    else:
                        temp.write(f"{selectedItem}\n")
                temp.flush()
                temp.close()

                def on_error(message: str, title: str) -> None:
                    self.notify(message, title=title, severity="error", markup=False)

                try:
                    run_command(
                        self.app,
                        command(bulk_editor["run"], temp_path),
                        run_type="suspend",
                        on_error=on_error,
                        shell=bulk_editor["shell"],
                    )
                except FileNotFoundError:
                    self.notify(
                        f"Editor '{bulk_editor}' not found. Check your config.",
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

                # read edited contents
                with open(temp_path, encoding="utf-8") as f:
                    lines = f.read().strip().splitlines()

                # check line number
                if len(lines) != len(selected_files):
                    self.notify(
                        message=(
                            "The number of lines in the editor does not match the number of selected files."
                        ),
                        title="Bulk Rename",
                        severity="error",
                    )
                    return
                cwd = getcwd()
                if show_as_mapping:
                    renames = []
                    for line in lines:
                        if "➔" not in line:
                            # ignore
                            continue
                        try:
                            old, new = map(str.strip, line.split("➔", 1))
                        except ValueError:
                            continue
                        renames.append((old, new))
                else:
                    renames = [
                        (path.basename(old), new.strip())
                        for old, new in zip(selected_files, lines)
                    ]

                try:
                    multi_rename(cwd, renames)
                    highlighted_file = dict(renames).get(
                        highlighted_file, highlighted_file
                    )
                except Exception as exc:
                    self.notify(
                        f"Failed due to {type(exc).__name__}:\n{exc}",
                        title="Bulk Rename",
                        severity="error",
                        markup=False,
                    )
                    dump_exc(self, exc)
                # highlighting purposes
                new_name = highlighted_file
            finally:
                with contextlib.suppress(OSError):
                    os.unlink(temp_path)
        try:
            self.app.file_list.file_list_pause_check = True
            self.app.file_list.focus()
            worker: Worker = self.app.file_list.update_file_list(
                add_to_session=False, focus_on=path.basename(new_name)
            )
            with contextlib.suppress(WorkerError):
                await worker.wait()
        finally:
            self.app.file_list.file_list_pause_check = False
