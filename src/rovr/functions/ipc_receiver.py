from __future__ import annotations

import asyncio
import json
from functools import partial
from typing import TypedDict

from textual import work

from rovr.app import Application


class IPCReceiver(TypedDict):
    action: str
    args: list[str]


async def conn(
    self: Application, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    data = await reader.read(1024)
    parsed: IPCReceiver = json.loads(data.decode())
    match parsed["action"]:
        case "cd":
            ...
    # addr = writer.get_extra_info("peername")
    # self.log(f"Received {message!r} from {addr!r}")

    writer.write("{'ok': true, 'output': 'Message received'}".encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()


@work
async def start_server(self: Application) -> None:
    server = await asyncio.start_server(partial(conn, self), "127.0.0.1", 0)
    addr = server.sockets[0].getsockname()
    self.call_after_refresh(self.notify, f"Serving on {addr}")
    async with server:
        await server.serve_forever()
