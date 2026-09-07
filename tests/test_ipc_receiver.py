import asyncio
import json
from types import SimpleNamespace
from typing import Any, cast

import pytest

from rovr.functions import ipc_receiver


class Writer:
    def __init__(self, port: int = 4321) -> None:
        self.data = b""
        self.port = port
        self.closed = False
        self.drained = False

    def write(self, data: bytes) -> None:
        self.data += data

    def get_extra_info(self, _name: str) -> tuple[str, int]:
        return ("127.0.0.1", self.port)

    async def drain(self) -> None:
        self.drained = True

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        pass


def reader_for(message: Any) -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    reader.feed_data(json.dumps(message).encode() + b"\n")
    reader.feed_eof()
    return reader


def response(writer: Writer) -> dict[str, Any]:
    return json.loads(writer.data)


@pytest.mark.parametrize(("permission", "expected"), [("allow", True), ("deny", False)])
async def test_check_permission_uses_action_permission(
    monkeypatch: pytest.MonkeyPatch, permission: str, expected: bool
) -> None:
    monkeypatch.setattr(
        ipc_receiver,
        "config",
        {"settings": {"ipc": {"permissions": {"quit": permission}}}},
    )

    assert (
        await ipc_receiver.check_permission(cast(Any, object()), "quit", []) is expected
    )


async def test_check_permission_uses_subaction_and_prompts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ipc_receiver,
        "config",
        {"settings": {"ipc": {"permissions": {"clipboard.copy": "prompt"}}}},
    )
    screens: list[Any] = []

    def push_screen(screen: Any, callback: Any) -> None:
        screens.append(screen)
        callback(True)

    app = SimpleNamespace(push_screen=push_screen)

    assert await ipc_receiver.check_permission(
        cast(Any, app), "clipboard", ["copy", "a"]
    )
    assert screens


def test_assemble_and_write_selects_output_or_error() -> None:
    success = Writer()
    failure = Writer()

    ipc_receiver.assemble_and_write(cast(Any, success), True, out=0)
    ipc_receiver.assemble_and_write(cast(Any, failure), False, err="bad")

    assert response(success) == {"ok": True, "out": 0}
    assert response(failure) == {"ok": False, "err": "bad"}


async def test_conn_rejects_wrong_token() -> None:
    writer = Writer()

    await ipc_receiver.conn(
        cast(Any, object()),
        reader_for({"token": "wrong", "action": "quit", "args": []}),
        cast(Any, writer),
        "secret",
    )

    assert response(writer) == {"ok": False, "err": "unauthorized"}


async def test_conn_identifies_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    writer = Writer(9876)
    monkeypatch.setattr(ipc_receiver.os, "getpid", lambda: 123)

    await ipc_receiver.conn(
        cast(Any, object()),
        reader_for({"token": "secret", "action": "_show_urself", "args": []}),
        cast(Any, writer),
        "secret",
    )

    assert response(writer) == {
        "ok": True,
        "out": {"pid": 123, "port": 9876},
    }


@pytest.mark.parametrize(
    ("action", "args", "error"),
    [
        ("cd", [], "path not provided"),
        ("cd", ["one", "two"], "too many arguments"),
        ("clipboard", [], "clipboard action not provided"),
        ("clipboard", ["invalid"], "clipboard action is not valid"),
        ("tab", [], "tab action not provided"),
        ("tab", ["invalid"], "tab action is not valid"),
        ("invalid", [], "action is not valid"),
    ],
)
async def test_conn_validates_actions(action: str, args: list[str], error: str) -> None:
    writer = Writer()

    await ipc_receiver.conn(
        cast(Any, object()),
        reader_for({"token": "secret", "action": action, "args": args}),
        cast(Any, writer),
        "secret",
    )

    assert response(writer) == {"ok": False, "err": error}


async def test_conn_copies_existing_items(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    existing = tmp_path / "existing"
    existing.touch()
    calls: list[tuple[list[str], str]] = []
    clipboard = SimpleNamespace(
        copy_to_clipboard=lambda paths, selection: calls.append((paths, selection)),
        cut_to_clipboard=lambda _paths, _selection: None,
    )
    app = SimpleNamespace(Clipboard=clipboard)

    async def allow(_app: Any, _action: str, _args: list[str]) -> bool:
        return True

    monkeypatch.setattr(ipc_receiver, "check_permission", allow)
    writer = Writer()

    await ipc_receiver.conn(
        cast(Any, app),
        reader_for({
            "token": "secret",
            "action": "clipboard",
            "args": ["copy", "--selection=replace", str(existing), "missing"],
        }),
        cast(Any, writer),
        "secret",
    )

    assert calls == [([str(existing)], "reselect")]
    assert response(writer) == {"ok": True, "out": ["missing"]}


async def test_wrapper_reports_internal_errors_and_closes_writer() -> None:
    reader = asyncio.StreamReader()
    reader.feed_data(b"not json\n")
    reader.feed_eof()
    writer = Writer()

    await ipc_receiver.wrapper(cast(Any, object()), "secret", reader, cast(Any, writer))

    assert response(writer)["err"].startswith("internal exception (JSONDecodeError)")
    assert writer.drained
    assert writer.closed
