import os
import platform
import sys
from io import TextIOWrapper
from multiprocessing import Process
from typing import cast

import rich_click as click
from rich import box
from rich.console import Console
from rich.table import Table

pprint = Console().print

textual_flags = set(os.environ.get("TEXTUAL", "").split(","))
# both flags exist if ran with `textual run --dev`
is_dev = {"debug", "devtools"}.issubset(textual_flags)

click.rich_click.USE_RICH_MARKUP = True
click.rich_click.USE_MARKDOWN = False
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = False
click.rich_click.MAX_WIDTH = 92 if is_dev else 85
click.rich_click.STYLE_OPTION = "bold cyan"
click.rich_click.STYLE_ARGUMENT = "bold cyan"
click.rich_click.STYLE_COMMAND = "bold cyan"
click.rich_click.STYLE_SWITCH = "bold cyan"
click.rich_click.STYLE_METAVAR = "bold yellow"
click.rich_click.STYLE_METAVAR_SEPARATOR = "dim"
click.rich_click.STYLE_USAGE = "bold cyan"
click.rich_click.STYLE_USAGE_COMMAND = "bold"
click.rich_click.STYLE_HELPTEXT_FIRST_LINE = ""
click.rich_click.STYLE_HELPTEXT = "dim"
click.rich_click.STYLE_OPTION_DEFAULT = "dim magenta"
click.rich_click.STYLE_REQUIRED_SHORT = "red"
click.rich_click.STYLE_REQUIRED_LONG = "dim red"
click.rich_click.STYLE_OPTIONS_PANEL_BORDER = "blue bold"
click.rich_click.STYLE_COMMANDS_PANEL_BORDER = "white"


def eager_set_folder(ctx: click.Context, param: click.Parameter, value: str) -> str:
    """Eager callback to set config folder before other options are processed.

    Returns:
        str: The config folder path (passthrough)
    """
    if value:
        from os import path

        from rovr.variables.maps import VAR_TO_DIR

        VAR_TO_DIR["CONFIG"] = path.realpath(value.replace("\\", "/"))
    return value


