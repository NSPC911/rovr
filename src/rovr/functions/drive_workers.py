from __future__ import annotations

import multiprocessing
from os import path

try:
    import psutil
    import psutil._ntuples
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
        partitions = psutil.disk_partitions(all=False)

        if os_type == "Windows":
            # For Windows, return the drive letters
            drives = [
                normalise(p.mountpoint)
                for p in partitions
                if p.device and ":" in p.device and path.isdir(p.device)
            ]
        else:
            drives = [
                normalise(p.mountpoint) for p in partitions if path.isdir(p.mountpoint)
            ]
    except Exception as exc:
        if globals().get("is_dev", False):
            print(f"Error getting mounted drives: {exc}\nReturning nothing...")
        # Fallback to home directory on error
        if os_type == "Windows":
            from string import ascii_uppercase

            drives: list[str] = [
                f"{letter}:/"
                for letter in ascii_uppercase
                if path.isdir(f"{letter}:\\")
            ]
        else:
            drives = ["/"]  # root should definitely exist right
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
