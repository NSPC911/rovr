import platform
import shutil
import tarfile
import time
import zipfile
from contextlib import suppress
from os import getcwd, listdir, makedirs, path, remove, walk

from send2trash import send2trash
from textual import events, work
from textual.color import Gradient
from textual.containers import HorizontalGroup, VerticalGroup, VerticalScroll
from textual.renderables.bar import Bar as BarRenderable
from textual.types import UnusedParameter
from textual.widgets import Label, ProgressBar
from textual.widgets.option_list import OptionDoesNotExist

from rovr.classes import Archive
from rovr.functions import icons as icon_utils
from rovr.functions import path as path_utils
from rovr.screens import CommonFileNameDoWhat, Dismissable, GiveMePermission, YesOrNo, FileInUse
from rovr.variables.constants import config


class ThickBar(BarRenderable):
    HALF_BAR_LEFT = "▐"
    BAR = "█"
    HALF_BAR_RIGHT = "▌"


class ProgressBarContainer(VerticalGroup):
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
            for path_item in new_label[1:-1]:
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
        dismiss_with: dict = {},
        notify: dict = {},
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
        self.update_icon(
            self.icon_label.content + " " + icon_utils.get_icon("general", "close")[0]
        )
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


class ProcessContainer(VerticalScroll):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(id="processes", *args, **kwargs)

    async def new_process_bar(
        self, max: int | None = None, id: str | None = None, classes: str | None = None
    ) -> ProgressBarContainer:
        new_bar: ProgressBarContainer = ProgressBarContainer(
            total=max, id=id, classes=classes
        )
        await self.mount(new_bar, before=0)
        return new_bar

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
        """
        # Create progress/process bar (why have I set names as such...)
        bar: ProgressBarContainer = self.app.call_from_thread(
            self.new_process_bar, classes="active"
        )
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
            if path.isdir(file):
                folders_to_delete.append(file)
            files_to_add, folders_to_add = path_utils.get_recursive_files(
                file, with_folders=True
            )
            files_to_delete.extend(files_to_add)
            folders_to_delete.extend(folders_to_add)
        self.app.call_from_thread(bar.update_progress, total=len(files_to_delete) + 1)
        action_on_permission_error = "ask"
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
                            if platform.system() == "Windows":
                                # An inherent issue with long paths on windows
                                path_to_trash = path_to_trash.replace("/", "\\")
                                pass
                            send2trash(path_to_trash)
                        except PermissionError as e:
                            # On Windows, a file being used by another process
                            # raises a PermissionError/OSError with winerror 32.
                            is_file_in_use = False
                            try:
                                # Some PermissionError instances expose winerror
                                is_file_in_use = getattr(e, "winerror", None) == 32
                            except Exception:
                                is_file_in_use = False
                            if is_file_in_use and platform.system() == "Windows":
                                # Ask the user specifically that the file is in use
                                response = self.app.call_from_thread(
                                    self.app.push_screen_wait,
                                    FileInUse(
                                        f"The file appears to be open in another application and cannot be deleted.\nPath: {item_dict['relative_loc']}",
                                        border_title=item_dict["relative_loc"],
                                    ),
                                )
                                # response is dict {"value": True/False} or bool
                                if isinstance(response, dict):
                                    if not response.get("value"):
                                        # cancel
                                        bar.panic()
                                        return
                                    else:
                                        # user pressed OK, try skipping
                                        continue
                                elif response is False:
                                    bar.panic()
                                    return
                                else:
                                    continue
                            # fallback for regular permission issues
                            if action_on_permission_error == "ask":
                                do_what = self.app.call_from_thread(
                                    self.app.push_screen_wait,
                                    GiveMePermission(
                                        "Path has no write access to be deleted.\nForcefully obtain and delete it?",
                                        border_title=item_dict["path"],
                                    ),
                                )
                                if do_what["toggle"]:
                                    action_on_permission_error = do_what["value"]
                                action = do_what["value"]
                            else:
                                action = action_on_permission_error
                            match action:
                                case "force":
                                    if path_utils.force_obtain_write_permission(
                                        item_dict["path"]
                                    ):
                                        remove(item_dict["path"])
                                case "skip":
                                    continue
                                case "cancel":
                                    bar.panic()
                                    return
                        except Exception as e:
                            do_what = self.app.call_from_thread(
                                self.app.push_screen_wait,
                                YesOrNo(
                                    f"Trashing failed due to\n{e}\nDo Permenant Deletion?",
                                    with_toggle=True,
                                    border_subtitle="If this is a bug, please file an issue!",
                                ),
                            )
                            if do_what["toggle"]:
                                ignore_trash = do_what["value"]
                            if do_what["value"]:
                                remove(item_dict["path"])
                            else:
                                continue
                    else:
                        remove(item_dict["path"])
                except FileNotFoundError:
                    # it's deleted, so why care?
                    pass
                except PermissionError:
                    # Try to detect if file is in use on Windows
                    e = None
                    try:
                        raise
                    except Exception as exc:
                        e = exc
                    is_file_in_use = False
                    try:
                        is_file_in_use = getattr(e, "winerror", None) == 32
                    except Exception:
                        is_file_in_use = False
                    if is_file_in_use and platform.system() == "Windows":
                        response = self.app.call_from_thread(
                            self.app.push_screen_wait,
                            FileInUse(
                                f"The file appears to be open in another application and cannot be deleted.\nPath: {item_dict['relative_loc']}",
                                border_title=item_dict["relative_loc"],
                            ),
                        )
                        if isinstance(response, dict):
                            if not response.get("value"):
                                bar.panic()
                                return
                            else:
                                continue
                        elif response is False:
                            bar.panic()
                            return
                        else:
                            continue
                    # fallback for regular permission issues
                    if action_on_permission_error == "ask":
                        do_what = self.app.call_from_thread(
                            self.app.push_screen_wait,
                            GiveMePermission(
                                "Path has no write access to be deleted.\nForcefully obtain and delete it?",
                                border_title=item_dict["path"],
                            ),
                        )
                        if do_what["toggle"]:
                            action_on_permission_error = do_what["value"]
                        action = do_what["value"]
                    else:
                        action = action_on_permission_error
                    match action:
                        case "force":
                            if path_utils.force_obtain_write_permission(
                                item_dict["path"]
                            ):
                                remove(item_dict["path"])
                        case "skip":
                            continue
                        case "cancel":
                            bar.panic()
                            return
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
        has_perm_error = False
        for folder in folders_to_delete:
            try:
                shutil.rmtree(folder)
            except PermissionError:
                has_perm_error = True
            except FileNotFoundError:
                # ig it got removed?
                pass
        if has_perm_error:
            bar.panic(
                notify={
                    "message": f"Certain files in {folder} could not be deleted due to PermissionError.",
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
            bar.icon_label.content + " " + icon_utils.get_icon("general", "check")[0],
        )
        self.app.call_from_thread(bar.progress_bar.advance)
        self.app.call_from_thread(bar.add_class, "done")

    @work(thread=True)
    def create_archive(self, files: list[str], archive_name: str) -> None:
        """
        Compress files into an archive.

        Args:
            files (list[str]): List of file paths to compress.
            archive_name (str): Path for the output archive.
        """
        bar: ProgressBarContainer = self.app.call_from_thread(
            self.new_process_bar, classes="active"
        )
        self.app.call_from_thread(
            bar.update_icon,
            icon_utils.get_icon("general", "zip")[0],
        )
        self.app.call_from_thread(bar.update_text, "Getting files to archive...", False)

        files_to_archive = []
        for p in files:
            if path.isdir(p):
                if not listdir(p):  # empty directory
                    files_to_archive.append(p)
                else:
                    for dirpath, _, filenames in walk(p):
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
                        if archive._is_zip:
                            assert isinstance(_archive, zipfile.ZipFile)
                            _archive.write(file_path, arcname=arcname)
                        else:
                            assert isinstance(_archive, tarfile.TarFile)
                            _archive.add(file_path, arcname=arcname)
                for p in files:
                    if path.isdir(p) and not listdir(p):
                        arcname = path.relpath(p, base_path)
                        _archive = archive._archive
                        if _archive:
                            if archive._is_zip:
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
            bar.icon_label.content + " " + icon_utils.get_icon("general", "check")[0],
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
        bar: ProgressBarContainer = self.app.call_from_thread(
            self.new_process_bar, classes="active"
        )
        self.app.call_from_thread(
            bar.update_icon,
            icon_utils.get_icon("general", "open")[0],
        )
        self.app.call_from_thread(
            bar.update_text,
            "Preparing to extract...",
        )

        do_what_on_existance = "ask"
        action_on_permission_error = "ask"
        try:
            if not path.exists(destination_path):
                makedirs(destination_path)

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
                        if action_on_permission_error == "ask":
                            do_what = self.app.call_from_thread(
                                self.app.push_screen_wait,
                                GiveMePermission(
                                    "Path has no write access to be overwritten.\nForcefully obtain and overwrite?",
                                    border_title=filename,
                                ),
                            )
                            if do_what["toggle"]:
                                action_on_permission_error = do_what["value"]
                            action = do_what["value"]
                        else:
                            action = action_on_permission_error
                        match action:
                            case "force":
                                if path_utils.force_obtain_write_permission(
                                    path.join(destination_path, filename)
                                ):
                                    archive.extract(file, path=destination_path)
                            case "skip":
                                continue
                            case "cancel":
                                bar.panic()
                                return
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
            dest = getcwd()
        bar: ProgressBarContainer = self.app.call_from_thread(
            self.new_process_bar, classes="active"
        )
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
        action_on_permission_error = "ask"
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
                    makedirs(
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
                    if action_on_permission_error == "ask":
                        do_what = self.app.call_from_thread(
                            self.app.push_screen_wait,
                            GiveMePermission(
                                "Path has no write access to be overwritten.\nForefully obtain and overwrite?",
                                border_title=item_dict["relative_loc"],
                            ),
                        )
                        if do_what["toggle"]:
                            action_on_permission_error = do_what["value"]
                        action = do_what["value"]
                    else:
                        action = action_on_permission_error
                    match action:
                        case "force":
                            if path_utils.force_obtain_write_permission(
                                path.join(dest, item_dict["relative_loc"])
                            ):
                                shutil.copy(
                                    item_dict["path"],
                                    path.join(dest, item_dict["relative_loc"]),
                                )
                        case "skip":
                            continue
                        case "cancel":
                            self.app.call_from_thread(bar.add_class, "error")
                            self.app.call_from_thread(
                                bar.update_icon,
                                icon_utils.get_icon("general", "copy")[0]
                                + " "
                                + icon_utils.get_icon("general", "close")[0],
                            )
                            return
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
        action_on_permission_error = "ask"
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
                    makedirs(
                        path_utils.normalise(
                            path.join(dest, item_dict["relative_loc"], "..")
                        ),
                        exist_ok=True,
                    )
                    if path.exists(path.join(dest, item_dict["relative_loc"])):
                        print(
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
                    if action_on_permission_error == "ask":
                        do_what = self.app.call_from_thread(
                            self.app.push_screen_wait,
                            GiveMePermission(
                                "Path has no write access to be overwritten.\nForcefully obtain and overwrite?",
                                border_title=item_dict["relative_loc"],
                            ),
                        )
                        if do_what["toggle"]:
                            action_on_permission_error = do_what["value"]
                        action = do_what["value"]
                    else:
                        action = action_on_permission_error
                    match action:
                        case "force":
                            if path_utils.force_obtain_write_permission(
                                path.join(dest, item_dict["relative_loc"])
                            ) and path_utils.force_obtain_write_permission(
                                item_dict["path"]
                            ):
                                shutil.move(
                                    item_dict["path"],
                                    path.join(dest, item_dict["relative_loc"]),
                                )
                        case "skip":
                            continue
                        case "cancel":
                            bar.panic(bar_text="Process cancelled.")
                            return
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
        has_perm_error = False
        for folder in cut_files__folders:
            try:
                skip = False
                for file in cut_ignore:
                    if folder in file:
                        skip = True
                        break
                if not skip:
                    shutil.rmtree(folder)
            except PermissionError:
                has_perm_error = True
            except FileNotFoundError:
                # ig it got removed?
                continue
        if has_perm_error:
            bar.panic(
                notify={
                    "message": f"Certain files in {folder} could not be deleted due to PermissionError.",
                    "title": "Delete Files",
                },
                bar_text=path.basename(cutted[-1]),
            )
            return
        # remove from clipboard
        for item in cutted:
            # cant bother to figure out how this happens,
            # just catch it
            with suppress(OptionDoesNotExist):
                self.app.call_from_thread(
                    self.app.query_one("Clipboard").remove_option,
                    path_utils.compress(item),
                )
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
