try:
    from os import environ

    import rich_click as click
    from rich import box
    from rich.console import Console
    from rich.table import Table

    pprint = Console().print

    click.rich_click.USE_RICH_MARKUP = True
    click.rich_click.USE_MARKDOWN = False
    click.rich_click.SHOW_ARGUMENTS = True
    click.rich_click.GROUP_ARGUMENTS_OPTIONS = False
    click.rich_click.MAX_WIDTH = 88
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

    global is_dev
    textual_flags = set(environ.get("TEXTUAL", "").split(","))
    # both flags exist if ran with `textual run --dev`
    is_dev = {"debug", "devtools"}.issubset(textual_flags)

    @click.command(help="A post-modern terminal file explorer")
    @click.option(
        "--mode",
        "mode",
        multiple=False,
        type=str,
        default="",
        help="Activate a preset mode defined in config (e.g., 'gui').",
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
        help="Write chosen file(s) (newline-separated) to this file on exit.",
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
    @click.option_panel("Config", options=["--mode", "--with", "--without"])
    @click.option_panel("Paths", options=["--chooser-file", "--cwd-file"])
    @click.option_panel(
        "Miscellaneous", options=["--version", "--config-path", "--help"]
    )
    @click.option_panel("Dev", options=["--show-keys", "--tree-dom"])
    @click.argument("path", type=str, required=False, default="")
    @click.rich_config({"show_arguments": True})
    def main(
        mode: str,
        with_features: list[str],
        without_features: list[str],
        show_config_path: bool,
        show_version: bool,
        cwd_file: str,
        chooser_file: str,
        show_keys: bool,
        path: str,
        tree_dom: bool,
    ) -> None:
        """A post-modern terminal file explorer"""
        from rovr.variables.maps import VAR_TO_DIR

        if show_config_path:
            from pathlib import Path

            def _normalise(location: str | bytes) -> str:
                from os import path

                return (
                    str(path.normpath(location)).replace("\\", "/").replace("//", "/")
                )

            table = Table(title="", border_style="blue", box=box.ROUNDED)
            table.add_column("type")
            table.add_column("path")
            path_config = Path(VAR_TO_DIR["CONFIG"])
            if path_config.is_relative_to(Path.home()):
                config_path = "~/" + _normalise(
                    str(path_config.relative_to(Path.home()))
                )
            else:
                config_path = path_config
            table.add_row("[cyan]custom config[/]", f"{config_path}/config.toml")
            table.add_row("[yellow]pinned folders[/]", f"{config_path}/pins.json")
            table.add_row("[hot_pink]custom styles[/]", f"{config_path}/style.tcss")
            table.add_row("[grey69]persistent state[/]", f"{config_path}/state.toml")
            pprint(table)
            return
        elif show_version:

            def _get_version() -> str:
                """Get version from package metadata

                Returns:
                    str: Current version
                """
                from importlib.metadata import PackageNotFoundError, version

                try:
                    return version("rovr")
                except PackageNotFoundError:
                    return "master"

            pprint(f"rovr version [cyan]v{_get_version()}[/]")
            return

        from rovr.functions.config import apply_mode
        from rovr.functions.utils import set_nested_value
        from rovr.variables.constants import config

        if mode:
            apply_mode(config, mode)

        for feature_path in with_features:
            set_nested_value(config, feature_path, True)

        for feature_path in without_features:
            set_nested_value(config, feature_path, False)

        from rovr.app import Application

        # TODO: Need to move this 'path' in the config dict, or a new runtime_config dict
        # Eventually there will be many options coming via arguments, but we cant keep sending all of
        # them via this Application's __init__ function here
        Application(
            startup_path=path,
            cwd_file=cwd_file if cwd_file else None,
            chooser_file=chooser_file if chooser_file else None,
            show_keys=show_keys,
            tree_dom=tree_dom,
            mode=mode,
        ).run()

except KeyboardInterrupt:
    pass
