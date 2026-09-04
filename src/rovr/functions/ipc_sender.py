import asyncio
import json
from os import environ
from typing import TypedDict


class SubIPCCommands(TypedDict):
    arg: str
    allowed: set[str]


# not maps but i dont know here to put this
ALLOWED_IPCS: list[str | SubIPCCommands] = [
    "cd",
    "cursor",
    SubIPCCommands({
        "arg": "clipboard",
        "allowed": {"copy", "paste", "cut", "list"}
    }),
    SubIPCCommands({
        "arg": "tab",
        "allowed": {"list", "create", "switch", "close"}
    }),
    "quit",
    "suspend",
    SubIPCCommands({
        "arg": "history",
        "allowed": {"list"}
    })
    # "exec"
]


async def send_message(port: int | None, action: str, *args: str) -> None:
    if port is None:
        # try getting it from env
        sport = environ.get("ROVR_IPC_PORT", None)
        if sport is None:
            print(
                '{"ok": false, "output": "No port specified and ROVR_IPC_PORT not set"}'
            )
    # check if action is valid
    if not any(action == p for p in ALLOWED_IPCS if isinstance(p, str)):
        # check subipccommands
        if not any(
            action == (comm := p)["arg"] for p in ALLOWED_IPCS if not isinstance(p, str)
        ):
            import difflib
            # get possible closest match because typo
            possible_matches = difflib.get_close_matches(
                action,
                [p if isinstance(p, str) else p["arg"] for p in ALLOWED_IPCS],
                n=1,
                cutoff=0.6,
            )
            if possible_matches:
                print(
                    f'{{"ok": false, "output": "Invalid action specified. Did you mean \'{possible_matches[0]}\'?"}}'
                )
            else:
                print(
                    '{"ok": false, "output": "Invalid action specified. Please check the documentation for valid actions."}'
                )
            return
        if not all(arg == comm["args"][0] for arg in args):
            print(
                '{"ok": false, "output": "Invalid arguments specified for the action. Please check the documentation for valid arguments."}'
            )
            return
    # time to individually check them yay!
    match action:
        case "cd":
            # check for `--exact`, as well as path itself if exact was used
            if "--exact" in args:
                if len(args) < 2:
                    print(
                        '{"ok": false, "output": "Missing path argument for cd with --exact"}'
                    )
                    return
                # check if path is valid
                import os

                if not os.path.exists(args[1]):
                    print(
                        f'{{"ok": false, "output": "Path \'{args[1]}\' does not exist"}}'
                    )
                    return
            # no need for else, because rovr will handle going to nearest folder
        case "cursor":
            # needs a number basically
            if len(args) < 1:
                print(
                    '{"ok": false, "output": "Missing argument for cursor. Please specify a number."}'
                )
                return
            from ast import literal_eval
            if type(literal_eval(args[0])) is not int:
                print(
                    '{"ok": false, "output": "Invalid argument for cursor. Please specify a number. (<int> for exact, -/+<int> for relative)"}'
                )
                return
        case "clipboard":
            match args[0]:
                case "copy" | "cut":
                    # these ones take in paths, and additional --select/--reselect
                    # --select adds them, --reselect unselects and then selects the new additions
                    # --select and --reselect cannot exist simultaneously
                    # path check will happen in app, because i want it to return invalid paths
                    # but we also need to consider dict transfer, we'll get to it soon trust
                    if "--select" in args and "--reselect" in args:
                        print(
                            '{"ok": false, "output": "Cannot use --select and --reselect simultaneously."}'
                        )
                        return
                    if len(args) < 3 and args[-1] in ("--select", "--reselect"):
                        print(
                            '{"ok": false, "output": "Missing path arguments for clipboard copy/cut with --select/--reselect."}'
                        )
                        return
    # create the json message
    # we probably need to change it later, its just temporary obv
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
        print(
            '{"ok": false, "output": "Could not connect to rovr\'s ipc. Is it running?"}'
        )
