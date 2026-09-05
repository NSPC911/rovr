# nuitka-project: --assume-yes-for-downloads
# nuitka-project: --disable-plugin=tk-inter
# nuitka-project: --enable-plugin=anti-bloat
# nuitka-project: --enable-plugin=implicit-imports
# nuitka-project: --enable-plugin=multiprocessing
# nuitka-project: --enable-plugin=options-nanny
# nuitka-project: --enable-plugins=no-qt
# nuitka-project: --include-data-dir=src/rovr=_rovr
# nuitka-project: --include-distribution-metadata=rovr
# nuitka-project: --nofollow-import-to="tkinter"
# nuitka-project: --nofollow-import-to=aiohttp
# nuitka-project: --onefile-cache-mode=cached
# nuitka-project: --onefile-child-grace-time=1
# nuitka-project: --python-flag=no_asserts
# nuitka-project: --python-flag=no_docstrings
# nuitka-project: --python-flag=no_site
# nuitka-project: --python-flag=safe_path
# nuitka-project: --python-flag=static_hashes
# nuitka-project: --warn-unusual-code

# nuitka-project-if: {OS} in ("MACOS"):
#    nuitka-project: --macos-app-console-mode=force
#    nuitka-project: --macos-signed-app-name=com.NSPC911.rovr

# nuitka-project-if: {OS} in ("Windows"):
#    nuitka-project: --windows-console-mode=force
#    nuitka-project: --output-filename=rovr.exe
# nuitka-project-else:
#    nuitka-project: --output-filename=rovr

import argparse
import logging
import os
import sys
import warnings
from io import TextIOWrapper
from typing import Callable, cast

from rovr import RESOURCE_PACKAGE, main, pprint
from rovr.functions.cli import (
    RichArgumentParser,
    RichPanelHelpAction,
    eager_set_folder,
    existing_dir,
)

logging.getLogger("textual_image._terminal").setLevel(logging.FATAL)
warnings.filterwarnings("ignore")

textual_flags = set(os.environ.get("TEXTUAL", "").split(","))
is_dev = {"debug", "devtools"}.issubset(textual_flags)


