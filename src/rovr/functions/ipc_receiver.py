from __future__ import annotations

import asyncio
import json
import os
import secrets
from functools import partial
from typing import Any, Callable, Literal, TypedDict, cast

from textual import work

from rovr.app import Application
from rovr.functions.cwd import getcwd
from rovr.functions.ipc_sender import p  # used just in case when needing to resolve
from rovr.screens.yes_or_no import YesOrNo
from rovr.variables.constants import config


class IPCReceiver(TypedDict):
    token: str
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


def assemble_and_write(
    writer: asyncio.StreamWriter,
    ok: bool | str,
    out: Any = None,
    err: Any = None,
) -> None:
    msg: dict[str, Any] = {"ok": ok}
    if ok and out is not None:
        msg["out"] = out
    elif err is not None:
        msg["err"] = err
    writer.write(json.dumps(msg).encode() + b"\n")


async def conn(
    self: Application,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    token: str,
) -> None:
    data = await reader.readline()
    parsed: IPCReceiver = json.loads(data.decode())
    if parsed.get("token") != token:
        assemble_and_write(writer, False, err="unauthorized")
        return
    action, args = parsed["action"], parsed["args"]
    if action == "_show_urself":
        addr = writer.get_extra_info("sockname")
        writer.write(
            json.dumps({
                "ok": True,
                "out": {"pid": os.getpid(), "port": addr[1]},
            }).encode()
            + b"\n"
        )
        return
    out, err = None, None
    ok: bool | str = True
    match action:
        case "cd":
            if len(args) != 1:
                ok = False
                err = "too many arguments" if len(args) > 1 else "path not provided"
            elif not await check_permission(self, action, args):
                ok = False
                err = "denied"
            else:
                if os.path.samefile(getcwd(), p(args[0])):
                    out = getcwd()
                else:
                    worker = self.cd(p(args[0]))
                    await worker.wait()
                    out = getcwd()
        case "clipboard":
            if len(args) == 0:
                return assemble_and_write(
                    writer, False, None, "clipboard action not provided"
                )
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
                        avail = [p(path) for path in args[1:] if os.path.exists(path)]
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
                return assemble_and_write(
                    writer, False, None, "tab action not provided"
                )
            match args[0]:
                case "list":
                    if not await check_permission(self, action, args):
                        ok = False
                        err = "denied"
                    else:
                        active = self.tabWidget.active_tab
                        tabs: list[str] = []
                        out: dict[str, int | list[str]] = {"focused": 0, "tabs": tabs}

                        for i, tab in enumerate(self.tabWidget.tabs):
                            tabs.append(tab.directory)
                            if tab is active:
                                out["focused"] = i
                case "new":
                    if len(args) > 3:
                        ok = False
                        err = "too many arguments"
                    elif not await check_permission(self, action, args):
                        ok = False
                        err = "denied"
                    else:
                        # optional path argument, if not provided, use cwd
                        # also may contain --focus flag, if not provided, do not focus
                        focus = "--focus" in args
                        if len(args) == 2 and focus:
                            # use cwd
                            path = getcwd()
                        elif len(args) == 2 and not focus:
                            # use provided path
                            path = os.path.abspath(args[1])
                        elif len(args) == 3 and focus:
                            path = os.path.abspath(
                                args[1] if args[1] != "--focus" else args[2]
                            )
                        else:
                            path = getcwd()
                        tab = await self.tabWidget.add_tab(path, focus=focus)
                        # get index
                        index = self.tabWidget.tabs.index(tab)
                        out = {"index": index, "path": tab.directory}
                case "focus":
                    if len(args) != 2:
                        ok = False
                        err = (
                            "too many arguments"
                            if len(args) > 2
                            else "tab index not provided"
                        )
                    elif not await check_permission(self, action, args):
                        ok = False
                        err = "denied"
                    else:
                        try:
                            index = int(args[1])
                        except ValueError:
                            ok = False
                            err = "tab index must be an integer"
                        else:
                            if index < 0 or index >= len(self.tabWidget.tabs):
                                ok = False
                                err = "tab index out of range"
                            else:
                                self.tabWidget.action_activate_tab(index)
                case "close":
                    if len(args) > 2:
                        ok = False
                        err = "too many arguments"
                    elif not await check_permission(self, action, args):
                        ok = False
                        err = "denied"
                    elif self.tabWidget.active_tab is None:
                        ok = False
                        err = "no active tab somehow"
                    else:
                        try:
                            index = (
                                int(args[1])
                                if len(args) == 2
                                else self.tabWidget.tabs.index(
                                    self.tabWidget.active_tab
                                )
                            )
                        except ValueError:
                            ok = False
                            err = "tab index must be an integer"
                        else:
                            if index < 0 or index >= len(self.tabWidget.tabs):
                                ok = False
                                err = "tab index out of range"
                            elif index == 0 and len(self.tabWidget.tabs) == 1:
                                ok = False
                                err = "cannot close the only tab"
                            else:
                                await self.tabWidget.remove_tab(
                                    self.tabWidget.tabs[index]
                                )
                case "history":
                    if len(args) > 2:
                        ok = False
                        err = "too many arguments for history"
                    elif not await check_permission(self, action, args):
                        ok = False
                        err = "denied"
                    elif self.tabWidget.active_tab is None:
                        ok = False
                        err = "no active tab somehow"
                    else:
                        try:
                            index = (
                                int(args[1])
                                if len(args) == 2
                                else self.tabWidget.tabs.index(
                                    self.tabWidget.active_tab
                                )
                            )
                        except ValueError:
                            ok = False
                            err = "tab index must be an integer"
                        else:
                            if index < 0 or index >= len(self.tabWidget.tabs):
                                ok = False
                                err = "tab index out of range"
                            else:
                                tab = self.tabWidget.tabs[index]
                                out = {
                                    "directories": list(tab.session.directories),
                                    "historyIndex": tab.session.historyIndex,
                                }
                case _:
                    ok = False
                    err = "tab action is not valid"
        case "notify":
            from rovr.functions.ipc_sender import IPC_PARSER

            if not await check_permission(self, action, args):
                return assemble_and_write(writer, False, None, "denied")
            try:
                notification = IPC_PARSER.parse_args([action, *args])
            except SystemExit:
                ok = False
                err = "invalid notification arguments"
            else:
                self.notify(
                    notification.message,
                    title=notification.title or "",
                    severity=notification.severity or "information",
                    timeout=notification.timeout,
                    markup=notification.markup,
                )
        case "quit":
            if not await check_permission(self, action, args):
                ok = False
                err = "denied"
            else:
                worker = self.action_quit("--no-cd" not in args)
                await worker.wait()
                if self.return_code is None:
                    ok = False
                    err = "processes still running, denied"
        case "suspend":
            if not await check_permission(self, action, args):
                ok = False
                err = "denied"
            else:
                from textual.app import WINDOWS

                if WINDOWS:
                    ok = False
                    err = "suspend is not available on Windows"
                else:
                    self.action_suspend_process()
        case "ask":
            if not await check_permission(self, action, args):
                ok = False
                err = "denied"
            elif len(args) != 1:
                ok = False
                err = ("too many arguments" if args else "question not provided",)
            else:
                from rovr.screens import YesOrNo

                out: bool = await self.push_screen_wait(YesOrNo(args[0]))
        case _:
            ok = False
            err = "action is not valid"
    assemble_and_write(writer, ok, out, err)


