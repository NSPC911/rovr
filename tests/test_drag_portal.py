import os
import sys
from pathlib import Path
from typing import Any

import pytest

from rovr.functions import drag_portal

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux portal")


@pytest.mark.asyncio
async def test_export_files_batches_descriptors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = []
    for index in range(drag_portal._FD_CHUNK + 1):
        file = tmp_path / str(index)
        file.touch()
        paths.append(str(file))

    calls: list[tuple[str, list[Any], list[int]]] = []

    async def call(
        member: str,
        signature: str = "",
        body: list[Any] | None = None,
        unix_fds: list[int] | None = None,
    ) -> list[Any]:
        assert signature in {"a{sv}", "saha{sv}"}
        descriptors = unix_fds or []
        for descriptor in descriptors:
            os.fstat(descriptor)
        calls.append((member, body or [], descriptors.copy()))
        return ["key"] if member == "StartTransfer" else []

    monkeypatch.setattr(drag_portal, "_call", call)

    transfer = await drag_portal.export_files(paths)

    assert transfer is not None
    assert transfer.mime_data == b"key\0"
    assert [call[0] for call in calls] == ["StartTransfer", "AddFiles", "AddFiles"]
    assert calls[1][1][1] == list(range(drag_portal._FD_CHUNK))
    assert calls[2][1][1] == [0]
    for _, _, descriptors in calls[1:]:
        for descriptor in descriptors:
            with pytest.raises(OSError):
                os.fstat(descriptor)


@pytest.mark.asyncio
async def test_failed_export_stops_transfer(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def call(member: str, *_args: Any, **_kwargs: Any) -> list[Any]:
        calls.append(member)
        if member == "StartTransfer":
            return ["key"]
        if member == "AddFiles":
            raise RuntimeError
        return []

    monkeypatch.setattr(drag_portal, "_call", call)

    assert await drag_portal.export_files([__file__]) is None
    assert calls == ["StartTransfer", "AddFiles", "StopTransfer"]
