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
        help="The path to change the current working directory to.",
        nargs=1,
    )

    clipboard = commands.add_parser("clipboard", help="Perform clipboard operations.")
    clipboard_commands = clipboard.add_subparsers(dest="operation", required=True)
    for operation in ("copy", "cut"):
        command = clipboard_commands.add_parser(
            operation,
            help=f"{operation.capitalize()} the passed items to rovr's clipboard",
        )
        command.add_argument(
            "--selection",
            choices=("keep", "add", "replace"),
            default="keep",
            help="Whether to keep, add, or replace the clipboard selection (default: keep)",
        )
        command.add_argument("paths", nargs="+")
    clipboard_commands.add_parser(
        "paste", help="Paste the contents of rovr's clipboard into the current view."
    )
    clipboard_commands.add_parser("list", help="List the contents of rovr's clipboard.")

    tab = commands.add_parser("tab", help="Perform tab operations.")
    subparser = tab.add_subparsers(dest="operation", required=True)
    for op, desc in zip(
        ("list", "new", "focus", "close", "history"),
        (
            "List all tabs",
            "Create a new tab",
            "Switch to a tab",
            "Close a tab",
            "Get the navigation history of a tab",
        ),
    ):
        command = subparser.add_parser(op, help=desc)
        if op in ("focus", "close", "history"):
            command.add_argument(
                "tab_index",
                type=int,
                help="The index of the tab to "
                + (
                    "focus"
                    if op == "focus"
                    else ("close" if op == "close" else "get the history of")
                    + ". If unspecified, uses focused tab."
                ),
                nargs=1 if op == "focus" else "?",
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
        "ask", help="Ask a yes or no question in the rovr instance."
    ).add_argument("question", help="The question to ask.")
    inp = commands.add_parser("input", help="Ask for input in the rovr instance.")
    inp.add_argument("prompt", help="The prompt to display.")
    inp.add_argument(
        "--is-path", action="store_true", help="Whether the input is a path."
    )

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
        path = p(parsed.path[0])
        if not os.path.exists(path):
            raise ValueError("does not exist.")
        return (path,)
    if parsed.action == "clipboard" and parsed.operation in ("copy", "cut"):
        return (
            parsed.operation,
            f"--selection={parsed.selection}",
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
        spid = os.environ.get("ROVR_IPC_PID")
        if spid is None:
            _print_error("ROVR_IPC_PID is not set")
            return
        try:
            pid = int(spid)
        except ValueError:
            _print_error("Invalid ROVR_IPC_PID")
            return

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
