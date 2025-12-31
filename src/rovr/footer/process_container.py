import os
import shutil
import tarfile
import time
import zipfile
from os import path
from typing import Callable, cast

from send2trash import send2trash
from textual import events, work
from textual.color import Gradient
from textual.containers import HorizontalGroup, VerticalGroup, VerticalScroll
from textual.renderables.bar import Bar as BarRenderable
from textual.types import UnusedParameter
from textual.widgets import Label, ProgressBar

from rovr.classes import Archive
from rovr.functions import icons as icon_utils
from rovr.functions import path as path_utils
from rovr.functions.utils import is_being_used
from rovr.screens import (
    CommonFileNameDoWhat,
    Dismissable,
    FileInUse,
    YesOrNo,
    typed,
)
from rovr.variables.constants import config, os_type, scroll_vindings


class ThickBar(BarRenderable):
    HALF_BAR_LEFT = "▐"
    BAR = "█"
    HALF_BAR_RIGHT = "▌"


class ProgressBarContainer(VerticalGroup, inherit_bindings=False):
    BINDINGS = scroll_vindings

    def __init__(
        self,
        total: int | None = None,
        label: str = "",
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        if hasattr(self.app.get_theme(self.app.theme), "bar_gradient"):
            gradient = Gradient.from_colors(
                *self.app.get_theme(self.app.theme).bar_gradient["default"]
            )
        else:
            gradient = None
        self.progress_bar = ProgressBar(
            total=total,
            show_percentage=config["interface"]["show_progress_percentage"],
            show_eta=config["interface"]["show_progress_eta"],
            gradient=gradient,
        )
        self.progress_bar.BAR_RENDERABLE = ThickBar
        self.icon_label = Label(id="icon")
        self.text_label = Label(label, id="label")
        self.label_container = HorizontalGroup(self.icon_label, self.text_label)

    async def on_mount(self) -> None:
        await self.mount_all([self.label_container, self.progress_bar])

    def update_text(self, label: str, is_path: bool = True) -> None:
        """
        Updates the text label
        Args:
            label (str): The new label
            is_path (bool) = True: Whether the text is a path or not
        """
        if is_path and config["interface"]["truncate_progress_file_path"]:
            new_label = label.split("/")
            new_path = new_label[0]
            for _ in new_label[1:-1]:
                new_path += "/\u2026"
            new_path += f"/{new_label[-1]}"
            label = new_path
        self.text_label.update(label)

    def update_icon(self, icon: str) -> None:
        """
        Updates the icon label
        Args:
            icon (str): The new icon
        """
        self.icon_label.update(icon)

    def update_progress(
        self,
        total: None | float | UnusedParameter = UnusedParameter(),
        progress: float | UnusedParameter = UnusedParameter(),
        advance: float | UnusedParameter = UnusedParameter(),
    ) -> None:
        self.progress_bar.update(total=total, progress=progress, advance=advance)

    def panic(
        self,
        dismiss_with: dict | None = None,
        notify: dict | None = None,
        bar_text: str = "",
    ) -> None:
        """Do something when an error occurs.
        Args:
            dismiss_with(dict): The message for the Dismissable screen (must contain `message` and `subtitle`)
            notify(dict): The notify message (must contain `message` and `title`)
            bar_text(str): The new text to update the label
        """
        if bar_text:
            self.update_text(bar_text, False)
        if self.progress_bar.total is None:
            self.progress_bar.update(total=1, progress=0)
        self.add_class("error")
        if hasattr(self.app.get_theme(self.app.theme), "bar_gradient"):
            self.progress_bar.gradient = Gradient.from_colors(
                *self.app.get_theme(self.app.theme).bar_gradient["error"]
            )
        assert isinstance(self.icon_label.content, str)
        self.update_icon(
            self.icon_label.content + " " + icon_utils.get_icon("general", "close")[0]
        )
        dismiss_with = dismiss_with or {}
        notify = notify or {}

        if dismiss_with:
            self.app.call_from_thread(
                self.app.push_screen_wait,
                Dismissable(
                    dismiss_with["message"], border_subtitle=dismiss_with["subtitle"]
                ),
            )
        if notify:
            self.notify(
                message=notify["message"], severity="error", title=notify["title"]
            )
        self.app.query_one("Clipboard").checker_wrapper()


class ProcessContainer(VerticalScroll):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(id="processes", *args, **kwargs)
        self.has_perm_error: bool = False
        self.has_in_use_error: bool = False

    async def new_process_bar(
        self, max: int | None = None, id: str | None = None, classes: str | None = None
    ) -> ProgressBarContainer:
        new_bar: ProgressBarContainer = ProgressBarContainer(
            total=max, id=id, classes=classes
        )
        await self.mount(new_bar, before=0)
        return new_bar

    def threaded_new_process_bar(
        self, max: int | None = None, id: str | None = None, classes: str | None = None
    ) -> ProgressBarContainer:
        bar = self.app.call_from_thread(
            self.new_process_bar, max=max, id=id, classes=classes
        )
        assert isinstance(bar, ProgressBarContainer)
        return bar

    @work(thread=True)
    def delete_files(
        self, files: list[str], compressed: bool = True, ignore_trash: bool = False
    ) -> None:
        """
        Remove files from the filesystem.

        Args:
            files (list[str]): List of file paths to remove.
            compressed (bool): Whether the file paths are compressed. Defaults to True.
            ignore_trash (bool): If True, files will be permanently deleted instead of sent to the recycle bin. Defaults to False.

        Raises:
            OSError: re-raises if the file usage handler fails
            PermissionError: re-raises if the file usage handler fails
        """
        # Create progress/process bar (why have I set names as such...)
        bar = self.threaded_new_process_bar(classes="active")
        self.app.call_from_thread(
            bar.update_icon,
            icon_utils.get_icon("general", "delete")[0],
        )
        self.app.call_from_thread(
            bar.update_text,
            "Getting files to delete...",
        )
        # get files to delete
        files_to_delete = []
        folders_to_delete = []
        for file in files:
            if compressed:
                file = path_utils.decompress(file)
            if path_utils.file_is_type(file) == "directory":
                folders_to_delete.append(file)
            files_to_add, folders_to_add = path_utils.get_recursive_files(
                file, with_folders=True
            )
            files_to_delete.extend(files_to_add)
            folders_to_delete.extend(folders_to_add)
        self.app.call_from_thread(bar.update_progress, total=len(files_to_delete) + 1)
        action_on_file_in_use = "ask"
        last_update_time = time.monotonic()
        for i, item_dict in enumerate(files_to_delete):
            current_time = time.monotonic()
            if (
                current_time - last_update_time > 0.25
                or i == len(files_to_delete) - 1
                or i == 0
            ):
                self.app.call_from_thread(
                    bar.update_text,
                    item_dict["relative_loc"],
                )
                self.app.call_from_thread(bar.update_progress, progress=i + 1)
                last_update_time = current_time
            if path.exists(item_dict["path"]):
                # I know that it `path.exists` prevents issues, but on the
                # off chance that anything happens, this should help
                try:
                    if config["settings"]["use_recycle_bin"] and not ignore_trash:
                        try:
                            path_to_trash = item_dict["path"]
                            if os_type == "Windows":
                                # An inherent issue with long paths on windows
                                path_to_trash = path_to_trash.replace("/", "\\")
                            send2trash(path_to_trash)
                        except (PermissionError, OSError) as e:
                            # On Windows, a file being used by another process
                            # raises a PermissionError/OSError with winerror 32.
                            if (
                                is_file_in_use := is_being_used(e)
                            ) and os_type == "Windows":
                                current_action, action_on_file_in_use = (
                                    self._handle_file_in_use_error(
                                        action_on_file_in_use,
                                        item_dict["relative_loc"],
                                        lambda: send2trash(path_to_trash),
                                    )
                                )
                                if current_action == "cancel":
                                    bar.panic()
                                    return
                                elif current_action == "skip":
                                    pass  # Skip this file, continue to next
                                continue
                            elif is_file_in_use:
                                # need to ensure unix users see an
                                # error so they create an issue
                                raise
                            # fallback for regular permission issues
                            if path_utils.force_obtain_write_permission(
                                item_dict["path"]
                            ):
                                os.remove(item_dict["path"])
                        except Exception as e:
                            do_what = self.app.call_from_thread(
                                self.app.push_screen_wait,
                                YesOrNo(
                                    f"Trashing failed due to\n{e}\nDo Permenant Deletion?",
                                    with_toggle=True,
                                    border_subtitle="If this is a bug, please file an issue!",
                                ),
                            )
                            do_what = cast(typed.YesOrNo, do_what)
                            if do_what["toggle"]:
                                ignore_trash = do_what["value"]
                            if do_what["value"]:
                                os.remove(item_dict["path"])
                            else:
                                continue
                    else:
                        os.remove(item_dict["path"])
                except FileNotFoundError:
                    # it's deleted, so why care?
                    pass
                except (PermissionError, OSError) as e:
                    # Try to detect if file is in use on Windows
                    if (is_file_in_use := is_being_used(e)) and os_type == "Windows":
                        current_action, action_on_file_in_use = (
                            self._handle_file_in_use_error(
                                action_on_file_in_use,
                                item_dict["relative_loc"],
                                lambda: os.remove(item_dict["path"]),
                            )
                        )
                        if current_action == "cancel":
                            bar.panic()
                            return
                        elif current_action == "skip":
                            pass  # Skip this file, continue to next
                        continue
                    elif is_file_in_use:
                        # need to ensure unix users see an
                        # error so they create an issue
                        self.app.panic()
                    # fallback for regular permission issues
                    if path_utils.force_obtain_write_permission(item_dict["path"]):
                        os.remove(item_dict["path"])
                except Exception as e:
                    # TODO: should probably let it continue, then have a summary
                    bar.panic(
                        dismiss_with={
                            "message": f"Deleting failed due to\n{e}\nProcess Aborted.",
                            "subtitle": "If this is a bug, please file an issue!",
                        },
                        bar_text="Unhandled Error",
                    )
                    return
        # The reason for an extra +1 in the total is for this
        # handling folders
        self.has_perm_error = False
        self.has_in_use_error = False
        for folder in folders_to_delete:
            shutil.rmtree(folder, onexc=self.rmtree_fixer)
        if self.has_in_use_error:
            bar.panic(
                notify={
                    "message": "Certain files could not be deleted as they are currently being used",
                    "title": "Delete Files",
                },
            )
            return
        if self.has_perm_error:
            bar.panic(
                notify={
                    "message": "Certain files could not be deleted due to PermissionError.",
                    "title": "Delete Files",
                },
            )
            return
        # if there werent any files, show something useful
        # aside from 'Getting files to delete...'
        if files_to_delete == [] and folders_to_delete != []:
            self.app.call_from_thread(
                bar.update_text,
                folders_to_delete[-1],
            )
        elif files_to_delete == folders_to_delete == []:
            # this cannot happen, but just as an easter egg :shippit:
            self.app.call_from_thread(
                bar.update_text, "Successfully deleted nothing!", False
            )
        # finished successfully
        self.app.call_from_thread(
            bar.update_icon,
            str(bar.icon_label.content)
            + " "
            + icon_utils.get_icon("general", "check")[0],  # type: ignore[unsupported-operator]
        )
        self.app.call_from_thread(bar.progress_bar.advance)
        self.app.call_from_thread(bar.add_class, "done")
        self.app.query_one("Clipboard").checker_wrapper()

    def _handle_file_in_use_error(
        self,
        action_on_file_in_use: str,
        item_display_name: str,
        retry_func: Callable[[], None],
    ) -> tuple[str, str]:
        """
        Handle file-in-use errors with user prompts and automatic retries.

        Args:
            action_on_file_in_use (str): Current action ("ask", "try_again", "skip", "cancel")
            item_display_name (str): Display name for the file
            retry_func (Callable): Function to call to retry the operation

        Returns:
            tuple[str, str]: (current_action, updated_default_action)
                - current_action: What to do with this file ("skip", "try_again", or raises)
                - updated_default_action: Updated default for future errors

        Raises:
            PermissionError: If it still fails
            OSError: If it still fails
        """
        persisted_default = action_on_file_in_use
        if action_on_file_in_use in ("skip", "cancel"):
            # Persisted skip/cancel: short-circuit without retry
            return action_on_file_in_use, action_on_file_in_use
        if action_on_file_in_use == "try_again":
            # Persisted try_again: attempt retry once just like interactive success path
            prev_action = action_on_file_in_use
            try:
                retry_func()
                return "try_again", prev_action
            except (PermissionError, OSError) as e:
                if not is_being_used(e):
                    # Different error type; propagate upwards
                    raise
                # Still in use; fall back to interactive prompt loop below
                action_on_file_in_use = "ask"

        while True:
            response = self.app.call_from_thread(
                self.app.push_screen_wait,
                FileInUse(
                    f"The file appears to be open in another application and cannot be operated on.\nPath: {item_display_name}",
                ),
            )
            response = cast(typed.FileInUse, response)
            # Handle toggle: remember the action for future file-in-use scenarios
            updated_action = persisted_default
            if response["toggle"]:
                updated_action = response["value"]
                persisted_default = updated_action

            if response["value"] == "cancel":
                return "cancel", updated_action
            elif response["value"] == "skip":
                return "skip", updated_action
            # Try again: check if file is still in use
            try:
                retry_func()
                return "try_again", updated_action  # Success, return updated action
            except (PermissionError, OSError) as e:
                if not is_being_used(e):
                    raise  # Not a file-in-use error, re-raise
                # Otherwise, loop again for another try/cancel

    def rmtree_fixer(
        self, function: Callable[[str], None], item_path: str, exc: BaseException
    ) -> None:
        """
        Ran when shutil.rmtree faces an issue
        Args:
            function(Callable): the function that caused the issue
            item_path(str): the path that caused the issue
            exc(BaseException): the exact exception that caused the error
        """
        if isinstance(exc, FileNotFoundError):
            # ig it got removed?
            return
        elif isinstance(exc, (OSError, PermissionError)) and is_being_used(exc):
            # cannot do anything
            self.has_in_use_error = True
        elif (isinstance(exc, OSError) and "symbolic" in exc.__str__()) or (
            path_utils.force_obtain_write_permission(item_path)
        ):
            os.remove(item_path)
        elif isinstance(exc, PermissionError):
            self.has_perm_error = True
        else:
            raise

    @work(thread=True)
    def create_archive(self, files: list[str], archive_name: str) -> None:
        """
        Compress files into an archive.

        Args:
            files (list[str]): List of file paths to compress.
            archive_name (str): Path for the output archive.
        """
        bar = self.threaded_new_process_bar(classes="active")
        self.app.call_from_thread(
            bar.update_icon,
            icon_utils.get_icon("general", "zip")[0],
        )
        self.app.call_from_thread(bar.update_text, "Getting files to archive...", False)

        files_to_archive = []
        for p in files:
            if path.isdir(p):
                if not os.listdir(p):  # empty directory
                    files_to_archive.append(p)
                else:
                    for dirpath, _, filenames in os.walk(p):
                        for f in filenames:
                            files_to_archive.append(path.join(dirpath, f))
            else:
                files_to_archive.append(p)

        files_to_archive = sorted(list(set(files_to_archive)))

        self.app.call_from_thread(bar.update_progress, total=len(files_to_archive) + 1)

        if len(files) == 1:
            base_path = path.dirname(files[0])
        else:
            base_path = path.commonpath(files)

        try:
            with Archive(archive_name, "w") as archive:
                assert archive._archive is not None
                last_update_time = time.monotonic()
                for i, file_path in enumerate(files_to_archive):
                    arcname = path.relpath(file_path, base_path)
                    current_time = time.monotonic()
                    if (
                        current_time - last_update_time > 0.25
                        or i == len(files_to_archive) - 1
                    ):
                        self.app.call_from_thread(
                            bar.update_text,
                            arcname,
                        )
                        self.app.call_from_thread(bar.update_progress, progress=i + 1)
                        last_update_time = current_time
                    _archive = archive._archive
                    if _archive:
                        if archive._archive_type == "zip":
                            assert isinstance(_archive, zipfile.ZipFile)
                            _archive.write(file_path, arcname=arcname)
                        else:
                            assert isinstance(_archive, tarfile.TarFile)
                            _archive.add(file_path, arcname=arcname)
                for p in files:
                    if path.isdir(p) and not os.listdir(p):
                        arcname = path.relpath(p, base_path)
                        _archive = archive._archive
                        if _archive:
                            if archive._archive_type == "zip":
                                assert isinstance(_archive, zipfile.ZipFile)
                                _archive.write(p, arcname=arcname)
                            else:
                                assert isinstance(_archive, tarfile.TarFile)
                                _archive.add(p, arcname=arcname)

        except Exception as e:
            bar.panic(
                dismiss_with={
                    "message": f"Archiving failed due to\n{e}\nProcess Aborted.",
                    "subtitle": "File an issue if this is a bug!",
                }
            )
            return

        self.app.call_from_thread(
            bar.update_icon,
            str(bar.icon_label.content)
            + " "
            + icon_utils.get_icon("general", "check")[0],
        )
        self.app.call_from_thread(bar.progress_bar.advance)
        self.app.call_from_thread(bar.add_class, "done")

    @work(thread=True)
    def unzip_file(self, archive_path: str, destination_path: str) -> None:
        """
        Extracts a zip archive to a destination.

        Args:
            archive_path (str): Path to the zip archive.
            destination_path (str): Path to the destination folder.
        """
        bar = self.threaded_new_process_bar(classes="active")
        self.app.call_from_thread(
            bar.update_icon,
            icon_utils.get_icon("general", "open")[0],
        )
        self.app.call_from_thread(
            bar.update_text,
            "Preparing to extract...",
        )

        do_what_on_existance = "ask"
        try:
            if not path.exists(destination_path):
                os.makedirs(destination_path)

            with Archive(archive_path, "r") as archive:
                file_list = archive.infolist()
                self.app.call_from_thread(bar.update_progress, total=len(file_list) + 1)

                last_update_time = time.monotonic()
                for i, file in enumerate(file_list):
                    filename = getattr(file, "filename", getattr(file, "name", ""))
                    current_time = time.monotonic()
                    if (
                        current_time - last_update_time > 0.25
                        or i == len(file_list) - 1
                        or i == 0
                    ):
                        self.app.call_from_thread(
                            bar.update_text,
                            filename,
                        )
                        self.app.call_from_thread(bar.update_progress, progress=i + 1)
                        last_update_time = current_time
                    if path.exists(path.join(destination_path, filename)):
                        if do_what_on_existance == "ask":
                            response = self.app.call_from_thread(
                                self.app.push_screen_wait,
                                CommonFileNameDoWhat(
                                    "Path already exists in destination\nWhat do you want to do now?",
                                    border_title=filename,
                                    border_subtitle=f"Extracting to {destination_path}",
                                ),
                            )
                            response = cast(typed.CommonFileNameDoWhat, response)
                            if response["same_for_next"]:
                                do_what_on_existance = response["value"]
                            val = response["value"]
                        else:
                            val = do_what_on_existance
                        match val:
                            case "overwrite":
                                pass
                            case "skip":
                                continue
                            case "rename":
                                base_name, extension = path.splitext(filename)
                                tested_number = 1
                                while True:
                                    new_filename = (
                                        f"{base_name} ({tested_number}){extension}"
                                    )
                                    new_path = path_utils.normalise(
                                        path.join(destination_path, new_filename)
                                    )
                                    if not path.exists(new_path):
                                        break
                                    tested_number += 1

                                source = archive.open(file)
                                if source:
                                    with source, open(new_path, "wb") as target:
                                        shutil.copyfileobj(source, target)
                                continue
                            case "cancel":
                                bar.panic()
                                return
                    try:
                        archive.extract(file, path=destination_path)
                    except PermissionError:
                        if path_utils.force_obtain_write_permission(
                            path.join(destination_path, filename)
                        ):
                            archive.extract(file, path=destination_path)
        except (zipfile.BadZipFile, tarfile.TarError, ValueError) as e:
            dismiss_with = {"subtitle": ""}
            if isinstance(e, ValueError) and "Password" in e.__str__():
                if "ZIP" in e.__str__():
                    dismiss_with["message"] = (
                        "Password-protected ZIP files cannot be unzipped"
                    )
                elif "RAR" in e.__str__():
                    dismiss_with["message"] = (
                        "Password-protected RAR files cannot be unzipped"
                    )
                else:
                    dismiss_with["message"] = (
                        "Password-protected archive files cannot be unzipped"
                    )
            else:
                dismiss_with = {
                    "message": f"Unzipping failed due to {type(e).__name__}\n{e}\nProcess Aborted.",
                    "subtitle": "If this is a bug, file an issue!",
                }
            bar.panic(dismiss_with=dismiss_with, bar_text="Error extracting archive")
            return
        except Exception as e:
            bar.panic(
                dismiss_with={
                    "message": f"Unzipping failed due to {type(e).__name__}\n{e}\nProcess Aborted.",
                    "subtitle": "If this is a bug, please file an issue!",
                },
                bar_text="Unhandled Error",
            )
            return

        self.app.call_from_thread(
            bar.update_icon,
            icon_utils.get_icon("general", "check")[0],
        )
        self.app.call_from_thread(bar.progress_bar.advance)
        self.app.call_from_thread(bar.add_class, "done")

    @work(thread=True)
    def paste_items(self, copied: list[str], cutted: list[str], dest: str = "") -> None:
        """
        Paste copied or cut files to the current directory
        Args:
            copied (list[str]): A list of items to be copied to the location
            cutted (list[str]): A list of items to be cut to the location
            dest (str) = getcwd(): The directory to copy to.
        """
        if dest == "":
            dest = os.getcwd()
        bar = self.threaded_new_process_bar(classes="active")
        self.app.call_from_thread(
            bar.update_icon,
            icon_utils.get_icon("general", "paste")[0],
        )
        self.app.call_from_thread(
            bar.update_text,
            "Getting items to paste...",
        )
        files_to_copy = []
        files_to_cut = []
        cut_files__folders = []
        for file in copied:
            files_to_copy.extend(path_utils.get_recursive_files(file))
        for file in cutted:
            if path.isdir(file):
                cut_files__folders.append(path_utils.normalise(file))
            files, folders = path_utils.get_recursive_files(file, with_folders=True)
            files_to_cut.extend(files)
            cut_files__folders.extend(folders)
        self.app.call_from_thread(
            bar.update_progress, total=int(len(files_to_copy) + len(files_to_cut)) + 1
        )
        action_on_existance = "ask"
        last_update_time = time.monotonic()
        if files_to_copy:
            self.app.call_from_thread(
                bar.update_icon,
                icon_utils.get_icon("general", "copy")[0],
            )
        for i, item_dict in enumerate(files_to_copy):
            current_time = time.monotonic()
            if (
                current_time - last_update_time > 0.25
                or i == len(files_to_copy) - 1
                or i == 0
            ):
                self.app.call_from_thread(
                    bar.update_text,
                    item_dict["relative_loc"],
                )
                last_update_time = current_time
                self.app.call_from_thread(bar.update_progress, progress=i + 1)
            if path.exists(item_dict["path"]):
                # again checks just in case something goes wrong
                try:
                    os.makedirs(
                        path_utils.normalise(
                            path.join(dest, item_dict["relative_loc"], "..")
                        ),
                        exist_ok=True,
                    )
                    if path.exists(path.join(dest, item_dict["relative_loc"])):
                        # check if overwrite
                        if action_on_existance == "ask":
                            response = self.app.call_from_thread(
                                self.app.push_screen_wait,
                                CommonFileNameDoWhat(
                                    "The destination already has file of that name.\nWhat do you want to do now?",
                                    border_title=item_dict["relative_loc"],
                                    border_subtitle=f"Copying to {dest}",
                                ),
                            )
                            response = cast(typed.CommonFileNameDoWhat, response)
                            if response["same_for_next"]:
                                action_on_existance = response["value"]
                            val = response["value"]
                        else:
                            val = action_on_existance
                        match val:
                            case "overwrite":
                                pass
                            case "skip":
                                continue
                            case "rename":
                                base_name, extension = path.splitext(
                                    item_dict["relative_loc"]
                                )
                                tested_number = 1
                                while True:
                                    new_rel_path = (
                                        f"{base_name} ({tested_number}){extension}"
                                    )
                                    if not path.exists(path.join(dest, new_rel_path)):
                                        break
                                    tested_number += 1
                                item_dict["relative_loc"] = new_rel_path
                            case "cancel":
                                bar.panic(bar_text="Process cancelled.")
                                return
                    if config["settings"]["copy_includes_metadata"]:
                        shutil.copy2(
                            item_dict["path"],
                            path.join(dest, item_dict["relative_loc"]),
                        )
                    else:
                        shutil.copy(
                            item_dict["path"],
                            path.join(dest, item_dict["relative_loc"]),
                        )
                except (OSError, PermissionError):
                    # OSError from shutil: The destination location must be writable;
                    # otherwise, an OSError exception will be raised
                    # Permission Error just in case
                    if path_utils.force_obtain_write_permission(
                        path.join(dest, item_dict["relative_loc"])
                    ):
                        shutil.copy(
                            item_dict["path"],
                            path.join(dest, item_dict["relative_loc"]),
                        )
                except FileNotFoundError:
                    # the only way this can happen is if the file is deleted
                    # midway through the process, which means the user is
                    # literally testing the limits, so yeah uhh, pass
                    pass
                except Exception as e:
                    # TODO: should probably let it continue, then have a summary
                    bar.panic(
                        dismiss_with={
                            "message": f"Copying failed due to {type(e).__name__}\n{e}\nProcess Aborted.",
                            "subtitle": "If this is a bug, please file an issue!",
                        },
                        bar_text="Unhandled Error",
                    )
                    return

        cut_ignore = []
        last_update_time = time.monotonic()
        if files_to_cut:
            self.app.call_from_thread(
                bar.update_icon,
                icon_utils.get_icon("general", "cut")[0],
            )
        for i, item_dict in enumerate(files_to_cut):
            current_time = time.monotonic()
            if (
                current_time - last_update_time > 0.25
                or i == len(files_to_cut) - 1
                or i == 0
            ):
                self.app.call_from_thread(
                    bar.update_text,
                    item_dict["relative_loc"],
                )
                self.app.call_from_thread(bar.update_progress, progress=i + 1)
                last_update_time = current_time
            if path.exists(item_dict["path"]):
                # again checks just in case something goes wrong
                try:
                    os.makedirs(
                        path_utils.normalise(
                            path.join(dest, item_dict["relative_loc"], "..")
                        ),
                        exist_ok=True,
                    )
                    if path.exists(path.join(dest, item_dict["relative_loc"])):
                        self.log(
                            path_utils.normalise(
                                path.join(dest, item_dict["relative_loc"])
                            ),
                            path_utils.normalise(item_dict["path"]),
                        )

                        if path_utils.normalise(
                            path.join(dest, item_dict["relative_loc"])
                        ) == path_utils.normalise(item_dict["path"]):
                            cut_ignore.append(item_dict["path"])
                            continue
                        if action_on_existance == "ask":
                            response = self.app.call_from_thread(
                                self.app.push_screen_wait,
                                CommonFileNameDoWhat(
                                    "The destination already has file of that name.\nWhat do you want to do now?",
                                    border_title=item_dict["relative_loc"],
                                    border_subtitle=f"Moving to {dest}",
                                ),
                            )
                            response = cast(typed.CommonFileNameDoWhat, response)
                            if response["same_for_next"]:
                                action_on_existance = response["value"]
                            val = response["value"]
                        else:
                            val = action_on_existance
                        match val:
                            case "overwrite":
                                pass
                            case "skip":
                                cut_ignore.append(item_dict["path"])
                                continue
                            case "rename":
                                base_name, extension = path.splitext(
                                    item_dict["relative_loc"]
                                )
                                tested_number = 1
                                while True:
                                    new_rel_path = (
                                        f"{base_name} ({tested_number}){extension}"
                                    )
                                    if not path.exists(path.join(dest, new_rel_path)):
                                        break
                                    tested_number += 1
                                item_dict["relative_loc"] = new_rel_path
                            case "cancel":
                                bar.panic(bar_text="Process cancelled.")
                                return
                    shutil.move(
                        item_dict["path"],
                        path.join(dest, item_dict["relative_loc"]),
                    )
                except (OSError, PermissionError):
                    # OSError from shutil: The destination location must be writable;
                    # otherwise, an OSError exception will be raised
                    # Permission Error just in case
                    if path_utils.force_obtain_write_permission(
                        path.join(dest, item_dict["relative_loc"])
                    ) and path_utils.force_obtain_write_permission(item_dict["path"]):
                        shutil.move(
                            item_dict["path"],
                            path.join(dest, item_dict["relative_loc"]),
                        )
                except FileNotFoundError:
                    # the only way this can happen is if the file is deleted
                    # midway through the process, which means the user is
                    # literally testing the limits, so yeah uhh, pass
                    pass
                except Exception as e:
                    # TODO: should probably let it continue, then have a summary
                    bar.panic(
                        dismiss_with={
                            "message": f"Moving failed due to {type(e).__name__}\n{e}\nProcess Aborted.",
                            "subtitle": "If this is a bug, please file an issue!",
                        },
                        bar_text="Unhandled Error",
                    )
                    return
        # delete the folders
        self.has_perm_error = False
        self.has_in_use_error = False
        for folder in cut_files__folders:
            skip = False
            for file in cut_ignore:
                if folder in file:
                    skip = True
                    break
            if not skip:
                shutil.rmtree(folder, onexc=self.rmtree_fixer)
        if self.has_in_use_error:
            bar.panic(
                notify={
                    "message": "Certain files could not be deleted as they are currently being used",
                    "title": "Delete Files",
                },
                bar_text=path.basename(cutted[-1]),
            )
            return
        if self.has_perm_error:
            bar.panic(
                notify={
                    "message": "Certain files could not be deleted due to PermissionError.",
                    "title": "Delete Files",
                },
                bar_text=path.basename(cutted[-1]),
            )
            return
        self.app.query_one("Clipboard").checker_wrapper()
        self.app.call_from_thread(
            bar.update_icon,
            icon_utils.get_icon("general", "cut" if len(cutted) else "copy")[0],
        )
        self.app.call_from_thread(
            bar.update_icon,
            icon_utils.get_icon("general", "check")[0],
        )
        self.app.call_from_thread(bar.progress_bar.advance)
        self.app.call_from_thread(bar.add_class, "done")

    async def on_key(self, event: events.Key) -> None:
        if event.key in config["keybinds"]["delete"]:
            event.stop()
            await self.remove_children(".done")
            await self.remove_children(".error")
