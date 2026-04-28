import os
import shutil
import sys
import time
import zipfile
from os import path
from typing import Callable, Literal, cast

from send2trash import send2trash
from textual import events, work
from textual.color import Gradient
from textual.containers import HorizontalGroup, VerticalGroup, VerticalScroll
from textual.renderables.bar import Bar as BarRenderable
from textual.types import UnusedParameter

from rovr.classes.archive import Archive
from rovr.functions import icons as icon_utils
from rovr.functions import path as path_utils
from rovr.functions.utils import is_being_used
from rovr.screens import (
    Dismissible,
    FileInUse,
    FileNameConflict,
    YesOrNo,
    typed,
)
from rovr.variables.constants import config, os_type, scroll_bindings
from rovr.widgets import Label, ProgressBar

if sys.version_info.major == 3 and sys.version_info.minor <= 13:
    from backports.zstd import tarfile
else:
    import tarfile


class ThickBar(BarRenderable):
    HALF_BAR_LEFT = "▐"
    BAR = "█"
    HALF_BAR_RIGHT = "▌"


class ProgressBarContainer(VerticalGroup, inherit_bindings=False):
    BINDINGS = scroll_bindings

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

    @work
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
            if len(new_label) == 1:
                self.text_label.update(label)
                return
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
            dismiss_with(dict): The message for the Dismissible screen (must contain `message` and `subtitle`)
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
                Dismissible(
                    dismiss_with["message"], border_subtitle=dismiss_with["subtitle"]
                ),
            )
        if notify:
            self.notify(
                message=notify["message"], severity="error", title=notify["title"]
            )
        self.app.Clipboard.checker_wrapper()