def _build_parser() -> argparse.ArgumentParser:
    formatter_class: type[argparse.HelpFormatter] = argparse.HelpFormatter
    with_context_help = "Set to __stdout__ to write to stdout (__stderr__ for stderr)"

    parser = RichArgumentParser(
        prog="rovr",
        description="a stylish, batteries-included terminal file manager.",
        usage="rovr [OPTIONS] [PATH ...]",
        formatter_class=formatter_class,
        add_help=False,
    )

    parser._positionals.title = "Arguments"
    parser._optionals.title = "Miscellaneous"
    parser._optionals.description = None

    config_group = parser.add_argument_group("Config")
    config_group.add_argument(
        "--with",
        dest="with_features",
        action="append",
        default=[],
        type=str,
        help="Enable a feature (e.g., 'plugins.bat').",
    )
    config_group.add_argument(
        "--with-feature",
        dest="with_features",
        action="append",
        type=str,
        help=argparse.SUPPRESS,
    )
    config_group.add_argument(
        "--without",
        dest="without_features",
        action="append",
        default=[],
        type=str,
        help="Disable a feature (e.g., 'interface.tooltips').",
    )
    config_group.add_argument(
        "--without-feature",
        dest="without_features",
        action="append",
        type=str,
        help=argparse.SUPPRESS,
    )
    config_group.add_argument(
        "--config-folder",
        dest="config_folder",
        default=None,
        type=existing_dir,
        help="Change the config folder location.",
    )
    config_group.add_argument(
        "--check-keys",
        action="store_true",
        help="Validate keys.toml and exit.",
    )

    paths_group = parser.add_argument_group("Paths")
    paths_group.description = with_context_help
    paths_group.add_argument(
        "--chooser-file",
        dest="chooser_file",
        default="",
        type=str,
        help="Write opened file(s) (\\n-separated) to this file on exit.",
    )
    paths_group.add_argument(
        "--cwd-file",
        dest="cwd_file",
        default="",
        type=str,
        help="Write the final working directory to this file on exit.",
    )

    misc_group = parser.add_argument_group("Miscellaneous")
    misc_group.add_argument(
        "-h",
        "--help",
        action=RichPanelHelpAction,
        nargs=0,
        help="Show this message and exit.",
    )
    misc_group.add_argument(
        "--version",
        dest="show_version",
        action="store_true",
        help="Show the current version of rovr.",
    )
    misc_group.add_argument(
        "--force-tty",
        dest="force_tty",
        action="store_true",
        help="Force rovr into the system tty (CONOUT$ or /dev/tty) even if stdout is a tty.",
    )
    misc_group.add_argument(
        "--ignore-missing-tty",
        dest="ignore_missing_tty",
        action="store_true",
        help="Ignore missing TTY and attempt to run anyway (not recommended)."
        if is_dev
        else argparse.SUPPRESS,
    )
    misc_group.add_argument(
        "--force-first-launch",
        dest="force_first_launch",
        action="store_true",
        help="Force the first launch experience (even if config exists).",
    )
    misc_group.add_argument(
        "--ignore-first-launch",
        dest="ignore_first_launch",
        action="store_true",
        help="Ignore first launch setup (not recommended).",
    )
    misc_group.add_argument(
        "--config-path",
        dest="show_config_path",
        action="store_true",
        help="Show the path to the config folder.",
    )

    dev_group = parser.add_argument_group("Dev")
    dev_group.add_argument(
        "--show-keys",
        dest="show_keys",
        action="store_true",
        help="Display keys that are being pressed.",
    )
    dev_group.add_argument(
        "--tree-dom",
        dest="tree_dom",
        action="store_true",
        help="Print the DOM of the app as a tree.",
    )
    dev_group.add_argument(
        "--dev",
        dest="dev",
        action="store_true",
        help="Run rovr in development mode.",
    )
    dev_group.add_argument(
        "--list-preview-themes",
        dest="list_preview_themes",
        action="store_true",
        help="List available preview themes.",
    )
    dev_group.add_argument(
        "--clear-cache",
        dest="clear_cache",
        action="store_true",
        help="Clear the cache folder.",
    )
    dev_group.add_argument(
        "--ipc",
        nargs=argparse.REMAINDER,
        metavar="COMMAND",
        help="Send a command to the running rovr instance",
    )
    dev_group.add_argument(
        "--ipc-to",
        nargs=argparse.REMAINDER,
        metavar="COMMAND",
        help="Send a command to a specific rovr instance",
    )
    dev_group.add_argument(
        "--force-crash-in",
        dest="force_crash_in",
        type=float,
        default=0,
        help="Force a crash after N seconds (for testing crash recovery)"
        if is_dev
        else argparse.SUPPRESS,
    )

    parser.add_argument("paths", nargs="*", default=[], type=str, metavar="PATH")

    return parser


def _redirect_windows_standard_input(tty_in: TextIOWrapper) -> Callable[[], None]:
    import ctypes
    import msvcrt
    from ctypes import wintypes

    std_input_handle = wintypes.DWORD(-10)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_std_handle = kernel32.GetStdHandle
    get_std_handle.argtypes = [wintypes.DWORD]
    get_std_handle.restype = wintypes.HANDLE
    set_std_handle = kernel32.SetStdHandle
    set_std_handle.argtypes = [wintypes.DWORD, wintypes.HANDLE]
    set_std_handle.restype = wintypes.BOOL

    original_handle = get_std_handle(std_input_handle)
    tty_handle = msvcrt.get_osfhandle(tty_in.fileno())
    if not set_std_handle(std_input_handle, tty_handle):
        raise ctypes.WinError(ctypes.get_last_error())

    def restore() -> None:
        if not set_std_handle(std_input_handle, original_handle):
            raise ctypes.WinError(ctypes.get_last_error())

    return restore


