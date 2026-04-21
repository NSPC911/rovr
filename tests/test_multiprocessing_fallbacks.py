from pathlib import Path

import pytest
from PIL import Image

from rovr.functions import drive_workers, preview_utils


class _DummyConn:
    def close(self) -> None:
        pass


class _DummyQueue:
    def close(self) -> None:
        pass

    def empty(self) -> bool:
        return True

    def get_nowait(self) -> list[str]:
        return []


def test_get_mounted_drives_with_timeout_fallbacks_on_fds_to_keep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FailingProcess:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        def start(self) -> None:
            raise ValueError("bad value(s) in fds_to_keep")

    monkeypatch.setattr(drive_workers.multiprocessing, "Queue", lambda: _DummyQueue())
    monkeypatch.setattr(drive_workers.multiprocessing, "Process", _FailingProcess)
    monkeypatch.setattr(
        drive_workers,
        "get_mounted_drives",
        lambda _os_type: ["/fallback-drive"],
    )

    assert drive_workers.get_mounted_drives_with_timeout("Linux") == ["/fallback-drive"]


def test_get_mounted_drives_with_timeout_reraises_other_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FailingProcess:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        def start(self) -> None:
            raise ValueError("other value error")

    monkeypatch.setattr(drive_workers.multiprocessing, "Queue", lambda: _DummyQueue())
    monkeypatch.setattr(drive_workers.multiprocessing, "Process", _FailingProcess)

    with pytest.raises(ValueError, match="other value error"):
        drive_workers.get_mounted_drives_with_timeout("Linux")


def test_resample_file_fallbacks_on_fds_to_keep(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FailingProcess:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        def start(self) -> None:
            raise ValueError("bad value(s) in fds_to_keep")

    file_path = tmp_path / "img.png"
    Image.new("RGB", (10, 10), color="red").save(file_path)

    monkeypatch.setattr(preview_utils.multiprocessing, "Process", _FailingProcess)
    monkeypatch.setattr(
        preview_utils.multiprocessing,
        "Pipe",
        lambda: (_DummyConn(), _DummyConn()),
    )

    result = preview_utils.resample_file(file_path.as_posix())
    assert result is not None
    assert isinstance(result, Image.Image)
