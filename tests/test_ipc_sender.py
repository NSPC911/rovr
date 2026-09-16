import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from rovr.functions import ipc_instances, ipc_sender


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


def test_p_expands_user_environment_and_relative_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("IPC_TEST_PATH", "folder")
    monkeypatch.setattr(
        ipc_sender.os.path, "expanduser", lambda path: path.replace("~", "home")
    )

    assert ipc_sender.p("~/$IPC_TEST_PATH") == str(tmp_path / "home" / "folder")


def test_prepare_cd_normalizes_existing_path(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()

    assert ipc_sender._prepare_message("cd", (str(target),)) == (str(target),)


def test_prepare_cd_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        ipc_sender._prepare_message("cd", (str(tmp_path / "missing"),))


def test_prepare_clipboard_and_new_tab_paths(tmp_path: Path) -> None:
    assert ipc_sender._prepare_message(
        "clipboard", ("copy", "--selection=replace", "one", "two")
    ) == (
        "copy",
        "--selection=replace",
        str(tmp_path / "one"),
        str(tmp_path / "two"),
    )
    assert ipc_sender._prepare_message("tab", ("new", "folder", "--focus")) == (
        "new",
        str(tmp_path / "folder"),
        "--focus",
    )


def test_prepare_list_instances_has_no_target() -> None:
    with pytest.raises(ValueError, match="does not target"):
        ipc_sender._prepare_message("list-instances", ())


@pytest.mark.parametrize(
    ("pid", "expected"),
    [(None, "ROVR_IPC_PID is not set"), ("not-a-pid", "Invalid ROVR_IPC_PID")],
)
async def test_send_message_rejects_missing_or_invalid_environment_pid(
    monkeypatch: pytest.MonkeyPatch, pid: str | None, expected: str
) -> None:
    errors: list[str] = []
    monkeypatch.delenv("ROVR_IPC_PID", raising=False)
    if pid is not None:
        monkeypatch.setenv("ROVR_IPC_PID", pid)
    monkeypatch.setattr(ipc_sender, "_print_error", errors.append)

    await ipc_sender.send_message(None, "quit")

    assert errors == [expected]


async def test_send_message_writes_authenticated_json_and_prints_response(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = asyncio.StreamReader()
    reader.feed_data(b'{"ok": true}\n')
    reader.feed_eof()
    writer = Writer()

    async def open_connection(host: str, port: int) -> tuple[asyncio.StreamReader, Any]:
        assert (host, port) == ("127.0.0.1", 4321)
        return reader, writer

    monkeypatch.setattr(
        ipc_instances,
        "instance_for_pid",
        lambda pid: {"pid": pid, "port": 4321, "token": "secret"},
    )
    monkeypatch.setattr(ipc_sender.asyncio, "open_connection", open_connection)

    await ipc_sender.send_message(123, "quit", "--no-cd")

    assert json.loads(writer.data) == {
        "token": "secret",
        "action": "quit",
        "args": ["--no-cd"],
    }
    assert json.loads(capsys.readouterr().out) == {"ok": True}
    assert writer.closed


async def test_send_message_reports_missing_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    errors: list[str] = []
    monkeypatch.setattr(ipc_instances, "instance_for_pid", lambda _pid: None)
    monkeypatch.setattr(ipc_sender, "_print_error", errors.append)

    await ipc_sender.send_message(123, "quit")

    assert errors == ["Could not find rovr instance with PID 123"]
