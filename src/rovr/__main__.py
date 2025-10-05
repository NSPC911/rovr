try:
    import click

    from rovr.functions.path import normalise
    from rovr.functions.utils import pprint, set_nested_value
    from rovr.variables.constants import config
    from rovr.variables.maps import VAR_TO_DIR

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
        "config_path",
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
    @click.argument("path", type=str, required=False, default="")
    def main(
        with_features: list[str],
        without_features: list[str],
        config_path: bool,
        show_version: bool,
        cwd_file: str,
        chooser_file: str,
        path: str,
    ) -> None:
        """A post-modern terminal file explorer"""

        if config_path:
            pprint(
                f"[cyan]Config Path[/cyan]: [pink]{normalise(VAR_TO_DIR['CONFIG'])}[/pink]"
            )
            return
        elif show_version:
            pprint("v0.3.0")
            return

        for feature_path in with_features:
            set_nested_value(config, feature_path, True)

        for feature_path in without_features:
            set_nested_value(config, feature_path, False)

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
