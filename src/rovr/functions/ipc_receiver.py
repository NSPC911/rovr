from __future__ import annotations

import asyncio
import json
import os
from functools import partial
from typing import Any, Callable, Literal, TypedDict, cast

from textual import work

from rovr.app import Application
from rovr.functions.cwd import getcwd
from rovr.header.tabs import TablineTab
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
                case "paste":
                    if not await check_permission(self, action, args):
                        ok = False
                        err = "denied"
                    else:
                        selected_items = (
                            self.Clipboard.selected
                        )  # dont include highlighted
                        to_copy, to_cut = (
                            [
                                item.path
                                for item in selected_items
                                if item.type_of_selection == "copy"
                            ],
                            [
                                item.path
                                for item in selected_items
                                if item.type_of_selection == "cut"
                            ],
                        )
                        # we will be ignoring the prompt that PasteButton
                        # does because we are assuming that ipc paste is
                        # a prompt (default) else the person kniws what
                        # they want from rovr
                        worker = self.app.query_one("ProcessContainer").paste_items(
                            to_copy, to_cut, getcwd()
                        )
                        await worker.wait()
                        out = {"copy": len(to_copy), "cut": len(to_cut)}
                case "copy" | "cut":
                    if not await check_permission(self, action, args):
                        ok = False
                        err = "denied"
                    else:
                        # what we want to do is check for flags (because we allow `--select` and `--reselect`)
                        # as well as existance of those paths (return paths that dont exist at all)
                        # for paths already in clipboard, ignore, unless either flag is included
                        flags = {arg for arg in args if arg.startswith("--")}
                        avail = [path for path in args[1:] if os.path.exists(path)]
                        out: list[str] = [
                            path
                            for path in args[1:]
                            if not (path in avail or path.startswith("--"))
                        ]
                        if not avail:
                            ok = False
                            err = "no paths provided"
                        if "--reselect" in flags and "--select" in flags:
                            ok = False
                            err = "cannot use both --select and --reselect"
                        if avail:
                            func: Callable[
                                [list[str], Literal["reselect", "select", "no"]], None
                            ] = (
                                self.Clipboard.copy_to_clipboard
                                if args[0] == "copy"
                                else self.Clipboard.cut_to_clipboard
                            )
                            func(
                                avail,
                                "select"
                                if "--select" in flags
                                else ("reselect" if "--reselect" in flags else "no"),
                            )
                case _:
                    ok = False
                    err = "clipboard action is not valid"
        case "tab":
            if len(args) == 0:
                ok = False
                err = "tab action not provided"
            match args[0]:
                case "list":
                    if not await check_permission(self, action, args):
                        ok = False
                        err = "denied"
                    else:
                        active = self.tabWidget.active_tab
                        tabs: list[str] = []
                        out: dict[str, int | list[str]] = {"focused": 0, "tabs": tabs}

                        for i, tab in enumerate(self.tabWidget.query(TablineTab)):
                            tabs.append(tab.directory)
                            if tab is active:
                                out["focused"] = i

    msg: dict[str, Any] = {"ok": ok}
    if ok and out is not None:
        msg["out"] = out
    elif err is not None:
        msg["err"] = err
    writer.write(json.dumps(msg).encode())


async def wrapper(
    self: Application, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    # addr = writer.get_extra_info("peername")
    # self.log(f"Received {message!r} from {addr!r}")

    try:
        await conn(self, reader, writer)
    except Exception as exc:
        writer.write(
            json.dumps({
                "ok": False,
                "err": f"internal exception ({type(exc).__name__}): {exc}",
            }).encode()
        )
    finally:
        await writer.drain()
        writer.close()
        await writer.wait_closed()


@work
async def start_server(self: Application) -> None:
    server = await asyncio.start_server(partial(wrapper, self), "127.0.0.1", 0)
    addr = server.sockets[0].getsockname()
    self.call_after_refresh(self.notify, f"Serving on {addr}")
    os.environ["ROVR_IPC_PORT"] = str(addr[1])
    async with server:
        await server.serve_forever()