@click.command(help="A post-modern terminal file explorer")
@click.option(
    "--config-folder",
    "config_folder",
    multiple=False,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=None,
    is_eager=True,
    callback=eager_set_folder,
    help="Change the config folder location.",
)
@click.option(
    "--with",
    "with_features",
    multiple=True,
    type=str,
    help="Enable a feature (e.g., 'plugins.bat').",
)
@click.option(
    "--without",
    "without_features",
    multiple=True,
    type=str,
    help="Disable a feature (e.g., 'interface.tooltips').",
)
@click.option(
    "--force-first-launch",
    "force_first_launch",
    multiple=False,
    type=bool,
    default=False,
    is_flag=True,
    help="Force the first launch experience (even if config exists).",
)
@click.option(
    "--ignore-first-launch",
    "ignore_first_launch",
    multiple=False,
    type=bool,
    default=False,
    is_flag=True,
    help="Ignore first launch setup (not recommended).",
)
@click.option(
    "--config-path",
    "show_config_path",
    multiple=False,
    type=bool,
    default=False,
    is_flag=True,
    help="Show the path to the config folder.",
)
@click.option(
    "--version",
    "show_version",
    multiple=False,
    type=bool,
    default=False,
    is_flag=True,
    help="Show the current version of rovr.",
)
@click.option(
    "--force-tty",
    "force_tty",
    multiple=False,
    type=bool,
    default=False,
    is_flag=True,
    help="Force rovr into the system tty ([grey50]CONOUT$[/] or [grey50]/dev/tty[/]) even if stdout is not a tty. Buggy on Windows.",
)
@click.option(
    "--cwd-file",
    "cwd_file",
    multiple=False,
    type=str,
    default="",
    help="Write the final working directory to this file on exit.",
)
@click.option(
    "--chooser-file",
    "chooser_file",
    multiple=False,
    type=str,
    default="",
    help="Write chosen file(s) (`\\n`-separated) to this file on exit.",
)
@click.option(
    "--show-keys",
    "show_keys",
    multiple=False,
    type=bool,
    default=False,
    is_flag=True,
    help="Display Keys that are being pressed",
)
@click.option(
    "--tree-dom",
    "tree_dom",
    multiple=False,
    type=bool,
    default=False,
    is_flag=True,
    help="Print the DOM of the app as a tree",
)
@click.option(
    "--dev",
    multiple=False,
    type=bool,
    default=False,
    is_flag=True,
    help="Run rovr in development mode (lets you tail the [link=https://textual.textualize.io/guide/devtools/#console][u]console[/][/link])",
)
@click.option(
    "--list-preview-themes",
    multiple=False,
    type=bool,
    default=False,
    is_flag=True,
    help="List available preview themes.",
)
@click.option(
    "--force-crash-in",
    multiple=False,
    type=float,
    default=0,
    is_flag=False,
    help="Force a crash after N seconds (for testing crash recovery)",
    hidden=not is_dev,
)
@click.option_panel("Config", options=["--with", "--without", "--config-folder"])
@click.option_panel(
    "Paths",
    options=["--chooser-file", "--cwd-file"],
    help="Set to __stdout__ to write to stdout (__stderr__ for stderr)",
    inline_help_in_title=True,
    help_style="not dim italic",
)
@click.option_panel(
    "Miscellaneous",
    options=[
        "--version",
        "--force-tty",
        "--force-first-launch",
        "--ignore-first-launch",
        "--config-path",
        "--help",
    ],
)
@click.option_panel(
    "Dev",
    options=[
        "--show-keys",
        "--tree-dom",
        "--dev",
        "--list-preview-themes",
        "--force-crash-in" if is_dev else "",  # click has no issues with this
    ],
)
@click.argument("path", type=str, required=False, default="")
@click.rich_config({"show_arguments": True})
def cli(
    config_folder: str,
    with_features: list[str],
    force_first_launch: bool,
    ignore_first_launch: bool,
    without_features: list[str],
    show_config_path: bool,
    show_version: bool,
    force_tty: bool,
    cwd_file: str
    | TextIOWrapper
    | None,  # necessary because later on, replaced by stdout/stderr file
    chooser_file: str
    | TextIOWrapper
    | None,  # necessary because later on, replaced by stdout/stderr file
    show_keys: bool,
    path: str,
    tree_dom: bool,
    dev: bool,
    list_preview_themes: bool,
    force_crash_in: float,
) -> None:
    """A post-modern terminal file explorer"""

    global is_dev
    if dev or is_dev:
        os.environ["TEXTUAL"] = "devtools,debug"
        is_dev = True
        pprint("  [bold bright_cyan]Development mode activated![/]")
        pprint(
            "  [dim]Make sure to have [grey50]`textual console`[/] (or [grey50]`uvx --from textual-dev textual console`[/]) running![/]"
        )
        pprint(
            "  [dim]  - Keep in mind that the console needs to be running [i]before[/] you start the app![/]"
        )

    if list_preview_themes:
        from pygments.styles import get_all_styles
        from rich.syntax import Syntax

        styles = list(get_all_styles())
        if sys.stdout.isatty():
            test_python = """# test of all syntax features
def example_function(param1, param2="default"):
    \"\"\"This is an example function.\"\"\"
    if param1 > 0:
        print(f"Param1 is positive: {param1}")
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

    from rovr.variables.maps import VAR_TO_DIR

    if show_config_path:

        def _normalise(location: str | bytes) -> str:
            from os import path

            return str(path.normpath(location)).replace("\\", "/").replace("//", "/")

        config_path = _normalise(VAR_TO_DIR["CONFIG"])

        if sys.stdout.isatty():
            table = Table(title="", border_style="blue", box=box.ROUNDED)
            table.add_column("type")
            table.add_column("path")
            table.add_row("[cyan]custom config[/]", f"{config_path}/config.toml")
            table.add_row("[yellow]pinned folders[/]", f"{config_path}/pins.json")
            table.add_row("[hot_pink]custom styles[/]", f"{config_path}/style.tcss")
            table.add_row("[grey69]persistent state[/]", f"{config_path}/state.toml")
            pprint(table)
        else:
            # print as json for user to parse (jq, nu, pwsh, idk)
            print(f"""\u007b
    "custom_config": "{config_path}/config.toml",
    "pinned_folders": "{config_path}/pins.json",
    "custom_styles": "{config_path}/style.tcss",
    "persistent_state": "{config_path}/state.toml"
