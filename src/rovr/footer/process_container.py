from __future__ import annotations

import errno
import os
import shutil
import stat
import subprocess
import sys
import time
from functools import partial
from os import path
from threading import get_ident
from typing import Any, Callable, Literal, TypeVar

from textual import events, work
from textual.app import ComposeResult
from textual.color import Gradient
from textual.containers import HorizontalGroup, VerticalGroup, VerticalScroll
from textual.geometry import clamp
from textual.reactive import reactive
from textual.renderables.bar import Bar as BarRenderable
from textual.screen import Screen, ScreenResultType
from textual.timer import Timer
from textual.types import UnusedParameter
from textual.widget import Widget
from textual.widgets import Label, ProgressBar
from textual.widgets._progress_bar import UNUSED

import rovr.screens as screens
from rovr.classes.mixins import Action, Actionable
from rovr.classes.type_aliases import BarPanicDismissible, BarPanicNotify, CallableNone
from rovr.functions import icons as icons
from rovr.functions import path as path_utils
from rovr.functions.cwd import getcwd
from rovr.functions.utils import dump_on_exc, is_being_used, should_cancel
from rovr.variables.constants import config

WIN32 = sys.platform == "win32"
P = TypeVar("P")


class ThickBar(BarRenderable):
    HALF_BAR_LEFT = "▐"
    BAR = "█"
    HALF_BAR_RIGHT = "▌"


class PasteCancelled(Exception):
    pass


class ProcessProgressBar(ProgressBar):
    _update_timer: Timer | None = None
    _finished: bool = False
    BAR_RENDERABLE = ThickBar

    def _on_mount(self, event: events.Mount) -> None:
        event.prevent_default()
        self.update()
        self._clock.reset()
        if not self._finished:
            self._update_timer = self.set_interval(1, self.update)

    def finish(self) -> None:
        self._finished = True
        if self._update_timer is not None:
            self._update_timer.stop()
            self._update_timer = None

    def _compute_percentage(self) -> float | None:
        if self.total:
            # i just didnt like how inaccurate 99.5% looks (it shows 100%, which is stupid af)
            return clamp(int(100 * (self.progress / self.total)) / 100, 0.0, 1.0)
        elif self.total == 0:
            return 1.0
        return None


def is_path_in_directory(parent: str, child: str, resolve: bool = True) -> bool:
    """Checks if the absolute path of a child is within the absolute path of a parent directory.
    Args:
        parent (str): The parent directory path.
        child (str): The child path to check.
        resolve (bool): Whether to resolve symbolic links and relative paths. Defaults to True.
    Returns:
        bool: True if the resolved child path is within the resolved parent directory, False otherwise.
    """
    func = path.realpath if resolve else path.abspath
    parent = path.normcase(func(parent))
    child = path.normcase(func(child))
    try:
        return path.commonpath([parent, child]) == parent
    except ValueError:
        return False


def helper_rename(target: str) -> str:
    """Helper function to rename a file or directory if it already exists.
    Args:
        target (str): The target file or directory path.
    Returns:
        str: The new name for the file or directory that does not conflict with existing names.
    """
    base_name, extension = path.splitext(target)
    tested_number = 1
    while True:
        new_name = f"{base_name} ({tested_number}){extension}"
        if not path.lexists(new_name):
            return new_name
        tested_number += 1


copy_func = partial(
    shutil.copy2 if config["settings"]["copy_includes_metadata"] else shutil.copy,
    follow_symlinks=False,
)


def display_path(item: str, relative_to: str) -> str:
    try:
        return path.relpath(item, relative_to)
    except Exception:
        return item


def panic_cancel(bar: ProgressBarContainer) -> bool:
    if should_cancel():
        bar.panic(bar_text="Worker Cancelled.")
        return True
    return False