class ProcessContainer(VerticalScroll):
    def __init__(self) -> None:
        super().__init__(id="processes")
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

    def handle_file_in_use_error(
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
                    f"The file appears to be open elsewhere.\nHence, I cannot take any action on it.\nPath: {item_display_name}",
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
        elif (
            isinstance(exc, OSError)
            and "symbolic" in exc.__str__()
            or path_utils.force_obtain_write_permission(item_path)
        ):
            os.remove(item_path)
        elif isinstance(exc, PermissionError):
            self.has_perm_error = True
        else:
            raise

    @staticmethod
    def is_path_within_directory(parent_path: str, child_path: str) -> bool:
        parent = path.normcase(path.abspath(parent_path))
        child = path.normcase(path.abspath(child_path))
        try:
            return path.commonpath([parent, child]) == parent
        except ValueError:
            return False

    @staticmethod
    def get_archive_member_name(member: object) -> str:
        return str(getattr(member, "filename", getattr(member, "name", "")))

    def is_archive_member_directory(self, member: object) -> bool:
        if isinstance(member, zipfile.ZipInfo):
            return member.is_dir()
        if isinstance(member, tarfile.TarInfo):
            return member.isdir()
        is_dir_attr = getattr(member, "isdir", None)
        if callable(is_dir_attr):
            return bool(is_dir_attr())
        if isinstance(is_dir_attr, bool):
            return is_dir_attr
        filename = self.get_archive_member_name(member)
        return filename.endswith(("/", "\\"))

    @staticmethod
    def is_relative_path_within(relative_path: str, relative_root: str) -> bool:
        rel = path.normpath(relative_path)
        root = path.normpath(relative_root)
        return rel == root or rel.startswith(root + path.sep)

    @staticmethod
    def retarget_relative_paths(
        items: list[path_utils.FileObj], old_root: str, new_root: str
    ) -> None:
        old_root_norm = path.normpath(old_root)
        new_root_norm = path.normpath(new_root)
        old_root_with_sep = old_root_norm + path.sep
        for item in items:
            rel = path.normpath(item["relative_loc"])
            if rel == old_root_norm:
                item["relative_loc"] = path_utils.normalise(new_root_norm)
                continue
            if rel.startswith(old_root_with_sep):
                suffix = rel.removeprefix(old_root_with_sep)
                item["relative_loc"] = path_utils.normalise(
                    path.join(new_root_norm, suffix)
                )

    @work(thread=True)
    def delete_files(self, files: list[str], ignore_trash: bool = False) -> None:
        """
        Remove files from the filesystem.

        Args:
            files (list[str]): List of file paths to remove.
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
                        except (PermissionError, OSError) as exc:
                            # On Windows, a file being used by another process
                            # raises a PermissionError/OSError with winerror 32.
                            if (
                                is_file_in_use := is_being_used(exc)
                            ) and os_type == "Windows":
                                current_action, action_on_file_in_use = (
                                    self.handle_file_in_use_error(
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
                        except Exception as exc:
                            path_utils.dump_exc(self, exc)
                            do_what = self.app.call_from_thread(
                                self.app.push_screen_wait,
                                YesOrNo(
                                    f"Trashing failed due to\n{exc}\nDo Permanent Deletion?",
                                    with_toggle=True,
                                    border_subtitle="If this is a bug, please file an issue!",
                                    destructive=True,
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
                except (PermissionError, OSError) as exc:
                    # Try to detect if file is in use on Windows
                    if (is_file_in_use := is_being_used(exc)) and os_type == "Windows":
                        current_action, action_on_file_in_use = (
                            self.handle_file_in_use_error(
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
                except Exception as exc:
                    # TODO: should probably let it continue, then have a summary
                    path_utils.dump_exc(self, exc)
                    bar.panic(
                        dismiss_with={
                            "message": f"Deleting failed due to\n{exc}\nProcess Aborted.",
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
        # if there weren't any files, show something useful
        # aside from 'Getting files to delete...'
        if files_to_delete == [] and folders_to_delete != []:
            self.app.call_from_thread(
                bar.update_text,
                files[-1],
            )
        elif files_to_delete == folders_to_delete == []:
            # this cannot happen, but just as an easter egg
            self.app.call_from_thread(
                bar.update_text, "Successfully deleted nothing!", False
            )
        # finished successfully
        self.app.call_from_thread(
            bar.update_icon,
            str(bar.icon_label.content)
            + " "
            + icon_utils.get_icon("general", "check")[0],
        )
        self.app.call_from_thread(bar.progress_bar.advance)
        self.app.call_from_thread(bar.add_class, "done")
        self.app.Clipboard.checker_wrapper()

    @work(thread=True)
    def create_archive(
        self,
        files: list[str],
        archive_name: str,
        algo: Literal["zip", "tar", "tar.gz", "tar.bz2", "tar.xz", "tar.zst"],
        level: int,
    ) -> None:
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
            with Archive(archive_name, algo, "w", level) as archive:
                assert archive._archive is not None
                last_update_time = time.monotonic()
                for i, file_path in enumerate(files_to_archive):
                    archive_name = path.relpath(file_path, base_path)
                    current_time = time.monotonic()
                    if (
                        current_time - last_update_time > 0.25
                        or i == len(files_to_archive) - 1
                    ):
                        self.app.call_from_thread(
                            bar.update_text,
                            archive_name,
                        )
                        self.app.call_from_thread(bar.update_progress, progress=i + 1)
                        last_update_time = current_time
                    _archive = archive._archive
                    if _archive:
                        if archive._archive_type == "zip":
                            assert isinstance(_archive, zipfile.ZipFile)
                            _archive.write(file_path, arcname=archive_name)
                        else:
                            assert isinstance(_archive, tarfile.TarFile)
                            _archive.add(file_path, arcname=archive_name)
                for p in files:
                    if path.isdir(p) and not os.listdir(p):
                        archive_name = path.relpath(p, base_path)
                        _archive = archive._archive
                        if _archive:
                            if archive._archive_type == "zip":
                                assert isinstance(_archive, zipfile.ZipFile)
                                _archive.write(p, arcname=archive_name)
                            else:
                                assert isinstance(_archive, tarfile.TarFile)
                                _archive.add(p, arcname=archive_name)

        except Exception as exc:
            path_utils.dump_exc(self, exc)
            bar.panic(
                dismiss_with={
                    "message": f"Archiving failed due to\n{exc}\nProcess Aborted.",
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
    def extract_archive(self, archive_path: str, destination_path: str) -> None:
        """
        Extracts a zip archive to a destination.

        Args:
            archive_path (str): Path to the zip archive.
            destination_path (str): Path to the destination folder.

        Raises:
            ValueError: If the archive contains unsafe paths that could lead to path traversal vulnerabilities.
                      ╰─ this is automatically caught
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

        do_what_on_existence = "ask"
        try:
            if not path.exists(destination_path):
                os.makedirs(destination_path)

            with Archive(archive_path, mode="r") as archive:
                file_list = archive.infolist()
                self.app.call_from_thread(bar.update_progress, total=len(file_list) + 1)

                last_update_time = time.monotonic()
                for i, file in enumerate(file_list):
                    filename = self.get_archive_member_name(file)
                    if filename == "":
                        continue
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
                    normalised_name = path.normpath(filename)
                    member_drive, _ = path.splitdrive(normalised_name)
                    if member_drive or path.isabs(normalised_name):
                        raise ValueError(
                            f"Unsafe archive member path '{filename}' is absolute and cannot be extracted."
                        )
                    final_path = path.abspath(
                        path.join(destination_path, normalised_name)
                    )
                    if not self.is_path_within_directory(destination_path, final_path):
                        raise ValueError(
                            f"Unsafe archive member path '{filename}' escapes destination directory."
                        )
                    final_path = path_utils.normalise(final_path)
                    member_is_dir = self.is_archive_member_directory(file)
                    if path.lexists(final_path):
                        existing_is_dir = path.isdir(final_path)
                        if member_is_dir and existing_is_dir:
                            pass
                        else:
                            is_type_mismatch = member_is_dir != existing_is_dir
                            effective_action = do_what_on_existence
                            if is_type_mismatch and effective_action == "overwrite":
                                effective_action = "ask"
                            if effective_action == "ask":
                                response = self.helper_push_and_get_filenameconflict(
                                    FileNameConflict(
                                        (
                                            "Path already exists in destination\nWhat do you want to do now?"
                                            if not is_type_mismatch
                                            else "Destination path type does not match archive member.\nWhat do you want to do now?"
                                        ),
                                        border_title=filename,
                                        border_subtitle=f"Extracting to {destination_path}",
                                        allow_overwrite=not is_type_mismatch,
                                    ),
                                )
                                if response["same_for_next"]:
                                    do_what_on_existence = response["value"]
                                val = response["value"]
                            else:
                                val = effective_action
                            match val:
                                case "overwrite":
                                    if path.isdir(final_path):
                                        shutil.rmtree(final_path)
                                    else:
                                        os.remove(final_path)
                                case "skip":
                                    continue
                                case "rename":
                                    final_path = path_utils.normalise(
                                        self.helper_rename(final_path)
                                    )
                                case "cancel":
                                    bar.panic()
                                    return
                    try:
                        if member_is_dir:
                            os.makedirs(final_path, exist_ok=True)
                            continue
                        os.makedirs(path.dirname(final_path), exist_ok=True)
                        source = archive.open(file)
                        if source:
                            with source, open(final_path, "wb") as target:
                                shutil.copyfileobj(source, target)
                    except PermissionError:
                        retry_target = (
                            final_path
                            if path.lexists(final_path)
                            else path.dirname(final_path)
                        )
                        if not (
                            retry_target
                            and path_utils.force_obtain_write_permission(retry_target)
                        ):
                            bar.panic(
                                dismiss_with={
                                    "message": "Extracting failed due to\nPermission Error\nProcess Aborted.",
                                    "subtitle": "If this is a bug, please file an issue!",
                                },
                                bar_text="Permission Error",
                            )
                            return
                        try:
                            if member_is_dir:
                                os.makedirs(final_path, exist_ok=True)
                            else:
                                os.makedirs(path.dirname(final_path), exist_ok=True)
                                source = archive.open(file)
                                if source:
                                    with source, open(final_path, "wb") as target:
                                        shutil.copyfileobj(source, target)
                        except PermissionError as exc:
                            path_utils.dump_exc(self, exc)
                            bar.panic(
                                dismiss_with={
                                    "message": f"Extracting failed due to\n{exc}\nProcess Aborted.",
                                    "subtitle": "If this is a bug, please file an issue!",
                                },
                                bar_text="Permission Error",
                            )
                            return
        except (zipfile.BadZipFile, tarfile.TarError, ValueError) as exc:
            dismiss_with = {"subtitle": ""}
            if isinstance(exc, ValueError) and "Password" in exc.__str__():
                if "ZIP" in exc.__str__():
                    dismiss_with["message"] = (
                        "Password-protected ZIP files cannot be unzipped"
                    )
                elif "RAR" in exc.__str__():
                    dismiss_with["message"] = (
                        "Password-protected RAR files cannot be unzipped"
                    )
                else:
                    dismiss_with["message"] = (
                        "Password-protected archive files cannot be unzipped"
                    )
            else:
                path_utils.dump_exc(self, exc)
                dismiss_with = {
                    "message": f"Unzipping failed due to {type(exc).__name__}\n{exc}\nProcess Aborted.",
                    "subtitle": "If this is a bug, file an issue!",
                }
            bar.panic(dismiss_with=dismiss_with, bar_text="Error extracting archive")
            return
        except Exception as exc:
            path_utils.dump_exc(self, exc)
            bar.panic(
                dismiss_with={
                    "message": f"Unzipping failed due to {type(exc).__name__}\n{exc}\nProcess Aborted.",
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
    def paste_items(
        self, copied: list[str], has_cut: list[str], dest: str = ""
    ) -> None:
        """
        Paste copied or cut files to the current directory
        Args:
            copied (list[str]): A list of items to be copied to the location
            has_cut (list[str]): A list of items to be cut to the location
            dest (str): The directory to copy to.
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
        files_to_copy: list[path_utils.FileObj] = []
        files_to_cut: list[path_utils.FileObj] = []
        copy_folders_to_create: list[path_utils.FileObj] = []
        cut_folders_to_create: list[path_utils.FileObj] = []
        cut_files__folders: list[str] = []
        for file in copied:
            if path.isdir(file):
                normalised_file = path_utils.normalise(file)
                copy_folders_to_create.append(
                    path_utils.FileObj(
                        path=normalised_file,
                        relative_loc=path.basename(path.normpath(normalised_file)),
                    )
                )
                files, folders = path_utils.get_recursive_files(file, with_folders=True)
                files_to_copy.extend(files)
                for folder in folders:
                    copy_folders_to_create.append(
                        path_utils.FileObj(
                            path=folder,
                            relative_loc=path_utils.normalise(
                                path.relpath(folder, file + "/..")
                            ),
                        )
                    )
            else:
                files_to_copy.extend(path_utils.get_recursive_files(file))
        for file in has_cut:
            if path.isdir(file):
                normalised_file = path_utils.normalise(file)
                cut_files__folders.append(normalised_file)
                cut_folders_to_create.append(
                    path_utils.FileObj(
                        path=normalised_file,
                        relative_loc=path.basename(path.normpath(normalised_file)),
                    )
                )
                files, folders = path_utils.get_recursive_files(file, with_folders=True)
                files_to_cut.extend(files)
                cut_files__folders.extend(folders)
                for folder in folders:
                    cut_folders_to_create.append(
                        path_utils.FileObj(
                            path=folder,
                            relative_loc=path_utils.normalise(
                                path.relpath(folder, file + "/..")
                            ),
                        )
                    )
            else:
                files_to_cut.extend(path_utils.get_recursive_files(file))
        files_to_copy = list({item["path"]: item for item in files_to_copy}.values())
        files_to_cut = list({item["path"]: item for item in files_to_cut}.values())
        copy_folders_to_create = list(
            {item["relative_loc"]: item for item in copy_folders_to_create}.values()
        )
        cut_folders_to_create = list(
            {item["relative_loc"]: item for item in cut_folders_to_create}.values()
        )
        cut_files__folders = sorted(
            set(cut_files__folders), key=str.__len__, reverse=True
        )
        self.app.call_from_thread(
            bar.update_progress,
            total=int(
                len(files_to_copy)
                + len(files_to_cut)
                + len(copy_folders_to_create)
                + len(cut_folders_to_create)
            )
            + 1,
        )
        action_on_existence = "ask"
        copy_skipped_roots: list[str] = []
        cut_skipped_roots: list[str] = []
        progress_count = 0
        last_update_time = time.monotonic()
        if files_to_copy or copy_folders_to_create:
            self.app.call_from_thread(
                bar.update_icon,
                icon_utils.get_icon("general", "copy")[0],
            )
        for folder_dict in copy_folders_to_create:
            progress_count += 1
            relative_loc = folder_dict["relative_loc"]
            self.app.call_from_thread(bar.update_text, relative_loc)
            self.app.call_from_thread(bar.update_progress, progress=progress_count)
            destination_folder = path_utils.normalise(path.join(dest, relative_loc))
            try:
                if path.exists(destination_folder) and not path.isdir(
                    destination_folder
                ):
                    if (
                        action_on_existence == "ask"
                        or action_on_existence == "overwrite"
                    ):
                        response = self.helper_push_and_get_filenameconflict(
                            FileNameConflict(
                                "Cannot create a directory because destination is a file.\nWhat do you want to do now?",
                                border_title=relative_loc,
                                border_subtitle=f"Copying to {dest}",
                                allow_overwrite=False,
                            )
                        )
                        if response["same_for_next"]:
                            action_on_existence = response["value"]
                        val = response["value"]
                    else:
                        val = action_on_existence
                    match val:
                        case "skip":
                            copy_skipped_roots.append(relative_loc)
                            continue
                        case "rename":
                            new_relative_loc = path_utils.normalise(
                                path.relpath(
                                    self.helper_rename(destination_folder), dest
                                )
                            )
                            old_relative_loc = folder_dict["relative_loc"]
                            folder_dict["relative_loc"] = new_relative_loc
                            self.retarget_relative_paths(
                                copy_folders_to_create,
                                old_relative_loc,
                                new_relative_loc,
                            )
                            self.retarget_relative_paths(
                                files_to_copy, old_relative_loc, new_relative_loc
                            )
                            destination_folder = path_utils.normalise(
                                path.join(dest, new_relative_loc)
                            )
                        case "cancel":
                            bar.panic(bar_text="Process cancelled.")
                            return
                os.makedirs(destination_folder, exist_ok=True)
            except Exception as exc:
                path_utils.dump_exc(self, exc)
                bar.panic(
                    dismiss_with={
                        "message": f"Copying failed due to {type(exc).__name__}\n{exc}\nProcess Aborted.",
                        "subtitle": "If this is a bug, please file an issue!",
                    },
                    bar_text="Unhandled Error",
                )
                return
        for i, item_dict in enumerate(files_to_copy):
            progress_count += 1
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
            self.app.call_from_thread(bar.update_progress, progress=progress_count)
            if any(
                self.is_relative_path_within(item_dict["relative_loc"], root)
                for root in copy_skipped_roots
            ):
                continue
            if path.exists(item_dict["path"]):
                # again checks just in case something goes wrong
                try:
                    destination_item = path.join(dest, item_dict["relative_loc"])
                    os.makedirs(
                        path_utils.normalise(path.dirname(destination_item)),
                        exist_ok=True,
                    )
                    if path.lexists(destination_item):
                        # check if overwrite
                        if action_on_existence == "ask":
                            response = self.helper_push_and_get_filenameconflict(
                                FileNameConflict(
                                    "The destination already has file of that name.\nWhat do you want to do now?",
                                    border_title=item_dict["relative_loc"],
                                    border_subtitle=f"Copying to {dest}",
                                    allow_overwrite=False,
                                ),
                            )
                            if response["same_for_next"]:
                                action_on_existence = response["value"]
                            val = response["value"]
                        else:
                            val = action_on_existence
                        match val:
                            case "overwrite":
                                pass
                            case "skip":
                                continue
                            case "rename":
                                item_dict["relative_loc"] = path_utils.normalise(
                                    path.relpath(
                                        self.helper_rename(
                                            path.join(dest, item_dict["relative_loc"])
                                        ),
                                        dest,
                                    )
                                )
                            case "cancel":
                                bar.panic(bar_text="Process cancelled.")
                                return
                    self.helper_copy(
                        item_dict["path"],
                        path.join(dest, item_dict["relative_loc"]),
                    )
                except shutil.SameFileError:
                    if action_on_existence == "ask":
                        response = self.helper_push_and_get_filenameconflict(
                            FileNameConflict(
                                "Target and Destination are the same files.\nWhat do you want to do now?",
                                border_title=item_dict["relative_loc"],
                                border_subtitle=f"Copying to {dest}",
                            )
                        )
                        if response["same_for_next"]:
                            action_on_existence = response["value"]
                        val = response["value"]
                    else:
                        val = action_on_existence
                    match val:
                        case "skip":
                            continue
                        case "rename":
                            item_dict["relative_loc"] = path_utils.normalise(
                                path.relpath(
                                    self.helper_rename(
                                        path.join(dest, item_dict["relative_loc"])
                                    ),
                                    dest,
                                )
                            )
                        case "cancel":
                            bar.panic(bar_text="Process cancelled.")
                            return
                    self.helper_copy(
                        item_dict["path"], path.join(dest, item_dict["relative_loc"])
                    )
                except (OSError, PermissionError):
                    # OSError from shutil: The destination location must be writable;
                    # otherwise, an OSError exception will be raised
                    # Permission Error just in case
                    if path_utils.force_obtain_write_permission(
                        path.join(dest, item_dict["relative_loc"])
                    ):
                        self.helper_copy(
                            item_dict["path"],
                            path.join(dest, item_dict["relative_loc"]),
                        )
                except FileNotFoundError:
                    # the only way this can happen is if the file is deleted
                    # midway through the process, which means the user is
                    # literally testing the limits, so yeah uhh, pass
                    pass
                except Exception as exc:
                    # TODO: should probably let it continue, then have a summary
                    bar.panic(
                        dismiss_with={
                            "message": f"Copying failed due to {type(exc).__name__}\n{exc}\nProcess Aborted.",
                            "subtitle": "If this is a bug, please file an issue!",
                        },
                        bar_text="Unhandled Error",
                    )
                    path_utils.dump_exc(self, exc)
                    return

        cut_ignore = []
        last_update_time = time.monotonic()
        if files_to_cut or cut_folders_to_create:
            self.app.call_from_thread(
                bar.update_icon,
                icon_utils.get_icon("general", "cut")[0],
            )
        for folder_dict in cut_folders_to_create:
            progress_count += 1
            relative_loc = folder_dict["relative_loc"]
            self.app.call_from_thread(bar.update_text, relative_loc)
            self.app.call_from_thread(bar.update_progress, progress=progress_count)
            destination_folder = path_utils.normalise(path.join(dest, relative_loc))
            try:
                if path.exists(destination_folder) and not path.isdir(
                    destination_folder
                ):
                    if (
                        action_on_existence == "ask"
                        or action_on_existence == "overwrite"
                    ):
                        response = self.helper_push_and_get_filenameconflict(
                            FileNameConflict(
                                "Cannot create a directory because destination is a file.\nWhat do you want to do now?",
                                border_title=relative_loc,
                                border_subtitle=f"Moving to {dest}",
                                allow_overwrite=False,
                            )
                        )
                        if response["same_for_next"]:
                            action_on_existence = response["value"]
                        val = response["value"]
                    else:
                        val = action_on_existence
                    match val:
                        case "skip":
                            cut_skipped_roots.append(relative_loc)
                            continue
                        case "rename":
                            new_relative_loc = path_utils.normalise(
                                path.relpath(
                                    self.helper_rename(destination_folder), dest
                                )
                            )
                            old_relative_loc = folder_dict["relative_loc"]
                            folder_dict["relative_loc"] = new_relative_loc
                            self.retarget_relative_paths(
                                cut_folders_to_create,
                                old_relative_loc,
                                new_relative_loc,
                            )
                            self.retarget_relative_paths(
                                files_to_cut, old_relative_loc, new_relative_loc
                            )
                            destination_folder = path_utils.normalise(
                                path.join(dest, new_relative_loc)
                            )
                        case "cancel":
                            bar.panic(bar_text="Process cancelled.")
                            return
                os.makedirs(destination_folder, exist_ok=True)
            except Exception as exc:
                path_utils.dump_exc(self, exc)
                bar.panic(
                    dismiss_with={
                        "message": f"Moving failed due to {type(exc).__name__}\n{exc}\nProcess Aborted.",
                        "subtitle": "If this is a bug, please file an issue!",
                    },
                    bar_text="Unhandled Error",
                )
                return
        for i, item_dict in enumerate(files_to_cut):
            progress_count += 1
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
                last_update_time = current_time
            self.app.call_from_thread(bar.update_progress, progress=progress_count)
            if any(
                self.is_relative_path_within(item_dict["relative_loc"], root)
                for root in cut_skipped_roots
            ):
                cut_ignore.append(item_dict["path"])
                continue
            if path.exists(item_dict["path"]):
                # again checks just in case something goes wrong
                destination_item = path.join(dest, item_dict["relative_loc"])
                moved = False
                try:
                    os.makedirs(
                        path_utils.normalise(path.dirname(destination_item)),
                        exist_ok=True,
                    )
                    if path.exists(destination_item):
                        self.log(
                            path_utils.normalise(destination_item),
                            path_utils.normalise(item_dict["path"]),
                        )

                        if path_utils.normalise(
                            destination_item
                        ) == path_utils.normalise(item_dict["path"]):
                            cut_ignore.append(item_dict["path"])
                            continue
                        is_type_mismatch = path.isdir(destination_item)
                        effective_action = action_on_existence
                        if is_type_mismatch and effective_action == "overwrite":
                            effective_action = "ask"
                        if effective_action == "ask":
                            response = self.helper_push_and_get_filenameconflict(
                                FileNameConflict(
                                    (
                                        "The destination already has file of that name.\nWhat do you want to do now?"
                                        if not is_type_mismatch
                                        else "Destination has a directory with the same name.\nWhat do you want to do now?"
                                    ),
                                    border_title=item_dict["relative_loc"],
                                    border_subtitle=f"Moving to {dest}",
                                    allow_overwrite=not is_type_mismatch,
                                ),
                            )
                            if response["same_for_next"]:
                                action_on_existence = response["value"]
                            val = response["value"]
                        else:
                            val = effective_action
                        match val:
                            case "overwrite":
                                pass
                            case "skip":
                                cut_ignore.append(item_dict["path"])
                                continue
                            case "rename":
                                new_relative_loc = path_utils.normalise(
                                    path.relpath(
                                        self.helper_rename(
                                            path.join(dest, item_dict["relative_loc"])
                                        ),
                                        dest,
                                    )
                                )
                                item_dict["relative_loc"] = new_relative_loc
                                destination_item = path.join(
                                    dest, item_dict["relative_loc"]
                                )
                            case "cancel":
                                bar.panic(bar_text="Process cancelled.")
                                return
                    shutil.move(
                        item_dict["path"],
                        destination_item,
                    )
                    moved = True
                except (OSError, PermissionError):
                    # OSError from shutil: The destination location must be writable;
                    # otherwise, an OSError exception will be raised
                    # Permission Error just in case
                    if path_utils.force_obtain_write_permission(
                        destination_item
                    ) and path_utils.force_obtain_write_permission(item_dict["path"]):
                        shutil.move(
                            item_dict["path"],
                            destination_item,
                        )
                        moved = True
                except FileNotFoundError:
                    # the only way this can happen is if the file is deleted
                    # midway through the process, which means the user is
                    # literally testing the limits, so yeah uhh, pass
                    pass
                except Exception as exc:
                    # TODO: should probably let it continue, then have a summary
                    path_utils.dump_exc(self, exc)
                    bar.panic(
                        dismiss_with={
                            "message": f"Moving failed due to {type(exc).__name__}\n{exc}\nProcess Aborted.",
                            "subtitle": "If this is a bug, please file an issue!",
                        },
                        bar_text="Unhandled Error",
                    )
                    return
                if not moved and path.exists(item_dict["path"]):
                    cut_ignore.append(item_dict["path"])
        # delete the folders
        self.has_perm_error = False
        self.has_in_use_error = False
        for folder in cut_files__folders:
            skip = any(
                self.is_path_within_directory(folder, ignored_file)
                for ignored_file in cut_ignore
            )
            if not skip and path.exists(folder):
                shutil.rmtree(folder, onexc=self.rmtree_fixer)
        if self.has_in_use_error:
            bar.panic(
                notify={
                    "message": "Certain files could not be deleted as they are currently being used",
                    "title": "Delete Files",
                },
                bar_text=path.basename(has_cut[-1]),
            )
            return
        if self.has_perm_error:
            bar.panic(
                notify={
                    "message": "Certain files could not be deleted due to PermissionError.",
                    "title": "Delete Files",
                },
                bar_text=path.basename(has_cut[-1]),
            )
            return
        self.app.Clipboard.checker_wrapper()
        self.app.call_from_thread(
            bar.update_icon,
            icon_utils.get_icon("general", "cut" if len(has_cut) else "copy")[0],
        )
        self.app.call_from_thread(
            bar.update_icon,
            icon_utils.get_icon("general", "check")[0],
        )
        self.app.call_from_thread(bar.progress_bar.advance)
        self.app.call_from_thread(bar.add_class, "done")

    def on_key(self, event: events.Key) -> None:
        if event.key in config["keybinds"]["delete"]:
            event.stop()
            self.action_delete()

    def action_delete(self) -> None:
        self.remove_children(".done")
        self.remove_children(".error")

    def helper_copy(self, target: str, destination: str) -> None:
        if config["settings"]["copy_includes_metadata"]:
            shutil.copy2(target, destination)
        else:
            shutil.copy(target, destination)

    def helper_push_and_get_filenameconflict(
        self, screen: FileNameConflict
    ) -> typed.FileNameConflict:
        response = self.app.call_from_thread(self.app.push_screen_wait, screen)
        return cast(typed.FileNameConflict, response)

    @staticmethod
    def helper_rename(target: str) -> str:
        base_name, extension = path.splitext(target)
        tested_number = 1
        while True:
            new_name = f"{base_name} ({tested_number}){extension}"
            if not path.exists(new_name):
                return new_name
            tested_number += 1
