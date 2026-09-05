from __future__ import annotations

import asyncio
import json
import os
from functools import partial
from typing import Any, TypedDict, cast

from textual import work

from rovr.app import Application
from rovr.screens.yes_or_no import YesOrNo
from rovr.variables.constants import config


class IPCReceiver(TypedDict):
    action: str
    args: list[str]


async def check_permission(self: Application, action: str, args: list[str]) -> bool:
    permissions = cast(
        dict[str, str], cast(dict[str, Any], config)["settings"]["ipc"]["permissions"]
    )
    permission_key = action
    if permission_key not in permissions and args:
        permission_key += f".{args[0]}"
        args = args[1:]
    permission = permissions.get(permission_key, "deny")

    if permission != "prompt":
        return permission == "allow"

    response = asyncio.get_running_loop().create_future()
    self.push_screen(
        YesOrNo(
            f"Allow IPC action '{permission_key}'?\nArguments: {json.dumps(args)}",
            border_title="IPC Permission",
        ),
        response.set_result,
    )
    return await response


async def conn(
    self: Application, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    data = await reader.read(1024)
    parsed: IPCReceiver = json.loads(data.decode())
    action, args = parsed["action"], parsed["args"]
    out, err = None, None
    ok: bool | str = True
    match action:
        case "cd":
            from rovr.functions.path import ensure_existing_directory

            exact = "--exact" in args
            paths = [arg for arg in args if arg != "--exact"]
            if not paths:
                ok = False
                err = "directory not provided"
            elif len(paths) > 1 or len(args) != len(paths) + exact:
                ok = False
                err = "too many paths given"
            elif exact and not os.path.isdir(paths[0]):
                ok = False
                err = "directory does not exist"
            elif not await check_permission(self, action, args):
                ok = False
                err = "denied"
            else:
                self.cd(out := ensure_existing_directory(paths[0]))
        case "clipboard":
            if len(args) == 0:
                ok = False
                err = "clipboard action not provided"
            match args[0]:
                case "list":
                    if not await check_permission(self, action, args):
                        ok = False
                        err = "denied"
                    else:
                        options = self.Clipboard.options
                        selected = self.Clipboard.selected
                        # we need to parse this as well yay
                        out = [
                            {
                                "path": option.value.path,
                                "type": option.value.type_of_selection,
                                "selected": option.value in selected,
                            }
                            for option in options
                        ]

    msg: dict[str, bool | str | list] = {"ok": ok}
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
    os.environ["ROVR_IPC_PORT"] = str(addr[1])
    async with server:
        await server.serve_forever()