class ProgressBarContainer(VerticalGroup, inherit_bindings=False):
    def __init__(
        self,
        total: int | None = None,
        label: str = "",
        text_interval: float = 0.25,
        advance_interval: float = 0,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
            markup=False,
        )
        self.progress_bar = ProcessProgressBar(
            total=total,
            show_percentage=config["interface"]["show_progress_percentage"],
            show_eta=config["interface"]["show_progress_eta"],
            gradient=self.get_gradient("default"),
        )
        self.icon_label = Label(id="icon")
        self.text_label = Label(label, id="label")
        self.label_container = HorizontalGroup(self.icon_label, self.text_label)
        self.text_interval = text_interval
        self.advance_interval = advance_interval
        self.__state: Literal["error", "done", "running"] = "running"
        self._advance_by: float = 0
        self._last_text_update: float | None = None
        self._last_advance: float | None = None
        self.in_thread = lambda: self.app._thread_id != get_ident()
        self._can_set_text: bool = True
        self._queued_text: tuple[str, bool] = ("", False)

    def compose(self) -> ComposeResult:
        yield self.label_container
        yield self.progress_bar

    def get_gradient(self: Widget, state: str) -> Gradient | None:
        gradient_colors = getattr(
            self.app.get_theme(self.app.theme),
            "bar_gradient",
            {},
        ).get(state)
        if gradient_colors is not None:
            try:
                return Gradient.from_colors(*reversed(gradient_colors))
            except ValueError:
                return None

    def call_safe(self, func: Callable[..., P], *args: Any, **kwargs: Any) -> P:
        if self.in_thread():
            return self.app.call_from_thread(func, *args, **kwargs)
        return func(*args, **kwargs)

    def set_text(self, label: str, is_path: bool = True, force: bool = False) -> None:
        """
        Updates the text label
        Args:
            label (str): The new label
            is_path (bool) = True: Whether the text is a path or not
        """
        self._queued_text = (label, is_path)
        if not (self.__state == "running" or force):
            return

        now = time.monotonic()
        if (
            not force
            and self._last_text_update is not None
            and now - self._last_text_update < self.text_interval
        ):
            return
        self._last_text_update = now

        if is_path:
            label = path_utils.control(label)
            if config["interface"]["truncate_progress_file_path"]:
                new_label = label.split("/")
                if len(new_label) == 1:
                    self.text_label.update(label)
                    return
                new_path = new_label[0]
                for p in new_label[1:-1]:
                    new_path += f"/{p[0]}"
                label = new_path + f"/{new_label[-1]}"

        self.call_safe(self.text_label.update, label)

    def set_icon(self, icon: str) -> None:
        self.call_next(self.icon_label.update, icon)

    def set_progress(
        self,
        total: float | UnusedParameter = UNUSED,
        progress: float | UnusedParameter = UNUSED,
    ) -> None:
        self.progress_bar.update(total=total, progress=progress)

    def advance(self, amount: float = 1) -> None:
        if self.__state != "running":
            return
        self._advance_by += amount
        now = time.monotonic()
        if (
            self._last_advance is not None
            and now - self._last_advance < self.advance_interval
        ):
            return
        self._last_advance = now
        self._flush_advance()

    def _flush_advance(self) -> None:
        amount, self._advance_by = self._advance_by, 0
        if not amount:
            return
        self.call_safe(self.progress_bar.advance, amount)

    def _set_panic_state(self, bar_text: str, notify: BarPanicNotify | None) -> None:
        self._flush_advance()
        if bar_text:
            self.set_text(bar_text, False, force=True)
        else:
            self.set_text(*self._queued_text, force=True)
        if self.progress_bar.total is None:
            self.progress_bar.update(total=1, progress=0)
        self.progress_bar.finish()
        self.add_class("error")
        self.progress_bar.gradient = self.get_gradient("error")
        assert isinstance(self.icon_label.content, str)
        self.set_icon(
            f"{self.icon_label.content} {icons.get_icon('general', 'close')[0]}"
        )

        if notify:
            self.notify(
                message=notify["message"], severity="error", title=notify["title"]
            )
        self.app.Clipboard.checker_wrapper()

    def panic(
        self,
        dismiss_with: BarPanicDismissible | None = None,
        notify: BarPanicNotify | None = None,
        bar_text: str = "",
        exceptions: list[tuple[str, Exception]] | None = None,
        action: str = "handle",
    ) -> None:
        """Do something when an error occurs.
        Args:
            dismiss_with(dict): The message for the Dismissible screen (must contain `message` and `subtitle`)
            notify(dict): The notify message (must contain `message` and `title`)
            bar_text(str): The new text to update the label
            exceptions(list): A list of tuples containing the file and the exception that occurred
            action(str): The action that was being performed when the error occurred
        """
        if self.__state != "running":
            return
        self.__state = "error"
        self.call_safe(self._set_panic_state, bar_text, notify)

        for file, exc in exceptions or []:
            self.notify(
                message=f"Failed to {action} {file} due to {exc!r}",
                severity="error",
                markup=False,
            )
            path_utils.dump_exc(self, exc)

        if dismiss_with:
            self.call_safe(
                self.app.push_screen,
                screens.Dismissible(
                    dismiss_with["message"], border_subtitle=dismiss_with["subtitle"]
                ),
            )

    def ok(self, text: str = "") -> None:
        """Do something when the process is successful.
        Args:
            text(str): The new text to update the label
        """
        if self.__state != "running":
            return
        if self.in_thread():
            self.app.call_from_thread(self.ok, text)
            return
        self.__state = "done"
        self._flush_advance()
        if text:
            self.set_text(text, False, force=True)
        else:
            self.set_text(*self._queued_text, force=True)
        if self.progress_bar.total is None:
            self.progress_bar.update(total=1, progress=1)
        else:
            self.progress_bar.update(progress=self.progress_bar.total)
        self.progress_bar.finish()
        self.add_class("done")
        assert isinstance(self.icon_label.content, str)
        self.set_icon(
            f"{self.icon_label.content} {icons.get_icon('general', 'check')[0]}"
        )
        self.app.Clipboard.checker_wrapper()


