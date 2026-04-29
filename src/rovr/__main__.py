# nuitka-project: --assume-yes-for-downloads
# nuitka-project: --clang
# nuitka-project: --disable-plugin=tk-inter
# nuitka-project: --enable-plugin=anti-bloat
# nuitka-project: --enable-plugin=implicit-imports
# nuitka-project: --enable-plugin=multiprocessing
# nuitka-project: --enable-plugin=options-nanny
# nuitka-project: --enable-plugins=no-qt
# nuitka-project: --include-package-data=rovr
# nuitka-project: --nofollow-import-to="tkinter"
# nuitka-project: --nofollow-import-to=aiohttp
# nuitka-project: --onefile-cache-mode=cached
# nuitka-project: --onefile-child-grace-time=1
# nuitka-project: --python-flag=isolated
# nuitka-project: --python-flag=no_asserts
# nuitka-project: --python-flag=no_docstrings
# nuitka-project: --python-flag=no_site
# nuitka-project: --python-flag=safe_path
# nuitka-project: --python-flag=static_hashes
# nuitka-project: --report=report.xml
# nuitka-project: --warn-unusual-code

# nuitka-project-if: {OS} in ("MACOS"):
#    nuitka-project: --macos-app-console-mode=force
#    nuitka-project: --macos-signed-app-name=com.NSPC911.rovr

# nuitka-project-if: {OS} in ("Windows"):
#    nuitka-project: --windows-console-mode=force

import argparse
import logging
import os
import sys
from io import TextIOWrapper
from typing import cast

from rovr import main, pprint
from rovr.functions.cli import (
    RichArgumentParser,
    RichPanelHelpAction,
    eager_set_folder,
    existing_dir,
)

logging.getLogger("textual_image._terminal").setLevel(logging.FATAL)

textual_flags = set(os.environ.get("TEXTUAL", "").split(","))
is_dev = {"debug", "devtools"}.issubset(textual_flags)


def _build_parser() -> argparse.ArgumentParser:
    formatter_class: type[argparse.HelpFormatter] = argparse.HelpFormatter
    with_context_help = "Set to __stdout__ to write to stdout (__stderr__ for stderr)"

    parser = RichArgumentParser(
        prog="rovr",
        description="A post-modern terminal file explorer",
        usage="rovr [OPTIONS] [PATH]",
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

    paths_group = parser.add_argument_group("Paths")
    paths_group.description = with_context_help
    paths_group.add_argument(
        "--chooser-file",
        dest="chooser_file",
        default="",
        type=str,
        help="Write chosen file(s) (\\n-separated) to this file on exit.",
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
        help="Force rovr into the system tty (CONOUT$ or /dev/tty) even if stdout is not a tty. Buggy on Windows.",
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
        "--force-crash-in",
        dest="force_crash_in",
        type=float,
        default=0,
        help="Force a crash after N seconds (for testing crash recovery)"
        if is_dev
        else argparse.SUPPRESS,
    )

    parser.add_argument("path", nargs="?", default="", type=str, metavar="PATH")

    return parser


def cli(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    eager_set_folder(args.config_folder)

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

        config_path = _normalise(RovrVars.ROVRCONFIG)

        if sys.stdout.isatty():
            from rich import box
            from rich.table import Table

            table = Table(title="", border_style="blue", box=box.ROUNDED)
            table.add_column("type")
            table.add_column("path")
            table.add_row("[cyan]custom config[/]", f"{config_path}/config.toml")
            table.add_row("[hot_pink]custom styles[/]", f"{config_path}/style.tcss")
            table.add_row("[yellow]pinned folders[/]", f"{config_path}/pins.json")
            table.add_row("[grey69]persistent state[/]", f"{config_path}/state.toml")
            table.add_row("[red]logs[/]", f"{config_path}/logs/")
            pprint(table)
        else:
            print(f"""\u007b
    "custom_config": "{config_path}/config.toml",
    "pinned_folders": "{config_path}/pins.json",
    "custom_styles": "{config_path}/style.tcss",
    "persistent_state": "{config_path}/state.toml",
    "logs": "{config_path}/logs/"
\u007d""")
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

                commit_hash_file = resources.files("rovr") / "COMMIT_HASH"
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

    import rovr.monkey_patches._classes  # noqa: F401, I001
    import rovr.monkey_patches._platform  # noqa: F401

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

    if sys.stdout.isatty():
        Application(
            startup_path=args.path,
            cwd_file=cwd_file if cwd_file else None,
            chooser_file=chooser_file if chooser_file else None,
            show_keys=args.show_keys,
            tree_dom=args.tree_dom,
            force_crash_in=args.force_crash_in,
        ).run()
    elif args.force_tty:
        open_stdout = "CONOUT$" if os.name == "nt" else "/dev/tty"
        open_stdin = "CONIN$" if os.name == "nt" else "/dev/tty"
        try:
            with (
                open(open_stdout, "w") as tty_out,
                open(open_stdin, "r") as tty_in,
            ):
                sys.__stdout__ = sys.stdout = tty_out
                sys.__stderr__ = sys.stderr = tty_out
                sys.__stdin__ = sys.stdin = tty_in
                Application(
                    startup_path=args.path,
                    cwd_file=cwd_file if cwd_file else None,
                    chooser_file=chooser_file if chooser_file else None,
                    show_keys=args.show_keys,
                    tree_dom=args.tree_dom,
                    force_crash_in=args.force_crash_in,
                ).run()
        finally:
            sys.__stdout__ = sys.stdout = backup_stdout
            sys.__stderr__ = sys.stderr = backup_stderr
            sys.__stdin__ = sys.stdin = backup_stdin
    else:
        print("Error: rovr needs a TTY to run in application.")
        exit(1)


if __name__ == "__main__":
    main()
