import asyncio
import json
import os
from typing import NoReturn

from rovr.functions.cli import RichArgumentParser


def _print_error(message: str) -> None:
    from rovr.functions.cli import print_rich_error

    print_rich_error(message)


class IPCArgumentParser(RichArgumentParser):
    def error(self, message: str) -> NoReturn:
        _print_error(message)
        self.print_help()
        raise SystemExit(2)


def _build_parser() -> IPCArgumentParser:
    parser = IPCArgumentParser(
        prog="rovr --ipc", description="Send a command to a running rovr instance."
    )
    commands = parser.add_subparsers(
        dest="action", required=True, title="commands", metavar="COMMAND"
    )

    commands.add_parser(
        "cd", help="Change the current working directory of the rovr instance."
    ).add_argument(
        "path",
        help="The path to change the current working directory to. If empty, returns the current working directory.",
        nargs="?",
    )

    clipboard = commands.add_parser("clipboard", help="Perform clipboard operations.")
    clipboard_commands = clipboard.add_subparsers(dest="operation", required=True)
    for operation in ("copy", "cut"):
        command = clipboard_commands.add_parser(
            operation,
            help=f"{operation.capitalize()} the passed items to rovr's clipboard",
        )
        selection = command.add_mutually_exclusive_group()
        selection.add_argument(
            "--select",
            action="store_true",
            help="Select the added items in the clipboard",
        )
        selection.add_argument(
            "--reselect",
            action="store_true",
            help="Unselect all items in the clipboard and select the added items",
        )
        command.add_argument("paths", nargs="+")
    clipboard_commands.add_parser(
        "paste", help="Paste the contents of rovr's clipboard into the current view."
    )
    clipboard_commands.add_parser("list", help="List the contents of rovr's clipboard.")

    tab = commands.add_parser("tab", help="Perform tab operations.")
    subparser = tab.add_subparsers(dest="operation", required=True)
    for op, desc in zip(
        ("list", "new", "focus", "close"),
        ("List all tabs", "Create a new tab", "Switch to a tab", "Close a tab"),
    ):
        command = subparser.add_parser(op, help=desc)
        if op in ("focus", "close"):
            command.add_argument(
                "tab_index",
                type=int,
                help=f"The index of the tab to {'focus' if op == 'focus' else 'close. If unspecified, uses focused tab.'}",
                nargs="?",
            )
        elif op == "new":
            command.add_argument(
                "path",
                type=str,
                nargs="?",
                help="The path to open in the new tab. If unspecified, opens the current working directory.",
            )
            # --focus optional
            command.add_argument(
                "--focus",
                action="store_true",
                help="Focus the new tab after creating it.",
            )

    commands.add_parser(
        "history", help="Get the navigation history of a tab in the rovr instance."
    ).add_argument(
        "index",
        type=int,
        help="The tab index to get the navigation history for. If unspecified, uses the focused tab.",
        nargs="?",
    )

    commands.add_parser("quit", help="Quit the rovr instance.").add_argument(
        "--no-cd",
        action="store_true",
        help="If using --cwd-file, do not write cwd before quitting",
    )

    commands.add_parser(
        "suspend", help="Suspend the rovr instance (Unavailable on Windows)."
    )

    commands.add_parser("list-instances", help="List running rovr instances.")

    commands.add_parser(
        "choice", help="Ask a yes or no question in the rovr instance."
    ).add_argument("question", help="The question to ask.")

    notify = commands.add_parser(
        "notify", help="Send a notification to the rovr instance."
    )
    notify.add_argument("message", help="The message to send.")
    notify.add_argument("--title", help="The title of the notification.")
    notify.add_argument(
        "--severity",
        choices=("information", "warning", "error"),
        help="Severity of notification",
    )
    notify.add_argument("--markup", action="store_true", help="Render with rich markup")
    notify.add_argument(
        "--timeout",
        type=float,
        help="Hide notification after this time passed (default 5s)",
    )
    return parser


IPC_PARSER = _build_parser()


def p(path: str) -> str:
    return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))


def _prepare_message(action: str, args: tuple[str, ...]) -> tuple[str, ...]:
    parsed = IPC_PARSER.parse_args([action, *args])
    if parsed.action == "list-instances":
        raise ValueError("list-instances does not target a specific instance")
    if parsed.action == "cd" and parsed.path:
        path = p(parsed.path)
        if not os.path.exists(path):
            raise ValueError("does not exist.")
        return (path,)
    if parsed.action == "clipboard" and parsed.operation in ("copy", "cut"):
        flag = (
            "--select" if parsed.select else "--reselect" if parsed.reselect else None
        )
        return (
            parsed.operation,
            *((flag,) if flag else ()),
            *map(p, parsed.paths),
        )
    if parsed.action == "tab" and parsed.operation == "new" and parsed.path:
        return (
            parsed.operation,
            p(parsed.path),
            *(("--focus",) if parsed.focus else ()),
        )
    return args


async def send_message(pid: int | None, action: str, *args: str) -> None:
    try:
        args = _prepare_message(action, args)
    except ValueError as error:
        print(f'{{"ok": false, "err": "{str(error)}"}}')
        return

    if pid is None:
        sport = os.environ.get("ROVR_IPC_PORT")
        token = os.environ.get("ROVR_IPC_TOKEN")
        if sport is None or token is None:
            _print_error("ROVR_IPC_PORT and ROVR_IPC_TOKEN are not set")
            return
        try:
            port = int(sport)
        except ValueError:
            _print_error("Invalid ROVR_IPC_PORT")
            return
    else:
        from rovr.functions.ipc_instances import instance_for_pid

        instance = instance_for_pid(pid)
        if instance is None:
            _print_error(f"Could not find rovr instance with PID {pid}")
            return
        port, token = instance["port"], instance["token"]

    json_message = json.dumps({"token": token, "action": action, "args": args})
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(json_message.encode() + b"\n")
        await writer.drain()

        data = await reader.readline()
        print(data.decode())
        writer.close()
        await writer.wait_closed()
    except ConnectionRefusedError:
        _print_error("Could not connect to rovr's ipc. Is it running?")
