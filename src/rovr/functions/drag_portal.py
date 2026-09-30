# some xdg shtick for drag and drop because flatpak is a thing people apparently use

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Sequence
from contextlib import suppress
from typing import Any

PORTAL_MIME = "application/vnd.portal.filetransfer"

_DESTINATION = "org.freedesktop.portal.Documents"
_PATH = "/org/freedesktop/portal/documents"
_INTERFACE = "org.freedesktop.portal.FileTransfer"
_FD_CHUNK = 16
_bus: Any = None


async def _call(
    member: str,
    signature: str = "",
    body: list[Any] | None = None,
    unix_fds: list[int] | None = None,
) -> list[Any]:
    from dbus_fast import Message, MessageType
    from dbus_fast.aio import MessageBus

    _bus: MessageBus | None = globals().get("_bus")
    if _bus is None or not _bus.connected:
        _bus = await MessageBus(negotiate_unix_fd=True).connect()

    reply = await asyncio.wait_for(
        _bus.call(
            Message(
                destination=_DESTINATION,
                path=_PATH,
                interface=_INTERFACE,
                member=member,
                signature=signature,
                body=body or [],
                unix_fds=unix_fds or [],
            )
        ),
        5,
    )
    if reply.message_type is MessageType.ERROR:
        raise RuntimeError(f"{reply.error_name}: {reply.body}")
    globals()["_bus"] = _bus
    return reply.body


async def _add_files(key: str, paths: Sequence[str]) -> None:
    for start in range(0, len(paths), _FD_CHUNK):
        descriptors: list[int] = []
        try:
            for path in paths[start : start + _FD_CHUNK]:
                descriptors.append(os.open(path, os.O_PATH | os.O_CLOEXEC))
            await _call(
                "AddFiles",
                "saha{sv}",
                [key, list(range(len(descriptors))), {}],
                descriptors,
            )
        finally:
            for descriptor in descriptors:
                os.close(descriptor)


class DragTransfer:
    def __init__(self, key: str) -> None:
        self.key = key

    @property
    def mime_data(self) -> bytes:
        return self.key.encode() + b"\0"

    async def stop(self) -> None:
        with suppress(Exception):
            await _call("StopTransfer", "s", [self.key])


async def export_files(paths: Sequence[str]) -> DragTransfer | None:
    """Register paths with the portal.

    Returns:
        A live transfer, or None when the portal is unavailable.
    """
    if sys.platform != "linux" or not paths:
        return None

    key = ""
    try:
        key = (await _call("StartTransfer", "a{sv}", [{}]))[0]
        await _add_files(key, paths)
    except Exception:
        if key:
            with suppress(Exception):
                await _call("StopTransfer", "s", [key])
        return None
    return DragTransfer(key)
