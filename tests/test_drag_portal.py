from pathlib import Path

import pytest

from rovr.functions import drag_portal


def test_export_is_skipped_without_paths() -> None:
    assert drag_portal.export_files([]) is None


def test_export_is_skipped_for_missing_paths(tmp_path: Path) -> None:
    assert drag_portal.export_files([(tmp_path / "missing.txt").as_posix()]) is None


def test_export_is_skipped_off_linux(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file = tmp_path / "file.txt"
    file.touch()
    monkeypatch.setattr(drag_portal.platform, "system", lambda: "Windows")
    assert drag_portal.export_files([file.as_posix()]) is None


def test_export_is_skipped_without_libsystemd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    file = tmp_path / "file.txt"
    file.touch()
    monkeypatch.setattr(drag_portal, "_library", lambda: None)
    assert drag_portal.export_files([file.as_posix()]) is None


def test_mime_data_is_the_nul_terminated_key() -> None:
    assert drag_portal.DragTransfer("aKey123").mime_data == b"aKey123\x00"


def test_stop_is_harmless_without_a_portal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(drag_portal, "_library", lambda: None)
    drag_portal.DragTransfer("aKey123").stop()


def _skip_without_portal(paths: list[str]) -> drag_portal.DragTransfer:
    transfer = drag_portal.export_files(paths)
    if transfer is None:
        pytest.skip("no session bus with the FileTransfer portal here")
    return transfer


def test_export_registers_a_session(tmp_path: Path) -> None:
    file = tmp_path / "file.txt"
    file.write_text("contents")
    transfer = _skip_without_portal([file.as_posix()])
    key = transfer.mime_data.removesuffix(b"\x00")
    assert key and not key.startswith(b"file://")
    transfer.stop()


def test_export_registers_more_files_than_one_message_holds(tmp_path: Path) -> None:
    files = []
    for index in range(drag_portal._FD_CHUNK + 1):
        file = tmp_path / f"file-{index}.txt"
        file.touch()
        files.append(file.as_posix())
    _skip_without_portal(files).stop()


def test_export_registers_directories(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    _skip_without_portal([tmp_path.as_posix()]).stop()
