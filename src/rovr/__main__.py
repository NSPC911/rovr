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
        "--config-file",
        "-c",
        "config_file",
        type=str,
        default=None,
        help="Specify a custom config file path.",
    )
    @click.argument("path", type=str, required=False, default="")
    def main(
        with_features: list[str],
        without_features: list[str],
        config_path: bool,
        show_version: bool,
        path: str,
        config_file: str,
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

        if config_file:
            from rovr.functions.config import load_config

            global config
            config = load_config(config_file)

        for feature_path in with_features:
            set_nested_value(config, feature_path, True)

        for feature_path in without_features:
            set_nested_value(config, feature_path, False)

        from rovr.app import Application

        # TODO: Need to move this 'path' in the config dict, or a new runtime_config dict
        # Eventually there will be many options coming via arguments, but we cant keep sending all of
        # them via this Application's __init__ function here
        Application(watch_css=True, startup_path=path).run()

except KeyboardInterrupt:
    pass