\u007d""")
        return
    elif show_version:

        def _get_version() -> list[str]:
            """Get version from package metadata

            Returns:
                str: Current version
            """
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

    if force_first_launch and ignore_first_launch:
        pprint(
            "[bold red]Error:[/] --force-first-launch and --ignore-first-launch are mutually exclusive, and hence cannot be used simultaneously."
        )
        sys.exit(1)
    elif ignore_first_launch:
        if not config_folder and (
            not os.path.exists(VAR_TO_DIR["CONFIG"])
            or len(os.listdir(VAR_TO_DIR["CONFIG"])) == 0
        ):
            pprint(
                "[bold yellow]Warning:[/] Ignoring first launch setup is not recommended. Some features may not work properly without proper configuration."
            )
            # Actually skip the first launch setup
            pass
        else:
            pprint(
                "[bold yellow]Warning[/]: Config already available, `--ignore-first-launch` does nothing."
            )
    elif force_first_launch or (
        not config_folder
        and (
            not os.path.exists(VAR_TO_DIR["CONFIG"])
            or len(os.listdir(VAR_TO_DIR["CONFIG"])) == 0
        )
    ):
        from rovr.first_launch import FirstLaunchApp

        FirstLaunchApp(can_exit=force_first_launch).run()

    if force_first_launch:
        return

    # start separate thread for platform to cache
    platproc = Process(target=platform.system)
    platproc.start()

    from rovr.functions.utils import set_nested_value
    from rovr.variables.constants import config

    for feature_path in with_features:
        set_nested_value(cast(dict, config), feature_path, True)

    for feature_path in without_features:
        set_nested_value(cast(dict, config), feature_path, False)

    if not sys.stdout.isatty():
        sys.__backup__stdout__ = sys.__stdout__
        sys.__backup__stderr__ = sys.__stderr__
        sys.__backup__stdin__ = sys.__stdin__

    from rovr.app import Application

    # __backup__std***__ for future
    if chooser_file == "__stdout__":
        if hasattr(sys, "__backup__stdout__"):
            chooser_file = sys.__backup__stdout__
        else:
            chooser_file = sys.__stdout__
    elif chooser_file == "__stderr__":
        if hasattr(sys, "__backup__stderr__"):
            chooser_file = sys.__backup__stderr__
        else:
            chooser_file = sys.__stderr__

    if cwd_file == "__stdout__":
        if hasattr(sys, "__backup__stdout__"):
            cwd_file = sys.__backup__stdout__
        else:
            cwd_file = sys.__stdout__
    elif cwd_file == "__stderr__":
        if hasattr(sys, "__backup__stderr__"):
            cwd_file = sys.__backup__stderr__
        else:
            cwd_file = sys.__stderr__

    if sys.stdout.isatty():
        Application(
            startup_path=path,
            cwd_file=cwd_file if cwd_file else None,
            chooser_file=chooser_file if chooser_file else None,
            show_keys=show_keys,
            tree_dom=tree_dom,
            force_crash_in=force_crash_in,
        ).run()
    elif force_tty:
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
                    startup_path=path,
                    cwd_file=cwd_file if cwd_file else None,
                    chooser_file=chooser_file if chooser_file else None,
                    show_keys=show_keys,
                    tree_dom=tree_dom,
                    force_crash_in=force_crash_in,
                ).run()
        finally:
            sys.__stdout__ = sys.stdout = sys.__backup__stdout__
            sys.__stderr__ = sys.stderr = sys.__backup__stderr__
            sys.__stdin__ = sys.stdin = sys.__backup__stdin__
    else:
        print(
            "Error: rovr needs a TTY to run in application.",
        )
    platproc.join()


if __name__ == "__main__":
    from rovr import main

    main()