async def wrapper(
    self: Application,
    token: str,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    # addr = writer.get_extra_info("peername")
    # self.log(f"Received {message!r} from {addr!r}")

    try:
        await conn(self, reader, writer, token)
    except Exception as exc:
        writer.write(
            json.dumps({
                "ok": False,
                "err": f"internal exception ({type(exc).__name__}): {exc}",
            }).encode()
            + b"\n"
        )
    finally:
        await writer.drain()
        writer.close()
        await writer.wait_closed()


@work
async def start_server(self: Application) -> None:
    from rovr.functions.ipc_instances import publish_instance, unpublish_instance

    token = secrets.token_urlsafe(32)
    server = await asyncio.start_server(partial(wrapper, self, token), "127.0.0.1", 0)
    addr = server.sockets[0].getsockname()
    async with server:
        descriptor = publish_instance(addr[1], token)
        # quite weird that globals().get("is_dev", False) is not working here
        if {"debug", "devtools"}.issubset(
            set(os.environ.get("TEXTUAL", "").split(","))
        ):
            self.call_after_refresh(self.notify, f"Serving on {addr}")
        os.environ["ROVR_IPC_PORT"] = str(addr[1])
        os.environ["ROVR_IPC_TOKEN"] = token
        try:
            await server.serve_forever()
        finally:
            unpublish_instance(descriptor, token)
            if os.environ.get("ROVR_IPC_TOKEN") == token:
                os.environ.pop("ROVR_IPC_PORT", None)
                os.environ.pop("ROVR_IPC_TOKEN", None)
