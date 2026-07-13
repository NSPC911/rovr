from __future__ import annotations

import multiprocessing
import re
import subprocess
from fnmatch import fnmatch
from os import path

from rovr.classes.config import RovrConfig

_OCTAL_ESCAPE = re.compile(r"\\([0-7]{3})")


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


def _get_windows_drives() -> list[str]:
    import ctypes

    bitmask = ctypes.windll.kernel32.GetLogicalDrives()  # type: ignore[attr-defined]
    return [f"{chr(ord('A') + i)}:/" for i in range(26) if bitmask & (1 << i)]


def _get_linux_drives() -> list[str]:
    # raises OSError if procfs isn't readable, so callers can fall back to `df`
    physical_fstypes: set[str] = set()
    with open("/proc/filesystems") as f:
        for line in f:
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 2:
                continue
            nodev, fstype = fields
            if nodev != "nodev" or fstype in ("zfs", "btrfs"):
                physical_fstypes.add(fstype)

    drives = []
    with open("/proc/mounts") as f:
        for line in f:
            fields = line.split()
            if len(fields) < 3:
                continue
            device, mountpoint, fstype = fields[0], fields[1], fields[2]
            if device in ("", "none") or fstype not in physical_fstypes:
                continue
            drives.append(
                _OCTAL_ESCAPE.sub(lambda m: chr(int(m.group(1), 8)), mountpoint)
            )
    return drives


def _get_posix_drives() -> list[str]:
    # used on macOS, Android/Termux, BSD, and as a Linux fallback when procfs
    # isn't readable; -P avoids df wrapping long device paths across lines
    result = subprocess.run(["df", "-P"], capture_output=True, text=True, check=True)
    drives = []
    for line in result.stdout.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 6:
            continue
        device = fields[0]
        mountpoint = " ".join(fields[5:])
        if not device.startswith("/dev/"):
            continue
        drives.append(mountpoint)
    return drives


def get_mounted_drives(os_type: str, config: "RovrConfig") -> list[str]:
    """
    Worker function to get mounted drives - isolated from config imports.

    Args:
        os_type: Operating system type ("Windows", "Darwin", or other)

    Returns:
        list[str]: List of mounted drives.
    """
    drives = []
    try:
        if os_type == "Windows":
            raw_drives = _get_windows_drives()
        elif os_type == "Linux":
            try:
                raw_drives = _get_linux_drives()
            except OSError:
                raw_drives = _get_posix_drives()
        else:
            raw_drives = _get_posix_drives()
        drives = [normalise(d) for d in raw_drives if path.isdir(d)]
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
    exclude_patterns: list[str] = config.get("settings", {}).get("drive_exclude", [])
    if exclude_patterns:
        drives = [d for d in drives if not any(fnmatch(d, p) for p in exclude_patterns)]
    return drives


def get_mounted_drives_worker(
    queue: "multiprocessing.Queue[list[str]]", os_type: str, config: "RovrConfig"
) -> None:
    """
    Multiprocessing worker that gets mounted drives and puts result in a queue.

    Args:
        queue: Multiprocessing queue to put the result into
        os_type: Operating system type ("Windows", "Darwin", or other)
        config: Application config dict
    """
    try:
        result = get_mounted_drives(os_type, config)
        queue.put(result)
    except Exception:
        queue.put([])