def cli(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    eager_set_folder(args.config_folder)
    if args.ipc is not None:
        if not args.ipc:
            parser.error("--ipc requires a command")
        args.ipc_to = (os.environ.get("ROVR_IPC_PORT", "x"), *args.ipc)

    if args.ipc_to is not None:
        if not args.ipc_to:
            parser.error("--ipc-to requires a port and a command")
        if {"-h", "--help"} & set(args.ipc_to):
            from rovr.functions.ipc_sender import IPC_PARSER

            ipc_args = (
                args.ipc
                if args.ipc is not None
                else args.ipc_to[1:]
                if args.ipc_to[0].isdigit()
                else args.ipc_to
            )
            IPC_PARSER.parse_args(ipc_args)
            return
        if not args.ipc_to[0].isdigit():
            parser.error("--ipc-to requires a port number as the first argument")
        if not args.ipc_to[1:]:
            parser.error("--ipc-to requires a command after the port number")
        args.ipc_to = (int(args.ipc_to[0]), *args.ipc_to[1:])

        import asyncio

        from rovr.functions.ipc_sender import send_message

        asyncio.run(send_message(args.ipc_to[0], args.ipc_to[1], *args.ipc_to[2:]))
        return
    if args.check_keys:
        from rovr.functions.config import load_keys, validate_keys

        errors = validate_keys(load_keys())
        if errors:
            for error in errors:
                print(f"Error: {error}", file=sys.stderr)
            raise SystemExit(1)
        print("keys.toml is valid.")
        return
    if args.clear_cache:
        from os import _exit as exit
        from shutil import rmtree

        from rovr.variables.maps import RovrVars

        rmtree(
            (prevpath := os.path.join(RovrVars.ROVRTEMP, "previews")),
            ignore_errors=True,
        )
        # check if cache is fully cleaned
        if not os.path.exists(prevpath) or not (items := os.listdir(prevpath)):
            pprint("[bold green]Cache cleared successfully![/]")
            exit(0)
        else:
            pprint("[bold red]Failed to clear cache![/]")
            pprint(f"[red]{len(items)} items still exist.[/]")
            exit(1)

    global is_dev
    if args.dev or is_dev:
        os.environ["TEXTUAL"] = "devtools,debug"
        is_dev = True
        pprint("  [bold bright_cyan]Development mode activated![/]")
        pprint(
            "  [dim]Make sure to have [grey50]`textual console`[/] (or [grey50]`uvx --from textual-dev textual console`[/]) running![/]"
        )
        pprint(
            "  [dim]  - Keep in mind that the console needs to be running [i]before[/] you start the app![/]"
        )

    if args.list_preview_themes:
        from pygments.styles import get_all_styles
        from rich.syntax import Syntax

        styles = list(get_all_styles())
        if sys.stdout.isatty():
            test_python = """# test of all syntax features
def example_function(param1, param2=\"default\"):
    \"\"\"This is an example function.\"\"\"
    if param1 > 0:
        print(f\"Param1 is positive: {param1}\")
    return param2
example_function(10)"""
            for style in styles:
                syntax = Syntax(
                    test_python,
                    "python",
                    theme=style,
                    line_numbers=True,
                    background_color="default",
                )
                pprint(
                    f"\n[bold underline]Preview of style: [cyan]{style}[/][/]",
                    syntax,
                )
        else:
            print("\n".join(styles))
        return

    from rovr.variables.maps import RovrVars

    if args.show_config_path:

        def _normalise(location: str | bytes) -> str:
            from os import path

            return str(path.normpath(location)).replace("\\", "/").replace("//", "/")

        _conf = _normalise(RovrVars.ROVRCONFIG)
        _state = _normalise(RovrVars.ROVRSTATE)
        _temp = _normalise(RovrVars.ROVRTEMP)

        if sys.stdout.isatty():
            from rich import box
            from rich.table import Table

            table = Table(title="", border_style="blue", box=box.ROUNDED)
            table.add_column("type")
            table.add_column("path")
            table.add_row("[cyan]main config[/]", f"{_conf}/config.toml")
            table.add_row("[green]keys[/]", f"{_conf}/keys.toml")
            table.add_row("[hot_pink]global styles[/]", f"{_conf}/style.tcss")
            table.add_row("[magenta1]themes[/]", f"{_conf}/themes/")
            table.add_row("[yellow]pinned folders[/]", f"{_conf}/pins.json")
            table.add_row("[grey69]persistent state[/]", f"{_state}/state.toml")
            table.add_row("[red]logs[/]", f"{_temp}/logs/")
            pprint(table)
        else:
            print(f"""{{
    "main_config": "{_conf}/config.toml",
    "keys": "{_conf}/keys.toml",
    "global_styles": "{_conf}/style.tcss",
    "themes": "{_conf}/themes/",
    "pinned_folders": "{_conf}/pins.json",
    "persistent_state": "{_state}/state.toml",
    "logs": "{_temp}/logs/"
}}""")
        return
    if args.show_version:

        def _get_version() -> list[str]:
            from importlib.metadata import PackageNotFoundError, version

            try:
                ver = version("rovr")
            except PackageNotFoundError:
                ver = "unknown"

            try:
                from importlib import resources

                commit_hash_file = resources.files(RESOURCE_PACKAGE) / "COMMIT_HASH"
                commit_hash = commit_hash_file.read_text(encoding="utf-8").strip()
                if commit_hash:
                    return [ver, commit_hash]
            except Exception:
                pass

            return [ver, ""]

        ver = _get_version()
        if sys.stdout.isatty():
            pprint(
                f"rovr [bold cyan]{ver[0]}[/]"
                + (
                    f" ([link=https://github.com/NSPC911/rovr/commit/{ver[1]}][dim]{ver[1][:7]}[/][/])"
                    if ver[1]
                    else ""
                )
            )
        else:
            print(f"rovr {ver[0]} ({ver[1][:7]})" if ver[1] else f"rovr {ver[0]}")
        return

    if args.force_first_launch and args.ignore_first_launch:
        pprint(
            "[bold red]Error:[/] --force-first-launch and --ignore-first-launch are mutually exclusive, and hence cannot be used simultaneously."
        )
        sys.exit(1)
    config_missing = not os.path.exists(RovrVars.ROVRCONFIG) or not os.listdir(
        RovrVars.ROVRCONFIG
    )
    if args.ignore_first_launch:
        if config_missing:
            pprint(
                "[bold yellow]Warning:[/] Ignoring first launch setup is not recommended. Some features may not work properly without proper configuration."
            )
        else:
            pprint(
                "[bold yellow]Warning[/]: Config already available, `--ignore-first-launch` does nothing."
            )
    elif args.force_first_launch or config_missing:
        from rovr.first_launch import FirstLaunchApp

        FirstLaunchApp(can_exit=args.force_first_launch).run()

    if args.force_first_launch:
        return

    import rovr.monkey_patches._platform  # noqa: F401, I001
    import rovr.monkey_patches._textual  # noqa: F401

    from rovr.functions.config import set_nested_value
    from rovr.variables.constants import config

    for feature_path in args.with_features:
        set_nested_value(cast(dict, config), feature_path, True)

    for feature_path in args.without_features:
        set_nested_value(cast(dict, config), feature_path, False)

    cwd_file: str | TextIOWrapper | None = args.cwd_file
    chooser_file: str | TextIOWrapper | None = args.chooser_file

    backup_stdout = sys.__stdout__
    backup_stderr = sys.__stderr__
    backup_stdin = sys.__stdin__

    from rovr.app import Application

    if chooser_file == "__stdout__":
        chooser_file = backup_stdout
    elif chooser_file == "__stderr__":
        chooser_file = backup_stderr

    if cwd_file == "__stdout__":
        cwd_file = backup_stdout
    elif cwd_file == "__stderr__":
        cwd_file = backup_stderr

    new_app = lambda: Application(
        startup_path=args.paths,
        cwd_file=cwd_file if cwd_file else None,
        chooser_file=chooser_file if chooser_file else None,
        show_keys=args.show_keys,
        force_crash_in=args.force_crash_in,
        force_exit_on_shutdown=True,
    )

    if args.tree_dom:
        import asyncio

        async def print_dom(app: Application) -> None:
            async with app.run_test() as pilot:
                await pilot.pause(0.1)
                pprint(app.tree)

        asyncio.run(print_dom(new_app()))
    elif args.ignore_missing_tty or sys.stdout.isatty():
        try:
            app = new_app()
            app.run()
        finally:
            app.cancel_force_exit_timer()
    elif args.force_tty:
        open_stdout = "CONOUT$" if os.name == "nt" else "/dev/tty"
        open_stdin = "CONIN$" if os.name == "nt" else "/dev/tty"
        try:
            with (
                open(open_stdout, "w") as tty_out,
                open(open_stdin, "r") as tty_in,
            ):
                restore_standard_input = (
                    _redirect_windows_standard_input(tty_in)
                    if os.name == "nt"
                    else None
                )
                try:
                    sys.__stdout__ = sys.stdout = tty_out
                    sys.__stderr__ = sys.stderr = tty_out
                    sys.__stdin__ = sys.stdin = tty_in

                    from rich.color import ColorSystem

                    from rovr import get_console

                    if get_console()._detect_color_system() == ColorSystem.WINDOWS:
                        from textual import constants

                        constants.COLOR_SYSTEM = "truecolor"
                    app = new_app()
                    try:
                        app.run()
                    finally:
                        app.cancel_force_exit_timer()
                finally:
                    if restore_standard_input is not None:
                        restore_standard_input()
        finally:
            sys.__stdout__ = sys.stdout = backup_stdout
            sys.__stderr__ = sys.stderr = backup_stderr
            sys.__stdin__ = sys.stdin = backup_stdin
    else:
        print("Error: rovr needs a TTY to run in application.")
        exit(1)


if __name__ == "__main__":
    main()
