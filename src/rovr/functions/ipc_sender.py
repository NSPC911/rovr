import argparse
import asyncio
import json
import os
from typing import NoReturn


class IPCArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _build_parser() -> argparse.ArgumentParser:
    parser = IPCArgumentParser(add_help=False)
    commands = parser.add_subparsers(dest="action", required=True)

    cd = commands.add_parser("cd", add_help=False)
    cd.add_argument("--exact", action="store_true")
    cd.add_argument("path")

    cursor = commands.add_parser("cursor", add_help=False)
    cursor.add_argument("offset", type=int)

    clipboard = commands.add_parser("clipboard", add_help=False)
    clipboard_commands = clipboard.add_subparsers(dest="operation", required=True)
    for operation in ("copy", "cut"):
        command = clipboard_commands.add_parser(operation, add_help=False)
        selection = command.add_mutually_exclusive_group()
        selection.add_argument("--select", action="store_true")
        selection.add_argument("--reselect", action="store_true")
        command.add_argument("paths", nargs="+")
    clipboard_commands.add_parser("paste", add_help=False)
    clipboard_commands.add_parser("list", add_help=False)

    tab = commands.add_parser("tab", add_help=False)
    tab.add_argument("operation", choices=("list", "create", "switch", "close"))

    history = commands.add_parser("history", add_help=False)
    history.add_argument("operation", choices=("list",))

    commands.add_parser("quit", add_help=False)
    commands.add_parser("suspend", add_help=False)
    return parser


IPC_PARSER = _build_parser()


def _print_error(message: str) -> None:
    from rovr.functions.cli import print_rich_error

    print_rich_error(message)


def _validate_message(action: str, args: tuple[str, ...]) -> None:
    parsed = IPC_PARSER.parse_args([action, *args])
    if parsed.action == "cd" and parsed.exact and not os.path.exists(parsed.path):
        raise ValueError(f"Path '{parsed.path}' does not exist")


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
        _print_error(str(error))
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
