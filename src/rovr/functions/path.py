import os
import platform
import stat
import subprocess
from os import path

import psutil
from lzstring import LZString
from rich.console import Console

from rovr.functions.icons import get_icon_for_file, get_icon_for_folder

lzstring = LZString()
pprint = Console().print


config = {}
pins = {}


def normalise(location: str | bytes) -> str | bytes:
    """'Normalise' the path
    Args:
        location (str): The location to the item

    Returns:
        str: A normalised path
    """
    # path.normalise fixes the relative references
    # replace \\ with / on windows
    # by any chance if somehow a \\\\ was to enter, fix that
    return path.normpath(location).replace("\\", "/").replace("//", "/")


# Okay so the reason why I have wrapper functions is
# I was messing around with different LZString options
# and Encoded URI Component seems to best option. I've just
# left it here, in case we can switch to something like
# base 64 because Encoded URI Component can get quite long
# very fast, which isn't really the purpose of LZString
def compress(text: str) -> str:
    return lzstring.compressToEncodedURIComponent(text)


def decompress(text: str) -> str:
    return lzstring.decompressFromEncodedURIComponent(text)


def open_file(filepath: str) -> None:
    """Cross-platform function to open files with their default application.

    Args:
        filepath (str): Path to the file to open
    """
    system = platform.system().lower()

    try:
        match system:
            case "windows":
                os.startfile(filepath)
            case "darwin":  # macOS
                subprocess.run(["open", filepath], check=True)
            case _:  # Linux and other Unix-like
                subprocess.run(["xdg-open", filepath], check=True)
    except Exception as e:
        print(f"Error opening file: {e}")


def get_cwd_object(cwd: str | bytes, show_hidden: bool = False) -> tuple[list[dict], list[dict]]:
    """
    Get the objects (files and folders) in a provided directory
    Args:
        cwd(str): The working directory to check
        show_hidden(bool): Whether to include hidden files/folders (starting with .)

    Returns:
        folders(list[dict]): A list of dictionaries, containing "name" as the item's name and "icon" as the respective icon
        files(list[dict]): A list of dictionaries, containing "name" as the item's name and "icon" as the respective icon
    """
    folders, files = [], []
    try:
        listed_dir = os.scandir(cwd)
    except (PermissionError, FileNotFoundError, OSError):
        print(f"PermissionError: Unable to access {cwd}")
        return [PermissionError], [PermissionError]
    for item in listed_dir:
        # Skip hidden files if show_hidden is False (macOS only)
        if not show_hidden and item.name.startswith('.') and platform.system() == "Darwin":
            continue
            
        if item.is_dir():
            folders.append({
                "name": f"{item.name}",
                "icon": get_icon_for_folder(item.name),
                "dir_entry": item,
            })
        else:
            files.append({
                "name": item.name,
                "icon": get_icon_for_file(item.name),
                "dir_entry": item,
            })
    # Sort folders and files properly
    folders.sort(key=lambda x: x["name"].lower())
    files.sort(key=lambda x: x["name"].lower())
    print(f"Found {len(folders)} folders and {len(files)} files in {cwd}")
    return folders, files


def file_is_type(file_path: str) -> str:
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
        platform.system() == "Windows"
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
    if path.isfile(path.realpath(object_path)) or path.islink(
        path.realpath(object_path)
    ):
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


def get_mounted_drives() -> list:
    """
    Get a list of mounted drives on the system.

    Returns:
        list: List of mounted drives.
    """
    drives = []
    try:
        # get all partitions
        partitions = psutil.disk_partitions(all=False)

        if platform.system() == "Windows":
            # For Windows, return the drive letters
            drives = [
                normalise(p.mountpoint)
                for p in partitions
                if p.device and ":" in p.device
            ]
        elif platform.system() == "Darwin":
            # For macOS, filter out system volumes and keep only user-relevant drives
            drives = [
                p.mountpoint for p in partitions if _should_include_macos_mount_point(p)
            ]
        else:
            # For other Unix-like systems (Linux, WSL, etc.), filter out system mount points
            drives = [
                p.mountpoint for p in partitions if _should_include_linux_mount_point(p)
            ]
    except Exception as e:
        print(f"Error getting mounted drives: {e}")
        print("Using fallback method")
        drives = [path.expanduser("~")]
    return drives
