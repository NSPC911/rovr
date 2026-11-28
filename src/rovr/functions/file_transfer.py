import asyncio
import os
from contextlib import ExitStack
from itertools import batched
from typing import Any

from dbus_fast import Message, MessageType
from dbus_fast.aio import MessageBus


async def export_files(paths: list[str]) -> tuple[bytes, MessageBus]:
    """Export files read-only for a drag.

    Returns:
        The MIME payload and the connection that owns the transfer.
    """
    bus = MessageBus(negotiate_unix_fd=True)

    async def call(
        member: str, signature: str, body: list[Any], fds: list[int] | None = None
    ) -> list[Any]:
        reply = await bus.call(
            Message(
                destination="org.freedesktop.portal.Documents",
                path="/org/freedesktop/portal/documents",
                interface="org.freedesktop.portal.FileTransfer",
                member=member,
                signature=signature,
                body=body,
                unix_fds=fds or [],
            )
        )
        if reply is None or reply.message_type == MessageType.ERROR:
            raise OSError(reply.error_name if reply else "Missing portal reply")
        return reply.body

    try:
        async with asyncio.timeout(2):
            await bus.connect()
            (key,) = await call("StartTransfer", "a{sv}", [{}])
            for batch in batched(paths, 16):
                with ExitStack() as stack:
                    fds = []
                    for path in batch:
                        fd = os.open(path, os.O_PATH | os.O_CLOEXEC)
                        stack.callback(os.close, fd)
                        fds.append(fd)
                    await call(
                        "AddFiles", "saha{sv}", [key, list(range(len(fds))), {}], fds
                    )
        return key.encode() + b"\0", bus
    except BaseException:
        bus.disconnect()
        raise