class ProcessContainer(Actionable, VerticalScroll):
    key_contexts = ("processes", "scroll")
    theme: reactive[str] = reactive("textual-dark")
    ACTIONS = [Action("delete", config["keybinds"]["delete"])]

    def __init__(self) -> None:
        super().__init__(id="processes")

    def watch_theme(self, theme: str) -> None:
        error_gradient = ProgressBarContainer.get_gradient(self, "error")
        default_gradient = ProgressBarContainer.get_gradient(self, "default")

        for bar in self.query(ProgressBarContainer):
            if bar.has_class("error") and error_gradient:
                bar.progress_bar.gradient = error_gradient
            elif default_gradient:
                bar.progress_bar.gradient = default_gradient
            else:
                bar.progress_bar.gradient = None

    async def new_process_bar(
        self,
        total: int | None = None,
        text_interval: float = 0.25,
        advance_interval: float = 0,
        id: str | None = None,
        classes: str | None = None,
    ) -> ProgressBarContainer:
        new_bar = ProgressBarContainer(
            total=total,
            text_interval=text_interval,
            advance_interval=advance_interval,
            id=id,
            classes=classes,
        )
        await self.mount(new_bar, before=0)
        return new_bar

    def threaded_new_process_bar(
        self,
        total: int | None = None,
        text_interval: float = 0.25,
        advance_interval: float = 0,
        id: str | None = None,
        classes: str | None = None,
    ) -> ProgressBarContainer:
        bar = self.app.call_from_thread(
            self.new_process_bar,
            total=total,
            text_interval=text_interval,
            advance_interval=advance_interval,
            id=id,
            classes=classes,
        )
        assert isinstance(bar, ProgressBarContainer)
        return bar

    def handle_file_in_use_error(
        self,
        action_on_file_in_use: str,
        item_display_name: str,
        retry_func: Callable[[], Any],
    ) -> tuple[str, str]:
        """Ask how to handle an item in use and retry when requested.

        Returns:
            The action for this item and the remembered action for later items.

        Raises:
            PermissionError: The retry failed for a reason other than file use.
            OSError: The retry failed for a reason other than file use.
        """
        default_action = action_on_file_in_use
        action = default_action

        while True:
            if action == "ask":
                response: screens.FileInUse.ReturnType = self.app.call_from_thread(
                    self.app.push_screen_wait,
                    screens.FileInUse(
                        "The file appears to be open elsewhere and cannot be changed."
                        f"\nPath: {item_display_name}"
                    ),
                )
                action = response["value"]
                if response["toggle"]:
                    default_action = action

            if action != "try_again":
                return action, default_action

            try:
                retry_func()
                return action, default_action
            except FileNotFoundError:
                return action, default_action
            except (PermissionError, OSError) as exc:
                if not is_being_used(exc):
                    raise
                # A remembered retry gets one attempt, then asks instead of looping.
                action = "ask"

    @work(thread=True)
    def delete_files(self, files: list[str]) -> None:
        """Permanently remove files from the filesystem, bypassing the recycle bin.

        Args:
            files (list[str]): List of file paths to remove.
        """

        def work_size(item: str) -> int:
            if path.islink(item) or path.isjunction(item) or not path.isdir(item):
                return 1
            size = 1
            for root, dirs, file_names in os.walk(item, topdown=True):
                size += len(dirs) + len(file_names)
                dirs[:] = [
                    name
                    for name in dirs
                    if not path.islink(path.join(root, name))
                    and not path.isjunction(path.join(root, name))
                ]
            return size

        bar = self.threaded_new_process_bar(classes="active", advance_interval=0.25)
        bar.set_icon(icons.get_icon("general", "delete")[0])
        bar.set_text("Getting files to delete...", False)
        bar.set_progress(total=sum(map(work_size, files)))
        errors: list[tuple[str, Exception]] = []

        action_on_file_in_use = "ask"

        def remove_file(item: str) -> bool:
            nonlocal action_on_file_in_use

            bar.set_text(item)

            def remove() -> None:
                if path.isjunction(item):
                    os.rmdir(item)
                else:
                    os.unlink(item)

            try:
                remove()
            except PermissionError as exc:
                if is_being_used(exc) and WIN32:
                    try:
                        action, action_on_file_in_use = self.handle_file_in_use_error(
                            action_on_file_in_use, item, remove
                        )
                    except Exception as retry_exc:
                        errors.append((item, retry_exc))
                        return True
                    if action == "cancel":
                        bar.panic(bar_text="Deletion cancelled.")
                        return False
                    if action == "skip":
                        bar.advance()
                        return True
                elif is_being_used(exc):
                    raise
                elif path_utils.force_obtain_write_permission(item):
                    try:
                        remove()
                    except Exception as retry_exc:
                        errors.append((item, retry_exc))
                        return True
                else:
                    errors.append((item, exc))
                    return True
            except FileNotFoundError:
                pass
            except Exception as exc:
                errors.append((item, exc))
                return True

            bar.advance()
            return True

        for file in files:
            if should_cancel():
                bar.panic(bar_text="Worker Cancelled.")
                # use break so errors can still be reported if any
                break
            if not path.lexists(file):
                # ignore
                bar.advance()
                continue
            elif path.islink(file) or path.isjunction(file):
                if not remove_file(file):
                    return
                continue
            elif path.isdir(file):
                bar.set_text(file)
                directories: list[str] = []
                for root, dirs, file_names in os.walk(file, topdown=True):
                    for name in file_names:
                        if panic_cancel(bar):
                            return
                        file_path = path.join(root, name)
                        if not remove_file(file_path):
                            return
                    for name in list(dirs):
                        if panic_cancel(bar):
                            return
                        dir_path = path.join(root, name)
                        if path.islink(dir_path) or path.isjunction(dir_path):
                            dirs.remove(name)
                            if not remove_file(dir_path):
                                return
                        else:
                            directories.append(dir_path)
                for dir_path in reversed(directories):
                    bar.set_text(dir_path)
                    try:
                        os.rmdir(dir_path)
                        bar.advance()
                    except OSError as exc:
                        # check if it is because non-empty directory, if so, ignore
                        # because relevant exception is from the file deletion above
                        if exc.errno != errno.ENOTEMPTY:
                            errors.append((dir_path, exc))
                    except Exception as exc:
                        errors.append((dir_path, exc))
                if panic_cancel(bar):
                    break
                bar.set_text(file)
                try:
                    os.rmdir(file)
                    bar.advance()
                except FileNotFoundError:
                    # it's gone, so why care?
                    bar.advance()
                except OSError as exc:
                    if exc.errno != errno.ENOTEMPTY:
                        errors.append((file, exc))
            elif path.isfile(file):
                if not remove_file(file):
                    return
        if not files:
            # this cannot happen, but just as an easter egg
            bar.ok("Successfully deleted nothing!")
        if errors:
            bar.panic(
                notify={
                    "message": f"Failed to delete {len(errors)} items.",
                    "title": "Delete Error",
                },
                bar_text=f"Failed to delete {len(errors)} items",
                exceptions=errors,
                action="delete",
            )
        else:
            bar.ok()

        import gc

        gc.collect()

    @work(thread=True)
    def trash_files(self, files: list[str]) -> None:
        """Send files to the recycle bin.

        Folders are recycled as-is, so that a selected folder becomes a single
        trash entry instead of one entry per file it contains (recursively)

        Args:
            files (list[str]): List of top-level file/folder paths to trash.
        """
        if not config["settings"]["use_recycle_bin"]:
            self.notify("Recycle Bin is disabled in settings.", severity="warning")
            return
        from pytrash import RecycleBin

        recycle_bin = RecycleBin()
        bar = self.threaded_new_process_bar(classes="active")
        bar.set_icon(icons.get_icon("general", "trash")[0])
        bar.set_text("Getting files to trash...", False)
        bar.set_progress(total=len(files) + 1, progress=0)
        failed: list[tuple[str, Exception]] = []
        action_on_file_in_use = "ask"
        for file in files:
            if panic_cancel(bar):
                break
            bar.set_text(file)
            if not path.lexists(file):
                # ignore
                bar.advance()
                continue
            try:
                file = path.normpath(file)
                recycle_bin.recycle([file])
                bar.advance()
            except FileNotFoundError:
                # it's gone, so why care?
                bar.advance()
            except (PermissionError, OSError) as exc:
                is_file_in_use = is_being_used(exc)
                if is_file_in_use and WIN32:
                    action, action_on_file_in_use = self.handle_file_in_use_error(
                        action_on_file_in_use,
                        file,
                        lambda: recycle_bin.recycle([file]),
                    )
                    if action == "cancel":
                        bar.panic(bar_text="Trashing cancelled.")
                        return
                    bar.advance()
                elif path_utils.force_obtain_write_permission(file):
                    try:
                        recycle_bin.recycle([file])
                        bar.advance()
                    except Exception as e:
                        failed.append((file, e))
                else:
                    failed.append((file, exc))
            except Exception as exc:
                failed.append((file, exc))
        if failed:
            bar.panic(
                notify={
                    "message": f"Failed to trash {len(failed)} items.",
                    "title": "Trash Error",
                },
                bar_text=f"Failed to trash {len(failed)} items",
                exceptions=failed,
                action="trash",
            )
        else:
            bar.ok()

        import gc

        gc.collect()

    @work(thread=True)
    def create_archive(
        self,
        files: list[str],
        archive_name: str,
        algo: Literal["zip", "tar", "tar.gz", "tar.bz2", "tar.xz", "tar.zst"],
        level: int,
        password: str | None = None,  # soon soon trust me
    ) -> None:
        """Compress files into an archive.

        Args:
            files (list[str]): List of file paths to compress.
            archive_name (str): Path for the output archive.
            algo: Compression algorithm to use.
            level (int): Compression level (0-9 (or 0-22 for zstd)).
            password (str | None): Currently does nothing.
        """
        from multiarchive import Archive

        start, bar = getcwd(), self.threaded_new_process_bar(classes="active")
        bar.set_icon(icons.get_icon("general", "zip")[0])
        bar.set_text("Getting files to archive...", False)
        files_to_archive: list[path_utils.FileObj] = []
        for file in files:
            objs = path_utils.get_recursive_files(file, True)
            files_to_archive.extend(objs[0])
            files_to_archive.extend(
                {
                    "path": folder,
                    "relative_loc": (
                        path.relpath(folder, start) if path.isabs(folder) else folder
                    ),
                }
                for folder in objs[1]
                if not os.listdir(folder)
            )

        bar.set_progress(total=len(files_to_archive) + 1, progress=0)
        onerr = lambda e: bar.panic({
            "message": f"Failed to create archive {archive_name} due to {e!r}",
            "subtitle": "Press any key to dismiss.",
        })

        with (
            dump_on_exc(self, Exception, other_callers=onerr),
            Archive(archive_name, algo, "w", level, strict_timestamps=True) as archive,
        ):
            for obj in files_to_archive:
                if panic_cancel(bar):
                    break
                bar.set_text(display_path(obj["path"], start))
                archive.add(obj["path"], obj["relative_loc"])
                bar.advance()
        bar.ok()

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
        from multiarchive import Archive

        bar = self.threaded_new_process_bar(classes="active")
        bar.set_icon(icons.get_icon("general", "open")[0])
        bar.set_text("Preparing to extract...", False)
        os.makedirs(destination_path, exist_ok=True)
        archive: Archive | None = None
        password: bytes | None = None
        password_res: str | UnusedParameter | None = UNUSED
        while archive is None:
            if password_res is None:
                bar.panic(notify={"title": "", "message": "No password provided."})
                return
            if isinstance(password_res, str):
                password = password_res.encode()
            try:
                archive = Archive.open_archive(archive_path, "r", pwd=password)
            except ValueError as e:
                # check error is due to password
                if "password required" in str(e).lower():
                    password_res = self.push_screen(
                        screens.ModalInput(
                            border_title="Enter password for archive",
                            border_subtitle="Escape to cancel",
                        )
                    )
            except KeyError as e:
                if "invalid password" in str(e).lower():
                    password_res = self.push_screen(
                        screens.ModalInput(
                            border_title="Enter password for archive",
                            border_subtitle="Escape to cancel",
                            initial_value=password.decode() if password else "",
                            allow_initial=False,
                        ),
                    )
        del password
        bar.set_progress(total=len(members := archive.infolist()) + 1, progress=0)
        unsaferes: bool | None = None
        conflictres: screens.FileNameConflict.ReturnType | None = None
        permissionres: Literal["try_again", "cancel", "skip"] | None = None

        # -------------------- bunch of helper functions ----------------------------------------------------------------------

        def confirm_unsafe_member(message: str) -> bool | None:
            nonlocal unsaferes
            if unsaferes is not None:
                return unsaferes

            res: screens.YesOrNo.ReturnType | None = self.push_screen(
                screens.YesOrNo(
                    message=message,
                    border_subtitle="Escape to cancel",
                    destructive=True,
                    with_toggle=True,
                    allow_cancel=True,
                ),
            )
            if res is None:
                return None
            if res["toggle"]:
                unsaferes = res["value"]
            return res["value"]

        def conflict_resolve(
            message: str, allow_overwrite: bool
        ) -> Literal["overwrite", "rename", "skip", "cancel"]:
            nonlocal conflictres
            # earlier overwrite cannot be reused when overwrite is not allowed
            if conflictres is not None and (
                allow_overwrite or conflictres["value"] != "overwrite"
            ):
                return conflictres["value"]
            res: screens.FileNameConflict.ReturnType = self.push_screen(
                screens.FileNameConflict(
                    message=message,
                    border_subtitle=f"Extracting to {destination_path}",
                    allow_overwrite=allow_overwrite,
                ),
            )
            if res["same_for_next"]:
                conflictres = res
            return res["value"]

        def run_with_permission_prompt(func: CallableNone, path_str: str) -> bool | None:
            nonlocal permissionres
            use_remembered = True
            while True:
                try:
                    func()
                    return True
                except PermissionError:
                    action = permissionres if use_remembered else None
                    if action is None:
                        response: screens.FileInUse.ReturnType = self.push_screen(
                            screens.FileInUse(
                                f"Permission denied while extracting:\n{path_str}",
                                border_title="Permission Error",
                            ),
                        )
                        action = response["value"]
                        if response["toggle"]:
                            permissionres = action
                    if action == "skip":
                        return False
                    if action == "cancel":
                        return None

                    retry_target = (
                        path_str if path.lexists(path_str) else path.dirname(path_str)
                    )
                    if retry_target:
                        path_utils.force_obtain_write_permission(retry_target)
                    # Do not loop forever when a remembered retry keeps failing.
                    use_remembered = False

        # ------------------------ theres one more below btw ---------------------------------------------------------------------

        for member in members:
            bar.set_text(member.name)
            # do some pre checks like absolute path and escaping destination
            normalised = path.normpath(member.name)
            res: bool | None = None
            if path.isabs(normalised):
                res = confirm_unsafe_member(
                    f"{member.name!r} is an absolute path"
                    "\nExtracting it may cause unintended consequences."
                    "\nDo you want to extract this?"
                )
                if res is None:
                    raise ValueError(
                        f"Unsafe archive member path {member.name!r} is an absolute"
                        " path and cannot be extracted."
                    )
            final_path = path.abspath(path.join(destination_path, normalised))
            if res is None and (
                not is_path_in_directory(destination_path, final_path, False)
            ):
                res = confirm_unsafe_member(
                    f"{member.name!r} escapes the destination directory (via relative path)"
                    "\nExtracting it may cause unintended consequences."
                    "\nDo you want to extract this?"
                )
                if res is None:
                    raise ValueError(
                        f"Unsafe archive member path {member.name!r} escapes the"
                        " destination directory and cannot be extracted."
                    )
            if res is None and (not is_path_in_directory(destination_path, final_path)):
                res = confirm_unsafe_member(
                    f"{member.name!r} escapes the destination directory (via symlink)"
                    "\nExtracting it may cause unintended consequences."
                    "\nDo you want to extract this?"
                )
                if res is None:
                    raise ValueError(
                        f"Unsafe archive member path {member.name!r} escapes"
                        " destination via a symbolic link."
                    )
            if res is False:
                bar.advance()
                continue

            if path.lexists(final_path):
                # isdir follows links, but links are still conflicts
                # even if they point to directories
                existing_is_link = path.islink(final_path) or path.isjunction(final_path)
                existing_is_dir = path.isdir(final_path) and not existing_is_link
                if member.is_dir and existing_is_dir:
                    pass
                else:
                    same_type = member.is_dir == existing_is_dir
                    action = conflict_resolve(
                        "Path already exists in destination.\nWhat do you want to do?",
                        allow_overwrite=same_type,
                    )
                    match action:
                        case "skip":
                            bar.advance()
                            continue
                        case "cancel":
                            bar.panic(), archive.close()
                            return
                        case "rename":
                            final_path = helper_rename(final_path)
                        case "overwrite":
                            removed = run_with_permission_prompt(
                                lambda: os.unlink(final_path), final_path
                            )
                            if removed is None:
                                bar.panic(), archive.close()
                                return
                            if not removed:
                                bar.advance()
                                continue

            def extract_member() -> None:
                if member.is_dir:
                    os.makedirs(final_path, exist_ok=True)
                else:
                    os.makedirs(path.dirname(final_path), exist_ok=True)
                    source = archive.open(member)
                    if source:
                        with source, open(final_path, "wb") as target:
                            shutil.copyfileobj(source, target)

            extracted = run_with_permission_prompt(extract_member, final_path)
            if extracted is None:
                bar.panic(), archive.close()
                return
            bar.advance()
        archive.close(), bar.ok()

    @work(thread=True)
    def paste_items(
        self, type_of_selection: Literal["copy", "cut"], paths: list[str], dest: str = ""
    ) -> None | Literal[True]:
        dest = path.abspath(dest or getcwd())
        bar = self.threaded_new_process_bar(classes="active")
        bar.set_icon(icons.get_icon("general", type_of_selection)[0])
        bar.set_text(
            f"Getting items to {'move' if type_of_selection == 'cut' else 'copy'}",
            False,
        )
        sources = list(
            {path.normcase(path.abspath(p)): path.normpath(p) for p in paths}.values()
        )

        def is_real_dir(item: str) -> bool:
            return (
                path.isdir(item) and not path.islink(item) and not path.isjunction(item)
            )

        # A selected directory already includes any selected descendants.
        # because of ipc allowing it to happen
        sources = [
            source
            for source in sources
            if not any(
                source != other
                and is_real_dir(other)
                and is_path_in_directory(other, source, False)
                for other in sources
            )
        ]

        work_sizes: dict[str, int] = {}

        def work_size(item: str) -> int:
            key = path.normcase(path.abspath(item))
            if key in work_sizes:
                return work_sizes[key]
            if not is_real_dir(item):
                work_sizes[key] = 1
                return 1
            try:
                entries = list(os.scandir(item))
            except OSError:
                work_sizes[key] = 1
                return 1
            size = sum(work_size(entry.path) for entry in entries) or 1
            work_sizes[key] = size
            return size

        bar.set_progress(total=sum(map(work_size, sources)) + 1, progress=0)

        errors: list[tuple[str, Exception]] = []
        if path.lexists(dest) and not path.isdir(dest):
            self.notify(
                f"Paste destination is not a directory: {dest}",
                title="Paste Error",
                severity="error",
                markup=False,
            )
            bar.panic(bar_text="Invalid paste destination")
            return
        conflictres: screens.FileNameConflict.ReturnType | None = None
        action_on_file_in_use = "ask"

        def conflict_resolve(
            source: str, destination: str, allow_overwrite: bool
        ) -> Literal["overwrite", "rename", "skip", "cancel"]:
            nonlocal conflictres
            # Reuse the user's choice unless a remembered overwrite is unsafe here.
            if conflictres is not None and (
                allow_overwrite or conflictres["value"] != "overwrite"
            ):
                return conflictres["value"]
            response: screens.FileNameConflict.ReturnType = self.push_screen(
                screens.FileNameConflict(
                    "The destination already contains an item with this name.\n"
                    "What do you want to do?",
                    border_title=display_path(destination, dest),
                    border_subtitle=(
                        f"{'Moving' if type_of_selection == 'cut' else 'Copying'} "
                        f"from {path.dirname(source)}"
                    ),
                    allow_overwrite=allow_overwrite,
                )
            )
            if response["same_for_next"]:
                conflictres = response
            return response["value"]

        def transfer(source: str, destination: str) -> bool:
            if should_cancel():
                raise PasteCancelled
            if not path.lexists(source):
                bar.advance(work_size(source))
                return True

            bar.set_text(display_path(destination, dest))
            source_is_dir = is_real_dir(source)
            created_directory = False

            def copy_link() -> None:
                if path.isjunction(source):
                    # luv windows
                    target = path.realpath(source)
                    if target.startswith("\\\\?\\UNC\\"):
                        target = f"\\\\{target[8:]}"
                    elif target.startswith("\\\\?\\"):
                        target = target[4:]
                    result = subprocess.run(
                        'mklink /J "%ROVR_JUNCTION_DESTINATION%" "%ROVR_JUNCTION_TARGET%"',
                        shell=True,
                        capture_output=True,
                        env=os.environ
                        | {
                            "ROVR_JUNCTION_DESTINATION": destination,
                            "ROVR_JUNCTION_TARGET": target,
                        },
                        text=True,
                    )
                    if result.returncode:
                        raise OSError(result.stderr.strip() or result.stdout.strip())
                    return

                target = os.readlink(source)
                target_is_directory = path.isdir(source) or bool(
                    getattr(os.lstat(source), "st_file_attributes", 0)
                    & stat.FILE_ATTRIBUTE_DIRECTORY
                )
                try:
                    os.symlink(
                        target,
                        destination,
                        target_is_directory=target_is_directory,
                    )
                except OSError as exc:
                    sudo = (
                        shutil.which("sudo")
                        if getattr(exc, "winerror", None) == 1314
                        else None
                    )
                    if not sudo:
                        raise
                    subprocess.run(
                        [
                            sudo,
                            sys.executable,
                            "-c",
                            "import os,sys;os.symlink(sys.argv[1],sys.argv[2],target_is_directory=sys.argv[3]=='1')",
                            target,
                            destination,
                            str(int(target_is_directory)),
                        ],
                        check=True,
                        capture_output=True,
                    )

            if path.lexists(destination):
                destination_is_dir = is_real_dir(destination)
                try:
                    same_path = path.samefile(source, destination)
                except OSError:
                    same_path = False

                action = conflict_resolve(
                    source,
                    destination,
                    allow_overwrite=(
                        source_is_dir == destination_is_dir and not same_path
                    ),
                )
                if action == "cancel":
                    raise PasteCancelled
                if action == "skip":
                    bar.advance(work_size(source))
                    return False
                if action == "rename":
                    destination = helper_rename(destination)
                    destination_is_dir = False
                    bar.set_text(display_path(destination, dest))
                elif not (source_is_dir and destination_is_dir):
                    if path.isjunction(destination):
                        os.rmdir(destination)
                    else:
                        os.unlink(destination)

            if not path.lexists(destination):
                # Avoid walking whole trees when no merge or nested conflict is needed.
                os.makedirs(path.dirname(destination), exist_ok=True)
                if type_of_selection == "cut":
                    shutil.move(source, destination)
                    bar.advance(work_size(source))
                    return True
                elif source_is_dir:
                    os.mkdir(destination)
                    created_directory = True
                else:
                    if path.islink(source) or path.isjunction(source):
                        copy_link()
                    else:
                        copy_func(source, destination)
                    bar.advance()
                if not source_is_dir:
                    return True

            complete = True
            entries = list(os.scandir(source))
            if not entries:
                bar.advance()
            for entry in entries:
                if not transfer(entry.path, path.join(destination, entry.name)):
                    complete = False
            # A skipped child must remain at its source during a cut.
            if type_of_selection == "cut" and complete:
                os.rmdir(source)
            elif created_directory and config["settings"]["copy_includes_metadata"]:
                shutil.copystat(source, destination, follow_symlinks=False)
            return complete

        for source in sources:
            if should_cancel():
                bar.panic(bar_text="Worker Cancelled.")
                return
            if not path.lexists(source):
                bar.advance(work_size(source))
                continue
            destination = path.join(dest, path.basename(path.normpath(source)))
            # Copying into a descendant would recursively consume the new copy.
            if is_real_dir(source) and is_path_in_directory(source, dest, False):
                errors.append((
                    source,
                    ValueError("Cannot paste a directory inside itself"),
                ))
                bar.advance(work_size(source))
                continue

            try:
                transfer(source, destination)
            except PasteCancelled:
                bar.panic(bar_text="Pasting cancelled.")
                return
            except (PermissionError, OSError) as exc:
                if is_being_used(exc) and WIN32:
                    try:
                        action, action_on_file_in_use = self.handle_file_in_use_error(
                            action_on_file_in_use,
                            source,
                            lambda: transfer(source, destination),
                        )
                    except PasteCancelled:
                        bar.panic(bar_text="Pasting cancelled.")
                        return
                    except Exception as retry_exc:
                        errors.append((source, retry_exc))
                    else:
                        if action == "cancel":
                            bar.panic(bar_text="Pasting cancelled.")
                            return
                else:
                    errors.append((source, exc))
            except Exception as exc:
                errors.append((source, exc))

        if errors:
            bar.panic(
                notify={
                    "message": f"Failed to paste {len(errors)} items.",
                    "title": "Paste Error",
                },
                bar_text=f"Failed to paste {len(errors)} items",
                exceptions=errors,
                action="paste",
            )
            return

        bar.ok()
        return True

    @work(thread=True)
    def remote_download(self, uris: list[str], paths: list[str]) -> None:
        """Pull from remote uris

        Args:
            uris (list[str]): A list of uris to download from
        """
        from contextlib import ExitStack
        from urllib import error, request

        chunk_size = 1024 * 1024

        dest = getcwd()
        bar = self.threaded_new_process_bar(total=len(uris) + 1, classes="active")
        bar.set_icon(icons.get_icon("general", "down")[0])
        bar.set_text("Downloading items...")

        with ExitStack() as stack:
            reqs = (
                request.Request(uri, headers={"User-Agent": "Mozilla/5.0"})
                for uri in uris
            )

            opened: list[tuple[Any, str]] = []
            failures: list[tuple[str, Exception]] = []
            for req, filename in zip(reqs, paths):
                full_path = (
                    filename if path.isabs(filename) else path.join(dest, filename)
                )
                bar.set_text(display_path(full_path, dest))
                try:
                    resp: Any = stack.enter_context(request.urlopen(req, timeout=5))
                    opened.append((resp, full_path))
                except Exception as e:
                    failures.append((filename, e))
                    if isinstance(e, error.HTTPError):
                        bar.set_text(f"HTTP Error {e.code} for {filename}. Skipping...")
                    elif isinstance(e, error.URLError):
                        bar.set_text(
                            f"Network Error: {e.reason} for {filename}. Skipping..."
                        )
                    else:
                        bar.set_text(f"Failed to open {filename}: {e}. Skipping...")

            # set the max of progress bar to be total size of all successfully opened files
            bar.set_progress(sum((r.length or 0) for r, _ in opened) + len(failures) + 1)

            for resp, filename in opened:
                bar.set_text(display_path(filename, dest))
                try:
                    with open(filename, "wb") as file:
                        while chunk := resp.read(chunk_size):
                            if should_cancel():
                                bar.panic(bar_text="Download cancelled.")
                                return
                            file.write(chunk)
                            bar.advance(len(chunk))
                except (error.URLError, error.HTTPError, OSError) as e:
                    # Handles network drops midway through an active stream or disk write errors
                    failures.append((filename, e))
                    bar.set_text(f"Error reading/saving {path.basename(filename)}: {e}")
                    continue
            if not failures:
                bar.ok()
            else:
                bar.panic(
                    notify={
                        "message": f"Failed to download {len(failures)} items.",
                        "title": "Download Error",
                    },
                    bar_text=f"Failed to download {len(failures)} items",
                    exceptions=failures,
                    action="download",
                )

    def action_delete(self) -> None:
        self.remove_children(".done, .error")

    def push_screen(self, screen: Screen) -> ScreenResultType:
        """Push a screen onto the screen stack.

        Args:
            screen (Screen): The screen to push.

        Returns:
            ScreenResultType: The result of the screen when it is popped off the stack.
        """
        return self.app.call_from_thread(self.app.push_screen_wait, screen)
