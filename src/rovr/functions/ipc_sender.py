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

    cd = commands.add_parser(
        "cd", help="Change the current working directory of the rovr instance."
    )
    cd.add_argument(
        "--exact",
        action="store_true",
        help="Do not attempt to go to nearest existing parent directory if the specified path does not exist.",
    )
    cd.add_argument("path")

    cursor = commands.add_parser("cursor", help="Move the cursor in the current view.")
    cursor.add_argument(
        "offset",
        type=int,
        help="The number of lines to move the cursor. Positive values move the cursor down, negative values move it up.",
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
        ("list", "create", "switch", "close"),
        ("List all tabs", "Create a new tab", "Switch to a tab", "Close a tab"),
    ):
        command = subparser.add_parser(op, help=desc)
        if op in ("switch", "close"):
            command.add_argument(
                "tab_index",
                type=int,
                help="The index of the tab to switch to or close. If unspecified, uses focused tab.",
            )

    history = commands.add_parser("history", help="Perform command history operations.")
    history.add_argument(
        "operation",
        choices=("list",),
        help="List the command history of the rovr instance.",
    )

    commands.add_parser("quit", help="Quit the rovr instance.")
    commands.add_parser(
        "suspend", help="Suspend the rovr instance (Unavailable on Windows)."
    )
    return parser


IPC_PARSER = _build_parser()


def _validate_message(action: str, args: tuple[str, ...]) -> None:
    parsed = IPC_PARSER.parse_args([action, *args])
    if parsed.action == "cd" and parsed.exact and not os.path.exists(parsed.path):
        raise ValueError("does not exist.")


async def send_message(port: int | None, action: str, *args: str) -> None:
    if port is None:
        sport = os.environ.get("ROVR_IPC_PORT")
        if sport is None:
            _print_error("No port specified and ROVR_IPC_PORT not set")
            return
        try:
            port = int(sport)
        except ValueError:
            _print_error("Invalid ROVR_IPC_PORT")
            return

    try:
        _validate_message(action, args)
    except ValueError as error:
        print(f'{{"ok": false, "err": "{str(error)}"}}')
        return

    json_message = json.dumps({"action": action, "args": args})
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(json_message.encode())
        await writer.drain()

        data = await reader.read(1024)
        print(data.decode())
        writer.close()
        await writer.wait_closed()
    except ConnectionRefusedError:
        _print_error("Could not connect to rovr's ipc. Is it running?")
