import multiprocessing
from os import path

try:
    import psutil
except ModuleNotFoundError:
    from typing import Callable

    class _Psutil:
        def __getatt__(self) -> Callable[[], list]:
            return lambda: []

    psutil = _Psutil()  # ty: ignore[invalid-assignment]


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
    # Skip all uncommon places but include:
    # - /run/media, /media: removable media
    # - /mnt: common mounts
    # Some things that should be excluded:
    # - /mnt/wslg: WSL GUI support directory
    # - /mnt/wsl: WSL system integration directory
    return partition.mountpoint.startswith((
        "/run/media/",
        "/media/",
        "/mnt/",
    )) and not partition.mountpoint.startswith((
        "/mnt/wslg",
        "/mnt/wsl",
    ))


def get_mounted_drives(os_type: str) -> list[str]:
    """
    Worker function to get mounted drives - isolated from config imports.

    Args:
        os_type: Operating system type ("Windows", "Darwin", or other)

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
    except Exception as exc:
        if globals().get("is_dev", False):
            print(f"Error getting mounted drives: {exc}\nReturning nothing...")
        # Fallback to home directory on error
        drives = []
    return drives


def get_mounted_drives_worker(
    queue: "multiprocessing.Queue[list[str]]", os_type: str
) -> None:
    """
    Multiprocessing worker that gets mounted drives and puts result in a queue.

    Args:
        queue: Multiprocessing queue to put the result into
        os_type: Operating system type ("Windows", "Darwin", or other)
    """
    try:
        result = get_mounted_drives(os_type)
        queue.put(result)
    except Exception:
        queue.put([])
