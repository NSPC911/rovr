import ctypes
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest

from rovr.classes.config import RovrConfig
from rovr.functions import drive_workers


@pytest.fixture
def config() -> RovrConfig:
    return cast("RovrConfig", {"settings": {"drive_exclude": []}})


def test_get_mounted_drives_filters_non_directory_posix_mounts(
    monkeypatch: pytest.MonkeyPatch,
    config: RovrConfig,
) -> None:
    """
    Ensure get_mounted_drives filters out mountpoints that are not directories
    on POSIX-like systems.
    """
    # Mix of directory and non-directory mountpoints
    monkeypatch.setattr(
        drive_workers,
        "_get_posix_drives",
        lambda: ["/", "/mnt/usb", "/not_a_directory"],
    )

    def fake_isdir(path: str) -> bool:
        # Treat "/not_a_directory" as a non-directory mountpoint
        return path != "/not_a_directory"

    monkeypatch.setattr(drive_workers.path, "isdir", fake_isdir)

    drives = drive_workers.get_mounted_drives("Darwin", config)

    assert drives == ["/", "/mnt/usb"]


def test_get_mounted_drives_filters_non_directory_linux_mounts(
    monkeypatch: pytest.MonkeyPatch,
    config: RovrConfig,
) -> None:
    """
    Ensure get_mounted_drives filters out mountpoints that are not directories
    on Linux.
    """
    monkeypatch.setattr(
        drive_workers,
        "_get_linux_drives",
        lambda: ["/", "/media/usb", "/proc", "/not_a_directory"],
    )

    def fake_isdir(path: str) -> bool:
        # Simulate "/not_a_directory" being invalid
        return path != "/not_a_directory"

    monkeypatch.setattr(drive_workers.path, "isdir", fake_isdir)

    drives = drive_workers.get_mounted_drives("Linux", config)

    assert drives == ["/", "/media/usb", "/proc"]


def test_normalise_joins_and_fixes_slashes() -> None:
    assert drive_workers.normalise("/foo", "bar") == "/foo/bar"


def test_normalise_no_args_raises() -> None:
    with pytest.raises(ValueError):
        drive_workers.normalise()


def test_get_linux_drives_filters_pseudo_filesystems(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    filesystems = tmp_path / "filesystems"
    filesystems.write_text("nodev\tsysfs\nnodev\ttmpfs\n\text4\nnodev\tzfs\n")
    mounts = tmp_path / "mounts"
    mounts.write_text(
        "sysfs /sys sysfs rw 0 0\n"
        "tmpfs /run tmpfs rw 0 0\n"
        "/dev/sda1 / ext4 rw 0 0\n"
        "tank /tank zfs rw 0 0\n"
        "none /none none rw 0 0\n"
        "/dev/sda2 /mnt/with\\040space ext4 rw 0 0\n"
    )
    real_open = open

    def fake_open(path: str, *args: object, **kwargs: object) -> object:
        if path == "/proc/filesystems":
            return real_open(filesystems)
        if path == "/proc/mounts":
            return real_open(mounts)
        raise AssertionError(path)

    monkeypatch.setattr("builtins.open", fake_open)

    drives = drive_workers._get_linux_drives()

    assert drives == ["/", "/tank", "/mnt/with space"]


def test_get_posix_drives_filters_non_device_mounts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    df_output = (
        "Filesystem     512-blocks      Used Available Capacity  Mounted on\n"
        "/dev/disk3s1s1  971350180 486312345 400000000    56%    /\n"
        "tmpfs                   0         0         0     0%    /private/tmp\n"
        "/dev/disk3s5   1000000000 200000000 700000000    23%    /System/Volumes/Data\n"
    )
    mock_result = MagicMock(stdout=df_output)
    monkeypatch.setattr(drive_workers.subprocess, "run", lambda *a, **k: mock_result)

    drives = drive_workers._get_posix_drives()

    assert drives == ["/", "/System/Volumes/Data"]


def test_get_windows_drives_reads_bitmask(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_kernel32 = MagicMock()
    # bits 0 (A) and 2 (C) set
    fake_kernel32.GetLogicalDrives.return_value = 0b101
    fake_windll = MagicMock(kernel32=fake_kernel32)
    monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)

    drives = drive_workers._get_windows_drives()

    assert drives == ["A:/", "C:/"]


def test_get_mounted_drives_applies_exclude_patterns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(drive_workers, "_get_posix_drives", lambda: ["/", "/mnt/usb"])
    monkeypatch.setattr(drive_workers.path, "isdir", lambda p: True)

    config = cast("RovrConfig", {"settings": {"drive_exclude": ["/mnt/*"]}})
    drives = drive_workers.get_mounted_drives("Darwin", config)

    assert drives == ["/"]


def test_get_mounted_drives_falls_back_on_exception(
    monkeypatch: pytest.MonkeyPatch, config: RovrConfig
) -> None:
    def boom() -> list[str]:
        raise RuntimeError("no drives for you")

    monkeypatch.setattr(drive_workers, "_get_posix_drives", boom)

    drives = drive_workers.get_mounted_drives("Darwin", config)

    assert drives == ["/"]


def test_get_mounted_drives_linux_falls_back_to_posix_on_oserror(
    monkeypatch: pytest.MonkeyPatch, config: RovrConfig
) -> None:
    monkeypatch.setattr(
        drive_workers,
        "_get_linux_drives",
        lambda: (_ for _ in ()).throw(OSError("no procfs")),
    )
    monkeypatch.setattr(drive_workers, "_get_posix_drives", lambda: ["/data"])
    monkeypatch.setattr(drive_workers.path, "isdir", lambda p: True)

    drives = drive_workers.get_mounted_drives("Linux", config)

    assert drives == ["/data"]


def test_get_mounted_drives_windows_normalises_and_applies_exclusions(
    monkeypatch: pytest.MonkeyPatch,
    config: RovrConfig,
) -> None:
    monkeypatch.setattr(
        drive_workers,
        "_get_windows_drives",
        lambda: ["C:/", "D:/", "E:/Data", "F:", "G:/"],
    )

    def fake_isdir(path_str: str) -> bool:
        return any(path_str.startswith(drive) for drive in ["C:/", "D:/", "E:/"])

    monkeypatch.setattr(drive_workers.path, "isdir", fake_isdir)

    config["settings"]["drive_exclude"] = ["E:/*"]

    drives = drive_workers.get_mounted_drives("Windows", config)

    assert drives == ["C:/", "D:/"]
