from __future__ import annotations

import multiprocessing
import re
import subprocess
from fnmatch import fnmatch
from multiprocessing.connection import Connection
from multiprocessing.synchronize import Event
from os import path
from time import monotonic
from typing import cast

from rovr.classes.config import RovrConfig
from rovr.functions.multiprocessing_utils import start_process

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

    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
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
    try:
        result = subprocess.run(
            ["df", "-P"], capture_output=True, text=True, check=True, timeout=2
        )
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        return ["/"]
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


def get_mounted_drives(platform: str, config: "RovrConfig") -> list[str]:
    """
    Worker function to get mounted drives - isolated from config imports.

    Args:
        platform: System platform ("win32", "darwin", "linux", etc.)

    Returns:
        list[str]: List of mounted drives.
    """
    drives = []
    try:
        if platform == "win32":
            raw_drives = _get_windows_drives()
        elif platform == "linux":
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
        if platform == "win32":
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
    queue: "multiprocessing.Queue[list[str]]", platform: str, config: "RovrConfig"
) -> None:
    """
    Multiprocessing worker that gets mounted drives and puts result in a queue.

    Args:
        queue: Multiprocessing queue to put the result into
        platform: System platform ("win32", "darwin", "linux", etc.)
        config: Application config dict
    """
    try:
        result = get_mounted_drives(platform, config)
        queue.put(result)
    except Exception:
        queue.put([])


def watch_mounted_drives(
    connection: Connection,
    stop: Event,
    platform: str,
    exclude_patterns: list[str],
    interval: float,
) -> None:
    config = cast(RovrConfig, {"settings": {"drive_exclude": exclude_patterns}})
    try:
        while not stop.is_set():
            connection.send(("started", monotonic()))
            connection.send(("result", get_mounted_drives(platform, config)))
            if stop.wait(interval):
                break
    except (BrokenPipeError, EOFError, OSError):
        pass
    finally:
        connection.close()


class DriveWatcher:
    """Poll a persistent drive scanner without waiting for filesystem access."""

    def __init__(
        self, platform: str, exclude_patterns: list[str], interval: float
    ) -> None:
        self.platform = platform
        self.exclude_patterns = list(exclude_patterns)
        self.interval = max(1.0, interval)
        self.process: multiprocessing.Process | None = None
        self.connection: Connection | None = None
        self.stop: Event | None = None
        self.deadline: float | None = None
        self.restart_at = 0.0

    def _start(self) -> None:
        receiver, sender = multiprocessing.Pipe(duplex=False)
        self.connection = receiver
        try:
            self.stop = multiprocessing.Event()
            self.process = multiprocessing.Process(
                target=watch_mounted_drives,
                args=(
                    sender,
                    self.stop,
                    self.platform,
                    self.exclude_patterns,
                    self.interval,
                ),
                daemon=True,
            )
            start_process(self.process)
            self.deadline = monotonic() + 10.0
        except BaseException:
            self.close()
            raise
        finally:
            sender.close()

    def poll(self) -> list[str] | None:
        """Poll the scanner and restart a dead or stalled worker.

        Returns:
            The latest drive list, or None if no scan has completed.
        """
        if self.process is None:
            if monotonic() < self.restart_at:
                return None
            self._start()
        assert self.connection is not None and self.process is not None
        drives = None
        disconnected = False
        try:
            while self.connection.poll():
                kind, value = self.connection.recv()
                if kind == "started":
                    self.deadline = value + 2.0
                elif kind == "result":
                    drives = value
                    self.deadline = None
        except (EOFError, OSError):
            disconnected = True
        if (
            disconnected
            or not self.process.is_alive()
            or (self.deadline is not None and monotonic() >= self.deadline)
        ):
            self.close()
            self.restart_at = monotonic() + self.interval
        return drives

    def close(self) -> None:
        """Stop the scanner and release its process and pipe handles."""
        if self.stop is not None:
            self.stop.set()
        if self.process is not None:
            if self.process.pid is not None:
                self.process.join(timeout=0.1)
                if self.process.is_alive():
                    self.process.terminate()
                    self.process.join(timeout=0.5)
                if self.process.is_alive():
                    self.process.kill()
                    self.process.join()
            self.process.close()
            self.process = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        self.stop = None
        self.deadline = None
