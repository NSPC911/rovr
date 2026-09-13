import asyncio
import json
import os
from pathlib import Path
from typing import Any

import pytest

from rovr.functions import ipc_instances


class Writer:
    def __init__(self) -> None:
        self.data = b""
        self.closed = False

    def write(self, data: bytes) -> None:
        self.data += data

    async def drain(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        pass


@pytest.fixture
def ipc_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    directory = tmp_path / "ipc"
    monkeypatch.setattr(ipc_instances, "IPC_DIRECTORY", directory)
    return directory


def test_publish_and_unpublish_instance(
    monkeypatch: pytest.MonkeyPatch, ipc_directory: Path
) -> None:
    monkeypatch.setattr(ipc_instances.os, "getpid", lambda: 123)

    descriptor = ipc_instances.publish_instance(4321, "secret")

    assert descriptor == ipc_directory / "123.json"
    assert json.loads(descriptor.read_text()) == {
        "pid": 123,
        "port": 4321,
        "token": "secret",
    }
    if os.name != "nt":
        assert descriptor.stat().st_mode & 0o777 == 0o600
        assert ipc_directory.stat().st_mode & 0o777 == 0o700

    ipc_instances.unpublish_instance(descriptor, "wrong")
    assert descriptor.exists()
    ipc_instances.unpublish_instance(descriptor, "secret")
    assert not descriptor.exists()


@pytest.mark.parametrize(
    "descriptor",
    [
        {"pid": True, "port": 1234, "token": "secret"},
        {"pid": 123, "port": 0, "token": "secret"},
        {"pid": 123, "port": 65536, "token": "secret"},
        {"pid": 123, "port": 1234, "token": ""},
        {"pid": 123, "port": 1234},
    ],
)
def test_read_descriptor_rejects_invalid_values(
    ipc_directory: Path, descriptor: dict[str, Any]
) -> None:
    ipc_directory.mkdir()
    path = ipc_directory / "123.json"
    path.write_text(json.dumps(descriptor))
    path.chmod(0o600)

    assert ipc_instances._read_descriptor(path) is None


def test_read_descriptor_rejects_wrong_filename_and_permissions(
    ipc_directory: Path,
) -> None:
    ipc_directory.mkdir()
    descriptor = {"pid": 123, "port": 4321, "token": "secret"}
    wrong_name = ipc_directory / "other.json"
    wrong_name.write_text(json.dumps(descriptor))
    wrong_name.chmod(0o600)
    assert ipc_instances._read_descriptor(wrong_name) is None

    path = ipc_directory / "123.json"
    path.write_text(json.dumps(descriptor))
    path.chmod(0o644)
    if os.name != "nt":
        assert ipc_instances._read_descriptor(path) is None


async def test_probe_instance_reports_running(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "123.json"
    path.touch()
    reader = asyncio.StreamReader()
    reader.feed_data(b'{"ok": true, "out": {"pid": 123, "port": 4321}}\n')
    reader.feed_eof()
    writer = Writer()

    async def open_connection(_host: str, _port: int) -> tuple[Any, Any]:
        return reader, writer

    monkeypatch.setattr(ipc_instances.asyncio, "open_connection", open_connection)

    assert await ipc_instances._probe_instance(
        path, {"pid": 123, "port": 4321, "token": "secret"}
    ) == {"pid": 123, "status": "running"}
    assert json.loads(writer.data) == {
        "token": "secret",
        "action": "_show_urself",
        "args": [],
    }
    assert writer.closed
    assert path.exists()


async def test_probe_instance_removes_unreachable_descriptor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "123.json"
    path.touch()

    async def refuse(_host: str, _port: int) -> tuple[Any, Any]:
        raise ConnectionRefusedError

    monkeypatch.setattr(ipc_instances.asyncio, "open_connection", refuse)

    assert (
        await ipc_instances._probe_instance(
            path, {"pid": 123, "port": 4321, "token": "secret"}
        )
        is None
    )
    assert not path.exists()


async def test_probe_instance_keeps_timed_out_descriptor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "123.json"
    path.touch()

    async def time_out(_host: str, _port: int) -> tuple[Any, Any]:
        raise TimeoutError

    monkeypatch.setattr(ipc_instances.asyncio, "open_connection", time_out)

    assert await ipc_instances._probe_instance(
        path, {"pid": 123, "port": 4321, "token": "secret"}
    ) == {"pid": 123, "status": "unresponsive"}
    assert path.exists()


async def test_discover_instances_removes_invalid_and_sorts(
    monkeypatch: pytest.MonkeyPatch, ipc_directory: Path
) -> None:
    ipc_directory.mkdir()
    for pid in (20, 10):
        path = ipc_directory / f"{pid}.json"
        path.write_text(json.dumps({"pid": pid, "port": 4000 + pid, "token": "x"}))
        path.chmod(0o600)
    invalid = ipc_directory / "invalid.json"
    invalid.write_text("bad json")
    invalid.chmod(0o600)

    async def probe(
        _path: Path, descriptor: ipc_instances.Instance
    ) -> ipc_instances.InstanceInfo:
        return {"pid": descriptor["pid"], "status": "running"}

    monkeypatch.setattr(ipc_instances, "_probe_instance", probe)

    assert await ipc_instances.discover_instances() == [
        {"pid": 10, "status": "running"},
        {"pid": 20, "status": "running"},
    ]
    assert not invalid.exists()
