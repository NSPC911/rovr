from __future__ import annotations

import asyncio
import base64
import os
import re
import shlex
import stat
import sys
from contextlib import suppress
from functools import lru_cache, partial
from os import path
from subprocess import CompletedProcess
from typing import Any, Callable, Literal, TypedDict, overload

from rich.console import Console
from textual import work
from textual.app import App
from textual.dom import DOMNode

from rovr import pprint
from rovr.classes.config import _OpenerIf, _RightClickIf
from rovr.classes.type_aliases import (
    SortByOptions,
)
from rovr.variables.constants import log_name

from .drive_workers import normalise
from .icons import get_icon_for_file, get_icon_for_folder

natsort_compiled = re.compile(r"(\d+)")


def _natsort(key: str) -> tuple[str | int, ...]:
    return tuple(
        int(text) if text.isdigit() else text for text in natsort_compiled.split(key)
    )


@lru_cache(maxsize=2048)
def natsort(key: str) -> tuple[str | int, ...]:
    return _natsort(key)


def natsort_cacheless(key: str) -> tuple[str | int, ...]:
    return _natsort(key)


def is_hidden_file(entry: os.DirEntry) -> bool:
    """Check whether a ``DirEntry`` represents a hidden item.

    Args:
        entry: A ``DirEntry`` from ``os.scandir``.

    Returns:
        ``True`` if the entry is hidden, ``False`` otherwise.
    """
    if entry.name.startswith(".") and sys.platform != "win32":
        return True
    try:
        file_stat = entry.stat(follow_symlinks=False)
    except OSError:
        return False

    if sys.platform == "darwin":
        return bool(file_stat.st_flags & stat.UF_HIDDEN)
    if sys.platform == "win32":
        return bool(file_stat.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
    return False


# insanely scuffed implementation, but it's required due
# to Textual's strict limitation for ids to consist of
# letters, numbers, underscores, or hyphens, and must
# not begin with a number
def compress(text: Any) -> str:
    text = str(text)
    return "u_" + base64.urlsafe_b64encode(text.encode("utf-8")).decode(
        "ascii"
    ).replace("=", "_")


def decompress(text: str) -> str:
    return base64.urlsafe_b64decode(text[2:].replace("_", "=").encode("ascii")).decode(
        "utf-8"
    )


def samefile(path1: str, path2: str) -> bool:
    """Check if two paths refer to the same file.

    Args:
        path1 (str): The first file path.
        path2 (str): The second file path.

    Returns:
        bool: True if both paths refer to the same file, False otherwise.
    """
    try:
        return os.path.samefile(path1, path2)
    except (OSError, FileNotFoundError):
        return False


create_proc = partial(
    asyncio.create_subprocess_exec,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)


@work
async def open_file(app: App, filepath: str) -> None:
    """Cross-platform function to open files with their default application.

    Args:
        app (App): The Textuall application instance
        filepath (str): Path to the file to open
    """
    system = sys.platform
    # check if it is available first
    if not path.exists(filepath):
        app.notify(
            f"File not found: {filepath}",
            title="Open File",
            severity="error",
            markup=False,
        )
        return

    try:
        match system:
            case "win32":
                process = await create_proc("cmd", "/c", "start", "", filepath)
            case "darwin":  # macOS
                process = await create_proc("open", filepath)
            case _:  # Linux and other Unix-like
                process = await create_proc("xdg-open", filepath)
        _, stderr = await process.communicate()
        if process.returncode != 0:
            if system == "win32":
                # try with powershell
                _, stderr = await (
                    process := await create_proc(
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        "Start-Process",
                        filepath,
                    )
                ).communicate()
                if process.returncode and process.returncode != 0:
                    # honestly cant do anything about this, i dont want to risk
                    # stdout corruption (stares at pixelorama) by trying os.startfile
                    # so just raise it and let the user deal with it
                    app.notify(
                        str(stderr.decode().strip()),
                        title=f"Open File (exited with code {process.returncode})",
                        severity="error",
                        markup=False,
                    )
            else:
                app.notify(
                    f"stderr: {stderr.decode().strip()}",
                    title=f"Open File (exited with code {process.returncode})",
                    severity="error",
                    markup=False,
                )
        elif process.returncode and process.returncode != 0:
            app.notify(
                f"Process exited with return code {process.returncode}",
                title="Open File",
                severity="error",
                markup=False,
            )
    except Exception as e:
        app.notify(str(e), title="Open File", severity="error", markup=False)


def get_filtered_dir_names(cwd: str | bytes, show_hidden: bool = False) -> set[str]:
    """
    Get the names of all items in a directory, respecting the show_hidden setting.
    This function is used for comparison in file watchers to avoid refresh loops.

    Args:
        cwd(str): The working directory to check
        show_hidden(bool): Whether to include hidden files/folders

    Returns:
        set[str]: A set of item names in the directory

    Raises:
        PermissionError: When access to the directory is denied
    """
    try:
        listed_dir = os.scandir(cwd)
    except (PermissionError, FileNotFoundError, OSError):
        raise PermissionError(f"PermissionError: Unable to access {cwd}")

    names = set()
    for item in listed_dir:
        if not show_hidden and is_hidden_file(item):
            continue
        names.add(item.name)

    return names


class CWDObjectReturnDict(TypedDict):
    name: str
    icon: Callable[[], tuple[str, str]]
    dir_entry: os.DirEntry


def get_extension_sort_key(file_dict: dict) -> tuple[int, str]:
    name = file_dict["name"]
    if "." not in name:
        # files without extensions
        return (1, name.lower())
    elif name.startswith(".") and name.count(".") == 1:
        # dotfiles
        return (2, name[1:].lower())
    else:
        # files with extensions
        return (3, name.split(".")[-1].lower())


def sorter(
    thing: CWDObjectReturnDict, sort_st: Literal["ctime", "mtime", "size"]
) -> int | float | str:
    try:
        match sort_st:
            case "ctime":
                return thing["dir_entry"].stat().st_ctime_ns
            case "mtime":
                return thing["dir_entry"].stat().st_mtime_ns
            case "size":
                try:
                    return thing["dir_entry"].stat().st_size
                except FileNotFoundError:
                    return 0  # only for this, since it makes sense
    except FileNotFoundError:
        # if  we cant access it, sort with name
        return thing["name"].lower()


@overload
def sync_get_cwd_object(
    dom_node: DOMNode,
    cwd: str,
    show_hidden: bool = False,
    sort_by: SortByOptions | None = "name",
    reverse: bool = False,
) -> tuple[list[CWDObjectReturnDict], list[CWDObjectReturnDict]]: ...


@overload
def sync_get_cwd_object(
    dom_node: DOMNode,
    cwd: str,
    show_hidden: bool = False,
    sort_by: SortByOptions | None = "name",
    reverse: bool = False,
    return_nothing_if_this_returns_true: Callable[[], bool] | None = None,
) -> (
    tuple[list[CWDObjectReturnDict], list[CWDObjectReturnDict]] | tuple[None, None]
): ...


def sync_get_cwd_object(
    dom_node: DOMNode,
    cwd: str,
    show_hidden: bool = False,
    sort_by: SortByOptions | None = "name",
    reverse: bool = False,
    return_nothing_if_this_returns_true: Callable[[], bool] | None = None,
) -> tuple[list[CWDObjectReturnDict], list[CWDObjectReturnDict]] | tuple[None, None]:
    """
    Get the objects (files and folders) in a provided directory
    Args:
        dom_node(DOMNode): The DOM node requesting this operation
        cwd(str): The working directory to check
        show_hidden(bool): Whether to include hidden files/folders (dot-prefixed on Unix; flagged hidden on Windows/macOS)
        sort_by(str): What to sort by
        reverse(bool): Whether to reverse the sorting
        return_nothing_if_this_returns_true(Callable[[], bool] | None): A callable that returns a bool. If it returns True, the function returns None.

    Returns:
        tuple[list[dict], list[dict]]: (folders, files) on success
        tuple[None, None]: When early termination is triggered

    Raises:
        TypeError: if the wrong type is received
        PermissionError: When access to the directory is denied
    """

    try:
        scanned_entries = os.scandir(cwd)
    except (PermissionError, FileNotFoundError, OSError):
        raise PermissionError(f"PermissionError: Unable to access {cwd}")

    with scanned_entries as entries:
        if (
            return_nothing_if_this_returns_true is not None
            and return_nothing_if_this_returns_true()
        ):
            if globals().get("is_dev", False):
                print("Cut off early after scandir")
            return None, None

        folders: list[CWDObjectReturnDict] = []
        files: list[CWDObjectReturnDict] = []

        for item in entries:
            if not isinstance(item, os.DirEntry):
                raise TypeError(f"Expected a DirEntry object but got {type(item)}")
            if not show_hidden and is_hidden_file(item):
                continue

            if item.is_dir():
                folders.append({
                    "name": item.name,
                    "icon": lambda item=item: get_icon_for_folder(
                        item.path, is_symlink=item.is_symlink() or item.is_junction()
                    ),
                    "dir_entry": item,
                })
            else:
                files.append({
                    "name": item.name,
                    "icon": lambda item=item: get_icon_for_file(
                        item.path, is_symlink=item.is_symlink()
                    ),
                    "dir_entry": item,
                })
            if (
                return_nothing_if_this_returns_true is not None
                and return_nothing_if_this_returns_true()
            ):
                dom_node.log("Cut off early during dictionary building")
                return None, None

    dom_node.log(f"Collected {len(folders)} folders and {len(files)} files in {cwd}")

    # sort order
    match sort_by:
        case "name":
            folders.sort(key=lambda x: x["name"].lower(), reverse=reverse)
            files.sort(key=lambda x: x["name"].lower(), reverse=reverse)
        case "natural":
            if len(folders) < 1024:
                folders.sort(key=lambda x: natsort(x["name"]), reverse=reverse)
            else:
                folders.sort(
                    key=lambda x: natsort_cacheless(x["name"]), reverse=reverse
                )
            if len(files) < 1024:
                files.sort(key=lambda x: natsort(x["name"]), reverse=reverse)
            else:
                files.sort(key=lambda x: natsort_cacheless(x["name"]), reverse=reverse)
        case "created":
            folders.sort(key=lambda x: sorter(x, "ctime"), reverse=reverse)
            files.sort(key=lambda x: sorter(x, "ctime"), reverse=reverse)
        case "modified":
            folders.sort(key=lambda x: sorter(x, "mtime"), reverse=reverse)
            files.sort(key=lambda x: sorter(x, "mtime"), reverse=reverse)
        case "size":
            # no we will not be calculating the folder size
            folders.sort(key=lambda x: x["name"].lower(), reverse=reverse)
            files.sort(key=lambda x: sorter(x, "size"), reverse=reverse)
        case "extension":
            # folders dont have extensions btw
            # and i will not count dot prepended folders
            folders.sort(key=lambda x: x["name"].lower(), reverse=reverse)
            files.sort(key=get_extension_sort_key, reverse=reverse)
        case None:
            pass

    if (
        return_nothing_if_this_returns_true is not None
        and return_nothing_if_this_returns_true()
    ):
        dom_node.log("Cut off early before reversing results")
        return None, None

    dom_node.log(f"Found {len(folders)} folders and {len(files)} files in {cwd}")
    return folders, files


def force_obtain_write_permission(item_path: str) -> bool:
    """
    Forcefully obtain write permission to a file or directory.

    Args:
        item_path (str): The path to the file or directory.

    Returns:
        bool: True if permission was granted successfully, False otherwise.
    """
    if not path.exists(item_path):
        return False
    try:
        current_permissions = stat.S_IMODE(os.lstat(item_path).st_mode)
        os.chmod(item_path, current_permissions | stat.S_IWRITE)
        return True
    except (OSError, PermissionError) as e:
        pprint(
            f"[bright_red]Permission Error:[/] Failed to change permission for {item_path}: {e}"
        )
        return False


class FileObj(TypedDict):
    path: str
    relative_loc: str


@overload
def get_recursive_files(object_path: str) -> list[FileObj]: ...


@overload
def get_recursive_files(
    object_path: str, with_folders: Literal[False]
) -> list[FileObj]: ...


@overload
def get_recursive_files(
    object_path: str, with_folders: Literal[True]
) -> tuple[list[FileObj], list[str]]: ...


def get_recursive_files(
    object_path: str, with_folders: bool = False
) -> list[FileObj] | tuple[list[FileObj], list[str]]:
    """Get the files available at a directory recursively, regardless of whether it is a directory or not
    Args:
        object_path (str): The object's path
        with_folders (bool): Return a list of folders as well

    Returns:
        list: A list of dictionaries, with a "path" key and "relative_loc" key
        OR
        list: A list of dictionaries, with a "path" key and "relative_loc" key for files
        list: A list of path strings that were involved in the file list.
    """
    if not path.isdir(object_path):
        if with_folders:
            return [
                FileObj(
                    path=normalise(object_path),
                    relative_loc=path.basename(object_path),
                )
            ], []
        return [
            FileObj(
                path=normalise(object_path),
                relative_loc=path.basename(object_path),
            )
        ]
    else:
        files = []
        folders = []
        for folder, folders_in_folder, files_in_folder in os.walk(object_path):
            if with_folders:
                for folder_in_folder in folders_in_folder:
                    full_path = normalise(path.join(folder, folder_in_folder))
                    if full_path not in folder:
                        folders.append(full_path)
            for file in files_in_folder:
                full_path = normalise(path.join(folder, file))  # normalise the path
                files.append(
                    FileObj(
                        path=full_path,
                        relative_loc=normalise(
                            path.relpath(full_path, object_path + "/..")
                        ),
                    )
                )
        if with_folders:
            return files, folders
        return files


def ensure_existing_directory(directory: str) -> str:
    while not (path.exists(directory) and path.isdir(directory)):
        parent = path.dirname(directory)
        # If we can't even access the root then there is a bigger problem
        # and this could result in infinite loop
        if parent == directory:
            break

        directory = parent
    if directory == "":
        directory = "."
    return directory


def get_direntry_for(file_path: str) -> os.DirEntry | None:
    """Get the DirEntry object for a given file path.

    Args:
        file_path (str): The path to the file

    Returns:
        DirEntryType | None: The DirEntry object if found, else None
    """
    parent_dir = path.dirname(file_path)
    base_name = path.basename(file_path)
    try:
        with os.scandir(parent_dir) as it:
            for filepath in it:
                if filepath.name == base_name:
                    return filepath
    except (PermissionError, FileNotFoundError, OSError):
        return None
    return None


# trust me ruff, I know what I'm doing
def dump_exc(widget: DOMNode | None, exc: Exception | Traceback) -> str | None:  # noqa: F821
    """Dump an exception to the console for debugging purposes.

    Args:
        widget (DOMNode, None): The widget where the exception occurred.
        exc (Exception, Traceback): The exception to dump.

    Returns:
        str: The path to the log file where the exception was dumped.
    """
    from datetime import datetime

    from rich.panel import Panel
    from rich.traceback import Traceback

    from rovr.variables.maps import RovrVars

    rich_traceback = (
        Traceback.from_exception(
            type(exc),
            exc,
            exc.__traceback__,
            width=None,
            code_width=None,
            show_locals=True,
            max_frames=5,
        )
        if isinstance(exc, Exception)
        else exc
    )
    if isinstance(widget, DOMNode):
        widget.log(rich_traceback)

    dump_path = path.join(
        path.realpath(RovrVars.ROVRCONFIG),
        "logs",
        f"{log_name}.log",
    )
    os.makedirs(path.dirname(dump_path), exist_ok=True)

    log_dir = path.dirname(dump_path)
    log_files = sorted(f for f in os.listdir(log_dir) if f.endswith(".log"))
    available_slots = 50 if path.basename(dump_path) in log_files else 49
    for log_file in log_files[: max(0, len(log_files) - available_slots)]:
        oldest = path.join(log_dir, log_file)
        with suppress(OSError):
            os.remove(oldest)

    with open(dump_path, "a", encoding="utf-8") as file_log:
        # don't need to handle OS Error, Textual automatically chains errors
        error_log = Console(file=file_log, legacy_windows=True)
        # section it with time and date
        error_log.print(
            Panel(rich_traceback, title=f"Exception dumped on {str(datetime.now())}")
        )
    return dump_path


def ifed(app: App, conditions: _RightClickIf | _OpenerIf) -> bool:
    """Checks if the conditions for an option are met, used to determine if an option should be disabled

    Args:
        app: The app, needed to check the conditions
        conditions: The conditions to check, can be based on the highlighted file, current directory, os, or if the highlighted file is a directory

    Returns:
        Whether the option should be disabled based on the conditions
    """
    from fnmatch import fnmatch

    dir_entry: os.DirEntry | None = getattr(
        app.file_list.highlighted_option, "dir_entry", None
    )
    disabled = False
    for thing in conditions:
        match thing:
            case "path":
                disabled = not (
                    any(
                        dir_entry and fnmatch(dir_entry.path, pattern)
                        for pattern in conditions.get("path", [])
                    )
                )
            case "os":
                disabled = not any(
                    os.lower() == sys.platform for os in conditions["os"]
                )
            case "cwd":
                disabled = not (
                    any(
                        fnmatch(app.file_list.current_directory, pattern)
                        for pattern in conditions["cwd"]
                    )
                )
            case "directory":
                if conditions["directory"]:
                    disabled = not (dir_entry and dir_entry.is_dir())
                else:
                    disabled = not (dir_entry and not dir_entry.is_dir())
        if disabled:
            break
    return disabled


def run_opener(app: App, target_path: str) -> None:
    from fnmatch import fnmatch

    from rovr.variables.constants import config

    from . import utils

    groups = config["settings"].get("openers", {}).get("groups", {})
    matches = config["settings"].get("openers", {}).get("match", {})

    for pattern, group_names in matches.items():
        if not fnmatch(target_path, pattern):
            continue
        for group_name in group_names:
            if group_name not in groups:
                app.notify(
                    f"Opener group '{group_name}' not found in configuration.",
                    title="Opener Error",
                    severity="warning",
                    markup=False,
                )
                continue
            for opener in groups[group_name]:
                if isinstance(opener, str):
                    runner = opener
                elif ifed(app, opener.get("if", {})):
                    continue
                elif isinstance(opener["run"], (list, str)):
                    runner = opener["run"]
                else:
                    return
                if isinstance(runner, str):
                    to_run = runner.replace("${path}", shlex.quote(target_path))
                else:
                    to_run = [part.replace("${path}", target_path) for part in runner]
                if to_run == runner:
                    if isinstance(runner, str):
                        to_run = runner + " " + shlex.quote(target_path)
                    else:
                        to_run = runner + [target_path]

                try:
                    proc = utils.run_command(
                        app,
                        to_run,
                        run_type=("orphan" if opener.get("orphan", True) else "suspend")
                        if isinstance(opener, dict)
                        else "orphan",
                        shell=opener.get("shell", True)
                        if isinstance(opener, dict)
                        else True,
                    )
                except Exception:
                    continue
                if isinstance(proc, CompletedProcess):
                    if proc.returncode == 0:
                        return
                else:
                    return
    open_file(app, target_path)
