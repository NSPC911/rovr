import asyncio
import base64
import ctypes
import fnmatch
import os
import stat
import subprocess
from os import path
from typing import Callable, Literal, NamedTuple, TypeAlias, TypedDict, overload

import psutil
from natsort import natsorted
from rich.console import Console
from rich.traceback import Traceback
from textual import work
from textual.app import App
from textual.dom import DOMNode
from textual.highlight import guess_language

from rovr.functions.icons import get_icon_for_file, get_icon_for_folder
from rovr.monkey_patches.puremagic_patch import puremagic
from rovr.variables.constants import config, log_name, os_type

# windows needs nt, because scandir returns
# nt.DirEntry instead of os.DirEntry on
# windows. weird, yes, but I can't do anything
if os_type == "Windows":
    import nt

    DirEntryType: TypeAlias = os.DirEntry | nt.DirEntry
    DirEntryTypes = (os.DirEntry, nt.DirEntry)
else:
    DirEntryType: TypeAlias = os.DirEntry
    DirEntryTypes = os.DirEntry

pprint = Console().print


def normalise(*location: str | bytes) -> str:
    """'Normalise' the path
    Args:
        *location (str | bytes): The location to the item

    Returns:
        str: A normalised path

    Raises:
        ValueError: When no path components are provided
    """
    if not location:
        raise ValueError("At least one path component must be provided")
    # path.normalise fixes the relative references
    # replace \\ with / on windows
    # by any chance if somehow a \\\\ was to enter, fix that
    return (
        str(path.normpath(path.join(*location))).replace("\\", "/").replace("//", "/")
    )


def is_hidden_file(filepath: str) -> bool:
    if os_type == "Windows":
        try:
            GetFileAttributesW = ctypes.windll.kernel32.GetFileAttributesW
            GetFileAttributesW.argtypes = [ctypes.c_wchar_p]
            GetFileAttributesW.restype = ctypes.c_uint32
            attrs = GetFileAttributesW(filepath)
            if attrs == 0xFFFFFFFF:  # INVALID_FILE_ATTRIBUTES
                return False
            return bool(attrs & 0x02)  # FILE_ATTRIBUTE_HIDDEN
        except (OSError, AttributeError):
            return False
    elif os_type == "Darwin":
        # dotfiles should always be hidden, and so should UF_HIDDEN-flagged files
        name_hidden = path.basename(filepath).startswith(".")
        try:
            st = os.stat(filepath, follow_symlinks=False)
            flag_hidden = bool(
                getattr(st, "st_flags", 0) & getattr(stat, "UF_HIDDEN", 0)
            )
        except OSError:
            flag_hidden = False
        return name_hidden or flag_hidden
    else:
        return path.basename(filepath).startswith(".")


# insanely scuffed implementation, but it's required due
# to Textual's strict limitation for ids to consist of
# letters, numbers, underscores, or hyphens, and must
# not begin with a number
def compress(text: str) -> str:
    return "u_" + base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")


def decompress(text: str) -> str:
    return base64.urlsafe_b64decode(text[2:].encode("ascii")).decode("utf-8")


