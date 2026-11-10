from __future__ import annotations

import asyncio
import json
import os
import secrets
from functools import partial
from typing import Any, Literal, TypedDict, cast

from textual import work
from textual.worker import Worker

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
            f"Allow IPC action '{permission_key}'?"
            + (f"\nArguments: {json.dumps(args)}" if args else ""),
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
    try:
        data = await asyncio.wait_for(reader.readline(), timeout=1)
    except asyncio.TimeoutError:
        assemble_and_write(writer, False, err="no newline")
        return
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
    ok: bool = True

    async def checker() -> bool:
        nonlocal ok, err
        if not (ok := await check_permission(self, action, args)):
            err = "denied"
        return ok

    match action:
        case "cd":
            if len(args) != 1:
                ok = False
                err = "too many arguments" if len(args) > 1 else "path not provided"
            elif await checker():
                try:
                    if os.path.samefile(getcwd(), p(args[0])):
                        out = getcwd()
                    else:
                        worker = self.cd(p(args[0]))
                        if isinstance(worker, Worker):
                            await worker.wait()
                            out = getcwd()
                        elif isinstance(worker, BaseException):
                            raise worker
                        else:
                            ok = False
                            err = "app possibly shutting down"
                except Exception as exc:
                    ok = False
                    err = f"{type(exc).__name__}: {exc}"
        case "clipboard":
            if len(args) == 0:
                return assemble_and_write(
                    writer, False, None, "clipboard action not provided"
                )
            match args[0]:
                case "list":
                    if await checker():
                        items = self.Clipboard.options
                        out = [
                            {
                                "type": item.type_of_selection,
                                "paths": item.paths,
                                "active": item.active,
                            }
                            for item in items
                        ]
                case "paste":
                    if await checker():
                        # dont include highlighted
                        type_of_selection, paths = self.Clipboard.selected
                        # we will be ignoring the prompt that PasteButton
                        # does because we are assuming that ipc paste is
                        # a prompt (default) else the person kniws what
                        # they want from rovr
                        if type_of_selection is None or not paths:
                            ok = False
                            err = "no clipboard entry selected"
                        else:
                            worker: Worker[None | Literal[True]] = self.app.query_one(
                                "ProcessContainer"
                            ).paste_items(
                                type_of_selection,
                                paths,
                                getcwd(),
                            )
                            await worker.wait()
                            if ok := bool(worker.result):
                                out = {
                                    "copy": len(paths)
                                    if type_of_selection == "copy"
                                    else 0,
                                    "cut": len(paths)
                                    if type_of_selection == "cut"
                                    else 0,
                                }
                            else:
                                err = "user intervened"
                case "copy" | "cut":
                    if await checker():
                        select = "--select" in args
                        avail = list(
                            dict.fromkeys(
                                p(path)
                                for path in args[1:]
                                if not path.startswith("--") and os.path.exists(path)
                            )
                        )
                        out: list[str] = [
                            path
                            for path in args[1:]
                            if not (path in avail or path.startswith("--"))
                        ]
                        w = (
                            self.Clipboard.copy_to_clipboard
                            if args[0] == "copy"
                            else self.Clipboard.cut_to_clipboard
                        )(avail, select)
                        if isinstance(w, Worker):
                            await w.wait()
                case "remove" | "select":
                    if await checker():
                        try:
                            index = int(args[1])
                        except (IndexError, ValueError):
                            ok = False
                            err = "index must be an integer"
                        else:
                            if index < 0 or index >= len(self.Clipboard.options):
                                ok = False
                                err = "index out of range"
                            elif args[0] == "remove":
                                await self.Clipboard.remove_block(index)
                            else:
                                self.Clipboard.set_index(index)
                case "unselect":
                    if await checker():
                        if self.Clipboard._active is None:
                            ok = False
                            err = "no selection to unselect"
                        else:
                            try:
                                out = self.Clipboard.options.index(self.Clipboard._active)
                                self.Clipboard.set_index(None)
                            except ValueError:
                                ok = False
                                err = "active selection not found somehow"
                case _:
                    ok = False
                    err = "clipboard action is not valid"
        case "tab":
            if len(args) == 0:
                return assemble_and_write(writer, False, None, "tab action not provided")
            match args[0]:
                case "list":
                    if await checker():
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
                    elif await checker():
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
                    elif await checker():
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
                    elif self.tabWidget.active_tab is None:
                        ok = False
                        err = "no active tab somehow"
                    elif await checker():
                        try:
                            index = (
                                int(args[1])
                                if len(args) == 2
                                else self.tabWidget.tabs.index(self.tabWidget.active_tab)
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
                    elif self.tabWidget.active_tab is None:
                        ok = False
                        err = "no active tab somehow"
                    elif await checker():
                        try:
                            index = (
                                int(args[1])
                                if len(args) == 2
                                else self.tabWidget.tabs.index(self.tabWidget.active_tab)
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
                                    "index": tab.session.historyIndex,
                                }
                case _:
                    ok = False
                    err = "tab action is not valid"
        case "theme":
            if len(args) == 0:
                return assemble_and_write(
                    writer, False, None, "theme action not provided"
                )
            match args[0]:
                case "list":
                    if await checker():
                        out = sorted(self.available_themes)
                case "query":
                    if await checker():
                        from rovr.functions.themes import resolve_theme_ansi

                        _, fixed = resolve_theme_ansi(
                            self.current_theme, config["theme"]["transparent"]
                        )
                        out = {
                            "theme": self.theme,
                            "transparent": bool(self.ansi_color),
                            "fixed": fixed,
                        }
                case "set":
                    if len(args) != 2:
                        ok = False
                        err = (
                            "too many arguments"
                            if len(args) > 2
                            else "theme name not provided"
                        )
                    elif args[1] not in self.available_themes:
                        ok = False
                        err = f"unknown theme: {args[1]}"
                    elif await checker():
                        self.theme = args[1]
                        out = self.theme
                case _:
                    ok = False
                    err = "theme action is not valid"
        case "notify":
            from rovr.functions.ipc_sender import IPC_PARSER

            if await checker():
                try:
                    notification = IPC_PARSER.parse_args([action, *args])
                except SystemExit:
                    ok = False
                    err = "invalid notification arguments"
                else:
                    if notification.markup:
                        from textual.content import Content

                        try:
                            Content.from_markup(notification.message)
                        except Exception as exc:
                            return assemble_and_write(
                                writer, False, None, f"invalid markup: {exc}"
                            )

                    self.notify(
                        notification.message,
                        title=notification.title or "",
                        severity=notification.severity or "information",
                        timeout=notification.timeout,
                        markup=notification.markup,
                    )
        case "quit":
            if await checker():
                worker: Worker = self.action_quit("--no-cd" not in args)
                await worker.wait()
                if self.return_code is None:
                    ok = False
                    err = "processes still running, denied"
        case "suspend":
            if await checker():
                from textual.app import WINDOWS

                if WINDOWS:
                    ok = False
                    err = "suspend is not available on Windows"
                else:
                    self.action_suspend_process()
        case "ask":
            if len(args) != 1:
                ok = False
                err = "too many arguments" if args else "question not provided"
            elif await checker():
                out: bool = await self.push_screen_wait(YesOrNo(args[0]))
        case "input":
            if len(args) > 2 or len(args) == 0:
                ok = False
                err = "too many arguments" if len(args) > 2 else "prompt not provided"
            elif len(args) == 1 and args[0] == "--is-path":
                ok = False
                err = "prompt not provided"
            elif await checker():
                from rovr.screens import ModalInput

                out: str = await self.push_screen_wait(
                    ModalInput(args[0], is_path="--is-path" in args)
                )
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


@work(group="ipc")
async def start_server(self: Application) -> None:
    from rovr.functions.ipc_instances import publish_instance, unpublish_instance

    token = secrets.token_urlsafe(32)
    server = await asyncio.start_server(partial(wrapper, self, token), "127.0.0.1", 0)
    addr = server.sockets[0].getsockname()
    async with server:
        descriptor = publish_instance(addr[1], token)
        # quite weird that globals().get("is_dev", False) is not working here
        if {"debug", "devtools"}.issubset(set(os.environ.get("TEXTUAL", "").split(","))):
            self.call_after_refresh(self.notify, f"Serving on {addr}")
        os.environ["ROVR_IPC_PID"] = str(os.getpid())
        try:
            await server.serve_forever()
        finally:
            unpublish_instance(descriptor, token)
            os.environ.pop("ROVR_IPC_PID", None)
