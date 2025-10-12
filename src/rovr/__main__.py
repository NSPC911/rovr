try:
    import rich_click as click
    from rich import box
    from rich.table import Table

    from rovr.functions.path import normalise
    from rovr.functions.utils import pprint, set_nested_value
    from rovr.variables.constants import config
    from rovr.variables.maps import VAR_TO_DIR

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

    @click.command(help="A post-modern terminal file explorer")
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
    @click.option_panel("Config", options=["--with", "--without"])
    @click.option_panel("Paths", options=["--chooser-file", "--cwd-file"])
    @click.option_panel(
        "Miscellaneous", options=["--version", "--config-path", "--help"]
    )
    @click.argument("path", type=str, required=False, default="")
    @click.rich_config({"show_arguments": True})
    def main(
        with_features: list[str],
        without_features: list[str],
        show_config_path: bool,
        show_version: bool,
        cwd_file: str,
        chooser_file: str,
        path: str,
    ) -> None:
        """A post-modern terminal file explorer"""

        for feature_path in with_features:
            set_nested_value(config, feature_path, True)

        for feature_path in without_features:
            set_nested_value(config, feature_path, False)

        if show_config_path:
            from pathlib import Path

            table = Table(title="", border_style="blue", box=box.ROUNDED)
            table.add_column("type")
            table.add_column("path")
            path_config = Path(VAR_TO_DIR["CONFIG"])
            if path_config.is_relative_to(Path.home()):
                config_path = "~/" + normalise(
                    str(path_config.relative_to(Path.home()))
                )
            else:
                config_path = path_config
            table.add_row("[cyan]custom config[/]", f"{config_path}/config.toml")
            table.add_row("[yellow]pinned folders[/]", f"{config_path}/pins.json")
            table.add_row("[hot_pink]custom styles[/]", f"{config_path}/style.tcss")
            if config["settings"]["cd_on_quit"]:
                table.add_row(
                    "[green]path saved on quit[/]",
                    f"{config_path}/rovr_cd_on_quit",
                )
            pprint(table)
            return
        elif show_version:
            pprint("v0.3.0")
            return

        from rovr.app import Application

        # TODO: Need to move this 'path' in the config dict, or a new runtime_config dict
        # Eventually there will be many options coming via arguments, but we cant keep sending all of
        # them via this Application's __init__ function here
        Application(
            watch_css=True,
            startup_path=path,
            cwd_file=cwd_file if cwd_file else None,
            chooser_file=chooser_file if chooser_file else None,
        ).run()

except KeyboardInterrupt:
    pass
