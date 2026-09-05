from __future__ import annotations

import asyncio
import json
import os
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
    out, err, ok = None, None, True
    match parsed["action"]:
        case "cd":
            from rovr.functions.path import ensure_existing_directory

            if "--exact" in parsed["args"] and len(parsed["args"]) == 1:
                ok = False
                err = "directory not provided"
            elif ("--exact" in parsed["args"] and len(parsed["args"]) > 2) or ("--exact" not in parsed["args"] and len(parsed["args"]) > 1):
                ok = False
                err = "too many paths given"
            path = parsed["args"][0] if parsed["args"][0] != "--exact" else parsed["args"][0]
            if not os.path.samefile(out := ensure_existing_directory(path), path) and len(parsed["args"]) == 2:
                ok = False
                err = "directory does not exist"
            else:
                self.cd(out)

    msg: dict[str, bool | str] = {"ok": ok}
    if ok and out is not None:
        msg["out"] = out
    elif err is not None:
        msg["err"] = err
    writer.write(json.dumps(msg).encode())

    # addr = writer.get_extra_info("peername")
    # self.log(f"Received {message!r} from {addr!r}")

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