@work
async def open_file(app: App, filepath: str) -> None:
    """Cross-platform function to open files with their default application.

    Args:
        app (App): The Textuall application instance
        filepath (str): Path to the file to open
    """
    system = os_type.lower()
    # check if it is available first
    if not path.exists(filepath):
        app.notify(f"File not found: {filepath}", title="Open File", severity="error")
        return

    try:
        match system:
            case "windows":
                process = await asyncio.create_subprocess_exec(
                    "cmd",
                    "/c",
                    "start",
                    "",
                    filepath,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            case "darwin":  # macOS
                process = await asyncio.create_subprocess_exec(
                    "open",
                    filepath,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            case _:  # Linux and other Unix-like
                process = await asyncio.create_subprocess_exec(
                    "xdg-open",
                    filepath,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
        _, stderr = await process.communicate()
        if stderr:
            app.notify(
                str(stderr.decode().strip()), title="Open File", severity="error"
            )
        elif process.returncode and process.returncode != 0:
            app.notify(
                f"Process exited with return code {process.returncode}",
                title="Open File",
                severity="error",
            )
    except Exception as e:
        app.notify(str(e), title="Open File", severity="error")


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
        if not show_hidden and is_hidden_file(item.path):
            continue
        names.add(item.name)

    return names


class CWDObjectReturnDict(TypedDict):
    name: str
    icon: list[str]
    dir_entry: DirEntryType


def get_extension_sort_key(file_dict: dict) -> tuple[int, str]:
    name = file_dict["name"]
    if "." not in name:
        # extensionless files
        return (1, name.lower())
    elif name.startswith(".") and name.count(".") == 1:
        # dotfiles
        return (2, name[1:].lower())
    else:
        # files with extensions
        return (3, name.split(".")[-1].lower())


@work(thread=True)
def threaded_get_cwd_object(
    node: DOMNode,
    cwd: str,
    show_hidden: bool = False,
    sort_by: Literal[
        "name", "size", "modified", "created", "extension", "natural"
    ] = "name",
    reverse: bool = False,
    return_nothing_if_this_returns_true: Callable[[], bool] | None = None,
) -> (
    tuple[list[CWDObjectReturnDict], list[CWDObjectReturnDict]]
    | tuple[None, None]
    | PermissionError
):
    try:
        return sync_get_cwd_object(
            node,
            cwd,
            show_hidden,
            sort_by,
            reverse,
            return_nothing_if_this_returns_true,
        )
    except PermissionError as exc:
        return exc


@overload
def sync_get_cwd_object(
    dom_node: DOMNode,
    cwd: str,
    show_hidden: bool = False,
    sort_by: Literal[
        "name", "size", "modified", "created", "extension", "natural"
    ] = "name",
    reverse: bool = False,
) -> tuple[list[CWDObjectReturnDict], list[CWDObjectReturnDict]]: ...


@overload
def sync_get_cwd_object(
    dom_node: DOMNode,
    cwd: str,
    show_hidden: bool = False,
    sort_by: Literal[
        "name", "size", "modified", "created", "extension", "natural"
    ] = "name",
    reverse: bool = False,
    return_nothing_if_this_returns_true: Callable[[], bool] | None = None,
) -> (
    tuple[list[CWDObjectReturnDict], list[CWDObjectReturnDict]] | tuple[None, None]
): ...


def sync_get_cwd_object(
    dom_node: DOMNode,
    cwd: str,
    show_hidden: bool = False,
    sort_by: Literal[
        "name", "size", "modified", "created", "extension", "natural"
    ] = "name",
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
        entries = list(os.scandir(cwd))
    except (PermissionError, FileNotFoundError, OSError):
        raise PermissionError(f"PermissionError: Unable to access {cwd}")

    dom_node.log(f"Scanned {len(entries)} entries in {cwd}")

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
        if not isinstance(item, DirEntryTypes):
            raise TypeError(f"Expected a DirEntry object but got {type(item)}")
        if not show_hidden and is_hidden_file(item.path):
            continue

        if item.is_dir():
            folders.append({
                "name": item.name,
                "icon": get_icon_for_folder(item.name),
                "dir_entry": item,
            })
        else:
            files.append({
                "name": item.name,
                "icon": get_icon_for_file(item.name),
                "dir_entry": item,
            })
        if (
            return_nothing_if_this_returns_true is not None
            and return_nothing_if_this_returns_true()
        ):
            if globals().get("is_dev", False):
                dom_node.log("Cut off early during dictionary building")
            return None, None

    dom_node.log(f"Collected {len(folders)} folders and {len(files)} files in {cwd}")

    # sort order
    match sort_by:
        case "name":
            folders.sort(key=lambda x: x["name"].lower())
            files.sort(key=lambda x: x["name"].lower())
        case "natural":
            # no we will not be using `natsort`'s os_sorted
            folders: list[CWDObjectReturnDict] = natsorted(
                folders, key=lambda x: x["name"].lower()
            )
            files: list[CWDObjectReturnDict] = natsorted(
                files, key=lambda x: x["name"].lower()
            )
        case "created":
            folders.sort(key=lambda x: x["dir_entry"].stat().st_ctime_ns)
            files.sort(key=lambda x: x["dir_entry"].stat().st_ctime_ns)
        case "modified":
            folders.sort(key=lambda x: x["dir_entry"].stat().st_mtime_ns)
            files.sort(key=lambda x: x["dir_entry"].stat().st_mtime_ns)
        case "size":
            # no we will not be calculating the folder size
            folders.sort(key=lambda x: x["name"].lower())
            files.sort(key=lambda x: x["dir_entry"].stat().st_size)
        case "extension":
            # folders dont have extensions btw
            # and i will not count dot prepended folders
            folders.sort(key=lambda x: x["name"].lower())
            files.sort(key=get_extension_sort_key)

    if (
        return_nothing_if_this_returns_true is not None
        and return_nothing_if_this_returns_true()
    ):
        if globals().get("is_dev", False):
            dom_node.log("Cut off early before reversing results")
        return None, None
    if reverse:
        files.reverse()
        folders.reverse()

    if globals().get("is_dev", False):
        dom_node.log(f"Found {len(folders)} folders and {len(files)} files in {cwd}")
    return folders, files


def file_is_type(
    file_path: str,
) -> Literal["unknown", "symlink", "directory", "junction", "file"]:
    """Get a given path's type
    Args:
        file_path(str): The file path to check

    Returns:
        str: The string that says what type it is (unknown, symlink, directory, junction or file)
    """
    try:
        file_stat = os.lstat(file_path)
    except (OSError, FileNotFoundError):
        return "unknown"
    mode = file_stat.st_mode
    if stat.S_ISLNK(mode):
        return "symlink"
    elif stat.S_ISDIR(mode):
        return "directory"
    elif (
        os_type == "Windows"
        and hasattr(file_stat, "st_file_attributes")
        and file_stat.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
    ):
        return "junction"
    else:
        return "file"


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


@overload
def get_recursive_files(object_path: str) -> list[dict]: ...


@overload
def get_recursive_files(
    object_path: str, with_folders: Literal[False]
) -> list[dict]: ...


@overload
def get_recursive_files(
    object_path: str, with_folders: Literal[True]
) -> tuple[list[dict], list[dict]]: ...


def get_recursive_files(
    object_path: str, with_folders: bool = False
) -> list[dict] | tuple[list[dict], list[dict]]:
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
    if file_is_type(object_path) != "directory":
        if with_folders:
            return [
                {
                    "path": normalise(object_path),
                    "relative_loc": path.basename(object_path),
                }
            ], []
        return [
            {
                "path": normalise(object_path),
                "relative_loc": path.basename(object_path),
            }
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
                files.append({
                    "path": full_path,
                    "relative_loc": normalise(
                        path.relpath(full_path, object_path + "/..")
                    ),
                })
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


def _should_include_macos_mount_point(partition: "psutil._common.sdiskpart") -> bool:
    """
    Determine if a macOS mount point should be included in the drive list.

    Args:
        partition: A partition object from psutil.disk_partitions()

    Returns:
        bool: True if the mount point should be included, False otherwise.
    """
    # Skip virtual/system filesystem types:
    # - autofs: Automounter filesystem for automatic mounting/unmounting
    # - devfs: Device filesystem providing access to device files
    # - devtmpfs: Device temporary filesystem (like devfs but in tmpfs)
    # - tmpfs: Temporary filesystem stored in memory
    if partition.fstype in ("autofs", "devfs", "devtmpfs", "tmpfs"):
        return False

    # Skip system volumes under /System/Volumes/ (VM, Preboot, Update, Data, etc.)
    if partition.mountpoint.startswith("/System/Volumes/"):
        return False

    # Include everything else unless it's a system path (/System/, /dev, /private)
    return not partition.mountpoint.startswith(("/System/", "/dev", "/private"))


def _should_include_linux_mount_point(partition: "psutil._common.sdiskpart") -> bool:
    """
    Determine if a Linux/WSL mount point should be included in the drive list.

    Args:
        partition: A partition object from psutil.disk_partitions()

    Returns:
        bool: True if the mount point should be included, False otherwise.
    """
    # Skip virtual/system filesystem types:
    # - autofs: Automounter filesystem for automatic mounting/unmounting
    # - devfs: Device filesystem providing access to device files
    # - devtmpfs: Device temporary filesystem (like devfs but in tmpfs)
    # - tmpfs: Temporary filesystem stored in memory
    # - proc: Process information filesystem
    # - sysfs: System information filesystem
    # - cgroup2: Control group filesystem for resource management
    # - debugfs, tracefs, fusectl, configfs: Kernel debugging/configuration filesystems
    # - securityfs, pstore, bpf: Security and kernel subsystem filesystems
    # - hugetlbfs, mqueue: Specialized system filesystems
    # - devpts: Pseudo-terminal filesystem
    # - binfmt_misc: Binary format support filesystem
    if partition.fstype in (
        "autofs",
        "devfs",
        "devtmpfs",
        "tmpfs",
        "proc",
        "sysfs",
        "cgroup2",
        "debugfs",
        "tracefs",
        "fusectl",
        "configfs",
        "securityfs",
        "pstore",
        "bpf",
        "hugetlbfs",
        "mqueue",
        "devpts",
        "binfmt_misc",
    ):
        return False

    # Skip system paths that users typically don't access:
    # - /dev, /proc, /sys: System directories
    # - /run: Runtime data directory
    # - /boot: Boot partition (typically not accessed by users)
    # - /mnt/wslg: WSL GUI support directory
    # - /mnt/wsl: WSL system integration directory
    # Include everything else (root filesystem, /home, /media, Windows drives in WSL like /mnt/c, etc.)
    return not partition.mountpoint.startswith((
        "/dev",
        "/proc",
        "/sys",
        "/run",
        "/boot",
        "/mnt/wslg",
        "/mnt/wsl",
    ))


def get_mounted_drives() -> list[str]:
    """
    Get a list of mounted drives on the system.

    Returns:
        list[str]: List of mounted drives.
    """
    drives = []
    try:
        # get all partitions
        partitions = psutil.disk_partitions(all=True)

        if os_type == "Windows":
            # For Windows, return the drive letters
            drives = [
                normalise(p.mountpoint)
                for p in partitions
                if p.device and ":" in p.device and path.isdir(p.device)
            ]
        elif os_type == "Darwin":
            # For macOS, filter out system volumes and keep only user-relevant drives
            drives = [
                p.mountpoint
                for p in partitions
                if path.isdir(p.mountpoint) and _should_include_macos_mount_point(p)
            ]
        else:
            # For other Unix-like systems (Linux, WSL, etc.), filter out system mount points
            drives = [
                p.mountpoint
                for p in partitions
                if path.isdir(p.mountpoint) and _should_include_linux_mount_point(p)
            ]
    except Exception as e:
        if globals().get("is_dev", False):
            print(f"Error getting mounted drives: {e}\nUsing fallback method...")
        drives = [path.expanduser("~")]
    return drives


def match_mime_to_preview_type(
    mime_type: str,
) -> Literal["text", "image", "pdf", "archive", "folder", "remime"] | None:
    """
    Match a MIME type against configured rules to determine preview type.

    Args:
        mime_type: The MIME type to match (e.g., "text/plain", "image/png")

    Returns:
        str : The preview type ("text", "image", "pdf", "archive", "folder")
        None: None if no rule matches
    """
    for pattern, preview_type in config["interface"]["mime_rules"].items():
        if fnmatch.fnmatch(mime_type, pattern):
            return preview_type
    return None


class MimeResult(NamedTuple):
    method: Literal["basic", "puremagic", "file1"]
    mime_type: str
    content: str | None = None


def get_mime_type(
    file_path: str, ignore: list[Literal["basic", "puremagic", "file1"]] | None = None
) -> MimeResult | None:
    """
    Synchronous/Threaded wrapper to get the MIME type of a file.

    Args:
        file_path: Path to the file to check
        ignore: List of detection methods to skip

    Returns:
        MimeResult: The method used and the detected MIME type
        None: If the method is not available or failed
    """
    if ignore is None:
        ignore = []

    file_extension = path.splitext(file_path)[1].lower()

    # Read file bytes once, reuse for both puremagic and basic detection
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read(1024)  # Read first 1KiB
    except OSError:
        # Cannot open file at all
        return None

    # Step 1: Try puremagic (magic byte detection) first
    if "puremagic" not in ignore:
        try:
            puremagic_result: list[puremagic.PureMagicWithConfidence] = (
                puremagic.magic_string(file_bytes)
            )
            if puremagic_result:
                # If multiple matches exist, prefer one matching the file extension
                for match in puremagic_result:
                    if match.extension.lower() == file_extension and match.mime_type:
                        return MimeResult("puremagic", match.mime_type)
                # Otherwise, return first result with a mime type
                for match in puremagic_result:
                    if match.mime_type:
                        return MimeResult("puremagic", match.mime_type)
        except Exception:
            # puremagic failed, continue to next method
            pass

    # Step 2: Try decoding as UTF-8 text
    # If puremagic didn't recognise it, it might perhaps be a plain text file
    if "basic" not in ignore:
        try:
            content = file_bytes.decode("utf-8")
            return MimeResult(
                "basic", f"text/{guess_language(content, file_path)}", content
            )
        except UnicodeDecodeError:
            # Not valid UTF-8 text
            pass

    # Step 3: Fall back to file(1) command if available
    if "file1" not in ignore:
        try:
            process = subprocess.run(
                ["file", "--mime-type", "-b", file_path],
                capture_output=True,
                text=True,
                check=True,
                timeout=1,
            )
            mime_type = process.stdout.strip()
            if mime_type:
                return MimeResult("file1", mime_type)
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ):
            # file(1) command failed or is not available
            pass

    return None


def dump_exc(widget: DOMNode | None, exc: Exception | Traceback) -> str | None:
    """Dump an exception to the console for debugging purposes.

    Args:
        widget (DOMNode, None): The widget where the exception occurred.
        exc (Exception, Traceback): The exception to dump.

    Returns:
        str: The path to the log file where the exception was dumped.
    """
    from datetime import datetime

    from rich.panel import Panel

    from rovr.variables.maps import VAR_TO_DIR

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
        path.realpath(VAR_TO_DIR["CONFIG"]),
        "logs",
        f"{log_name}.log",
    )
    os.makedirs(path.dirname(dump_path), exist_ok=True)
    with open(dump_path, "a", encoding="utf-8") as file_log:
        # don't need to handle OS Error, Textual automatically chains errors
        error_log = Console(file=file_log, legacy_windows=True)
        # section it with time and date
        error_log.print(
            Panel(rich_traceback, title=f"Exception dumped on {str(datetime.now())}")
        )
    return dump_path
